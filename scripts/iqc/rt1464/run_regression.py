#!/usr/bin/env python3
"""P1 复审 23 项运行回归执行器（裁决§五：QA 账号定向回归，核心问题=只填目标数字不操作是否判对/产正向证据）。

方法：pin→attempt 提交"合法操作/非法操作/空操作+答案"三态 response → 记录
Response/Judge/Evidence 三层（不只 correct=true/false）→ 与审查预期对比：
  PASS_RUNTIME           = 行为符合题目契约
  CONTRACT_DEFECT        = 契约声称的过程校验后端未执行（登记缺陷，不算测试失败）
  STATIC_VERIFIED/STATIC = 标签/Hint 顺序类=静态核对项
隔离：仅 QA child 0001…0099（QA_DATA_HYGIENE R1）；不触碰真实儿童数据。
"""
import json
import uuid
import urllib.request

API = "http://127.0.0.1:8000"
CHILD = "00000000-0000-0000-0000-000000000099"

def post(path, data):
    req = urllib.request.Request(API+path, json.dumps(data).encode(),
        {"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def pin(rvid):
    s = post("/v1/learning/sessions", {"child_id": CHILD, "subject": "math", "requested_minutes": 15})
    t = post("/v1/learning/tasks/next", {"child_id": CHILD, "session_id": s["session_id"],
        "subject": "math", "pin_resource_version_id": rvid})
    assert t.get("task_instance_id"), t
    wsid = (t["ui_schema"]["workspaces"][0].get("workspace_id") or "main")
    return t["task_instance_id"], wsid

def submit(rvid, ws_data, answer, hints=None):
    tid, wsid = pin(rvid)
    resp = {"schema_version": "2.0", "type": "attempt",
            "workspaces": [{"workspace_id": wsid, "data": ws_data}],
            "answer": {"value": answer}}
    out = post("/v1/learning/attempts", {"task_instance_id": tid, "attempt_no": 1,
        "response": resp, "used_hint_levels": hints or [],
        "submission_id": str(uuid.uuid4())})
    return {"tid": tid, "correct": out.get("correct"), "next_action": out.get("next_action"),
            "process_violation": out.get("process_violation"),
            "attempt_id": out.get("attempt_id"), "stored_evidence": bool(out)}

R = []
def run(rid, rvid, label, ws_data, answer, expect, kind, hints=None):
    o = submit(rvid, ws_data, answer, hints)
    obs = o["correct"]
    if kind == "runtime":
        # expect: (期望correct, 期望过程语义)
        exp_c, semantic = expect
        if obs == exp_c and (exp_c is not True or semantic == "operation_valid"):
            verdict = "PASS_RUNTIME"
        elif exp_c is True and obs is True and semantic == "process_should_not_be_credited":
            verdict = "CONTRACT_DEFECT"   # 只凭答案判对=过程校验缺失
        elif obs == exp_c:
            verdict = "PASS_RUNTIME"
        else:
            verdict = f"UNEXPECTED(obs={obs},exp={exp_c})"
    else:
        verdict = "STATIC"
    R.append({"id": rid, "rvid": rvid[:8], "label": label, "observed_correct": obs,
              "process_violation": o["process_violation"], "expected": str(expect),
              "verdict": verdict, "attempt_id": o["attempt_id"], "task": o["tid"]})
    print(f"{rid} [{rvid[:8]}] {label[:36]:38s} correct={str(obs):5s} → {verdict}")

PAT="1723d78a-44c9-419d-82d4-7a9f6a48520a"
M35="2ff4a288-9db7-4945-9ff8-db00eccaacdb"; M45="334962af-db9c-432e-9aa9-2d1cf5d5509d"
M15="579786c0-0dd8-442a-ac41-4a26b9fb4f48"; M25="9ab5d643-bd5b-4a77-8f22-f963d2b2ad84"
SHA="971b1f5e-6c4c-4fd2-ba92-e64c99ce9d3c"; PV="9d0d3a7e-57f6-4602-ab4d-1ead6affb26e"

# RT-01 pattern：beads=[1,2] 合法 / [2,1] 非法 / [] 空操作
run("RT-01-01", PAT, "摆珠[黄,蓝]+12", {"beads":[1,2],"blanks_filled":[1,2]}, 12, (True,"operation_valid"), "runtime")
run("RT-01-02", PAT, "摆珠[蓝,黄]+12(相位错)", {"beads":[2,1],"blanks_filled":[2,1]}, 12, (True,"process_should_not_be_credited"), "runtime")
run("RT-01-03", PAT, "未摆珠直接填12", {"beads":[],"blanks_filled":[]}, 12, (True,"process_should_not_be_credited"), "runtime")
run("RT-01-04", PAT, "Hint 3 级后填12(独立性记账)", {"beads":[1,2]}, 12, (True,"independence_accounting"), "runtime", hints=[1,2,3])
# RT-02 money 35
run("RT-02-01", M35, "[10,10,10,5]+35", {"selected_denominations":[10,10,10,5],"total":35}, 35, (True,"operation_valid"), "runtime")
run("RT-02-01b", M35, "[5]*7+35", {"selected_denominations":[5]*7,"total":35}, 35, (True,"operation_valid"), "runtime")
run("RT-02-02", M35, "空选币+35", {"selected_denominations":[],"total":0}, 35, (True,"process_should_not_be_credited"), "runtime")
run("RT-02-02b", M35, "[50]总额≠35 仍填35", {"selected_denominations":[50],"total":50}, 35, (True,"process_should_not_be_credited"), "runtime")
# RT-03 money 45
run("RT-03-01", M45, "[10,10,10,10,5]+45", {"selected_denominations":[10,10,10,10,5],"total":45}, 45, (True,"operation_valid"), "runtime")
run("RT-03-02", M45, "[50]+45(超付)", {"selected_denominations":[50],"total":50}, 45, (True,"process_should_not_be_credited"), "runtime")
run("RT-03-03", M45, "空选币+45", {"selected_denominations":[],"total":0}, 45, (True,"process_should_not_be_credited"), "runtime")
# RT-04 money 15
run("RT-04-01", M15, "[10,5]+15", {"selected_denominations":[10,5],"total":15}, 15, (True,"operation_valid"), "runtime")
run("RT-04-02", M15, "空+15", {"selected_denominations":[],"total":0}, 15, (True,"process_should_not_be_credited"), "runtime")
run("RT-04-03", M15, "[50]+15", {"selected_denominations":[50],"total":50}, 15, (True,"process_should_not_be_credited"), "runtime")
run("RT-04-04", M15, "[10,10]错组合+15", {"selected_denominations":[10,10],"total":20}, 15, (True,"process_should_not_be_credited"), "runtime")
# RT-05 shape-canvas
RECT=[[0,0],[3,0],[3,2],[0,2]]
run("RT-05-01", SHA, "3×2 rect+6", {"vertices":RECT,"area":6,"right_angles":4}, 6, (True,"operation_valid"), "runtime")
run("RT-05-01b", SHA, "2×3 rect+6", {"vertices":[[0,0],[2,0],[2,3],[0,3]],"area":6,"right_angles":4}, 6, (True,"operation_valid"), "runtime")
run("RT-05-02", SHA, "无 vertices+6", {"vertices":[],"area":0}, 6, (True,"process_should_not_be_credited"), "runtime")
run("RT-05-03", SHA, "平行四边形(非直角)面积6+6", {"vertices":[[0,0],[3,0],[4,2],[1,2]],"area":6,"right_angles":0}, 6, (True,"process_should_not_be_credited"), "runtime")
# RT-06 money 25
run("RT-06-01", M25, "[10,10,5]+25", {"selected_denominations":[10,10,5],"total":25}, 25, (True,"operation_valid"), "runtime")
run("RT-06-01b", M25, "[5]*5+25", {"selected_denominations":[5]*5,"total":25}, 25, (True,"operation_valid"), "runtime")
run("RT-06-02", M25, "空+25", {"selected_denominations":[],"total":0}, 25, (True,"process_should_not_be_credited"), "runtime")
run("RT-06-03", M25, "[50]+25", {"selected_denominations":[50],"total":50}, 25, (True,"process_should_not_be_credited"), "runtime")
# RT-07 place-value
run("RT-07-01", PV, "slots[3,5,2]+352", {"slots":{"h":3,"t":5,"o":2}}, 352, (True,"operation_valid"), "runtime")
run("RT-07-02", PV, "slots[3,2,5]+352(卡位错)", {"slots":{"h":3,"t":2,"o":5}}, 352, (True,"process_should_not_be_credited"), "runtime")
run("RT-07-02b", PV, "slots 空+352", {"slots":{}}, 352, (True,"process_should_not_be_credited"), "runtime")
print("RT-07-03 app_rd 标签证据来源=静态核对（结论 JSON 已含）；RT-07-04 Hint 顺序=静态")
R.append({"id":"RT-07-03","rvid":PV[:8],"label":"app_rd 标签能力证据","verdict":"STATIC_REVIEW","expected":"见复核结论 JSON","observed_correct":None,"process_violation":None})
R.append({"id":"RT-07-04","rvid":PV[:8],"label":"四级 Hint 顺序(L3 泄关键卡位>L4)","verdict":"STATIC_REVIEW","expected":"见复核结论 JSON","observed_correct":None,"process_violation":None})

json.dump(R, open("rt1464_results.json","w"), ensure_ascii=False, indent=1)
from collections import Counter
print("\n汇总:", dict(Counter(x["verdict"] for x in R)))
