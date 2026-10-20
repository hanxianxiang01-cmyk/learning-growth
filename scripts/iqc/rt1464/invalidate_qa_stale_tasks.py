#!/usr/bin/env python3
"""FE-1466 QA 旧风险遗留任务受控失效（裁决 20:13 §二）。

范围三重交集（缺一不入）：
1 身份=完整 UUID 白名单（12 个 QA child——由对账文件列明，真实 …0001 不在）；
2 任务挂本次 37 旧风险 RVID 集合；
3 会话 active/paused。
动作=task 级 status→'cancelled'（status 无 CHECK；既有枚举语义）。
混合会话核查（§二）：会话级作废会波及范围外任务 905 条 → 已放弃会话级，
仅动目标 task；attempt/evidence/session 零删除零改写。
Dry 默认零 DML（BUG-1456 纪律：判定全只读，写仅在 --apply）。
审计：FE1466_invalidation_run.json（目标清单/前后状态/时间/原因）。
"""
import json
import os
import sys
from datetime import datetime, timezone

import psycopg

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("IQC_MIGRATE_DB") or sys.exit("缺 IQC_MIGRATE_DB")
QA_CHILDREN = [  # §二.1 完整 UUID（对账文件 FE1466_open_tasks_full_reconciliation 来源）
    "00000000-0000-0000-0000-000000000099", "00000000-0000-0000-0000-000000000096",
    "00000000-0000-0000-0000-000000000097", "00000000-0000-0000-0000-000000000094",
    "00000000-0000-0000-0000-000000000087", "00000000-0000-0000-0000-000000000084",
    "00000000-0000-0000-0000-000000000093", "00000000-0000-0000-0000-000000000090",
    "00000000-0000-0000-0000-000000000092", "00000000-0000-0000-0000-000000000088",
    "00000000-0000-0000-0000-000000000089", "00000000-0000-0000-0000-000000000091",
]


def targets(conn, rvids):
    return conn.execute("""
        select t.task_instance_id::text, t.child_id::text, t.session_id::text,
               t.resource_version_id::text, t.status, s.status
        from task_instance t join learning_session s using(session_id)
        where t.resource_version_id = any(%s::uuid[])
          and t.child_id = any(%s::uuid[])
          and s.status in ('active','paused')
          and t.status = 'assigned'
        order by t.child_id, t.assigned_at""", (rvids, QA_CHILDREN)).fetchall()


def main():
    apply = "--apply" in sys.argv
    risk = json.load(open("/Users/hanxianxiang/WorkBuddy/2026-09-24-10-25-54/output/qa_item01_r2/FE1466_published_exposure.json"))
    rvids = [i["rvid"] for i in risk["items"]]
    conn = psycopg.connect(DB, autocommit=apply)
    try:
        rows = targets(conn, rvids)
        # 身份守卫：范围外 child 一条都不能有（真实 …0001 双保险）
        assert all(r[1] in QA_CHILDREN for r in rows)
        assert "00000000-0000-0000-0000-000000000001" not in {r[1] for r in rows}
        print(f"目标 {len(rows)} 条 task（QA 身份∩旧风险 rvid∩active/paused∩assigned）")
        if not apply:
            print("DRY：仅清单，零 DML。--apply 执行 task→cancelled")
            return 0
        ids = [r[0] for r in rows]
        conn.execute("update task_instance set status='cancelled' where task_instance_id = any(%s::uuid[]) and status='assigned'", (ids,))
        after = {r[0]: conn.execute("select status from task_instance where task_instance_id=%s", (r[0],)).fetchone()[0] for r in rows}
        assert all(v == "cancelled" for v in after.values())
    finally:
        if not apply:
            conn.rollback()
        conn.close()
    run = {"run_at": datetime.now(timezone.utc).isoformat(), "reason": "Q07 §二 QA 旧风险遗留任务受控失效",
           "granularity": "task-level（混合会话核查放弃会话级：77 会话含范围外任务 905 条）",
           "identity": "12 QA child 完整 UUID 白名单；真实 …0001 排除并断言",
           "attempt_evidence_session_changes": "零", "count": len(rows),
           "tasks": [{"task_id": r[0], "child": r[1], "session": r[2], "old_rvid": r[3],
                      "before": r[4], "after": "cancelled"} for r in rows]}
    json.dump(run, open(os.path.join(HERE, "FE1466_invalidation_run.json"), "w"), ensure_ascii=False, indent=1)
    print(f"失效完成 {len(rows)} 条，审计落盘")
    return 0


if __name__ == "__main__":
    sys.exit(main())
