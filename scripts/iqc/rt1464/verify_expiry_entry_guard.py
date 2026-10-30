#!/usr/bin/env python3
"""FE-1466 Q07 §二：失效任务提交入口守卫——目标环境定向复验（可复跑）。

两类显式执行模式（用户 2026-10-21 终审 §四 执行约定）：

  --no-write（默认，只读核查）
      只做只读 SQL 盘点；A–E 五个场景都需要真实提交，一律标
      SKIPPED_NOT_RUN，verdict=NOT_RUN_READ_ONLY。只读跑一遍不能冒充已验证。
  --allow-write（显式授权 QA 写入验证）
      允许对 QA 通道真实提交；每次写请求登记进 write_actions。

四类断言（均需写入授权）：

  A. NEW-SUB-EXPIRED   失效任务 + 新 submission_id        → 200 且 expired=true、
                                                          attempt_id=null、evidence_id=null、
                                                          correct=null、next_action=RETRY/task_expired
  B. REPLAY-EXACT      失效任务 + 历史 submission_id 同内容 → 200 重放同 attempt_id，不新增 attempt/证据
  C. CONFLICT-409      失效任务 + 历史 submission_id 异内容 → 409（不得被 expired 掩盖）
  D. NEW-REPLAY-EXPIRED 失效任务 + 新 submission_id 但
                        (task, attempt_no) 命中历史 V1 轨       → 200 重放（旧轨语义保持）
  E. CONTROL-NORMAL    正常 assigned 任务照常判分（不受守卫影响）

每类前后统计 attempt / mastery_evidence / learning_event 三表计数与
task.status，断言"零新增写入"或"重放不新增"。产物落
scripts/iqc/rt1464/FE1466_expiry_entry_reverify.json
（只读模式自动加 _readonly 后缀，不覆盖既有写验证证据）。

用法：
  # 只读核查（默认，安全）
  DATABASE_URL=postgresql://... python scripts/iqc/rt1464/verify_expiry_entry_guard.py
  # 显式授权 QA 写入验证
  DATABASE_URL=postgresql://... python scripts/iqc/rt1464/verify_expiry_entry_guard.py --allow-write
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone

import psycopg

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exec_mode import ExecMode, add_mode_args, resolve_mode  # noqa: E402

TABLES = ("attempt", "mastery_evidence", "learning_event")


def _db_url() -> str:
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        sys.exit("缺少 DATABASE_URL（psycopg 用，非 +psycopg 方言）")
    return raw.replace("postgresql+psycopg://", "postgresql://")


def _snapshot(conn, task_id: str) -> dict:
    snap = {}
    for t in TABLES:
        col = "task_instance_id"
        snap[t] = conn.execute(
            f"select count(*) from {t} where {col} = %s", (task_id,)
        ).fetchone()[0]
    snap["task_status"] = conn.execute(
        "select status from task_instance where task_instance_id = %s", (task_id,)
    ).fetchone()[0]
    return snap


def _evidence_for_attempt(conn, attempt_id: str) -> int:
    return conn.execute(
        "select count(*) from mastery_evidence where attempt_id = %s", (attempt_id,)
    ).fetchone()[0]


def _events_for_attempt(conn, attempt_id: str) -> int:
    return conn.execute(
        "select count(*) from learning_event where attempt_id = %s", (attempt_id,)
    ).fetchone()[0]


def _pick_cancelled(conn, *, want_attempts: int):
    """挑一条 cancelled 任务：want_attempts=None 表示 0 条历史；否则 >=1 条且返回其历史。"""
    if want_attempts == 0:
        row = conn.execute(
            """
            select t.task_instance_id
            from task_instance t
            left join attempt a on a.task_instance_id = t.task_instance_id
            where t.status = 'cancelled'
            group by 1 having count(a.attempt_id) = 0
            order by 1 limit 1
            """
        ).fetchone()
        return (row[0], []) if row else (None, [])

    row = conn.execute(
        """
        select t.task_instance_id
        from task_instance t
        left join attempt a on a.task_instance_id = t.task_instance_id
        where t.status = 'cancelled'
        group by 1 having count(a.attempt_id) >= 1
        order by count(a.attempt_id) desc, 1 limit 1
        """
    ).fetchone()
    if not row:
        return None, []
    tid = row[0]
    attempts = conn.execute(
        """
        select attempt_id, attempt_no, response, correct, submission_id
        from attempt where task_instance_id = %s order by attempt_no
        """,
        (tid,),
    ).fetchall()
    return tid, attempts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default=os.environ.get("API_BASE", "http://127.0.0.1:8000"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--assign-proof", action="store_true",
                    help="额外证明正常任务分支仍可判分（会真实答题一次，QA child only；"
                         "仅在 --allow-write 下生效）")
    add_mode_args(ap)
    args = ap.parse_args()
    mode: ExecMode = resolve_mode(args)

    base_out = args.out or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "FE1466_expiry_entry_reverify.json",
    )
    out_path = mode.default_out(base_out) if not args.out else base_out
    results: list[dict] = []
    ok_all = True

    def record(name, passed, detail):
        nonlocal ok_all
        # 只读模式：任何 None（未执行）都不算通过，且整轮 verdict 不得为 PASS。
        if passed is None:
            ok_all = False
        else:
            ok_all = ok_all and passed
        results.append({"case": name, "passed": passed, **detail})

    with psycopg.connect(_db_url()) as conn:
        conn.autocommit = True

        # ================= 只读模式：仅盘点样本，不做任何提交 =================
        if not mode.allows_write:
            tid_a, _ = _pick_cancelled(conn, want_attempts=0)
            tid_h, attempts = _pick_cancelled(conn, want_attempts=1)
            sample = {
                "cancelled_zero_history": str(tid_a) if tid_a else None,
                "cancelled_with_history": str(tid_h) if tid_h else None,
                "history_attempt_count": len(attempts),
                "history_has_submission_id": bool(attempts and attempts[0][4]),
            }
            for case, why in (
                ("A-NEW-SUB-EXPIRED", "需对 cancelled 任务发起一次真实提交"),
                ("B-REPLAY-EXACT", "需以历史 submission_id 发起真实重放提交"),
                ("C-CONFLICT-409", "需以历史 submission_id + 异内容发起真实提交"),
                ("D-V1-TRACK-REPLAY", "需以 (task, attempt_no) 发起真实 V1 轨提交"),
                ("E-CONTROL-NORMAL", "需对 assigned 任务真实答题一次"),
            ):
                results.append(mode.skip(case, why + "；当前为只读模式（--no-write）",
                                         sample_hint=sample))
            ok_all = False
            conn_ready = False
        else:
            conn_ready = True

        if conn_ready:
            # ================= 写入授权模式：原五场景 =================
            # ---------- A. 新提交进失效任务 → 受控 expired ----------
            tid_a, _ = _pick_cancelled(conn, want_attempts=0)
            if tid_a is None:
                record("A-NEW-SUB-EXPIRED", False, {"error": "无 cancelled 且零历史任务样本"})
            else:
                before = _snapshot(conn, tid_a)
                sub = uuid.uuid4()
                status, body = mode.guarded_post(args.api, "/v1/learning/attempts", {
                    "task_instance_id": str(tid_a),
                    "attempt_no": 1,
                    "submission_id": str(sub),
                    "response": {"answer": "0"},
                })
                after = _snapshot(conn, tid_a)
                passed = (
                    status == 200
                    and body.get("expired") is True
                    and body.get("attempt_id") is None
                    and body.get("evidence_id") is None
                    and body.get("correct") is None
                    and (body.get("next_action") or {}).get("type") == "RETRY"
                    and (body.get("next_action") or {}).get("policy_id") == "task_expired"
                    and before == after
                    and after["task_status"] == "cancelled"
                )
                record("A-NEW-SUB-EXPIRED", passed, {
                    "task_instance_id": str(tid_a),
                    "submission_id": str(sub),
                    "http_status": status,
                    "body": body,
                    "before": before,
                    "after": after,
                })

        # ---------- 取一条有历史的 cancelled 任务（B/C/D 共用） ----------
            tid_h, attempts = _pick_cancelled(conn, want_attempts=1)
            if not attempts:
                record("B-C-D-NO-SAMPLE", False, {"error": "无带历史 attempt 的 cancelled 任务"})
            else:
                hist = attempts[0]
                hist_attempt_id = str(hist[0])
                hist_attempt_no = int(hist[1])
                hist_response = hist[2]
                hist_sub = hist[4]

                # ---------- B. 精确重放（同 submission_id 同内容）→ 不新增 ----------
                if hist_sub is None:
                    record("B-REPLAY-EXACT", False, {
                        "reason": "样本历史 attempt 无 submission_id（V1 轨），B 用下一条样本",
                    })
                else:
                    before = _snapshot(conn, tid_h)
                    status, body = mode.guarded_post(args.api, "/v1/learning/attempts", {
                        "task_instance_id": str(tid_h),
                        "attempt_no": hist_attempt_no,
                        "submission_id": str(hist_sub),
                        "response": hist_response,
                    })
                    after = _snapshot(conn, tid_h)
                    passed = (
                        status == 200
                        and body.get("attempt_id") == hist_attempt_id
                        and before == after
                        and body.get("expired") is not True
                    )
                    record("B-REPLAY-EXACT", passed, {
                        "task_instance_id": str(tid_h),
                        "submission_id": str(hist_sub),
                        "http_status": status,
                        "replayed_attempt_id": body.get("attempt_id"),
                        "expected_attempt_id": hist_attempt_id,
                        "before": before,
                        "after": after,
                    })

                    # ---------- C. 同 submission_id 异内容 → 409 ----------
                    before_c = _snapshot(conn, tid_h)
                    alt = {"answer": "__different__"}
                    if isinstance(hist_response, dict) and "answer" in hist_response:
                        alt = {**hist_response, "answer": "__different__"}
                    status_c, body_c = mode.guarded_post(args.api, "/v1/learning/attempts", {
                        "task_instance_id": str(tid_h),
                        "attempt_no": hist_attempt_no,
                        "submission_id": str(hist_sub),
                        "response": alt,
                    })
                    after_c = _snapshot(conn, tid_h)
                    record("C-CONFLICT-409", status_c == 409 and before_c == after_c, {
                        "task_instance_id": str(tid_h),
                        "submission_id": str(hist_sub),
                        "http_status": status_c,
                        "detail": str(body_c.get("detail", ""))[:160],
                        "before": before_c,
                        "after": after_c,
                    })

                # ---------- D. 无 submission_id 但 (task, attempt_no) 命中 → V1 重放 ----------
                before_d = _snapshot(conn, tid_h)
                status_d, body_d = mode.guarded_post(args.api, "/v1/learning/attempts", {
                    "task_instance_id": str(tid_h),
                    "attempt_no": hist_attempt_no,
                    "response": hist_response,
                })
                after_d = _snapshot(conn, tid_h)
                record("D-V1-TRACK-REPLAY", (
                    status_d == 200
                    and body_d.get("attempt_id") == hist_attempt_id
                    and before_d == after_d
                ), {
                    "task_instance_id": str(tid_h),
                    "attempt_no": hist_attempt_no,
                    "http_status": status_d,
                    "replayed_attempt_id": body_d.get("attempt_id"),
                    "expected_attempt_id": hist_attempt_id,
                    "before": before_d,
                    "after": after_d,
                })

            # ---------- E. 正常 assigned 任务不受守卫影响（对照） ----------
            # 注意：本场景会真实写入一条 Attempt（可能带 Evidence）。它只证明
            # "守卫没把正常任务误判成 expired"，**不能**承担"替代题正确完成"的
            # 结论——判对与否取决于题面，脚本不保证 correct=true。
            row = conn.execute(
                """
                select x.task_instance_id, x.attempt_no_hint from (
                  select t.task_instance_id,
                         coalesce(max(a.attempt_no), 0) + 1 as attempt_no_hint
                  from task_instance t
                  left join attempt a on a.task_instance_id = t.task_instance_id
                  where t.status = 'assigned'
                    and t.child_id = '00000000-0000-0000-0000-000000000099'
                  group by 1
                  having coalesce(max(a.attempt_no), 0) = 0
                  order by 1 limit 1
                ) x
                """
            ).fetchone()
            if not row:
                record("E-CONTROL-NORMAL", None, {
                    "skipped": "SKIPPED_NO_SAMPLE",
                    "reason": "无 assigned 且零 attempt 的 QA child(0099) 任务可用",
                })
            else:
                tid_e, ano = row
                status_e, body_e = mode.guarded_post(args.api, "/v1/learning/attempts", {
                    "task_instance_id": str(tid_e),
                    "attempt_no": ano,
                    "submission_id": str(uuid.uuid4()),
                    "response": {"answer": "0"},
                })
                record("E-CONTROL-NORMAL", status_e == 200 and body_e.get("expired") is not True, {
                    "task_instance_id": str(tid_e),
                    "http_status": status_e,
                    "correct": body_e.get("correct"),
                    "expired": body_e.get("expired"),
                    "wrote_attempt": body_e.get("attempt_id") is not None,
                    "note": "对照项：不要求判对，只要求守卫不放行到 expired 分支；"
                            "本场景属写动作（真实 Attempt/Evidence），不计入'零新增'",
                })

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "api": args.api,
        "verdict": ("PASS" if ok_all else "FAIL") if mode.allows_write
                   else mode.verdict_when_all_skipped,
        "mode": mode.record(),
        "cases": results,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    for r in results:
        flag = {True: "PASS", False: "FAIL", None: "SKIP"}[r["passed"]]
        print(f"[{flag}] {r['case']}")
        for k in ("http_status", "detail", "before", "after", "skipped", "reason"):
            if k in r:
                print(f"        {k}: {json.dumps(r[k], ensure_ascii=False)}")
    print(f"\nmode={mode.name}  write_actions={len(mode.write_actions)}  "
          f"verdict={payload['verdict']}  out={out_path}")
    # 只读模式返回 0（核查本身成功），但 verdict 明确是 NOT_RUN_READ_ONLY。
    return 0 if (ok_all or not mode.allows_write) else 1


if __name__ == "__main__":
    raise SystemExit(main())