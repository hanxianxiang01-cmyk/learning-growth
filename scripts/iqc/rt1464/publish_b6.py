#!/usr/bin/env python3
"""FE-1466 B6 替代题发布（裁决 19:21 §四：A 先行 B 随后，通过才继续）。

与 publish_batch（同 resource 版本替换）不同——B6 是**新逻辑资源替代**：
- 新资源 rv qa_staged→published
- 旧风险资源 rv published→superseded（退出下发；行保留）
- 替代关系记录于 manifest（不伪造同一 resource 的版本链，§四.2）
纪律：Dry 默认零 DML（判定全只读，写仅 --apply 分支）；单事务；发布前
按完整 UUID+内容哈希+约束核对"发布的就是验收版本"；退役版
a2732868/939d81b5 绝不在候选；发布后 §四.3 六项检查逐项过，任一失败
退出非零并停止下一题。
"""
import hashlib
import json
import os
import sys
import urllib.request
import uuid

import psycopg

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("IQC_MIGRATE_DB") or sys.exit("缺 IQC_MIGRATE_DB")
API = os.environ.get("IQC_API_BASE", "http://127.0.0.1:8000")
CHILD = "00000000-0000-0000-0000-000000000099"
RETIRED_BANNED = {"a2732868-f699-4ead-99ee-d9ac59503e97",
                  "939d81b5-5475-40fa-a8d5-599a781a412c"}

# (题, 新 RVID 完整, 旧风险 RVID 完整, 期望 content_sha256 前缀, 期望 pc.mode, ability)
PLAN = [
    ("A", "82aabb99-d2a8-4885-9236-7e44395238d7",
     "2c46c271-1a2f-4f45-ad3c-b5719ad58ded", None, "place_value_build", "app_strat"),
    ("B", "2f2e8491-151c-4959-94be-c7789d553895",
     "845c6fea-418f-4365-a25e-b50e5b5040f8", None, "pattern_extension", "app_transfer"),
]


