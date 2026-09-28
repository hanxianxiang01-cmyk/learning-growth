"""CurriculumService.next_task —— FitBand 接 MasteryState + Resource 选下一题。

实现 Learning Path 闭环的最后一环：
  AbilityState(level, confidence) ──FitBand──> 难度带 ──> resource_version ──> 下一题
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AbilityState, Resource, ResourceVersion
from app.services.fitband import compute_fit_band


async def next_task(
    db: AsyncSession,
    *,
    child_id: uuid.UUID,
    ability_id: str,
) -> dict | None:
    """给孩子返回下一题：读取 mastery 状态算 fit_band，再选匹配难度的已发布资源版本。"""

    # 1. 读 ability_state
    state = await db.get(AbilityState, {"child_id": child_id, "ability_id": ability_id})

    if state is None:
        level, confidence = 0, 0.0
    else:
        level, confidence = state.level, float(state.confidence)

    # 2. FitBand（接 MasteryState）
    band_min, band_max = compute_fit_band(level=level, confidence=confidence)

    # 3. 选已发布资源版本（难度落在带内，取最新发布）
    result = await db.execute(
        select(ResourceVersion)
        .join(Resource, Resource.resource_id == ResourceVersion.resource_id)
        .where(
            Resource.ability_id == ability_id,
            ResourceVersion.review_status == "published",
            ResourceVersion.difficulty >= band_min,
            ResourceVersion.difficulty <= band_max,
        )
        .order_by(ResourceVersion.published_at.desc())
        .limit(1)
    )
    rv = result.scalar_one_or_none()

    if rv is None:
        return {
            "ability_id": ability_id,
            "fit_band": {"min": band_min, "max": band_max},
            "next_task": None,
            "reason": "no_published_resource_in_band",
        }

    return {
        "ability_id": ability_id,
        "fit_band": {"min": band_min, "max": band_max},
        "next_task": {
            "resource_version_id": rv.resource_version_id,
            "difficulty": rv.difficulty,
            "task_type": rv.task_type,
            "ui_schema": rv.ui_schema,
        },
        "reason": "selected",
    }