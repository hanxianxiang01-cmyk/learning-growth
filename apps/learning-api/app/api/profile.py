"""学习者画像 + 能力列表路由。

游客模式（V1.4）：路径里的 {child_id} 保留（冻结 OpenAPI 契约，删除会破坏消费者），
但**不再是授权依据**——必须与会话身份一致，否则 404。方案 3.2「前端传入的
guest_id 不能直接作为授权依据」在这里的落点就是 assert_owns_child。
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import GuestContext, assert_owns_child, require_guest
from app.core.database import get_db
from app.models import AbilityNode, AbilityState
from app.services.profile import build_learner_profile

router = APIRouter(prefix="/children", tags=["profile"])


@router.get("/{child_id}/profile")
async def get_profile(
    child_id: uuid.UUID,
    guest: GuestContext = Depends(require_guest),
    db: AsyncSession = Depends(get_db),
):
    await assert_owns_child(db, guest_child_id=guest.child_id, target_child_id=child_id)
    return await build_learner_profile(db, child_id)


@router.get("/{child_id}/abilities")
async def get_abilities(
    child_id: uuid.UUID,
    guest: GuestContext = Depends(require_guest),
    db: AsyncSession = Depends(get_db),
):
    """返回该 child 的能力状态列表（对齐 OpenAPI AbilityState[]）。"""
    await assert_owns_child(db, guest_child_id=guest.child_id, target_child_id=child_id)

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