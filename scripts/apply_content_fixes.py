#!/usr/bin/env python3
"""Q4 Rev.A 整改裁决·数据修复批次（产品方 2026-10-16 批准）。

范围（严格照裁决）：
A. 3 道 V1 数轴：visual.max 扩到覆盖题干全部中间态（13→16 / 11→14）
B. 9 道 Shape Gallery：shapes[].name 中性化为 "卡N"（不改变图形、kind、数量与正确答案）
通道（裁决要求"新资源版本发布、保留原始版本及变更记录"）：
- 新 resource_version（version_no+1，修复后 schema，review_status='published'）
- 原版本 review_status → 'superseded'（保留行=历史 task/evidence 的 rvid 对应关系不失效；
  不再进入生产选题池与 pin 放行集 {published, qa_staged}）
执行前置：**修复前浏览器取证必须已完成**（pin 固定旧 rvid，若先行 superseded 会拒 pin）。
输出：q4_reva_devfix/fix_manifest.json（逐题 before/after/新 rvid/回滚索引）。

安全性（产品方 PR#99 合并前确认 §一.2）：
- **默认 Dry Run，正式执行必须显式 --apply**；
- **幂等**：修复以 `review_status='published'` 行消费——已执行过的旧行转
  superseded 后重跑天然空操作（items=0），**不会再次生成版本**；
- manifest 防覆盖：正式执行成功后（items>0）manifest 落盘一次；重跑 items=0
  时不写 manifest（防抹掉真实变更记录），改打幂等提示并 exit 0；
- 原子性：全部 insert/update 收敛在**单事务**（psycopg with 块 + 末尾 commit），
  中途异常整体回滚，不产生部分更新。
"""
import json
import os
import sys
import uuid

import psycopg

URL = os.environ["DATABASE_URL"].replace("+psycopg", "")
OUT = os.path.join(os.environ["R2_OUT"], "q4_reva_devfix")
MAN_PATH = os.path.join(OUT, "fix_manifest.json")
DRY = "--apply" not in sys.argv

# ---- 修复表：前缀 → (新 max | name 中性化) ----
AXIS = {
    "e02a5afe": 16,   # 9→15→11：中间态 15 必须可达
    "a7fc3314": 14,   # 8→13→9：中间态 13
    "05a2649f": 14,   # 迁移同型
}

def fetch_all(conn):
    rows = conn.execute(
        """select resource_version_id, resource_id, version_no, review_status,
                  ui_schema::text, content::text
           from resource_version
           where review_status='published'""").fetchall()
    return rows

by8 = {}
with psycopg.connect(URL) as c:
    rows = fetch_all(c)
    for rvid, resid, vno, st, ui_s, ct_s in rows:
        by8[str(rvid)[:8]] = (rvid, resid, vno, json.loads(ui_s), json.loads(ct_s))

manifest = {"applied": not DRY, "items": []}

# 收集全部 shape-gallery 题（9 题按 Rev.A 清单=含类别词 name 的题；程序化判定防漏）
KIND_WORDS = ("正方形", "长方形", "三角形", "圆形")
shape_targets = []
for k, (rvid, resid, vno, ui, ct) in by8.items():
    ws = (ui.get("workspaces") or [{}])[0]
    if ws.get("renderer") == "shape-gallery":
        names = [s.get("name") for s in ws.get("config", {}).get("shapes", [])]
        if any(any(w in (n or "") for w in KIND_WORDS) for n in names):
            shape_targets.append(k)

with psycopg.connect(URL) as c:
    for prefix, new_max in AXIS.items():
        if prefix not in by8:
            print("   （%s 非 published 状态——已修复过或被隔离，幂等跳过）" % prefix)
            continue
        rvid, resid, vno, ui, ct = by8[prefix]
        old_ui = json.loads(json.dumps(ui))
        ui = json.loads(json.dumps(ui))
        ui["visual"]["max"] = new_max
        ui["ui_revision"] = (ui.get("ui_revision") or "v1") + ".1"
        nrvid = str(uuid.uuid4())
        manifest["items"].append({
            "kind": "axis_max_fix", "resource_id": str(resid),
            "old_rvid": str(rvid), "old_max": old_ui["visual"]["max"],
            "new_rvid": nrvid, "new_max": new_max, "new_version_no": vno + 1,
            "stem": ct.get("stem")[:60],
        })
        if not DRY:
            c.execute(
                """insert into resource_version (resource_version_id, resource_id, version_no,
                       difficulty, task_type, content, ui_schema, error_models, hint_policy,
                       mastery_rule, transfer_distance, review_status, reviewer_1, reviewer_2,
                       published_at, created_at)
                   select %s, resource_id, %s, difficulty, task_type, content, %s,
                          error_models, hint_policy, mastery_rule, transfer_distance,
                          'published', 'Q4-RevA-devfix', reviewer_2, now(), now()
                   from resource_version where resource_version_id=%s""",
                (uuid.UUID(nrvid), vno + 1,
                 json.dumps(ui, ensure_ascii=False), uuid.UUID(str(rvid))))
            c.execute("update resource_version set review_status='superseded' where resource_version_id=%s",
                      (uuid.UUID(str(rvid)),))
    for prefix in sorted(shape_targets):
        rvid, resid, vno, ui, ct = by8[prefix]
        ui2 = json.loads(json.dumps(ui))
        shapes = ui2["workspaces"][0]["config"]["shapes"]
        names_before = [s.get("name") for s in shapes]
        for i, s in enumerate(shapes, 1):
            s["name"] = f"卡{i}"
        ui2["ui_revision"] = (ui2.get("ui_revision") or "rev-1") + ".1"
        nrvid = str(uuid.uuid4())
        manifest["items"].append({
            "kind": "shape_name_neutralize", "resource_id": str(resid),
            "old_rvid": str(rvid), "names_before": names_before,
            "names_after": [s["name"] for s in shapes],
            "new_rvid": nrvid, "new_version_no": vno + 1,
            "stem": ct.get("stem")[:60],
        })
        if not DRY:
            c.execute(
                """insert into resource_version (resource_version_id, resource_id, version_no,
                       difficulty, task_type, content, ui_schema, error_models, hint_policy,
                       mastery_rule, transfer_distance, review_status, reviewer_1, reviewer_2,
                       published_at, created_at)
                   select %s, resource_id, %s, difficulty, task_type, content, %s,
                          error_models, hint_policy, mastery_rule, transfer_distance,
                          'published', 'Q4-RevA-devfix', reviewer_2, now(), now()
                   from resource_version where resource_version_id=%s""",
                (uuid.UUID(nrvid), vno + 1,
                 json.dumps(ui2, ensure_ascii=False), uuid.UUID(str(rvid))))
            c.execute("update resource_version set review_status='superseded' where resource_version_id=%s",
                      (uuid.UUID(str(rvid)),))
    if not DRY:
        c.commit()

os.makedirs(OUT, exist_ok=True)
if not manifest["items"]:
    # 幂等空跑：不写 manifest（防抹掉已执行的真实变更记录）
    print(("APPLIED(no-op)" if not DRY else "DRY-RUN(no-op)"),
          "| items: 0 —— 修复已全部生效，重复运行不再生成版本")
    sys.exit(0)
with open(os.path.join(OUT, "fix_manifest.json"), "w") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=1)
print(("APPLIED" if not DRY else "DRY-RUN"), "| items:", len(manifest["items"]))
for it in manifest["items"]:
    print(" ", it["kind"], it["old_rvid"][:8], "→", it["new_rvid"][:8],
          it.get("old_max") or "", it.get("names_before", "")[:2])
