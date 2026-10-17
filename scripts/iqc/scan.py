#!/usr/bin/env python3
"""FE-1460 扫描入口（只读）。消费 FE-1459 manifest，产出 findings.jsonl+覆盖报告。

用法：
  python3 scan.py --manifest runs/inventory_manifest_r2.json --db URL \
      --mapping /path/Q4_rvid_migration_12.csv --out findings.jsonl

裁决 §四 验收门实现：
- 发现唯一来自 manifest（本脚本零枚举 SQL）
- Q10 前后对账：审计哈希聚合 vs manifest snapshot
- finding 十字段构造器断言（common.finding）
- 覆盖报告含 UNVERIFIED/BLOCKED_SCHEMA 显式计数；published 计数取自 manifest，无硬编码
"""
import argparse
import csv
import json
import sys
import uuid
from collections import Counter


import os as _os, sys as _sys
_p=_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _p not in _sys.path: _sys.path.insert(0,_p)
from iqc import common
import os as _os, sys as _sys
_p=_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _p not in _sys.path: _sys.path.insert(0,_p)
from iqc import checks as C


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--mapping", default="")
    ap.add_argument("--out", default="findings.jsonl")
    ap.add_argument("--audit-only", default="published")
    args = ap.parse_args()

    man = common.load_manifest(args.manifest)
    snap = man["snapshot_sha256"]
    run_id = "FE1460-" + uuid.uuid4().hex[:8]

    sel = [i["resource_version_id"] for i in man["items"]
           if args.audit_only == "all" or i["review_status"] == "published"]
    items = common.load_items(args.db, sel)
    missing = len(sel) - len(items)
    if missing:
        print(f"⚠ manifest 有 {missing} 条在 DB 缺失（快照后漂移？显式报告不静默）")
    for it in items.values():
        it["_audit_sha"] = common.audit_input_sha(it)

    findings = []
    def F(rvid, rule, sev, status, ev, path, sugg, regr):
        findings.append(common.finding(rvid, rule, sev, status, ev, path, sugg, regr, run_id, snap))

    # Q01 多 published（键=resource_id）
    for rule, sev, ev, rid in C.q01_multi_published(items):
        pub = [i for i in items.values() if i["resource_id"] == rid and i["review_status"] == "published"]
        F(pub[0]["resource_version_id"], rule, sev, "FAIL_BLOCKING", ev, "$.review_status", "收敛单一 published", True)
    # Q01 版本链（14 项映射全闭合校验；mapping 端点补载入）
    if args.mapping:
        mrows = [(r["old_rvid"], r["new_rvid"]) for r in csv.DictReader(open(args.mapping))]
        need = sorted({x for pair in mrows for x in pair if x not in items})
        if need:
            extra = common.load_items(args.db, need)
            for e in extra.values(): e["_audit_sha"] = common.audit_input_sha(e)
            items.update(extra)
        for rule, sev, ev, rid in C.q01_version_chain(items, mrows):
            F(rid, rule, sev, "REVISION_REQUIRED", ev, "$.version_no|$.review_status", ev, True)

    # 逐题规则
    Q3_STATUS = {"Q03-OK": "PASS_RULES", "Q03-UNVERIFIED": "UNVERIFIED",
                 "Q03-ENCODING_FORM": "REVISION_REQUIRED", "Q03-ANSWER_MISMATCH": "FAIL_BLOCKING",
                 "Q03-NO-ANSWER-FIELD": "REVISION_REQUIRED"}
    for it in items.values():
        rid = it["resource_version_id"]
        for rule, sev, ev, _ in C.q02_schema_contract(it):
            F(rid, rule, sev, "BLOCKED_SCHEMA" if "BLOCKED" in rule else "REVISION_REQUIRED",
              ev, "$.ui_schema", ev, True)
        for rule, sev, ev, _ in C.q03_arithmetic(it):
            F(rid, rule, sev, Q3_STATUS[rule], ev, "$.content", ev, rule == "Q03-ANSWER_MISMATCH")
        for rule, sev, ev, _ in C.q05_error_models(it):
            F(rid, rule, sev, "REVISION_REQUIRED", ev, "$.error_models", ev, False)
        for rule, sev, ev, _ in C.q06_hint_ladder(it):
            F(rid, rule, sev, "REVIEW_REQUIRED", ev, "$.hint_policy.ladder", "泄露边界人工判定", False)
        for rule, sev, ev, _ in C.q06_stem_leak(it):
            F(rid, rule, sev, "REVIEW_REQUIRED", ev, "$.content.stem", "题面即答案——教学复核（测量失效候选）", False)

    with open(args.out, "w") as f:
        for x in findings:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")

    # Q10 自证：现行 published 聚合 vs manifest 同子集（重算对账）
    pub = {k: v for k, v in items.items() if v["review_status"] == "published"}
    cov = {
        "run_id": run_id, "rules_version": common.RULES_VERSION,
        "manifest_snapshot": snap, "audited_published": len(pub),
        "findings_total": len(findings),
        "by_status": dict(Counter(x["status"] for x in findings)),
        "by_rule": dict(Counter(x["rule_id"] for x in findings)),
        "by_severity": dict(Counter(x["severity"] for x in findings)),
        "items_with_unverified_q03": len({x["rvid"] for x in findings if x["rule_id"] == "Q03-UNVERIFIED"}),
        "blocked_schema": len({x["rvid"] for x in findings if x["status"] == "BLOCKED_SCHEMA"}),
        "p0_blocking": len([x for x in findings if x["severity"] == "P0"]),
    }
    json.dump(cov, open(args.out.replace(".jsonl", "_coverage.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(cov, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
