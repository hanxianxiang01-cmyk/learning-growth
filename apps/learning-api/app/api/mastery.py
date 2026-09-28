"""Mastery 评估路由。"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.mastery_db import evaluate_mastery_from_db

router = APIRouter(prefix="/mastery", tags=["mastery"])


@router.post("/evaluate")
async def evaluate(
    child_id: uuid.UUID,
    ability_id: str,
    db: AsyncSession = Depends(get_db),
):
    """从有效证据评估 mastery（对齐 OpenAPI /v1/mastery/evaluate）。

    走 DB 联表：加载 mastery_evidence + attempt + task_instance，组装后走纯计算。
    """
    return await evaluate_mastery_from_db(db, child_id, ability_id)