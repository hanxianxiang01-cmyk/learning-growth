"""Learning 编排路由 —— 严格对齐冻结 OpenAPI /v1/learning/*。

签名以 02_openapi_v1.3.1.yaml 为准。
"""
import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.learning import assign_next_task, request_hint, start_session, submit_attempt
from app.services.session_result import get_session_result

router = APIRouter(prefix="/learning", tags=["learning"])


@router.get("/sessions/{session_id}/result")
async def session_result(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """读取一次 session 的真实学习结果（服务端聚合，非前端快照）。

    这是冻结 OpenAPI 之外新增的只读聚合接口；不修改任何已有冻结端点。
    """
    try:
        return await get_session_result(db, session_id=session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/sessions", status_code=201)
async def create_session(
    payload: dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """开始学习 session（对齐 OpenAPI，body 传参）。"""
    return await start_session(
        db,
        child_id=payload["child_id"],
        subject=payload["subject"],
        requested_minutes=payload.get("requested_minutes"),
        plan_id=payload.get("plan_id"),
    )


@router.post("/tasks/next")
async def next_task(
    payload: dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """取下一题（对齐 OpenAPI，无 ability_id，后端自选能力）。"""
    return await assign_next_task(
        db,
        child_id=payload["child_id"],
        session_id=payload["session_id"],
        subject=payload["subject"],
        requested_minutes=payload.get("requested_minutes"),
    )


@router.post("/attempts")
async def submit(
    payload: dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """提交作答（对齐 OpenAPI，无 child_id，后端反查）。"""
    try:
        return await submit_attempt(
            db,
            task_instance_id=payload["task_instance_id"],
            attempt_no=int(payload.get("attempt_no", 1)),
            response=payload.get("response", {}),
            client_elapsed_ms=payload.get("client_elapsed_ms"),
            used_hint_levels=payload.get("used_hint_levels", []),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/hints")
async def hint(
    payload: dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """受控 Hint（对齐 OpenAPI，attempt_id → 反查资源 hint 阶梯）。"""
    try:
        return await request_hint(
            db,
            attempt_id=payload["attempt_id"],
            requested_level=payload.get("requested_level"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))