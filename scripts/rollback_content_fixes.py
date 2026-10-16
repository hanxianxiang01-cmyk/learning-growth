#!/usr/bin/env python3
"""Q4 Rev.A 数据修复回滚 v2（BUG-1456 根治版）。

两层防护（产品方裁决 §一——替代"只靠最后 rollback()"的一层守卫）：
1. **Dry Run 路径零 DML**：判定阶段全部只读 SELECT，写语句（DELETE/UPDATE）
   只在 `--apply` 分支才构造执行——DRY 连"执行后回滚"都不发生；
2. **事务安全**：`autocommit=False` 显式声明；正常 apply 才 `commit()`；
   异常路径统一 `rollback()`（apply 中途炸=整体回滚，无部分删除/部分恢复）。

以 fix_manifest.json 为准逐条回退：
- 新 rvid 已被 Task/Evidence 引用 → 拒绝删除（保版本与证据关联）；
- 旧 rvid 非 superseded → 幂等跳过（防重复回滚把事故重修复新版再删一遍）。

用法：rollback_content_fixes.py [--apply]   （默认 DRY，零写入）
"""
import json
import os
import sys
import uuid

import psycopg

URL = os.environ["DATABASE_URL"].replace("+psycopg", "")
RB_SCHEMA = os.environ.get("RB_SCHEMA", "")  # 测试隔离 schema（BUG-1456 事务验证用）
OUT = os.path.join(os.environ["R2_OUT"], "q4_reva_devfix")
DRY = "--apply" not in sys.argv


def plan_items(man, conn):
    """纯只读判定（零 DML）：返回 (可回退项, 引用保护项, 幂等跳过项)。"""
    todo, protected, idem = [], [], []
    for it in man["items"]:
        cur = conn.execute(
            "select review_status from resource_version where resource_version_id=%s",
            (uuid.UUID(it["old_rvid"]),)).fetchone()
        if cur is None:
            idem.append((it, "旧版行不存在"))
            continue
        if cur[0] != "superseded":
            idem.append((it, f"旧版状态={cur[0]}（已回滚过/异常态），幂等跳过"))
            continue
        consumed = conn.execute(
            "select count(*) from task_instance where resource_version_id=%s",
            (uuid.UUID(it["new_rvid"]),)).fetchone()[0]
        ev_consumed = conn.execute(
            """select count(*) from mastery_evidence
               where task_instance_id in (select task_instance_id from task_instance
               where resource_version_id=%s)""", (uuid.UUID(it["new_rvid"]),)).fetchone()[0]
        if consumed or ev_consumed:
            protected.append((it, consumed, ev_consumed))
            continue
        todo.append(it)
    return todo, protected, idem


def apply_plan(conn, todo):
    """写路径：仅 --apply 到达此处；commit/rollback 由调用方控制。"""
    for it in todo:
        conn.execute("delete from resource_version where resource_version_id=%s",
                     (uuid.UUID(it["new_rvid"]),))
        conn.execute("update resource_version set review_status='published' "
                     "where resource_version_id=%s", (uuid.UUID(it["old_rvid"]),))


def main(inject_error=False):
    """inject_error：测试钩子——apply 第 2 条写后抛异常，验证整体原子回滚。"""
    man = json.load(open(os.path.join(OUT, "fix_manifest.json")))
    with psycopg.connect(URL, autocommit=False) as c:
        try:
            todo, protected, idem = plan_items(man, c)
            for it, why in idem:
                print("[skip-idempotent]", it["old_rvid"][:8], why)
            for it, tn, en in protected:
                print(f"!! {it['new_rvid'][:8]} 已被 {tn} 个任务/{en} 条证据引用，"
                      f"跳过删除（保留版本与证据关联，人工裁决）")
            if DRY:
                for it in todo:
                    print("[dry] would roll back（本路径零 DML 执行）:",
                          it["old_rvid"][:8], "v", it["new_version_no"])
                c.rollback()
                print(f"DRY-RUN 完成：判定只读、零写语句执行、事务已回滚 | "
                      f"可回退={len(todo)} 保护={len(protected)} 幂等={len(idem)}")
                return 0
            if inject_error and len(todo) > 1:
                apply_plan(c, todo[:1])
                raise RuntimeError("测试注入：apply 中途异常（验证原子性）")
            apply_plan(c, todo)
            c.commit()
            print(f"ROLLED BACK {len(todo)}（保护 {len(protected)}，幂等 {len(idem)}）")
            return 0
        except BaseException:
            c.rollback()
            raise


if __name__ == "__main__":
    sys.exit(main(inject_error="--inject-error-test" in sys.argv))
