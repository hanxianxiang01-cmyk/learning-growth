"""learning_plan 路由：create + 读取当前 active plan。

游客模式（V1.4）：child_id 入参保留（契约不变），但必须等于会话身份，否则 404。
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import GuestContext, assert_owns_child, require_guest
from app.core.database import get_db
from app.services.planning import create_plan, get_current_plan, plan_to_dict

router = APIRouter(prefix="/learning/plans", tags=["plans"])


@router.post("/")
async def create(
    child_id: uuid.UUID,
    subject: str,
    guest: GuestContext = Depends(require_guest),
    db: AsyncSession = Depends(get_db),
):
    await assert_owns_child(db, guest_child_id=guest.child_id, target_child_id=child_id)
    plan = await create_plan(db, child_id=child_id, subject=subject)
    await db.commit()
    return plan_to_dict(plan)


@router.get("/current")
async def current(
    child_id: uuid.UUID,
    subject: str,
    guest: GuestContext = Depends(require_guest),
    db: AsyncSession = Depends(get_db),
):
    await assert_owns_child(db, guest_child_id=guest.child_id, target_child_id=child_id)
    plan = await get_current_plan(db, child_id=child_id, subject=subject)
    if plan is None:
        raise HTTPException(status_code=404, detail="No active learning plan")
    return plan_to_dict(plan)