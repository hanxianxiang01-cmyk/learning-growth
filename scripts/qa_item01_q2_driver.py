"""QA-ITEM-01 Q2 驱动：单画像 4 session × 5 请求 = 20 次非 Pin 选题 + 真实作答。

用法（外层 bash 负责按画像重启后端绑定 QA_CHILD_ID）：
  PROFILE_ID=0081 python q2_driver.py --phase prehist|main
trace 对账语义：每次请求先 trace（只读预测）→ tasks/next 实发 → 比较记账。
预历史（画像真实状态建立）走真实答题：正确/错误/高提示按画像剧本，零直写 Mastery。
"""
import argparse, hashlib, json, os, subprocess, sys, uuid
from datetime import datetime, timezone

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
A_ID = os.environ["PROFILE_ID"]  # 如 0081
CHILD = f"00000000-0000-0000-0000-00000000{A_ID}"
DBU = os.environ["DATABASE_URL"].replace("+psycopg", "")
OUTDIR = os.environ["Q2_OUT"]
os.makedirs(OUTDIR, exist_ok=True)
sys.path.insert(0, "/tmp")
from recompute_lib import recompute  # noqa: E402


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
        return {"_raw": raw[:200]}


import argparse as _ap0
_ph = _ap0.ArgumentParser(); _ph.add_argument("--phase", required=True)
_ph0, _ = _ph.parse_known_args()
LOG = open(f"{OUTDIR}/{A_ID}_{_ph0.phase}.jsonl", "a")
def log(o):
    o["ts"] = datetime.now(timezone.utc).isoformat()
    LOG.write(json.dumps(o, ensure_ascii=False) + "\n")


def new_session():
    return call("POST", "/v1/learning/sessions", {"child_id": CHILD, "subject": "math", "requested_minutes": 15})["session_id"]


def answer_of(rvid):
    v = db("select content, ui_schema from resource_version where resource_version_id=%s", (rvid,))[0]
    ct = v[0] if isinstance(v[0], dict) else json.loads(v[0])
    ui = v[1] if isinstance(v[1], dict) else json.loads(v[1])
    rend = ((ui.get("workspaces") or [{}])[0] if isinstance(ui, dict) else {}).get("renderer") or "v1"
    return str(ct.get("answer")), rend, ui


def submit(sid, tid, ans, hint, tag, correct_expect=None):
    sub = str(uuid.UUID(bytes=hashlib.sha256(f"{sid}|{tid}|{tag}".encode()).digest()[:16]))
    env = {"schema_version": "2.0", "type": "numeric", "ui_revision": "v1", "answer": str(ans),
           "workspaces": [{"workspace_id": "main", "data": {}}], "interaction_events": []}
    return call("POST", "/v1/learning/attempts", {"child_id": CHILD, "task_instance_id": tid,
            "attempt_no": 1, "response": env, "used_hint_levels": [hint], "submission_id": sub})


# ---- 画像剧本：预历史（真实答题建立）----
PREHIST = {
    "0081": [],  # A 零基础：无预历史（冷启动即被测点）
    "0082": [("app_rel", "correct", 0)] * 6 + [("app_cond", "correct", 2)] * 1,
    "0083": [("app_rd", "wrong", 0)] * 3,
    "0084": [("app_model", "correct", 3)] * 4,
    "0085": [("app_rel", "correct", 0)] * 3,
    "0086": [("app_transfer", "correct", 0)] * 2,
}

def build_prehist():
    for ab, mode, hint in PREHIST[A_ID]:
        sid = new_session()
        t = call("POST", "/v1/learning/tasks/next", {"child_id": CHILD, "session_id": sid, "subject": "math", "ability_id": ab})
        tid = t.get("task_instance_id")
        if not tid:
            log({"op": "prehist_skip", "ab": ab, "reason": t.get("reason")}); continue
        ans, rend, ui = answer_of(t["resource_version_id"])
        val = ans if mode == "correct" else "-999999"
        r = submit(sid, tid, val, hint, f"pre-{ab}-{mode}-{hint}")
        log({"op": "prehist_attempt", "ab": ab, "mode": mode, "hint": hint, "correct": r.get("correct"), "tid": str(tid)[:8]})
    print(f"预历史完成 {A_ID}")

BOOT_ABILITY = {"0081": "app_rel", "0082": "app_rel", "0083": "app_rd",
                "0084": "app_model", "0085": "app_rel", "0086": "app_transfer"}

def main_requests():
    total = 0
    # 冷启动 auto 空池取证（A 已 20/20）：每画像先打 1 次 auto 空池样本（若仍空）
    sid0 = new_session()
    tr0 = call("GET", f"/v1/learning/selection-trace?child_id={CHILD}&session_id={sid0}")
    t0 = call("POST", "/v1/learning/tasks/next", {"child_id": CHILD, "session_id": sid0, "subject": "math"})
    log({"op": "cold_start_probe", "has_state_rows": bool(tr0.get("per_ability")),
         "auto_outcome": "assigned" if t0.get("task_instance_id") else "empty_pool",
         "reason": t0.get("reason")})
    for s_idx in range(4):
        sid = new_session()
        for q_idx in range(5):
            tr = call("GET", f"/v1/learning/selection-trace?child_id={CHILD}&session_id={sid}")
            pred = (tr.get("predicted_selected") or {}).get("resource_version_id")
            body = {"child_id": CHILD, "session_id": sid, "subject": "math"}
            # 首请求且无状态行 → 前端挑战卡片语义（合法显式 ability_id），其余 auto
            if not tr.get("per_ability"):
                body["ability_id"] = BOOT_ABILITY[A_ID]
                mode = "explicit_bootstrap"
            else:
                mode = "auto"
            t = call("POST", "/v1/learning/tasks/next", body)
            tid = t.get("task_instance_id"); act = t.get("resource_version_id")
            outcome = "assigned" if tid else ("empty_pool" if t.get("reason") else "error")
            match = (pred is not None and str(act) == str(pred)) if tid else None
            rec = {"op": "q2_request", "session_idx": s_idx, "q_idx": q_idx, "outcome": outcome,
                   "reason": t.get("reason"), "ability": t.get("ability_id"),
                   "difficulty": t.get("difficulty"), "rvid": str(act)[:8] if act else None,
                   "trace_pred": str(pred)[:8] if pred else None,
                   "request_mode": mode,
                   "trace_vs_actual": ("MATCH" if match else "MISMATCH") if tid else "N/A(未出题)",
                   "trace_pool": {p["ability_id"]: p["eligible_pool_size"] for p in tr.get("per_ability", [])},
                   "trace_bands": {p["ability_id"]: p["fit_band"] for p in tr.get("per_ability", [])}}
            log(rec); total += 1
            if tid:
                ans, rend, ui = answer_of(act)
                hint = 0
                if A_ID == "0084":
                    hint = 3  # D 画像主链保持高提示依赖
                wrong = A_ID == "0083" and q_idx % 2 == 0  # C 画像主链仍穿插真实错误
                r = submit(sid, tid, ans if not wrong else "-999999", hint, f"m{s_idx}-{q_idx}")
                log({"op": "q2_attempt", "session_idx": s_idx, "q_idx": q_idx, "correct": r.get("correct"),
                     "hint": hint, "diagnosis": bool(r.get("diagnosis")), "next_action": (r.get("next_action") or {}).get("type")})
    print(f"主链 20 请求完成 {A_ID}（总账 {total}）")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--phase", required=True)
    a = ap.parse_args()
    if a.phase == "prehist":
        build_prehist()
    else:
        main_requests()
    LOG.close()