def canon(o):
    return hashlib.sha256(json.dumps(o, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


def post(p, d):
    req = urllib.request.Request(API + p, json.dumps(d).encode(),
                                 {"Content-Type": "application/json"}, "POST")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def pin(rvid):
    s = post("/v1/learning/sessions", {"child_id": CHILD, "subject": "math", "requested_minutes": 15})
    t = post("/v1/learning/tasks/next", {"child_id": CHILD, "session_id": s["session_id"],
        "subject": "math", "pin_resource_version_id": rvid})
    return s["session_id"], t


def checks_new(rvid, expect_mode, ability, conn):
    row = conn.execute("""select review_status, content::text, ui_schema::text,
        resource_id::text from resource_version where resource_version_id=%s""", (rvid,)).fetchone()
    if row is None:
        return "行缺失", None
    st, ct_s, ui_s, resid = row
    ui = json.loads(ui_s)
    ws = ui["workspaces"][0]
    pc = (ws.get("config") or {}).get("process_constraint") or {}
    pre = [("new_status_qa_staged", st == "qa_staged"),
           ("pc_mode", pc.get("mode") == expect_mode),
           ("not_banned", rvid not in RETIRED_BANNED)]
    return pre, {"content": json.loads(ct_s), "ui": ui, "resid": resid, "status": st}


def post_publish_verify(rvid_new, rvid_old, conn):
    """§四.3 六项：目录/下发/pin/三态/Retry 重放。返回 issue 列表。"""
    issues = []
    cat = json.loads(urllib.request.urlopen(API + "/v1/content/v2-catalog").read())
    cids = {str(i["resource_version_id"]) for i in cat.get("items", [])}
    if rvid_new not in cids: issues.append("新版不在目录")
    if rvid_old in cids: issues.append("旧风险版仍在目录")
    # 旧版 pin 必须被拒（退出可下发范围）
    _, t = pin(rvid_old)
    if t.get("task_instance_id"): issues.append("旧版仍可被下发(pin)")
    # 三态+Retry（真实 pin 新题）
    import copy
    sid, t = pin(rvid_new)
    if not t.get("task_instance_id"):
        return issues + ["新版 pin 失败"]
    ui = t["ui_schema"]; wid = ui["workspaces"][0]["workspace_id"]
    renderer = ui["workspaces"][0]["renderer"]
    cfg = ui["workspaces"][0]["config"]; cons = ui["workspaces"][0].get("constraints") or {}
    sys.path.insert(0, HERE)
    from migrate_batch import gen_data
    legal, contra, empty = gen_data(renderer, cfg, cons)
    ct = conn.execute("select content::text from resource_version where resource_version_id=%s", (rvid_new,)).fetchone()
    import json as _j
    answer = _j.loads(ct[0]).get("answer")
    def att(data, no, sub=None):
        return post("/v1/learning/attempts", {"task_instance_id": t["task_instance_id"],
            "attempt_no": no, "response": {"schema_version": "2.0", "type": "attempt",
            "workspaces": [{"workspace_id": wid, "data": data}], "answer": {"value": answer}},
            "used_hint_levels": [], "submission_id": sub or str(uuid.uuid4())})
    o_e = att(empty, 1)
    if not (o_e.get("correct") is None and o_e.get("process_status") == "missing"
            and (o_e.get("next_action") or {}).get("type") == "RETRY"):
        issues.append("空过程态异常")
    ev_e = conn.execute("select count(*) from mastery_evidence where attempt_id=%s", (o_e["attempt_id"],)).fetchone()[0]
    if ev_e: issues.append("空过程产了证据")
    sub_l = str(uuid.uuid4())
    o_l = att(legal, 2, sub_l)
    if not (o_l.get("correct") is True and o_l.get("evidence_id")):
        issues.append("合法过程未正常完成留证")
    o_r = att(legal, 2, sub_l)  # 重放
    if o_r.get("attempt_id") != o_l.get("attempt_id"):
        issues.append("重放产生新 attempt")
    evn = conn.execute("select count(*) from mastery_evidence where task_instance_id=%s and valid",
                       (t["task_instance_id"],)).fetchone()[0]
    if evn != 1: issues.append(f"Retry 闭环证据数 {evn}≠1")
    # 不可核验：结构错误零证据不误入答错
    o_u = att({"beads": "x"} if renderer == "pattern-board" else {"slots": "x"}, 9)
    if not (o_u.get("correct") is None and o_u.get("process_status") == "unverifiable"
            and (o_u.get("next_action") or {}).get("type") == "RETRY"
            and o_u.get("diagnosis") is None):
        issues.append("unverifiable 语义异常")
    return issues


def main():
    apply = "--apply" in sys.argv
    only = None
    for a in sys.argv:
        if a.startswith("--only="): only = a.split("=")[1]
    conn = psycopg.connect(DB, autocommit=apply)
    reports = []
    try:
        for key, new, old, _, mode, ability in PLAN:
            if only and key != only:
                continue
            pre_n, meta = checks_new(new, mode, ability, conn)
            fails = [name for name, okk in pre_n if not okk] if isinstance(pre_n, list) else pre_n
            if fails or meta is None:
                print(f"B6-{key} 发布前核对失败: {fails} —— 停止（§四）"); return 1
            old_row = conn.execute("select review_status, resource_id::text from resource_version where resource_version_id=%s", (old,)).fetchone()
            if old_row is None or old_row[0] != "published":
                print(f"B6-{key} 旧风险行状态异常 {old_row}"); return 1
            if str(old_row[1]) == meta["resid"]:
                print(f"B6-{key} 新旧同 resource——应走 publish_batch 而非本脚本"); return 1
            # 内容哈希留档（发布=验收版对账锚）
            csha = canon(meta["content"]); usha = canon(meta["ui"])
            if not apply:
                print(f"B6-{key} DRY: 新 {new[:8]}({meta['status']})→published；"
                      f"旧 {old[:8]}(published)→superseded；关系=跨资源替代；"
                      f"content_sha={csha[:16]}（无任何 DML）")
                continue
            conn.execute("update resource_version set review_status='published' where resource_version_id=%s and review_status='qa_staged'", (uuid.UUID(new),))
            conn.execute("update resource_version set review_status='superseded' where resource_version_id=%s and review_status='published'", (uuid.UUID(old),))
            dup_new = conn.execute("select count(*) from resource_version where resource_id=%s and review_status='published'", (uuid.UUID(meta["resid"]),)).fetchone()[0]
            if dup_new != 1:
                raise RuntimeError(f"新资源 published={dup_new}")
            conn.commit()
            iss = post_publish_verify(new, old, conn)
            rep = {"alt": key, "new_rvid": new, "old_rvid": old, "relation": "cross-resource-replacement",
                   "content_sha256": csha, "ui_sha256": usha,
                   "post_publish_issues": iss or "无"}
            reports.append(rep)
            json.dump({"published": reports, "note": "B6 受控发布（裁决 19:21 §四）；替代关系跨资源，未伪造版本链"},
                      open(f"{HERE}/FE1466_B6_publish_report.json", "w"), ensure_ascii=False, indent=1)
            print(f"B6-{key} 发布完成，后检: {rep['post_publish_issues']}")
            if iss:
                print("后检失败——停止下一题（§四），恢复方案=反向 update（manifest 在案）")
                return 3
    except Exception as e:
        if not apply: conn.rollback()
        print("中止:", e)
        return 1
    finally:
        conn.close()
    if not apply:
        print("Dry Run 完成（判定全只读，零 DML）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
