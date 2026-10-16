#!/usr/bin/env python3
"""Q4 Rev.A 数据修复回滚：删新 published 版本、原版本 superseded→published。
以 fix_manifest.json 为准逐条回退（新 rvid 若已被 QA/E2E 消费则拒绝盲删并报告）。"""
import json
import os
import sys
import uuid

import psycopg

URL = os.environ["DATABASE_URL"].replace("+psycopg", "")
OUT = os.path.join(os.environ["R2_OUT"], "q4_reva_devfix")
man = json.load(open(os.path.join(OUT, "fix_manifest.json")))
DRY = "--apply" not in sys.argv

with psycopg.connect(URL) as c:
    for it in man["items"]:
        consumed = c.execute(
            "select count(*) from task_instance where resource_version_id=%s",
            (uuid.UUID(it["new_rvid"]),)).fetchone()[0]
        ev_consumed = c.execute(
            """select count(*) from mastery_evidence
               where task_instance_id in (select task_instance_id from task_instance
               where resource_version_id=%s)""", (uuid.UUID(it["new_rvid"]),)).fetchone()[0]
        if consumed or ev_consumed:
            print(f"!! {it['new_rvid'][:8]} 已被 {consumed} 个任务/{ev_consumed} 条证据引用，"
                  f"跳过删除（保留版本与证据关联，人工裁决）")
            continue
        c.execute("delete from resource_version where resource_version_id=%s",
                  (uuid.UUID(it["new_rvid"]),))
        c.execute("update resource_version set review_status='published' where resource_version_id=%s",
                  (uuid.UUID(it["old_rvid"]),))
        print("rolled back", it["old_rvid"][:8], "v", it["new_version_no"])
    if not DRY:
        c.commit()
print(("ROLLED BACK" if not DRY else "DRY-RUN"), len(man["items"]))
