"""Curriculum next_task 路由。

游客模式（V1.4）：child_id 必须等于会话身份，否则 404。
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import GuestContext, assert_owns_child, require_guest
from app.core.database import get_db
from app.services.curriculum import next_task

router = APIRouter(prefix="/learning/tasks", tags=["curriculum"])


@router.post("/next")
async def get_next_task(
    child_id: uuid.UUID,
    ability_id: str,
    guest: GuestContext = Depends(require_guest),
    db: AsyncSession = Depends(get_db),
):
    """返回下一题（FitBand 接 MasteryState，选已发布资源版本）。"""
    await assert_owns_child(db, guest_child_id=guest.child_id, target_child_id=child_id)
    result = await next_task(db, child_id=child_id, ability_id=ability_id)
    return result