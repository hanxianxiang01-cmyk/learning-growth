"""成长报告路由（对齐 OpenAPI /v1/reports/monthly）。"""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.growth import get_or_create_monthly_report

router = APIRouter(prefix="/reports", tags=["growth"])


@router.get("/monthly")
async def monthly(
    child_id: uuid.UUID = Query(...),
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: AsyncSession = Depends(get_db),
):
    """月度成长报告（对齐 OpenAPI，month 格式 YYYY-MM）。"""
    year, mon = int(month[:4]), int(month[5:7])
    period_start = date(year, mon, 1)
    # 下月第一天作为开区间结束
    if mon == 12:
        period_end = date(year + 1, 1, 1)
    else:
        period_end = date(year, mon + 1, 1)

    return await get_or_create_monthly_report(
        db, child_id=child_id, period_start=period_start, period_end=period_end
    )