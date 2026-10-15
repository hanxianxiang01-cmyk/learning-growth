"""QA-ITEM-01 Q5：判分/典型错误/非法输入三类场景（对象=Q2 真实命中的 29 题）。

每题四场景：
S1 正确作答（answer=独立预期值，process data 空）→ 期望 correct=True 无诊断
S2 典型错误·无过程数据（wrong + workspaces data 全空）→ no_process_data 观察
S3 典型错误·带伪造过程（wrong + workspaces[0].data 有值）→ 无观察支持 → observation_only
S4 非法输入：(a) answer 缺失 (b) answer=None 字面 (c) response 非契约结构 → 受控拒绝/不判分，不污染
诊断分级：DIAGNOSIS_MATCH / GENERIC_FEEDBACK / DIAGNOSIS_MISMATCH / UNVERIFIED
"""
import hashlib, json, os, subprocess, sys, uuid
from datetime import datetime, timezone
from collections import Counter

BASE = "http://127.0.0.1:8000"
CHILD = "00000000-0000-0000-0000-000000000087"
DBU = os.environ["DATABASE_URL"].replace("+psycopg", "")
OUT = "/Users/hanxianxiang/WorkBuddy/2026-09-24-10-25-54/output/qa_item01"
LOG = open(f"{OUT}/q5_scenarios.jsonl", "w")


def log(o):
    o["ts"] = datetime.now(timezone.utc).isoformat()
    LOG.write(json.dumps(o, ensure_ascii=False) + "\n")


def call(method, path, body=None):
    cmd = ["curl", "-s", "--noproxy", "*", "-X", method, BASE + path, "-w", "\n__C__%{http_code}"]
    if body is not None:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(body)]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    btxt, _, code = out.rpartition("\n__C__")
    try:
        return int(code.strip()), json.loads(btxt)
    except Exception:
        return int(code.strip()), {"_raw": btxt[:200]}


def db(sql, params=()):
    import psycopg
    with psycopg.connect(DBU) as c:
        return c.execute(sql, params).fetchall()


sys.path.insert(0, "/tmp")
from recompute_lib import recompute

hits = json.load(open('/tmp/q2_hits.json'))
rows = db("""select rv.resource_version_id::text, r.ability_id, rv.content, rv.ui_schema, rv.error_models, r.title
            from resource_version rv join resource r using(resource_id) where rv.review_status='published'""")
by8 = {r[0][:8]: r for r in rows}
sid = call("POST", "/v1/learning/sessions", {"child_id": CHILD, "subject": "math", "requested_minutes": 60})[1]["session_id"]

