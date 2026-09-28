"""Demo seed：造一个演示孩子 + 全能力初始状态（幂等）。

用途：本地联调前端 http 模式。固定 child_id 便于 .env.local 引用。
学习闭环从 level 0 开始，点进去能体验「答错→Hint→重试→升级」完整链路。
"""
from __future__ import annotations

import asyncio
import os
import uuid
import warnings

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.content.ability_seed import ABILITY_NODES
from app.models import AbilityState, Child, Guardian

warnings.filterwarnings("ignore")

# 从环境变量读取数据库连接串（不硬编码任何凭据）。
# 未提供 DATABASE_URL 时给出清晰提示，而不是回落到某个真实地址。
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("请设置环境变量 DATABASE_URL 后再运行（例如 .env 或 export）。")

# 固定的演示 child / guardian id（方便前端引用）
DEMO_GUARDIAN_ID = uuid.UUID("00000000-0000-0000-0000-0000000000a1")
DEMO_CHILD_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def seed(db) -> None:
    # Guardian（幂等：存在则跳过）
    g = await db.get(Guardian, DEMO_GUARDIAN_ID)
    if g is None:
        db.add(Guardian(guardian_id=DEMO_GUARDIAN_ID, display_name="演示家长", status="active"))
        await db.flush()

    # Child（幂等）
    c = await db.get(Child, DEMO_CHILD_ID)
    if c is None:
        db.add(
            Child(
                child_id=DEMO_CHILD_ID,
                guardian_id=DEMO_GUARDIAN_ID,
                nickname="小明",
                grade="一年级",
                status="active",
            )
        )
        await db.flush()

    # 7 个能力初始状态（幂等：已有则跳过；level 0 从零基础开始）
    for node in ABILITY_NODES:
        aid = node["ability_id"]
        existing = await db.get(AbilityState, {"child_id": DEMO_CHILD_ID, "ability_id": aid})
        if existing is None:
            db.add(
                AbilityState(
                    child_id=DEMO_CHILD_ID,
                    ability_id=aid,
                    level=0,
                    confidence=0.0,
                    fit_band_min=1,
                    fit_band_max=1,
                    evidence_count=0,
                    trend="watch",
                )
            )
    await db.commit()

    # 回读确认
    result = await db.execute(
        select(AbilityState).where(AbilityState.child_id == DEMO_CHILD_ID)
    )
    states = list(result.scalars().all())


async def main() -> None:
    eng = create_async_engine(DATABASE_URL)
    Session = async_sessionmaker(eng, expire_on_commit=False)
    async with Session() as db:
        await seed(db)
    await eng.dispose()
    print(f"✅ Demo seed 完成：child_id={DEMO_CHILD_ID}")
    print(f"   能力状态数：{len(ABILITY_NODES)} 个，全部 level=0")


if __name__ == "__main__":
    asyncio.run(main())