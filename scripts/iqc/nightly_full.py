#!/usr/bin/env python3
"""FE-1463 夜间/手动全量扫描 + 问题 diff（裁决 §四 验收门 2/3/5）。

流程：动态 re-inventory（全状态全版本，非仅 published）→ scan --audit-only all
→ 与上一轮 findings 对比（新增/已修复/复发/持续）→ 工件归档 runs/nightly/。
只读纪律：全程 SELECT；0 写库 0 发布；P0/P1 新增→退出码非零（报告红但不改题）。
secret 缺失由 workflow 层显式失败——本脚本要求 --db 必传。
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
OUT_DIR = os.path.join(HERE, "runs", "nightly")


def key(f):
    return (f["rvid"], f["rule_id"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--mapping", default=os.path.join(HERE, "version_migration_map.csv"))
    ap.add_argument("--prev", default="")  # 上一轮 findings.jsonl
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # 1 re-inventory 全状态
    r = subprocess.run([sys.executable, os.path.join(HERE, "inventory.py"),
                        "--db", args.db, "--out", os.path.join(OUT_DIR, f"inventory_{ts}.json")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("INVENTORY FAIL（显式报错不静默）:", r.stderr[-300:]); return 1
    print(r.stdout.strip())

    # 2 scan all
    r = subprocess.run([sys.executable, os.path.join(HERE, "scan.py"),
                        "--manifest", os.path.join(OUT_DIR, f"inventory_{ts}.json"),
                        "--db", args.db, "--mapping", args.mapping,
                        "--audit-only", "all",
                        "--out", os.path.join(OUT_DIR, f"findings_{ts}.jsonl")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("SCAN FAIL:", r.stderr[-300:]); return 1

    cur = [json.loads(l) for l in open(os.path.join(OUT_DIR, f"findings_{ts}.jsonl"))]
    curmap = {key(f): f for f in cur}
    diff = {"run_ts": ts, "findings_now": len(cur)}
    if args.prev and os.path.exists(args.prev):
        prev = [json.loads(l) for l in open(args.prev)]
        prevmap = {key(f): f for f in prev}
        added = [curmap[k] for k in curmap.keys() - prevmap.keys()]
        fixed = [prevmap[k] for k in prevmap.keys() - curmap.keys()]
        persist = len(curmap.keys() & prevmap.keys())
        diff.update({
            "added": [{"rvid": a["rvid"][:8], "rule": a["rule_id"], "sev": a["severity"],
                       "evidence": a["evidence_pointer"][:80]} for a in sorted(added, key=lambda x: x["severity"])],
            "fixed": [{"rvid": b["rvid"][:8], "rule": b["rule_id"], "sev": b["severity"]} for b in fixed],
            "persistent": persist,
            "new_p0p1": len([a for a in added if a["severity"] in ("P0", "P1")])})
    diff["by_severity"] = dict(Counter(f["severity"] for f in cur))
    json.dump(diff, open(os.path.join(OUT_DIR, f"diff_{ts}.json"), "w"), ensure_ascii=False, indent=1)
    print("NIGHTLY DIFF:", json.dumps({k: (len(v) if isinstance(v, list) else v)
          for k, v in diff.items() if k in ("added", "fixed", "persistent", "new_p0p1", "findings_now")},
          ensure_ascii=False))
    # 阻断语义：新增 P0/P1 → 非零（夜间 job 红=提醒，不改题不发布）
    return 1 if diff.get("new_p0p1") else 0


if __name__ == "__main__":
    sys.exit(main())
