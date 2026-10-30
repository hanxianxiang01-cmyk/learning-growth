"""Mastery 评估路由。

游客模式（V1.4）：评估读的是个人证据，child_id 必须等于会话身份，否则 404。
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import GuestContext, assert_owns_child, require_guest
from app.core.database import get_db
from app.services.mastery_db import evaluate_mastery_from_db

router = APIRouter(prefix="/mastery", tags=["mastery"])


@router.post("/evaluate")
async def evaluate(
    child_id: uuid.UUID,
    ability_id: str,
    guest: GuestContext = Depends(require_guest),
    db: AsyncSession = Depends(get_db),
):
    """从有效证据评估 mastery（对齐 OpenAPI /v1/mastery/evaluate）。

    走 DB 联表：加载 mastery_evidence + attempt + task_instance，组装后走纯计算。
    """
    await assert_owns_child(db, guest_child_id=guest.child_id, target_child_id=child_id)
    return await evaluate_mastery_from_db(db, child_id, ability_id)