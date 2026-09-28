"""LearnerProfileService —— 按 child 返回能力切片 + 近期学习行为 + 强弱项。"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.content.ability_seed import ABILITY_NODES
from app.models import AbilityNode, AbilityState, Child

# 能力依赖链的教学顺序（读题理解 → … → 迁移变式），用于对 developing 排序，
# 保证"今日目标"推荐的是链上最底层、最该先练的能力，而非数据库无序返回的第一个。
_CANONICAL_ORDER = [n["ability_id"] for n in ABILITY_NODES]


async def build_learner_profile(db: AsyncSession, child_id: uuid.UUID) -> dict:
    # 孩子基础信息
    child = await db.get(Child, child_id)

    # 能力状态列表
    result = await db.execute(
        select(AbilityState).where(AbilityState.child_id == child_id)
    )
    states = list(result.scalars().all())

    # 拉取能力名称
    ability_ids = [s.ability_id for s in states]
    names: dict[str, str] = {}
    if ability_ids:
        nodes = await db.execute(
            select(AbilityNode).where(AbilityNode.ability_id.in_(ability_ids))
        )
        names = {n.ability_id: n.name for n in nodes.scalars().all()}

    level_by_ability = {s.ability_id: s.level for s in states}

    active = []
    strengths: list[str] = []
    developing: list[str] = []
    for s in states:
        item = {
            "ability_id": s.ability_id,
            "name": names.get(s.ability_id, s.ability_id),
            "level": s.level,
            "confidence": float(s.confidence),
            "fit_band": {
                "min": s.fit_band_min,
                "max": s.fit_band_max,
            },
            "evidence_count": s.evidence_count,
            "trend": s.trend,
        }
        active.append(item)
        if s.level >= 3:
            strengths.append(s.ability_id)
        else:
            developing.append(s.ability_id)

    # developing 按能力依赖链的规范顺序排序（链底层优先），而非数据库任意顺序。
    # 保证"今日目标"推荐的是该孩子最该先练的那一环。
    developing.sort(key=lambda aid: _CANONICAL_ORDER.index(aid) if aid in _CANONICAL_ORDER else len(_CANONICAL_ORDER))

    return {
        "child_id": child_id,
        "grade": child.grade if child else None,
        "active_abilities": active,
        "strengths": strengths,
        "developing": developing,
        "observations": [],
    }