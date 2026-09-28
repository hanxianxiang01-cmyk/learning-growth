"""Curriculum next_task 路由。"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.curriculum import next_task

router = APIRouter(prefix="/learning/tasks", tags=["curriculum"])


@router.post("/next")
async def get_next_task(
    child_id: uuid.UUID,
    ability_id: str,
    db: AsyncSession = Depends(get_db),
):
    """返回下一题（FitBand 接 MasteryState，选已发布资源版本）。"""
    result = await next_task(db, child_id=child_id, ability_id=ability_id)
    return result