"""learning_plan 路由：create + 读取当前 active plan。"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.planning import create_plan, get_current_plan, plan_to_dict

router = APIRouter(prefix="/learning/plans", tags=["plans"])


@router.post("/")
async def create(
    child_id: uuid.UUID,
    subject: str,
    db: AsyncSession = Depends(get_db),
):
    plan = await create_plan(db, child_id=child_id, subject=subject)
    await db.commit()
    return plan_to_dict(plan)


@router.get("/current")
async def current(
    child_id: uuid.UUID,
    subject: str,
    db: AsyncSession = Depends(get_db),
):
    plan = await get_current_plan(db, child_id=child_id, subject=subject)
    if plan is None:
        raise HTTPException(status_code=404, detail="No active learning plan")
    return plan_to_dict(plan)