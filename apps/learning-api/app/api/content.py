"""Content 只读端点（FE-1422a）。

GET /v1/content/v2-catalog：published + V2-assignable 资源目录。
冻结 OpenAPI 之外新增的只读接口（对齐 session_result 的先例）——不修改任何
已有冻结端点；供 QA/E2E 钉题发现 resource_version_id。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.learning import list_v2_catalog

router = APIRouter(prefix="/content", tags=["content"])


@router.get("/v2-catalog")
async def v2_catalog(db: AsyncSession = Depends(get_db)):
    """V2 资源目录（renderer / ability / difficulty 供 spec 按图索骥）。"""
    return {"items": await list_v2_catalog(db)}
