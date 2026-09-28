"""学习者画像 + 能力列表路由。"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import AbilityNode, AbilityState
from app.services.profile import build_learner_profile

router = APIRouter(prefix="/children", tags=["profile"])


@router.get("/{child_id}/profile")
async def get_profile(child_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await build_learner_profile(db, child_id)


@router.get("/{child_id}/abilities")
async def get_abilities(child_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """返回该 child 的能力状态列表（对齐 OpenAPI AbilityState[]）。"""
    result = await db.execute(
        select(AbilityState).where(AbilityState.child_id == child_id)
    )
    states = list(result.scalars().all())

    ability_ids = [s.ability_id for s in states]
    names: dict[str, str] = {}
    if ability_ids:
        nodes = await db.execute(
            select(AbilityNode).where(AbilityNode.ability_id.in_(ability_ids))
        )
        names = {n.ability_id: n.name for n in nodes.scalars().all()}

    return [
        {
            "ability_id": s.ability_id,
            "name": names.get(s.ability_id, s.ability_id),
            "level": s.level,
            "confidence": float(s.confidence),
            "fit_band": {"min": s.fit_band_min, "max": s.fit_band_max},
            "evidence_count": s.evidence_count,
            "trend": s.trend,
        }
        for s in states
    ]