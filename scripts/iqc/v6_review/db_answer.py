#!/usr/bin/env python3
"""FE-1445 复审：取真实题目的标准答案（只读）。

E2E 用它拿到「真值」，再去核对前端提交后的判分是否正确。
判据必须有独立事实源：如果拿被测系统自己算出来的结果当基准，
那只是自证（既不知道对错，也发现不了解包错误）。

用法：
    export DATABASE_URL="postgresql://..."
    python scripts/iqc/v6_review/db_answer.py <resource_version_id>

输出（stdout，JSON 单行）：
    {"resource_version_id": "...", "review_status": "published", "answer": 3}
"""
from __future__ import annotations

import json
import os
import sys

import psycopg


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: db_answer.py <resource_version_id>", file=sys.stderr)
        return 2
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("FATAL: 未设置 DATABASE_URL", file=sys.stderr)
        return 2

    rvid = sys.argv[1]
    with psycopg.connect(url) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        with conn.cursor() as cur:
            cur.execute(
                "select review_status, content from resource_version where resource_version_id=%s",
                (rvid,),
            )
            row = cur.fetchone()
    if row is None:
        print(f"FATAL: resource_version {rvid} 不存在", file=sys.stderr)
        return 2

    status, content = row
    if not isinstance(content, dict) or "answer" not in content:
        print(f"FATAL: 题目 {rvid} 的 content 无 answer 字段", file=sys.stderr)
        return 2

    print(json.dumps({
        "resource_version_id": rvid,
        "review_status": status,
        "answer": content["answer"],
        "stem": content.get("stem", "")[:60],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
