#!/usr/bin/env python3
"""FE-1466 迁移批执行器（B1-B6 通用，幂等）。

纪律（裁决 2026-10-20 10:30 §三）：
1 从现行 published 克隆 → 注入显式 process_constraint → 新 RVID 仅 qa_staged；
2 旧版全程 published 不动；**本脚本绝不改任何行的 review_status**（只 insert）；
3 三态复验（阶段C 同口径）：空→null/零证据、矛盾→false（负向按 renderer 冻结策略）、
  合法→true+恰一次；每批独立报告，不因上批通过免测；
4 数据卫生 R2：凭据经 IQC_MIGRATE_DB 环境变量显式注入（写账号），无静默回退；
5 幂等：该 resource 已有含 process_constraint 的 qa_staged 版→复用不重插（异常恢复友好），
  但三态复验每轮都跑（验证与建版解耦）。
"""
import argparse
import copy
import json
import os
import subprocess
import sys
import urllib.request
import uuid
from datetime import datetime, timezone

import psycopg
import psycopg.types.json as pj

API = "http://127.0.0.1:8000"
CHILD = "00000000-0000-0000-0000-000000000099"
MODE = {"money-board": "payment_change", "pattern-board": "pattern_extension",
        "shape-canvas": "shape_drawing", "place-value": "place_value_build"}
OUTPUT = "/Users/hanxianxiang/WorkBuddy/2026-09-24-10-25-54/output/qa_item01_r2"


def db_url():
    v = os.environ.get("IQC_MIGRATE_DB")
    if not v:
        sys.exit("缺 IQC_MIGRATE_DB（迁移需写账号显式注入；Keychain 条目为只读扫描专用）")
    return v


def post(p, d):
    req = urllib.request.Request(API + p, json.dumps(d).encode(),
                                 {"Content-Type": "application/json"}, "POST")
    return json.loads(urllib.request.urlopen(req).read())


def attempt(rvid, data, answer):
    s = post("/v1/learning/sessions", {"child_id": CHILD, "subject": "math", "requested_minutes": 15})
    t = post("/v1/learning/tasks/next", {"child_id": CHILD, "session_id": s["session_id"],
        "subject": "math", "pin_resource_version_id": rvid})
    if not t.get("task_instance_id"):
        return None, None, {"error": t.get("reason")}
    wsid = t["ui_schema"]["workspaces"][0].get("workspace_id") or "main"
    out = post("/v1/learning/attempts", {"task_instance_id": t["task_instance_id"], "attempt_no": 1,
        "response": {"schema_version": "2.0", "type": "attempt",
                     "workspaces": [{"workspace_id": wsid, "data": data}],
                     "answer": {"value": answer}},
        "used_hint_levels": [], "submission_id": str(uuid.uuid4())})
    return t["task_instance_id"], out, None


def ev_count(task_id):
    with psycopg.connect(db_url()) as c:
        return c.execute("select count(*) from mastery_evidence where task_instance_id=%s and valid",
                         (task_id,)).fetchone()[0]