results = []
for rvid8 in sorted(hits):
    r = by8[rvid8]
    full_rvid, ab, content, ui, em, title = r[0], r[1], r[2], r[3], r[4], r[5]
    content = content if isinstance(content, dict) else json.loads(content)
    ui = ui if isinstance(ui, dict) else json.loads(ui)
    ws = (ui.get("workspaces") or [{}])[0]
    expected = str(content.get("answer"))
    # 独立预期（复核器口径）：可重算题用自己算的值，其余回落 DB（已登记状态）
    m, rec = recompute(ws.get("renderer") or "v1", content)
    indep_ans = str(rec) if m in ("recompute", "rule") else expected
    indep = m in ("recompute", "rule")
    # 典型错误值：数字类 ±非零偏移；符号类翻号
    try:
        wrong_ans = str(int(float(expected)) + 10) if m != "sign" else ("加号" if "减" in expected else "减号")
    except Exception:
        wrong_ans = "ZZZ_WRONG"

    def new_task():
        code, t = call("POST", "/v1/learning/tasks/next", {"child_id": CHILD, "session_id": sid, "subject": "math", "pin_resource_version_id": full_rvid})
        return t

    def env_of(ans, data=None):
        return {"schema_version": "2.0", "type": (ws.get("renderer") or "numeric").replace("-", "_"),
                "ui_revision": ui.get("ui_revision", "v1"), "answer": ans,
                "workspaces": [{"workspace_id": ws.get("workspace_id", "main"), "data": data or {}}],
                "interaction_events": []}

    for scen, ans, data, expect in [
        ("S1_correct", indep_ans, None, "correct_true_no_diagnosis"),
        ("S2_wrong_noprocess", wrong_ans, None, "wrong+no_process_data_obs"),
        ("S3_wrong_withprocess", wrong_ans, {"touched": True}, "wrong_observation_only"),
        ("S4a_no_answer_field", None, None, "no_judge_or_reject"),
    ]:
        t = new_task()
        tid = t.get("task_instance_id")
        if not tid:
            log({"op": "skip", "rvid": rvid8, "scen": scen, "reason": t.get("reason")}); continue
        env = env_of(ans, data)
        if scen == "S4a_no_answer_field":
            env.pop("answer")
        sub = str(uuid.UUID(bytes=hashlib.sha256(f"{sid}|{tid}|{scen}".encode()).digest()[:16]))
        code, resp = call("POST", "/v1/learning/attempts", {"child_id": CHILD, "task_instance_id": tid,
            "attempt_no": 1, "response": env, "used_hint_levels": [0], "submission_id": sub})
        d = resp.get("diagnosis") if isinstance(resp, dict) else None
        # 独立判分核对
        got_correct = resp.get("correct") if isinstance(resp, dict) else None
        if scen == "S1_correct":
            verdict = "PASS" if got_correct is True and not d else f"FAIL:{got_correct},{bool(d)}"
        elif scen in ("S2_wrong_noprocess", "S3_wrong_withprocess"):
            # 诊断分级
            if got_correct is not False:
                verdict = f"FAIL:judge={got_correct}"
            else:
                if isinstance(d, dict):
                    st = d.get("status"); top = d.get("top_level_code")
                    obs_codes = [o.get("code") for o in (d.get("observations") or [])]
                    if scen == "S2_wrong_noprocess":
                        verdict = ("GENERIC_FEEDBACK" if top is None and "no_process_data" in obs_codes else
                                   ("DIAGNOSIS_MATCH" if top else f"UNEXPECTED:{st}"))
                    else:
                        verdict = ("UNVERIFIED:no_obs" if not obs_codes else f"CANDIDATES:{top}")
                else:
                    verdict = "NO_DIAGNOSIS_OBJ"
        else:  # S4a
            verdict = "UNJUDGED" if got_correct is None else f"POLLUTED:correct={got_correct}" if code == 200 else f"REJECTED:{code}"
        results.append({"rvid": rvid8, "ab": ab, "scen": scen, "http": code, "correct": got_correct,
                        "diagnosis_status": (d or {}).get("status") if isinstance(d, dict) else None,
                        "top_level_code": (d or {}).get("top_level_code") if isinstance(d, dict) else None,
                        "observations": [o.get("code") for o in ((d or {}).get("observations") or [])] if isinstance(d, dict) else None,
                        "independent_expected": indep, "verdict": verdict})
        log({"op": "q5", "rvid": rvid8, "ab": ab, "scen": scen, "resp": resp if code != 200 else {k: resp.get(k) for k in ("correct", "diagnosis", "next_action")}})

json.dump(results, open(f"{OUT}/q5_results.json", "w"), ensure_ascii=False, indent=1)
print("场景总数:", len(results))
print("按 verdict:", dict(Counter(r["verdict"].split(":")[0] for r in results)))
print("按场景:", {s: dict(Counter(r["verdict"].split(':')[0] for r in results if r["scen"] == s)) for s in ("S1_correct", "S2_wrong_noprocess", "S3_wrong_withprocess", "S4a_no_answer_field")})
diags = [r for r in results if r["scen"] == "S2_wrong_noprocess"]
print("S2 诊断状态分布:", dict(Counter(str(r["diagnosis_status"]) for r in diags)))
print("S2 top_level_code 非空数:", sum(1 for r in diags if r["top_level_code"]))
LOG.close()
