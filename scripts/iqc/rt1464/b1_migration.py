#!/usr/bin/env python3
"""FE-1466 B1 迁移批｜QA 版本生成 + 三态复验（步骤3/4，裁决 10:07）。

纪律：仅 clone+process_constraint → 新 RVID 保持 qa_staged；**不切换任何生产状态**；
复验=阶段C 同口径三态（空→null 零证据 / 矛盾→false / 合法→true 恰一次）+
DB 断言。旧版全程 published 可用（发布决定权在产品，=步骤5 报告之后）。
"""
import copy
import json
import urllib.request
import uuid

import psycopg

DB = "postgresql://h_pg_user:W5uae1dxfnm184UB@pgm-uf69q77eiyn7qt01fo.pg.rds.aliyuncs.com:5897/h_db"
API = "http://127.0.0.1:8000"
CHILD = "00000000-0000-0000-0000-000000000099"
MODE = {"money-board": "payment_change", "pattern-board": "pattern_extension"}


def post(p, d):
    req = urllib.request.Request(API + p, json.dumps(d).encode(),
                                 {"Content-Type": "application/json"}, "POST")
    return json.loads(urllib.request.urlopen(req).read())


def pin(rvid):
    s = post("/v1/learning/sessions", {"child_id": CHILD, "subject": "math", "requested_minutes": 15})
    t = post("/v1/learning/tasks/next", {"child_id": CHILD, "session_id": s["session_id"],
        "subject": "math", "pin_resource_version_id": rvid})
    assert t.get("task_instance_id"), t
    return s["session_id"], t


def attempt(rvid, data, answer):
    sid, t = pin(rvid)
    wsid = t["ui_schema"]["workspaces"][0].get("workspace_id") or "main"
    out = post("/v1/learning/attempts", {"task_instance_id": t["task_instance_id"], "attempt_no": 1,
        "response": {"schema_version": "2.0", "type": "attempt",
                     "workspaces": [{"workspace_id": wsid, "data": data}],
                     "answer": {"value": answer}},
        "used_hint_levels": [], "submission_id": str(uuid.uuid4())})
    return sid, t["task_instance_id"], out


def ev_count(task_id):
    with psycopg.connect(DB) as c:
        return c.execute("select count(*) from mastery_evidence where task_instance_id=%s and valid",
                         (task_id,)).fetchone()[0]


def legal_and_contra_data(renderer, cfg):
    """由题 config 生成合法过程数据与矛盾数据（与阶段C 同思路：操作真源字段）。"""
    if renderer == "money-board":
        price = cfg["price"]; dens = sorted(cfg.get("denominations") or [1, 5, 10, 50], reverse=True)
        counts, rest = {}, price
        for d in dens:
            if d <= rest:
                counts[str(d)] = rest // d; rest %= d
        contra = {str(max(dens)): 1}                      # 单枚最大币（超付，除非恰等）
        if sum(int(k) * v for k, v in contra.items()) == price:
            contra = {str(min(dens)): price + 1}          # 再不行用欠付
        return {"counts": counts, "total": price}, {"counts": contra, "total": price}, {"counts": {}, "total": 0}
    if renderer == "pattern-board":
        vis = cfg["visible"]; period = cfg.get("period") or (len(vis) if vis else 2)
        blanks = cfg.get("blanks") or 1
        period_seq = vis[:period]
        legal = {"beads": [period_seq[(len(vis) + i) % period] for i in range(blanks)]}
        rev = list(reversed(legal["beads"]))
        contra = {"beads": rev if rev != legal["beads"] else [legal["beads"][0]] * blanks}
        return legal, contra, {"beads": [None] * blanks}
    raise ValueError(renderer)


def main():
    bp = json.load(open("/Users/hanxianxiang/WorkBuddy/2026-09-24-10-25-54/output/qa_item01_r2/FE1466_migration_batch_proposal.json"))
    m = json.load(open("/Users/hanxianxiang/WorkBuddy/2026-09-24-10-25-54/output/qa_item01_r2/FE1466_risk_matrix_37.json"))
    b1 = set(tuple(x) for x in bp["batches"][0]["bands"])
    todo = [x for x in m["rows"] if (x["ability"], x["difficulty"]) in b1]
    results = []
    for x in todo:
        src = x["rvid"]; renderer = x["renderer"]
        with psycopg.connect(DB) as c:
            row = c.execute("""select resource_id,version_no,difficulty,task_type,content,ui_schema,
                error_models,hint_policy,mastery_rule,transfer_distance from resource_version
                where resource_version_id=%s""", (src,)).fetchone()
        resid, vno, diff, ttype, ct, ui, em, hp, mr, td = row
        ui = copy.deepcopy(ui)
        ui["workspaces"][0]["config"]["process_constraint"] = {"mode": MODE[renderer], "params": {}}
        new = str(uuid.uuid4())
        with psycopg.connect(DB, autocommit=True) as c:
            c.execute("""insert into resource_version (resource_version_id,resource_id,version_no,
                difficulty,task_type,content,ui_schema,error_models,hint_policy,mastery_rule,
                transfer_distance,review_status,reviewer_1,reviewer_2,created_at)
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'qa_staged','B1-migration','FE-1466',now())""",
                (new, resid, vno + 1, diff, ttype,
                 psycopg.types.json.Jsonb(ct), psycopg.types.json.Jsonb(ui),
                 psycopg.types.json.Jsonb(em), psycopg.types.json.Jsonb(hp),
                 psycopg.types.json.Jsonb(mr) if mr else None, td))
        cfg = ui["workspaces"][0].get("config") or {}
        answer = (ct or {}).get("answer")
        legal, contra, empty = legal_and_contra_data(renderer, cfg)
        r = {"src": src[:8], "new": new, "renderer": renderer, "status": "qa_staged"}
        sid1, tid1, o1 = attempt(new, empty, answer)
        r["empty"] = {"correct": o1["correct"], "ps": o1.get("process_status"), "ev": ev_count(tid1),
                      "na": (o1.get("next_action") or {}).get("type")}
        sid2, tid2, o2 = attempt(new, contra, answer)
        r["contra"] = {"correct": o2["correct"], "ps": o2.get("process_status"), "ev": ev_count(tid2)}
        sid3, tid3, o3 = attempt(new, legal, answer)
        r["legal"] = {"correct": o3["correct"], "ps": o3.get("process_status"), "ev": ev_count(tid3)}
        r["pass"] = (r["empty"]["correct"] is None and r["empty"]["ev"] == 0
                     and r["contra"]["correct"] is False
                     and r["legal"]["correct"] is True and r["legal"]["ev"] == 1)
        results.append(r)
        print(f"{src[:8]}→{new[:8]} {renderer:13s} empty={r['empty']['correct']}/{r['empty']['ps']}/ev{r['empty']['ev']} "
              f"contra={r['contra']['correct']}/ev{r['contra']['ev']} legal={r['legal']['correct']}/ev{r['legal']['ev']} => {'✓' if r['pass'] else '✗'}")
    json.dump({"batch": "B1", "note": "qa_staged 新约束版（未发布）；旧版保持 published 可用；三态复验=阶段C 同口径",
               "results": results, "all_pass": all(r["pass"] for r in results)},
              open("scripts/iqc/rt1464/FE1466_B1_migration_report.json", "w"), ensure_ascii=False, indent=1)
    print("B1 全过" if all(r["pass"] for r in results) else "有未过项——见报告")


if __name__ == "__main__":
    import psycopg.types.json
    main()
