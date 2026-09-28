"""Hint 路由。"""
from fastapi import APIRouter, Body

from app.services.hint import decide_hint

router = APIRouter(prefix="/hints", tags=["hints"])


@router.post("/")
async def get_hint(
    payload: dict = Body(...),
):
    """受控 Hint（0-4 阶梯，首次错误不揭答案）。"""
    attempt_count = int(payload.get("attempt_count", 1))
    requested_level = payload.get("requested_level")
    return decide_hint(
        attempt_count=attempt_count,
        requested_level=requested_level,
    ).to_dict()