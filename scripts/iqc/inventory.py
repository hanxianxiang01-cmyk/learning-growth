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
       rv.ui_schema::text, rv.content::text
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

    items, blocked = [], []
    status_dist, schema_dist = {}, {}
    for (rvid, resid, vno, st, diff, ttype, td, ab, title, ui_s, ct_s) in rows:
        ui = json.loads(ui_s) if ui_s else None
        ct = json.loads(ct_s) if ct_s else {}
        status_dist[st] = status_dist.get(st, 0) + 1
        form, info = classify_schema(ui)
        entry = {"resource_version_id": rvid, "resource_id": resid, "version_no": vno,
                 "review_status": st, "ability_id": ab, "difficulty": diff,
                 "task_type": ttype, "title": title,
                 "schema_form": form, "interaction": info,
                 "content_sha256": hashlib.sha256(json.dumps(ct, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16],
                 "ui_sha256": hashlib.sha256(json.dumps(ui, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16],
                 "transfer_distance": td}
        if form is None:
            entry["block_reason"] = info
            blocked.append(entry)
        else:
            schema_dist[form] = schema_dist.get(form, 0) + 1
        items.append(entry)

    # 内容级快照哈希：逐条字段排序拼接，与文件行序无关，可跨导出复现比对
    canon = json.dumps(sorted(i["resource_version_id"] + i["ui_sha256"] + i["content_sha256"] for i in items))
    snapshot_sha = hashlib.sha256(canon.encode()).hexdigest()

    manifest = {
        "inventory_version": "iqc-inventory/1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "discovered_total": len(items),        # ← 动态数，绝无 225 常量
        "status_distribution": status_dist,
        "schema_distribution": schema_dist,
        "blocked_unknown_schema": len(blocked),
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
