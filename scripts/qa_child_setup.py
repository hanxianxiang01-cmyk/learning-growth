"""QA-Simulator child 初始化（幂等）——数据卫生治理的前置件。

背景（docs/governance/QA_DATA_HYGIENE.md）：QA 回放 / E2E harness 的模拟作答
曾写入真实演示孩子（…0001），污染其 mastery 证据窗口（CI 窗口最近 8 条被
测试数据压住，真实水平测不准）。治理方式：测试流量统一切到虚拟儿童
QA-Simulator（…0099）。ability_state 主键含 child_id，分池天然隔离，零 DDL。

用法：
  DATABASE_URL=... python scripts/qa_child_setup.py
  DATABASE_URL=... python scripts/qa_child_setup.py --reset-bands
    （FE-1422a：把 QA 池 ability_state 恢复到创建默认 level0/conf0/band1~1——
     E2E 每轮写 attempt 会让 mastery 引擎推 level、band 漂移；pin 钉题路径
     已不依赖 band，但 qa_replay 等 mastery 回归仍需干净起点。）
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid

sys.path.insert(0, "apps/learning-api")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.content.ability_seed import ABILITY_NODES
from app.models import AbilityState, Child, Guardian

QA_GUARDIAN_ID = uuid.UUID("00000000-0000-0000-0000-0000000000a1")  # 复用演示家长
QA_CHILD_ID = uuid.UUID(os.environ.get("QA_CHILD_ID", "00000000-0000-0000-0000-000000000099"))


async def seed(db) -> None:
    g = await db.get(Guardian, QA_GUARDIAN_ID)
    if g is None:
        raise SystemExit("guardian 不存在，先跑 seed_demo.py")

    c = await db.get(Child, QA_CHILD_ID)
    if c is None:
        db.add(Child(child_id=QA_CHILD_ID, guardian_id=QA_GUARDIAN_ID,
                     nickname="QA-Simulator", grade="一年级", status="active"))
        await db.flush()
        print(f"创建 QA child {QA_CHILD_ID}")
    else:
        print(f"QA child 已存在：{c.nickname}")

    # 7 能力初始 state（幂等），保证 getProfile 返回完整能力切片
    for node in ABILITY_NODES:
        aid = node["ability_id"]
        existing = await db.get(AbilityState, {"child_id": QA_CHILD_ID, "ability_id": aid})
        if existing is None:
            db.add(AbilityState(child_id=QA_CHILD_ID, ability_id=aid, level=0,
                                confidence=0.0, fit_band_min=1, fit_band_max=1,
                                evidence_count=0, trend="watch"))
    await db.commit()


async def reset_bands(db) -> None:
    """QA 池 7 能力 state 恢复到创建默认（level/conf/band/evidence/trend）。

    只动 QA child（…0099）——真实 child 的 mastery 是人的数据，绝对不碰
    （docs/governance/QA_DATA_HYGIENE.md）。
    """
    rows = (
        await db.execute(select(AbilityState).where(AbilityState.child_id == QA_CHILD_ID))
    ).scalars().all()
    for st in rows:
        st.level = 0
        st.confidence = 0.0
        st.fit_band_min = 1
        st.fit_band_max = 1
        st.evidence_count = 0
        st.trend = "watch"
        st.last_evidence_at = None
        st.version = st.version + 1
    await db.commit()
    print(f"已重置 QA 池 {len(rows)} 个能力 band → (1,1)/level0")


async def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("需要 DATABASE_URL 环境变量")
    eng = create_async_engine(url)
    Session = async_sessionmaker(eng, expire_on_commit=False)
    async with Session() as db:
        await seed(db)
        if "--reset-bands" in sys.argv:
            await reset_bands(db)
        rs = await db.execute(select(AbilityState).where(AbilityState.child_id == QA_CHILD_ID))
        states = rs.scalars().all()
    await eng.dispose()
    print(f"✅ QA child 就绪：{len(states)} 个能力 state")


if __name__ == "__main__":
    asyncio.run(main())
