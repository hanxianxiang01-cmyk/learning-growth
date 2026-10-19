#!/usr/bin/env python3
"""FE-1464 首轮全库报告生成：消费最新 nightly 工件，分层统计+例外队列。"""
import glob
import json
import os
from collections import Counter, defaultdict

ff = sorted(glob.glob("scripts/iqc/runs/nightly/findings_*.jsonl"), key=os.path.getmtime)[-1]
inv = sorted(glob.glob("scripts/iqc/runs/nightly/inventory_*.json"), key=os.path.getmtime)[-1]
cur = [json.loads(l) for l in open(ff)]
man = json.load(open(inv))
items = {i["resource_version_id"]: i for i in man["items"]}

layer = defaultdict(Counter)
for f in cur:
    it = items.get(f["rvid"], {})
    layer["review_status"][it.get("review_status", "?")] += 1
    layer["schema_form"][it.get("schema_form", "?")] += 1
    st = (it.get("interaction") or {}).get("renderer") or "?"
    kind = "V1/legacy" if str(st).startswith("legacy") or st in ("none", "?") else "V2"
    layer["renderer_kind"][kind] += 1

# 硬约束分层：非现行状态（superseded/qa_retired/qa_staged/archived/draft）的发现
# → SUPERSEDED_AUDIT_ONLY 归层，不混现行通过率（rules.json states 语义）。
# scan 层规则判定不变（同一规则集审计全版本），口径修正在治理报告层显式完成。
def is_current(f):
    return items.get(f["rvid"], {}).get("review_status") == "published"
cur_now = [f for f in cur if is_current(f)]
audit_only = [f for f in cur if not is_current(f)]
sup = len(audit_only)
report = {
    "fe1464_first_full_baseline": {
        "run_findings": os.path.basename(ff),
        "inventory_run": os.path.basename(inv),
        "snapshot_sha256": man["snapshot_sha256"],
        "resources_discovered": man["discovered_total"],
        "findings_total": len(cur),
        "layering": {k: dict(v) for k, v in layer.items()},
        "current_published_findings": {
            "n": len(cur_now),
            "severity": dict(Counter(f["severity"] for f in cur_now)),
            "status": dict(Counter(f["status"] for f in cur_now)),
            "note": "现行通过率/治理只读本段"},
        "superseded_audit_only_findings": {
            "n": sup,
            "status": dict(Counter(f["status"] for f in audit_only)),
            "note": "SUPERSEDED_AUDIT_ONLY 口径：参与审计追溯，不混现行"},
        "severity": dict(Counter(f["severity"] for f in cur)),
        "status": dict(Counter(f["status"] for f in cur)),
        "rule_hits": dict(Counter(f["rule_id"] for f in cur)),
        "p0_p1_by_status": dict(Counter(f["status"] for f in cur if f["severity"] in ("P0", "P1"))),
        "exceptions_queue_review_required_rvid": sorted({f["rvid"][:8] for f in cur if f["status"] == "REVIEW_REQUIRED"}),
        "blocked_any": sorted({f["rvid"][:8] for f in cur if f["status"].startswith("BLOCKED")}),
        "baseline_note": "首轮=基线轮（无 prev→趋势 diff 空属预期）。本清单冻结为 FE-1464 治理输入；"
                         "superseded/qa_retired 发现计 SUPERSEDED_AUDIT_ONLY 口径——不进现行通过率；"
                         "夜间链（用户配 secret 后）以 nightly/latest_findings.jsonl 为锚自动 diff。",
    }
}
out = "scripts/iqc/runs/FE1464_first_full_report.json"
json.dump(report, open(out, "w"), ensure_ascii=False, indent=1)
b = report["fe1464_first_full_baseline"]
print(json.dumps({k: b[k] for k in ("resources_discovered", "findings_total", "severity", "status", "layering", "exceptions_queue_review_required_rvid", "blocked_any")}, ensure_ascii=False, indent=1))
