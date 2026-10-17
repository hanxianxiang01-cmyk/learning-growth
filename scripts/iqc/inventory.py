#!/usr/bin/env python3
"""FE-1459 IQC Inventory Adapter：动态枚举全库资源与版本（只读）。

硬约束（rules.json iqc.inventory / 方案附录A）：
- 无题数上限常量——发现数=当期 DB 实际数；
- 未知 Schema→BLOCKED_SCHEMA 显式登记，禁止静默跳过；
- 只读：SELECT 全量清单，零 DML；
- manifest 可复现：含来源快照 SHA-256（内容级）与逐条字段哈希。

用法：python3 inventory.py --out inventory_manifest.json [--db postgresql://…]
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

import psycopg

SQL = """
select rv.resource_version_id::text, rv.resource_id::text, rv.version_no,
       rv.review_status, rv.difficulty, rv.task_type, rv.transfer_distance,
       r.ability_id, r.title,
       rv.ui_schema::text, rv.content::text,
       rv.error_models::text, rv.hint_policy::text, rv.mastery_rule::text
from resource_version rv join resource r using(resource_id)
order by rv.resource_id, rv.version_no
-- 全状态动态枚举（published/draft/qa_staged/superseded/archived/qa_retired…按实际值）；
-- 无题数上限、无状态排除——发布资格由 Gate 分层判定，不由发现层过滤（方案 §3）
"""


def classify_schema(ui):
    if not isinstance(ui, dict):
        return None, "ui_schema 非对象"
    v = str(ui.get("schema_version") or "")
    if v == "2.0" and isinstance(ui.get("workspaces"), list):
        ws0 = ui["workspaces"][0] if ui["workspaces"] else {}
        return "V2", {"renderer": ws0.get("renderer"), "mode": ws0.get("mode"),
                      "has_contract": bool(ui.get("response_contract"))}
    if v == "1.0" and "kind" in ui:
        return "V1", {"kind": ui.get("kind"),
                      "renderer": f"legacy:{(ui.get('visual') or {}).get('type', 'direct')}",
                      "mode": None, "has_contract": bool(ui.get("response_schema"))}
    return None, f"未知 schema_version={v!r} 且无法按 legacy 形态判定"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="inventory_manifest.json")
    ap.add_argument("--db", default=os.environ.get("DATABASE_URL", "").replace("+psycopg", ""))
    args = ap.parse_args()
    if not args.db:
        sys.exit("需要 --db 或 DATABASE_URL")

    with psycopg.connect(args.db) as c:
        rows = c.execute(SQL).fetchall()   # 只读

    # 检查点1：完整状态覆盖——已知状态枚举全集显式列 0（enum 值域 ∪ 实际出现值）
    with psycopg.connect(args.db) as c:
        enum_vals = [r[0] for r in c.execute(
            "select distinct review_status from resource_version").fetchall()]
    KNOWN_STATUS = ["published", "draft", "qa_staged", "superseded", "archived", "qa_retired"]
    status_domain = sorted(set(KNOWN_STATUS) | set(enum_vals))  # 未知新状态并入显式报告

    items, blocked = [], []
    status_dist = {s: 0 for s in status_domain}   # 0 值显式在场
    schema_dist = {}
    for (rvid, resid, vno, st, diff, ttype, td, ab, title, ui_s, ct_s, em_s, hp_s, mr_s) in rows:
        ui = json.loads(ui_s) if ui_s else None
        ct = json.loads(ct_s) if ct_s else {}
        em = json.loads(em_s) if em_s else None
        hp = json.loads(hp_s) if hp_s else None
        mr = json.loads(mr_s) if mr_s else None
        status_dist[st] = status_dist.get(st, 0) + 1  # 域外值也会新增键，显式可见
        form, info = classify_schema(ui)
        entry = {"resource_version_id": rvid, "resource_id": resid, "version_no": vno,
                 "review_status": st, "ability_id": ab, "difficulty": diff,
                 "task_type": ttype, "title": title,
                 "schema_form": form, "interaction": info,
                 "transfer_distance": td,
                 # 检查点2：单题审计输入哈希=质量判断相关字段全集合（题面未变但 Hint 被改也能发现）
                 # 规范化=json.dumps sort_keys ensure_ascii=False（字段范围与排序固定，可复现）
                 "audit_input_sha256": hashlib.sha256(json.dumps(
                     {"ui_schema": ui, "content": ct, "error_models": em, "hint_policy": hp,
                      "mastery_rule": mr, "ability_id": ab, "difficulty": diff,
                      "version_no": vno, "review_status": st,
                      "response_axis": (ui or {}).get("response_contract") or (ui or {}).get("response_schema")},
                     ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()}
        if form is None:
            entry["block_reason"] = info
            blocked.append(entry)
        else:
            schema_dist[form] = schema_dist.get(form, 0) + 1
        items.append(entry)

    # 全库 Inventory 快照哈希：按 (resource_id, version_no) 稳定身份顺序聚合每题审计哈希+状态
    canon = json.dumps([[i["resource_id"], i["version_no"], i["resource_version_id"],
                         i["review_status"], i["audit_input_sha256"]]
                        for i in sorted(items, key=lambda x: (x["resource_id"], x["version_no"]))],
                       ensure_ascii=False, sort_keys=True)
    snapshot_sha = hashlib.sha256(canon.encode()).hexdigest()
    # ③ 检查点3：版本治理真检——按逻辑题目身份 resource_id 分组（非 RVID）
    from collections import Counter
    pub_by_resource = Counter(i["resource_id"] for i in items if i["review_status"] == "published")
    multi_pub = [{"resource_id": rid, "published_versions": n}
                 for rid, n in pub_by_resource.items() if n > 1]

    manifest = {
        "inventory_version": "iqc-inventory/1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "discovered_total": len(items),        # ← 动态数，绝无 225 常量
        "status_distribution": status_dist,
        "schema_distribution": schema_dist,
        "blocked_unknown_schema": len(blocked),
        "status_domain": status_domain,
        "status_zero_explicit": [s for s in status_domain if status_dist[s] == 0],
        "version_governance_Q01": {"group_key": "resource_id", "multi_published": multi_pub},
        "snapshot_sha256": snapshot_sha,
        "read_only": True,
        "items": items,
    }
    with open(args.out, "w") as f:
        json.dump(manifest, f, ensure_ascii=False)
    print(f"inventory: {len(items)} 条（动态发现）| 状态分布 {status_dist} | schema {schema_dist} | BLOCKED_SCHEMA {len(blocked)} | snapshot {snapshot_sha[:16]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
