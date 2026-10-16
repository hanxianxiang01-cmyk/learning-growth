#!/usr/bin/env python3
"""QA-ITEM-01 R2 六画像 120 次真实非 Pin 回归驱动（R2 裁决 §六.6）。

vs 第一轮 Q2 驱动的变化（对齐 FE-1453/1454/1452v2 新策略）：
- **不再需要 Bootstrap**：冷启动 auto 应直接出题（ITEM01-01 修复复验点）；
  探针（0094 保持的对照需求已并入 A 画像首请求）单列记录、不与 120 混合统计；
- trace 对账升级：predicted vs 实发比对 rvid/ability **且** policy 三元组
  （selection_reason/is_new_ability/new_ability_source）——新策略全字段追踪；
- 每请求落账 selection_reason/引入事件 → R2 硬门槛核算：
  无依据重复率（重复但 reason∉{remediation_review,pool_exhausted}=0%）、
  观察指标（总重复率/不同题覆盖率/合理复习比例）；
- 真实答题剧本沿用六画像语义（正确/错误/高提示/复习倾向），零直写 Mastery。

用法（外层按画像启动后端并绑定 QA_CHILD_ID + SELECTION_TRACE_ENABLED=true）：
  PROFILE_ID=0088 python qa_item01_r2_driver.py --phase prehist|main
"""
import argparse
import collections
import hashlib
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
A_ID = os.environ["PROFILE_ID"]
CHILD = f"00000000-0000-0000-0000-00000000{A_ID}"
DBU = os.environ["DATABASE_URL"].replace("+psycopg", "")
OUTDIR = os.environ["R2_OUT"]
os.makedirs(OUTDIR, exist_ok=True)

# 独立重算器（recompute 三态；驱动内主要用答案，留作答案可信自检）
sys.path.insert(0, os.path.join(OUTDIR, "_lib"))


def db(sql, params=()):
    import psycopg
    with psycopg.connect(DBU) as c:
        return c.execute(sql, params).fetchall()


def call(method, path, body=None):
    cmd = ["curl", "-s", "--noproxy", "*", "-X", method, BASE + path]
    if body is not None:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(body)]
    raw = subprocess.run(cmd, capture_output=True, text=True).stdout
    try:
        return json.loads(raw)
    except Exception:
        return {"_raw": raw[:300]}


_ap = argparse.ArgumentParser()
_ap.add_argument("--phase", required=True)
args, _ = _ap.parse_known_args()
LOG = open(f"{OUTDIR}/{A_ID}_{args.phase}.jsonl", "a")


def log(o):
    o["ts"] = datetime.now(timezone.utc).isoformat()
    LOG.write(json.dumps(o, ensure_ascii=False) + "\n")


def new_session():
    return call("POST", "/v1/learning/sessions",
                {"child_id": CHILD, "subject": "math", "requested_minutes": 15})["session_id"]


def answer_of(rvid):
    v = db("select content from resource_version where resource_version_id=%s", (rvid,))[0]
    ct = v[0] if isinstance(v[0], dict) else json.loads(v[0])
    return str(ct.get("answer"))


def submit(sid, tid, ans, hint, tag):
    sub = str(uuid.UUID(bytes=hashlib.sha256(f"{sid}|{tid}|{tag}".encode()).digest()[:16]))
    env = {"schema_version": "2.0", "type": "numeric", "ui_revision": "v1",
           "answer": str(ans), "workspaces": [{"workspace_id": "main", "data": {}}],
           "interaction_events": []}
    return call("POST", "/v1/learning/attempts",
                {"child_id": CHILD, "task_instance_id": tid, "attempt_no": 1,
                 "response": env, "used_hint_levels": [hint], "submission_id": sub})


# ---- 画像预历史（与第一轮同语义，走真实答题）----
PREHIST = {
    "0088": [],                                       # A' 零基础（冷启动即被测点）
    "0089": [("app_rel", "correct", 0)] * 6 + [("app_cond", "correct", 2)] * 1,  # B'
    "0090": [("app_rd", "wrong", 0)] * 3,            # C' 连续错误
    "0091": [("app_model", "correct", 3)] * 4,       # D' 高提示依赖
    "0092": [("app_rel", "correct", 0)] * 3,         # E' 重复暴露观察
    "0093": [("app_strat", "correct", 0)] * 2,       # F' 改 strat（transfer 观察项不入自动引入，稀疏画像换 strat 验受控）
}


