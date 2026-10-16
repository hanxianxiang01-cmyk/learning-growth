#!/usr/bin/env python3
"""Q4 Rev.A 数据修复回滚：删新 published 版本、原版本 superseded→published。
以 fix_manifest.json 为准逐条回退（新 rvid 若已被 Task/Evidence 引用则拒绝盲删并报告）。

⚠️ 事故教训（2026-10-16，本脚本旧版）：psycopg3 的 `with connect()` 上下文在
正常退出时**自动 commit**——旧版仅在显式分支调 c.commit()，DRY-RUN 的写操作
照样被上下文提交，导致 6 个修复新版被删、6 个泄露旧版回流 published。
根治：DRY 分支退出前**强制 c.rollback()**；并对 apply/本脚本统一加
`autocommit=False` 显式声明，写语义只认 --apply 路径。
"""
import json
import os
import sys
import uuid

import psycopg

URL = os.environ["DATABASE_URL"].replace("+psycopg", "")
OUT = os.path.join(os.environ["R2_OUT"], "q4_reva_devfix")
man = json.load(open(os.path.join(OUT, "fix_manifest.json")))
DRY = "--apply" not in sys.argv

with psycopg.connect(URL, autocommit=False) as c:
    try:
        for it in man["items"]:
            cur_status = c.execute(
                "select review_status from resource_version where resource_version_id=%s",
                (uuid.UUID(it["old_rvid"]),)).fetchone()
            if cur_status and cur_status[0] == "published":
                # 幂等：旧版已在 published=已回滚过（或事故回流），重复执行不再动
                print("[skip-idempotent]", it["old_rvid"][:8], "旧版已是 published，不重复回滚")
                continue
            if cur_status and cur_status[0] != "superseded":
                print(f"!! {it['old_rvid'][:8]} 状态={cur_status[0]}（非 superseded），跳过",
                      "（事故重修复旧版已再次 superseded 属正常，勿动）")
                continue
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
            print(("rolled back " if not DRY else "[dry] would roll back "),
                  it["old_rvid"][:8], "v", it["new_version_no"])
        if not DRY:
            c.commit()
            print("ROLLED BACK", len(man["items"]))
        else:
            c.rollback()  # 根治事故：DRY 绝不落库
            print("DRY-RUN（事务已回滚，零写入）", len(man["items"]))
    except BaseException:
        c.rollback()
        raise
