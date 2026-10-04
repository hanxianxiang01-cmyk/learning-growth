"""submission_id 落库迁移（FE-1410，docs/frontend/29 §5-2 待办）。

V2 规模化下发前的最后一笔 DDL 技术债：attempt 表加 submission_id 列 + 部分唯一索引，
把「同 submission_id 重放 / 异内容 409」的幂等契约（docs/frontend/29 §3）从
应用层纪律升级为数据库约束。

幂等（可重复执行）：
- ALTER TABLE ... ADD COLUMN IF NOT EXISTS
- CREATE UNIQUE INDEX IF NOT EXISTS ... WHERE submission_id IS NOT NULL（partial，
  尊重 V1 提交 submission_id 为 NULL 的双轨设计，NULL 不参与唯一性）

不改基线 SQL：v1.3.1 冻结物由 SHA256SUMS 管理；V2 schema 挂入属「V1.4 基线立版」
独立动作（docs/frontend/29 §5-6），本迁移只动运行库。

用法：
    DATABASE_URL=... python scripts/migrate_submission_id.py
"""
from __future__ import annotations

import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DDL = [
    "ALTER TABLE attempt ADD COLUMN IF NOT EXISTS submission_id uuid",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_attempt_submission_id "
    "ON attempt (submission_id) WHERE submission_id IS NOT NULL",
]

VERIFY = """
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'attempt' AND column_name = 'submission_id'
"""

INDEX_VERIFY = """
SELECT indexname, indexdef FROM pg_indexes
WHERE tablename = 'attempt' AND indexname = 'uq_attempt_submission_id'
"""


async def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("需要 DATABASE_URL 环境变量")

    eng = create_async_engine(url)
    try:
        async with eng.begin() as conn:
            for stmt in DDL:
                await conn.execute(text(stmt))
                print("执行:", stmt)

        async with eng.connect() as conn:
            col = (await conn.execute(text(VERIFY))).fetchall()
            print("\n列验证:", col)
            assert col and col[0][0] == "submission_id", "submission_id 列未创建"
            idx = (await conn.execute(text(INDEX_VERIFY))).fetchall()
            print("索引验证:", idx)
            assert idx, "uq_attempt_submission_id 索引未创建"
            # 存量 attempt 的 submission_id 均为 NULL（V1 历史提交，双轨兼容轨）
            null_cnt = (await conn.execute(
                text("SELECT count(*) FROM attempt WHERE submission_id IS NOT NULL")
            )).scalar()
            print(f"已带 submission_id 的历史 attempt: {null_cnt}（预期 0）")
        print("\nMIGRATION OK: submission_id 列 + 部分唯一索引就位")
    finally:
        await eng.dispose()


if __name__ == "__main__":
    asyncio.run(main())