def build_prehist():
    for ab, mode, hint in PREHIST.get(A_ID, []):
        sid = new_session()
        # R2：显式 ability_id 仅用于**建预历史**（=挑战卡语义，属合法显式通道），
        # 不再是冷启动绕过——主链 120 请求全 auto
        t = call("POST", "/v1/learning/tasks/next",
                {"child_id": CHILD, "session_id": sid, "subject": "math", "ability_id": ab})
        tid = t.get("task_instance_id")
        if not tid:
            log({"op": "prehist_skip", "ab": ab, "reason": t.get("reason")})
            continue
        ans = answer_of(t["resource_version_id"])
        val = ans if mode == "correct" else "-999999"
        r = submit(sid, tid, val, hint, f"pre-{ab}-{mode}")
        log({"op": "prehist_attempt", "ab": ab, "mode": mode, "hint": hint,
             "correct": r.get("correct"), "tid": str(tid)[:8]})
    print(f"预历史完成 {A_ID}")


def main_requests():
    """正式 20 请求（4 session × 5）**全 auto 非 Pin**；冷启动首请求=修复复验点。"""
    seen_rids = collections.Counter()
    reasons = collections.Counter()
    n_assigned = n_empty = mismatch_trace = 0
    for s_idx in range(4):
        sid = new_session()
        for q_idx in range(5):
            tr = call("GET", f"/v1/learning/selection-trace?child_id={CHILD}&session_id={sid}")
            pred_obj = tr.get("predicted_selected") or {}
            pred = pred_obj.get("resource_version_id")
            pred_pol = tr.get("predicted_policy") or {}
            t = call("POST", "/v1/learning/tasks/next",
                     {"child_id": CHILD, "session_id": sid, "subject": "math"})
            tid = t.get("task_instance_id")
            act = t.get("resource_version_id")
            outcome = "assigned" if tid else ("empty_pool" if t.get("reason") else "error")
            pol = t.get("strategy_policy") or {}
            rec = {"op": "r2_request", "session_idx": s_idx, "q_idx": q_idx,
                   "mode": "auto", "outcome": outcome, "reason": t.get("reason"),
                   "ability": t.get("ability_id"), "difficulty": t.get("difficulty"),
                   "rvid": str(act)[:8] if act else None,
                   "selection_reason": pol.get("selection_reason"),
                   "is_new_ability": pol.get("is_new_ability"),
                   "new_ability_source": pol.get("new_ability_source"),
                   "fit_band": pol.get("fit_band")}
            if tid:
                n_assigned += 1
                m = (str(act) == str(pred)) if pred else False
                pm = (pred_pol.get("selection_reason") == pol.get("selection_reason")
                      and pred_pol.get("is_new_ability") == pol.get("is_new_ability")) if pred_pol else None
                rec["trace_match"] = m
                rec["trace_policy_match"] = pm
                if not m or pm is False:
                    mismatch_trace += 1
                # resource 级曝光记账（换版本绕不过的口径自己也要算）
                rid = db("select resource_id from resource_version where resource_version_id=%s", (act,))[0][0]
                seen_rids[str(rid)] += 1
                reasons[pol.get("selection_reason") or "?"] += 1
                ans = answer_of(act)
                hint = 3 if A_ID == "0091" else 0
                wrong = A_ID == "0090" and q_idx % 2 == 0
                r = submit(sid, tid, ans if not wrong else "-999999", hint, f"m{s_idx}-{q_idx}")
                rec["attempt_correct"] = r.get("correct")
            else:
                n_empty += 1
                rec["trace_pred_when_empty"] = bool(pred)
                # 冷启动探针单列语义：A' 画像首请求若空池 → P0 复发实锤
                if s_idx == 0 and q_idx == 0:
                    rec["cold_start_gate"] = "FAIL_EMPTY_ON_FIRST_REQUEST"
            log(rec)
    summary = {"op": "r2_profile_summary", "profile": A_ID,
               "assigned": n_assigned, "empty": n_empty,
               "trace_mismatch": mismatch_trace,
               "unique_resources": len(seen_rids), "total": n_assigned,
               "reasons": dict(reasons)}
    log(summary)
    print(f"R2 主链 {A_ID}: {n_assigned}/20 assigned, trace_mismatch={mismatch_trace}")


if __name__ == "__main__":
    if args.phase == "prehist":
        build_prehist()
    else:
        main_requests()
    LOG.close()
