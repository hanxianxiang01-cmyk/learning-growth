#!/usr/bin/env python3
"""FE-1466 Q07 §二末段：失效批处理 × 作答提交 的**真实并发互斥**证明。

两类显式执行模式（用户 2026-10-21 终审 §四 执行约定）：

  --no-write（默认，只读核查）
      只读盘点候选样本与其归属（RVID/renderer/process_constraint/高风险口径），
      T0–T6 全部标 SKIPPED_NOT_RUN，verdict=NOT_RUN_READ_ONLY。
      **理由**：本测每一步都是写动作——T0 SELECT ... FOR UPDATE 会持锁
      阻塞他人，T3 UPDATE task_instance 改状态，收尾还要复位。它不是只读测试。
  --allow-write（显式授权 QA 写入验证）
      执行真实两连接争抢；锁、状态变更、收尾复位逐项登记进 write_actions。

真实并发时序（写入授权模式）：

  T0  invalidation 连接 BEGIN + SELECT ... FOR UPDATE（锁住目标 task）
  T1  并发发起 HTTP POST /v1/learning/attempts（另线程，新 submission_id）
  T2  断言提交请求在阻塞（pg_stat_activity 中 wait_event_type='Lock'，
      且此刻该 task 仍无新 attempt / 无新证据）→ 证明「未失效率先写入」
      不可能发生在失效提交之后
  T3  invalidation 连接 UPDATE status='cancelled' + COMMIT（释放锁）
  T4  阻塞的提交请求被放行 → 读到已提交的 cancelled → 返回
      expired=true / attempt_id=null / evidence_id=null，且三表零新增

判据（全部为硬断言）：
  - T2 时提交请求确实处于锁等待（不是"恰好很快跑完"）
  - T2 时 attempt/evidence/event 计数不变
  - T4 时响应为受控 expired，计数仍不变
  - 目标 task 状态在 T4 为 cancelled，且 attempt/evidence 零新增

自检：写入授权模式下全程不新增任何 attempt/evidence/event。开始前与结束后
对全局三表做计数比对，任何增量即 FAIL（防止测出数据污染）。注意三表计数
不变**不**等于"什么都没改"——任务状态变更与收尾复位单独记录在
status_before_reset / status_final / write_actions 里。

用法：
  # 只读核查（默认，安全）
  DATABASE_URL=postgresql://... python scripts/iqc/rt1464/verify_expiry_lock_concurrency.py
  # 显式授权 QA 写入验证
  DATABASE_URL=postgresql://... python scripts/iqc/rt1464/verify_expiry_lock_concurrency.py --allow-write
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

import psycopg

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exec_mode import ExecMode, add_mode_args, resolve_mode  # noqa: E402


def _db_url() -> str:
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        sys.exit("缺少 DATABASE_URL")
    return raw.replace("postgresql+psycopg://", "postgresql://")


def _post(api: str, path: str, payload: dict, timeout: float = 60.0):
    """并发侧的提交请求。

    2026-10-21 复审补正：本函数在 #124 改造 `_post`→`exec_mode` 时被删除，
    但调用点仍留着（submitter 线程里）。后果很隐蔽——submitter 的
    `except Exception` 会把 NameError 吞掉，只写进 result_holder["error"]，
    于是"并发提交"分支可能在**从未发出任何 HTTP 请求**的情况下走到收尾判定。

    现在保留为写模式的直连入口（写模式下才被调用；只读模式整段 T0-T6 SKIP，
    不会到达这里）。请求语义与原实现一致。
    """
    req = urllib.request.Request(
        api.rstrip("/") + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return e.code, {"raw": raw.decode(errors="replace")}


def _task_counts(conn, tid: str) -> dict:
    return {
        "attempt": conn.execute(
            "select count(*) from attempt where task_instance_id=%s", (tid,)).fetchone()[0],
        "evidence": conn.execute(
            "select count(*) from mastery_evidence where task_instance_id=%s", (tid,)).fetchone()[0],
        "event": conn.execute(
            "select count(*) from learning_event where task_instance_id=%s", (tid,)).fetchone()[0],
    }


def _task_meta(conn, tid: str) -> dict:
    """样本任务的完整归属（RVID/版本状态/renderer/会话）——复核补正。

    上一轮本脚本只记录 task_instance_id 与"已复位 assigned"，没有给出该任务
    关联的 RVID，导致无法判断"复位是否重新打开了旧风险通道"。本函数把归属
    一并落盘，并在收尾断言样本不属于四类高风险暴露口径。
    """
    r = conn.execute("""
        select t.status, t.child_id::text, t.session_id::text,
               t.resource_version_id::text, rv.review_status, rv.ui_schema,
               s.status
        from task_instance t
        join resource_version rv using(resource_version_id)
        join learning_session s on s.session_id = t.session_id
        where t.task_instance_id=%s
    """, (tid,)).fetchone()
    if not r:
        return {"exists": False}
    st, child, sess, rvid, rvst, ui, sst = r
    rends, pc = [], False
    for w in (ui or {}).get("workspaces") or []:
        if isinstance(w, dict):
            if w.get("renderer"):
                rends.append(w["renderer"])
            p = (w.get("config") or {}).get("process_constraint")
            if isinstance(p, dict) and p.get("mode"):
                pc = True
    rc = (ui or {}).get("response_contract") or {}
    ev = rc.get("evidence_targets")
    return {
        "exists": True, "task_status": st, "child": child, "session": sess,
        "session_status": sst, "rvid": rvid, "review_status": rvst,
        "renderers": rends, "has_process_constraint": pc, "evidence_targets": ev,
        # 四类高风险口径（与 exposure risk_note 同口径）+ 仍处于可下发状态
        "is_high_risk_channel": bool(
            ev and (set(rends) & {"place-value", "shape-canvas",
                                  "money-board", "pattern-board"})
            and not pc and rvst == "published"),
    }


def _global_counts(conn) -> dict:
    out = {}
    for t in ("attempt", "mastery_evidence", "learning_event"):
        out[t] = conn.execute(f"select count(*) from {t}").fetchone()[0]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default=os.environ.get("API_BASE", "http://127.0.0.1:8000"))
    ap.add_argument("--out", default=None)
    add_mode_args(ap)
    args = ap.parse_args()
    mode: ExecMode = resolve_mode(args)

    base_out = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "FE1466_expiry_lock_concurrency.json",
    )
    out_path = args.out or (base_out if mode.allows_write else mode.default_out(base_out))
    url = _db_url()
    steps: list[dict] = []
    ok = True

    def step(name, passed, detail):
        nonlocal ok
        if passed is None:
            ok = False
        else:
            ok = ok and passed
        steps.append({"step": name, "passed": passed, **detail})
        flag = {True: "PASS", False: "FAIL", None: "SKIP"}[passed]
        print(f"[{flag}] {name}")
        for k, v in detail.items():
            print(f"        {k}: {json.dumps(v, ensure_ascii=False)}")

    # 选样本：必须是 assigned 且零 attempt 的 QA(0099) 任务，**且优先非高风险资源**
    # （复核补正：上一轮任意取一条，未记录其 RVID，无法判断复位影响）。
    with psycopg.connect(url) as probe:
        row = probe.execute("""
            select x.task_instance_id::text, x.child_id::text from (
              select t.task_instance_id, t.child_id,
                     coalesce(max(a.attempt_no), 0) as mx
              from task_instance t
              left join attempt a on a.task_instance_id = t.task_instance_id
              where t.status = 'assigned'
                and t.child_id = '00000000-0000-0000-0000-000000000099'
              group by 1,2 having coalesce(max(a.attempt_no), 0) = 0
            ) x limit 40
        """).fetchall()
        if not row:
            sys.exit("无 assigned/零 attempt 的 QA(0099) 任务可用作并发样本")
        # 逐个检查归属，取第一条非高风险
        tid = child = None
        high_risk_candidates = 0
        for cand_id, cand_child in row:
            m = _task_meta(probe, cand_id)
            if not m.get("is_high_risk_channel"):
                tid, child = cand_id, cand_child
                break
            high_risk_candidates += 1
        if tid is None:
            sys.exit("40 条候选全属高风险口径——拒绝用高风险样本做锁实验")
        selected_meta = _task_meta(probe, tid)
        g0 = _global_counts(probe)

    # ================= 只读模式：只盘点候选与归属，不持锁、不改状态 =================
    if not mode.allows_write:
        for t in ("T0-INVALIDATION-HOLDS-LOCK", "T2-SUBMIT-BLOCKED-ON-LOCK",
                  "T3-INVALIDATION-COMMITS", "T4-RELEASED-EXPIRED-NO-WRITE",
                  "T5-ORDER-INVARIANT", "T6-NO-DATA-LEAK-AND-SAMPLE-ATTRIBUTION"):
            step(t, None, {
                "skipped": "SKIPPED_NOT_RUN",
                "reason": "本测每一步都是写动作（FOR UPDATE 持锁 / UPDATE 状态 / 收尾复位），"
                          "只读模式不执行；需 --allow-write 显式授权",
            })
        step("READONLY-SAMPLE-INVENTORY", True, {
            "candidates_examined": len(row),
            "high_risk_skipped": high_risk_candidates,
            "would_use_task": tid,
            "would_use_attribution": {
                "rvid": selected_meta.get("rvid"),
                "review_status": selected_meta.get("review_status"),
                "renderers": selected_meta.get("renderers"),
                "has_process_constraint": selected_meta.get("has_process_constraint"),
                "evidence_targets": selected_meta.get("evidence_targets"),
                "child": selected_meta.get("child"),
                "session": selected_meta.get("session"),
                "is_high_risk_channel": selected_meta.get("is_high_risk_channel"),
            },
            "global_counts_unchanged_probe": g0,
            "note": "只读模式仅做盘点：未持锁、未提交任何请求、未改任务状态。"
                    "本结果不构成并发互斥证据。",
        })
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "api": args.api,
            "verdict": mode.verdict_when_all_skipped,
            "mode": mode.record(),
            "invariant": "（未执行）失效批处理与作答提交的行锁互斥需 --allow-write 验证。",
            "steps": steps,
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\nmode={mode.name}  verdict={payload['verdict']}  out={out_path}")
        return 0

    inv = psycopg.connect(url, autocommit=False)   # 失效侧（显式事务）
    submitted_at = {}
    result_holder: dict = {}
    released = threading.Event()

    try:
        # ---------- T0：失效侧抢锁 ----------
        # 注意：这不是只读动作——FOR UPDATE 会阻塞本表的并发提交，必须在
        # write_actions 里如实登记（用户 §四 明文指出"锁测也不是只读测试"）。
        mode.note_write("row_lock", tid,
                        "SELECT ... FOR UPDATE 持有 task_instance 行锁（阻塞并发提交）")
        inv.execute("select status from task_instance where task_instance_id=%s for update", (tid,))
        t0_status = inv.execute(
            "select status from task_instance where task_instance_id=%s", (tid,)).fetchone()[0]
        step("T0-INVALIDATION-HOLDS-LOCK", t0_status == "assigned",
             {"task_instance_id": tid, "child": child, "status_under_lock": t0_status,
              "note": "FOR UPDATE 已持有，未提交"})

        def submitter():
            submitted_at["start"] = time.time()
            try:
                result_holder["status"], result_holder["body"] = _post(
                    args.api, "/v1/learning/attempts", {
                        "task_instance_id": tid,
                        "attempt_no": 1,
                        "submission_id": str(uuid.uuid4()),
                        "response": {"answer": "0"},
                    })
            except Exception as e:  # noqa: BLE001
                result_holder["error"] = repr(e)
            finally:
                submitted_at["end"] = time.time()
                released.set()

        th = threading.Thread(target=submitter, daemon=True)
        th.start()

        # ---------- T2：确认请求在等锁（不是已经跑完） ----------
        waiting = False
        deadline = time.time() + 12
        while time.time() < deadline:
            with psycopg.connect(url) as mon:
                hits = mon.execute("""
                    select count(*) from pg_stat_activity
                    where datname = current_database()
                      and wait_event_type = 'Lock'
                      and query ilike '%%for update%%'
                """).fetchone()[0]
            if hits >= 1 and not released.is_set():
                waiting = True
                break
            if released.is_set():
                break
            time.sleep(0.25)

        with psycopg.connect(url) as mon:
            mid = _task_counts(mon, tid)
            mid_status = mon.execute(
                "select status from task_instance where task_instance_id=%s", (tid,)).fetchone()[0]
        step("T2-SUBMIT-BLOCKED-ON-LOCK", waiting and mid == {"attempt": 0, "evidence": 0, "event": 0},
             {"lock_wait_observed": waiting,
              "request_finished_early": released.is_set(),
              "counts_while_blocked": mid, "status_while_blocked": mid_status,
              "note": "判据=请求未跑完且零写入；改写成 expired 不可能在此刻发生"})

        # ---------- T3：失效提交（UPDATE + COMMIT 放锁） ----------
        # 这不是"零变化"：任务状态被真实改写为 cancelled（收尾再复位）。
        mode.note_write("sql_dml", tid,
                        "UPDATE task_instance SET status='cancelled'（失效提交，真实状态变更）")
        inv.execute(
            "update task_instance set status='cancelled' where task_instance_id=%s", (tid,))
        inv.commit()
        commit_at = time.time()

        # ---------- T4：阻塞请求被放行 → 受控 expired ----------
        th.join(timeout=40)
        body = result_holder.get("body") or {}
        status = result_holder.get("status")
        with psycopg.connect(url) as mon:
            final = _task_counts(mon, tid)
            final_status = mon.execute(
                "select status from task_instance where task_instance_id=%s", (tid,)).fetchone()[0]

        passed_t4 = (
            status == 200
            and body.get("expired") is True
            and body.get("attempt_id") is None
            and body.get("evidence_id") is None
            and body.get("correct") is None
            and (body.get("next_action") or {}).get("policy_id") == "task_expired"
            and final == {"attempt": 0, "evidence": 0, "event": 0}
            and final_status == "cancelled"
        )
        step("T4-RELEASED-EXPIRED-NO-WRITE", passed_t4, {
            "http_status": status,
            "expired": body.get("expired"),
            "attempt_id": body.get("attempt_id"),
            "evidence_id": body.get("evidence_id"),
            "next_action": body.get("next_action"),
            "counts_after_release": final,
            "status_after_release": final_status,
            "elapsed_s": round((submitted_at.get("end", 0) - submitted_at.get("start", 0)), 2),
            "blocked_until_commit": submitted_at.get("end", 0) >= commit_at,
        })

        # 时序不变量：HTTP 结束时间不得早于失效 commit
        step("T5-ORDER-INVARIANT", submitted_at.get("end", 0) >= commit_at, {
            "submit_finished_at": submitted_at.get("end"),
            "invalidation_committed_at": commit_at,
            "note": "提交被放行严格晚于失效提交 → 不存在「失效后写入却成功」的窗口",
        })

    finally:
        # 收尾（复核补正）：不再"静默复位"。
        # 上一轮直接 update 回 assigned 却不记录 RVID，无法判断复位是否重开了
        # 旧风险通道。本次：①先取样本归属 ②若样本属四类高风险暴露口径，
        # 拒绝复位（保持 cancelled）并登记 ③否则复位并显式记录归属与理由。
        rollback_error = None
        try:
            if not inv.closed:
                inv.rollback()
        except Exception as e:  # noqa: BLE001
            # 不吞：收尾失败必须留痕。静默 pass 正是让「_post 未定义」这类
            # 缺陷躲过两轮复核的机制（宽泛 except 把 NameError 也吃了）。
            rollback_error = repr(e)
        inv.close()
        with psycopg.connect(url) as chk:
            meta = _task_meta(chk, tid)
            pre_reset_status = meta.get("task_status")
        high_risk = bool(meta.get("is_high_risk_channel"))
        if high_risk:
            reset_done = False
            reset_reason = ("样本属四类高风险暴露口径（evidence_targets ∧ renderer∈四类 "
                            "∧ 无 process_constraint ∧ published）——按纪律不复位，"
                            "保持 cancelled，避免锁测收尾重开旧通道")
        else:
            mode.note_write("state_restore", tid,
                            "UPDATE task_instance SET status='assigned'（锁测收尾复位）")
            with psycopg.connect(url, autocommit=True) as fix:
                fix.execute(
                    "update task_instance set status='assigned' "
                    "where task_instance_id=%s and status='cancelled'", (tid,))
            reset_done = True
            # 理由由实际归属数据生成（不写死，避免与实测值矛盾）
            why = []
            if not (set(meta.get("renderers") or []) & {"place-value", "shape-canvas",
                                                        "money-board", "pattern-board"}):
                why.append(f"renderer={meta.get('renderers') or '[]'} 不在四类")
            if not meta.get("evidence_targets"):
                why.append("无 evidence_targets 声明")
            if meta.get("review_status") != "published":
                why.append(f"review_status={meta.get('review_status')}")
            if meta.get("has_process_constraint"):
                why.append("已含 process_constraint")
            reset_reason = ("样本非高风险口径（" + "；".join(why) +
                            "）——复位为 assigned 属恢复原状，且该资源不构成 Q07 暴露通道")
        with psycopg.connect(url) as chk:
            meta_after = _task_meta(chk, tid)
            g1 = _global_counts(chk)
            final_counts = _task_counts(chk, tid)
        step("T6-NO-DATA-LEAK-AND-SAMPLE-ATTRIBUTION", g0 == g1, {
            "global_before": g0, "global_after": g1,
            "sample_task": tid,
            "sample_attribution": {
                "rvid": meta.get("rvid"),
                "review_status": meta.get("review_status"),
                "renderers": meta.get("renderers"),
                "has_process_constraint": meta.get("has_process_constraint"),
                "evidence_targets": meta.get("evidence_targets"),
                "session": meta.get("session"),
                "session_status": meta.get("session_status"),
                "child": meta.get("child"),
                "is_high_risk_channel": high_risk,
            },
            "status_before_reset": pre_reset_status,
            "reset_performed": reset_done,
            "status_final": meta_after.get("task_status"),
            "reset_reason": reset_reason,
            "final_counts_on_sample": final_counts,
            "rollback_error": rollback_error,
            "note": "三表计数不变只证明无新增作答/证据/事件；任务终态由 "
                    "status_before_reset/status_final 单独记录，不被计入'零变化'",
        })

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "api": args.api,
        "verdict": "PASS" if ok else "FAIL",
        "mode": mode.record(),
        "invariant": "失效批处理（UPDATE task_instance）与作答提交（SELECT ... FOR UPDATE）"
                     "在 PostgreSQL 行锁上互斥串行；失效提交后到达的提交只能读到 cancelled。",
        "concurrency_scope_note": (
            "本测覆盖单条 QA 样本上的失效批处理 × 单次提交。两次运行均通过只能说明"
            "该时序路径不存在绕过；不宜据此表述为「所有并发路径均不存在漏洞」——"
            "多任务批量失效、连接池重试、前端重放并发等路径未纳入本测范围。"
        ),
        "steps": steps,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\nverdict={payload['verdict']}  out={out_path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())