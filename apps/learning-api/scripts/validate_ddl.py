#!/usr/bin/env python3
"""DDL 可解析性校验 —— 检查关键结构是否齐全（语法级，不连接数据库）。

依据冻结基线 V1.3.1，必须确保：
- 18 张表全部存在；
- 复合外键 fk_learning_session_plan 存在；
- 复合唯一约束 uq_learning_plan_plan_child 存在；
- CREATE EXTENSION pgcrypto 存在。
"""
import re
import sys

EXPECTED_TABLES = [
    "guardian", "child", "textbook_profile", "ability_node", "ability_edge",
    "ability_state", "resource", "resource_version", "learning_plan",
    "learning_session", "task_instance", "attempt", "learning_event",
    "mastery_evidence", "growth_snapshot", "growth_report",
    "consent_record", "audio_asset",
]


def main(path: str) -> int:
    ddl = open(path, encoding="utf-8").read()
    failures: list[str] = []

    for t in EXPECTED_TABLES:
        if not re.search(rf"CREATE\s+TABLE\s+{t}\b", ddl, re.I):
            failures.append(f"缺表: {t}")

    if "fk_learning_session_plan" not in ddl:
        failures.append("缺复合外键 fk_learning_session_plan")
    if "uq_learning_plan_plan_child" not in ddl:
        failures.append("缺复合唯一约束 uq_learning_plan_plan_child")
    if "CREATE EXTENSION IF NOT EXISTS pgcrypto" not in ddl:
        failures.append("缺 CREATE EXTENSION pgcrypto")

    if failures:
        print("FAIL: DDL 校验未通过")
        for f in failures:
            print("  -", f)
        return 1

    print(f"PASS: DDL 校验通过（{len(EXPECTED_TABLES)} 张表 + 复合外键 + 复合唯一约束 + pgcrypto）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "schema.sql"))