def gen_data(renderer, cfg, cons):
    if renderer == "money-board":
        price = cfg["price"]; dens = sorted(cfg.get("denominations") or [1, 5, 10, 50], reverse=True)
        counts, rest = {}, price
        for d in dens:
            if d <= rest:
                counts[str(d)] = rest // d; rest %= d
        big = str(max(dens))
        contra_counts = {big: 1}
        if sum(int(k) * v for k, v in contra_counts.items()) == price:
            contra_counts = {str(min(dens)): price + 1}
        return ({"counts": counts, "total": price}, {"counts": contra_counts, "total": price},
                {"counts": {}, "total": 0})
    if renderer == "pattern-board":
        vis = cfg["visible"]; period = cfg.get("period") or len(vis)
        blanks = cons.get("blanks") or cfg.get("blanks") or 1
        seq = vis[:period]
        legal_beads = [seq[(len(vis) + i) % period] for i in range(blanks)]
        rev = legal_beads[::-1]
        contra_beads = rev if rev != legal_beads else [legal_beads[0]] * blanks
        return ({"beads": legal_beads}, {"beads": contra_beads}, {"beads": [None] * blanks})
    if renderer == "shape-canvas":
        area = cons.get("area") or cfg.get("target_area") or 6
        w, h = area, 1
        for i in range(2, area + 1):
            if area % i == 0 and i * (area // i) == area and i <= area // i + 2:
                w, h = i, area // i
                break
        if h < 1: w, h = area, 1
        legal = {"vertices": [[0, 0], [w, 0], [w, h], [0, h]], "area": area, "right_angles": 4}
        contra = {"vertices": [[0, 0], [w, 0], [w + 1, h], [1, h]], "area": area, "right_angles": 4}
        return legal, contra, {"vertices": [], "area": 0}
    if renderer == "place-value":
        target = cfg["target"]; ds = [int(x) for x in str(target)]
        sw = ds[:]; sw[-1], sw[-2] = sw[-2], sw[-1]
        contra = sw if sw != ds else ds[::-1]
        return ({"slots": ds}, {"slots": contra}, {"slots": [None] * len(ds)})
    raise ValueError(renderer)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", required=True, type=int)
    args = ap.parse_args()
    bp = json.load(open(f"{OUTPUT}/FE1466_migration_batch_proposal.json"))
    m = json.load(open(f"{OUTPUT}/FE1466_risk_matrix_37.json"))
    bands = set(tuple(x) for x in bp["batches"][args.batch - 1]["bands"])
    todo = [x for x in m["rows"] if (x["ability"], x["difficulty"]) in bands]
    print(f"B{args.batch}: {len(todo)} 题（bands={sorted(bands)}）")
    results = []
    for x in todo:
        src, renderer = x["rvid"], x["renderer"]
        with psycopg.connect(db_url()) as c:
            row = c.execute("""select resource_id,version_no,difficulty,task_type,content,ui_schema,
                error_models,hint_policy,mastery_rule,transfer_distance from resource_version
                where resource_version_id=%s""", (src,)).fetchone()
            reuse = c.execute("""select resource_version_id::text from resource_version
                where resource_id=%s and review_status='qa_staged' and ui_schema::text like %s
                order by version_no desc limit 1""", (row[0], '%"process_constraint"%')).fetchone()
            vmax = c.execute("select max(version_no) from resource_version where resource_id=%s",
                             (row[0],)).fetchone()[0]
        resid, vno, diff, ttype, ct, ui, em, hp, mr, td = row
        ui = copy.deepcopy(ui)
        ws = ui["workspaces"][0]
        ws["config"]["process_constraint"] = {"mode": MODE[renderer], "params": {}}
        cons = ws.get("constraints") or {}
        if reuse:
            new, created = reuse[0], False
        else:
            new, created = str(uuid.uuid4()), True
            with psycopg.connect(db_url(), autocommit=True) as c:
                c.execute("""insert into resource_version (resource_version_id,resource_id,version_no,
                    difficulty,task_type,content,ui_schema,error_models,hint_policy,mastery_rule,
                    transfer_distance,review_status,reviewer_1,reviewer_2,created_at)
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'qa_staged','migration','FE-1466',now())""",
                    (new, resid, vmax + 1, diff, ttype, pj.Jsonb(ct), pj.Jsonb(ui),
                     pj.Jsonb(em), pj.Jsonb(hp), pj.Jsonb(mr) if mr else None, td))
        answer = (ct or {}).get("answer")
        legal, contra, empty = gen_data(renderer, ws.get("config") or {}, cons)
        r = {"src": src, "new": new, "created": created, "renderer": renderer,
             "ability": x["ability"], "difficulty": x["difficulty"]}
        checks = {}
        for label, data in (("empty", empty), ("contra", contra), ("legal", legal)):
            tid, out, err = attempt(new, data, answer)
            if err:
                checks[label] = {"pin_error": err}
                continue
            checks[label] = {"correct": out.get("correct"), "ps": out.get("process_status"),
                             "ev": ev_count(tid) if tid else None,
                             "na": (out.get("next_action") or {}).get("type"),
                             "attempt": out.get("attempt_id"), "task": tid}
        r["checks"] = checks
        e, cn, lg = checks.get("empty", {}), checks.get("contra", {}), checks.get("legal", {})
        neg_allowed = renderer in ("pattern-board", "shape-canvas")
        r["pass"] = (e.get("correct") is None and e.get("ps") == "missing" and e.get("ev") == 0
                     and cn.get("correct") is False
                     and ((cn.get("ev") == 1) if neg_allowed else (cn.get("ev") == 0))
                     and lg.get("correct") is True and lg.get("ev") == 1)
        results.append(r)
        print(f"{src[:8]}→{new[:8]} {renderer:13s} empty={e.get('correct')}/{e.get('ev')} "
              f"contra={cn.get('correct')}/ev{cn.get('ev')} legal={lg.get('correct')}/ev{lg.get('ev')} => "
              f"{'✓' if r['pass'] else '✗'}")
    rep = {"batch": f"B{args.batch}", "generated": datetime.now(timezone.utc).isoformat(),
           "note": "qa_staged 新约束版（未发布）；旧版 published 全程不动；三态复验每批独立跑（验证与建版解耦，幂等复用已建行）",
           "results": results, "all_pass": all(r["pass"] for r in results)}
    out_path = f"scripts/iqc/rt1464/FE1466_B{args.batch}_migration_report.json"
    json.dump(rep, open(out_path, "w"), ensure_ascii=False, indent=1)
    print(f"B{args.batch}:", "全过" if rep["all_pass"] else "有未过项", "→", out_path)
    return 0 if rep["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
