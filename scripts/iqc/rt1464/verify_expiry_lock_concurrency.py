#!/usr/bin/env python3
"""FE-1466 Q07 §二末段：失效批处理 × 作答提交 的**真实并发互斥**证明。

用户裁决要求「不能只靠顺序执行演示推断并发边界」。本脚本用两连接
真实争抢 PostgreSQL 行锁，确定性地证明下述时序不变量：

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

自检：脚本全程不新增任何 attempt/evidence/event。开始前与结束后对全局
三表做计数比对，任何增量即 FAIL（防止测出数据污染）。

用法：
  DATABASE_URL=postgresql://... python scripts/iqc/rt1464/verify_expiry_lock_concurrency.py \
      [--api http://127.0.0.1:8000] [--out <path>]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import uuid
from datetime import datetime, timezone

import psycopg
import urllib.error
import urllib.request


def _db_url() -> str:
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        sys.exit("缺少 DATABASE_URL")
    return raw.replace("postgresql+psycopg://", "postgresql://")


def _post(api: str, path: str, payload: dict, timeout: float = 60.0):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        api.rstrip("/") + path, data=body,
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


def _global_counts(conn) -> dict:
    out = {}
    for t in ("attempt", "mastery_evidence", "learning_event"):
        out[t] = conn.execute(f"select count(*) from {t}").fetchone()[0]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default=os.environ.get("API_BASE", "http://127.0.0.1:8000"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    out_path = args.out or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "FE1466_expiry_lock_concurrency.json",
    )
    url = _db_url()
    steps: list[dict] = []
    ok = True

    def step(name, passed, detail):
        nonlocal ok
        ok = ok and passed
        steps.append({"step": name, "passed": passed, **detail})
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
        for k, v in detail.items():
            print(f"        {k}: {json.dumps(v, ensure_ascii=False)}")

    # 选一条 assigned 且零 attempt 的 QA(0099) 任务——验证后必须复位回 assigned
    with psycopg.connect(url) as probe:
        row = probe.execute("""
            select t.task_instance_id::text, t.child_id::text
            from task_instance t
            left join attempt a on a.task_instance_id = t.task_instance_id
            where t.status = 'assigned'
              and t.child_id = '00000000-0000-0000-0000-000000000099'
            group by 1,2 having count(a.attempt_id) = 0
            order by 1 limit 1
        """).fetchone()
        if not row:
            sys.exit("无 assigned/零 attempt 的 QA(0099) 任务可用作并发样本")
        tid, child = row
        g0 = _global_counts(probe)

    inv = psycopg.connect(url, autocommit=False)   # 失效侧（显式事务）
    submitted_at = {}
    result_holder: dict = {}
    released = threading.Event()

    try:
        # ---------- T0：失效侧抢锁 ----------
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
        # 复位样本任务（本脚本不产生业务数据，仅借用一条空任务做锁实验）
        try:
            if not inv.closed:
                inv.rollback()
        except Exception:  # noqa: BLE001
            pass
        inv.close()
        with psycopg.connect(url, autocommit=True) as fix:
            fix.execute(
                "update task_instance set status='assigned' where task_instance_id=%s and status='cancelled'",
                (tid,))
            g1 = _global_counts(fix)
        restored = fix_status = None
        with psycopg.connect(url) as chk:
            fix_status = chk.execute(
                "select status from task_instance where task_instance_id=%s", (tid,)).fetchone()[0]
            g1 = _global_counts(chk)
        step("T6-NO-DATA-LEAK", g0 == g1, {
            "global_before": g0, "global_after": g1,
            "sample_task_reset_to": fix_status,
        })

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "api": args.api,
        "verdict": "PASS" if ok else "FAIL",
        "invariant": "失效批处理（UPDATE task_instance）与作答提交（SELECT ... FOR UPDATE）"
                     "在 PostgreSQL 行锁上互斥串行；失效提交后到达的提交只能读到 cancelled。",
        "steps": steps,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\nverdict={payload['verdict']}  out={out_path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())