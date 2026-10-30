#!/usr/bin/env python3
"""FE-1466 Q07 复核补正：**「新 submission 借旧 attempt_no」绕过负例**（真实 DB）。

用户复核意见（2026-10-21 §三）：A 场景提交前 attempt 数为 0、B 是精确重放、
C 是同 ID 异内容、D 是 V1 重放——四者都没有直接呈现这条绕过路径。

负例定义（预注册，先写判据再执行）：
  已失效任务 + **已有历史 Attempt** + **新 submission_id** + **旧 attempt_no**
  →
    a) 必须返回受控失效 expired=true
    b) attempt_id 必须为 null —— 不得把旧 Attempt 冒充本次提交结果
    c) correct / evidence_id 必须为 null —— 不得重新判分
    d) 不得新增 attempt / mastery_evidence / learning_event（前后计数相等）
    e) 原历史 Attempt 行逐字段不变（不得被覆盖/改写）

对照（正向）：同 submission_id + 同内容 → 必须重放（即使 attempt_no 不同），
证明命中依据确实是 submission_id 而非 attempt_no 巧合。

自检：全程无新增业务数据；样本任务终态显式记录并复位（本次不再"静默复位"，
复位前后状态与 RVID 归属一并落盘——这是上一轮锁测缺失的项）。

用法：
  DATABASE_URL=postgresql://... python scripts/iqc/rt1464/verify_bypass_negative_case.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

import psycopg

QA_CHILD = "00000000-0000-0000-0000-000000000099"
FOUR = {"place-value", "shape-canvas", "money-board", "pattern-board"}


def _db_url() -> str:
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        sys.exit("缺少 DATABASE_URL")
    return raw.replace("postgresql+psycopg://", "postgresql://")


def _post(api: str, path: str, payload: dict, timeout: float = 40.0):
    req = urllib.request.Request(
        api.rstrip("/") + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return e.code, {"raw": raw.decode(errors="replace")}


def _counts(conn, tid: str) -> dict:
    return {
        "attempt": conn.execute(
            "select count(*) from attempt where task_instance_id=%s", (tid,)).fetchone()[0],
        "evidence": conn.execute(
            "select count(*) from mastery_evidence where task_instance_id=%s", (tid,)).fetchone()[0],
        "event": conn.execute(
            "select count(*) from learning_event where task_instance_id=%s", (tid,)).fetchone()[0],
    }


def _attempt_rows(conn, tid: str) -> list:
    return conn.execute("""
        select attempt_id::text, attempt_no, response::text, correct,
               submission_id::text
        from attempt where task_instance_id=%s order by attempt_no
    """, (tid,)).fetchall()


def _task_meta(conn, tid: str) -> dict:
    r = conn.execute("""
        select t.status, t.child_id::text, t.session_id::text,
               t.resource_version_id::text, rv.ui_schema, rv.review_status,
               s.status
        from task_instance t
        join resource_version rv using(resource_version_id)
        join learning_session s on s.session_id = t.session_id
        where t.task_instance_id=%s
    """, (tid,)).fetchone()
    if not r:
        return {}
    st, child, sess, rvid, ui, rvst, sst = r
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
        "task_status": st, "child": child, "session": sess,
        "session_status": sst, "rvid": rvid, "review_status": rvst,
        "renderers": rends, "has_process_constraint": pc,
        "evidence_targets": ev,
        "looks_like_current_exposure": bool(ev and (set(rends) & FOUR) and not pc),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default=os.environ.get("API_BASE", "http://127.0.0.1:8000"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out_path = args.out or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "FE1466_bypass_negative_case.json")

    steps, ok = [], True

    def step(name, passed, detail):
        nonlocal ok
        ok = ok and passed
        steps.append({"step": name, "passed": passed, **detail})
        flag = "PASS" if passed is True else ("SKIP" if passed is None else "FAIL")
        print(f"[{flag}] {name}")
        for k, v in detail.items():
            print(f"        {k}: {json.dumps(v, ensure_ascii=False)}")

    url = _db_url()
    with psycopg.connect(url) as c:
        # 选一条 cancelled 任务，**必须已有历史 Attempt**，且该 attempt 有 submission_id
        row = c.execute("""
            select t.task_instance_id::text
            from task_instance t
            join attempt a on a.task_instance_id = t.task_instance_id
            where t.status = 'cancelled' and a.submission_id is not null
            group by 1 order by 1 limit 1
        """).fetchone()
        if not row:
            sys.exit("无 cancelled 且带 submission_id 历史 Attempt 的样本")
        tid = row[0]
        meta = _task_meta(c, tid)

    print(f"样本任务 {tid}")
    print(f"  RVID={meta['rvid']} review_status={meta['review_status']} "
          f"renderers={meta['renderers']}")
    print(f"  当前口径暴露={meta['looks_like_current_exposure']} "
          f"has_process_constraint={meta['has_process_constraint']}")

    with psycopg.connect(url) as c:
        hist = _attempt_rows(c, tid)
        before = _counts(c, tid)
        # 取历史 attempt_no（用于构造"借旧 attempt_no"）与"不同 attempt_no"（正对照）
        old_no = hist[0][1]
        old_sub = hist[0][4]
        old_resp = json.loads(hist[0][2])
        max_no = max(h[1] for h in hist)

    # ---------- 负例：新 submission + 旧 attempt_no ----------
    new_sub = str(uuid.uuid4())
    status, body = _post(args.api, "/v1/learning/attempts", {
        "task_instance_id": tid,
        "attempt_no": old_no,            # 借用旧 attempt_no
        "submission_id": new_sub,        # 但是新提交
        "response": {"answer": "__probe_bypass__"},
    })
    with psycopg.connect(url) as c:
        after = _counts(c, tid)
        hist_after = _attempt_rows(c, tid)

    passed_neg = (
        status == 200
        and body.get("expired") is True
        and body.get("attempt_id") is None
        and body.get("correct") is None
        and body.get("evidence_id") is None
        and (body.get("next_action") or {}).get("policy_id") == "task_expired"
        and before == after
        and hist == hist_after          # 历史行逐字段不变
        and body.get("attempt_id") != hist[0][0]
    )
    step("N1-NEW-SUB-REUSE-OLD-ATTEMPT-NO-NOT-BYPASSED", passed_neg, {
        "sample_task": tid, "old_attempt_no": old_no, "new_submission_id": new_sub,
        "http_status": status,
        "expired": body.get("expired"),
        "attempt_id": body.get("attempt_id"),
        "must_not_equal_historical": hist[0][0],
        "correct": body.get("correct"),
        "evidence_id": body.get("evidence_id"),
        "next_action": body.get("next_action"),
        "counts_before": before, "counts_after": after,
        "history_unchanged": hist == hist_after,
    })

    # ---------- 正对照：同 submission + 同内容 → 重放（attempt_no 故意给最大+1） ----------
    status2, body2 = _post(args.api, "/v1/learning/attempts", {
        "task_instance_id": tid,
        "attempt_no": max_no + 1,        # attempt_no 不匹配历史
        "submission_id": old_sub,        # 但 submission 命中
        "response": old_resp,
    })
    with psycopg.connect(url) as c:
        after2 = _counts(c, tid)
    step("N2-REPLAY-KEYS-ON-SUBMISSION-NOT-ATTEMPT-NO", (
        status2 == 200 and body2.get("attempt_id") == hist[0][0]
        and before == after2 and body2.get("expired") is not True
    ), {
        "historical_submission_id": old_sub,
        "request_attempt_no": max_no + 1,
        "expected_attempt_id": hist[0][0],
        "replayed_attempt_id": body2.get("attempt_id"),
        "http_status": status2,
        "counts_before": before, "counts_after": after2,
    })

    # ---------- 负例2：新 submission + 全新 attempt_no ----------
    status3, body3 = _post(args.api, "/v1/learning/attempts", {
        "task_instance_id": tid,
        "attempt_no": max_no + 2,
        "submission_id": str(uuid.uuid4()),
        "response": {"answer": "__probe_new__"},
    })
    with psycopg.connect(url) as c:
        after3 = _counts(c, tid)
    step("N3-NEW-SUB-NEW-ATTEMPT-NO-REJECTED", (
        status3 == 200 and body3.get("expired") is True
        and body3.get("attempt_id") is None and before == after3
    ), {
        "http_status": status3, "expired": body3.get("expired"),
        "counts_before": before, "counts_after": after3,
    })

    # ---------- 终态：样本任务状态 + 归属（补上一轮缺失项） ----------
    with psycopg.connect(url) as c:
        final = _task_meta(c, tid)
    step("N4-SAMPLE-TERMINAL-STATE-RECORDED", final.get("task_status") == "cancelled", {
        "sample_task": tid,
        "final_task_status": final.get("task_status"),
        "rvid": final.get("rvid"),
        "review_status": final.get("review_status"),
        "renderers": final.get("renderers"),
        "looks_like_current_exposure": final.get("looks_like_current_exposure"),
        "note": "本脚本不改任务状态、不新增业务数据；样本是否可提交由守卫在运行时拒绝"
                "（N1/N3 已实证拒绝），不靠状态名推断",
    })

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "api": args.api,
        "purpose": "复核补正：新 submission 借旧 attempt_no 的绕过负例（用户 2026-10-21 §三）",
        "verdict": "PASS" if ok else "FAIL",
        "steps": steps,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\nverdict={payload['verdict']}  out={out_path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())