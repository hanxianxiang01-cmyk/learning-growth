"""游客模式路由（V1.4 纯游客模式）。

对外只多出 4 个端点，**不改动任何冻结 OpenAPI 既有端点的签名**：
- POST /v1/guest/bootstrap  首次进入即建游客（幂等：已有会话则复用）
- GET  /v1/guest/me         当前游客与配额状态（首页展示用）
- POST /v1/guest/heartbeat  刷新保留期（有效学习活动时调用）
- POST /v1/guest/logout     清除本地会话（配合「用户如何主动清除本地记录」）

清理管理端点（/v1/guest/admin/cleanup*）默认只在 QA/内网开放：它能看到
清理运行记录，属运维面而非儿童业务面。开关语义与 selection-trace 一致。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.qa import QA_CHILD_ID, is_qa_child
from app.api.deps import GuestContext, current_guest, require_guest
from app.services.guest import (
    SESSION_COOKIE_NAME,
    bootstrap_qa_session,
    cookie_kwargs,
    get_identity,
    revoke_session,
    touch_activity,
)
from app.services.guest_cleanup import list_recent_runs, run_cleanup
from app.services.guest_quota import usage_summary

router = APIRouter(prefix="/guest", tags=["guest"])


@router.post("/bootstrap")
async def bootstrap(
    response: Response,
    guest: GuestContext = Depends(current_guest),
    db: AsyncSession = Depends(get_db),
):
    """进入学习首页。已有会话则复用，没有就新建一个游客。

    幂等性来自 `current_guest`：同一次浏览反复调用不会产生新游客
    （否则每条记录都会被拆到不同身份，等价于没有身份）。
    """
    identity = await get_identity(db, child_id=guest.child_id)
    if identity is None:
        raise HTTPException(status_code=500, detail="游客身份缺失")
    return {
        "child_id": str(guest.child_id),
        "is_new": guest.is_new,
        "created_at": identity.created_at.isoformat(),
        "last_activity_at": identity.last_activity_at.isoformat(),
        "expires_at": identity.expires_at.isoformat(),
        "retention_days": get_settings().guest_retention_days,
        "quota": await usage_summary(db, child_id=guest.child_id),
    }


@router.get("/me")
async def me(
    guest: GuestContext = Depends(require_guest),
    db: AsyncSession = Depends(get_db),
):
    """当前游客身份 + 配额。前端用它替代原来的 ?child_id= 取身份。"""
    identity = await get_identity(db, child_id=guest.child_id)
    if identity is None:
        raise HTTPException(status_code=401, detail="游客会话无效或已过期")
    return {
        "child_id": str(guest.child_id),
        "created_at": identity.created_at.isoformat(),
        "last_activity_at": identity.last_activity_at.isoformat(),
        "expires_at": identity.expires_at.isoformat(),
        "retention_days": get_settings().guest_retention_days,
        "quota": await usage_summary(db, child_id=guest.child_id),
    }


@router.post("/heartbeat")
async def heartbeat(
    guest: GuestContext = Depends(require_guest),
    db: AsyncSession = Depends(get_db),
):
    """刷新「最后一次有效学习活动」与保留期（方案 4.1）。

    只应由真实学习活动触发，不要挂在页面挂载上——否则「打开页面就算活动」，
    保留期会被无限延长，7 天承诺失效。
    """
    await touch_activity(db, child_id=guest.child_id)
    await db.commit()
    identity = await get_identity(db, child_id=guest.child_id)
    return {
        "child_id": str(guest.child_id),
        "last_activity_at": identity.last_activity_at.isoformat() if identity else None,
        "expires_at": identity.expires_at.isoformat() if identity else None,
    }


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """清除本地会话（不清服务端学习数据——那是清理任务/人工申请的事）。

    方案第七章要求交代「用户如何主动清除本地记录」。本端点负责服务端那一半
    （撤销会话），前端再清本地缓存；学习数据按 7 天保留期自然清理。
    """
    token = request.cookies.get(SESSION_COOKIE_NAME)
    revoked = await revoke_session(db, token=token)
    await db.commit()
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return {"revoked": revoked}


# ---- 运维面：清理任务 ----


def _require_ops_enabled() -> None:
    if not get_settings().selection_trace_enabled:
        # 与 selection-trace 同一开关语义：生产默认不暴露运维端点
        raise HTTPException(status_code=404)


@router.post("/qa-session")
async def qa_session(
    response: Response,
    child_id: str = "",
    db: AsyncSession = Depends(get_db),
):
    """为 QA 测试池签发会话（E2E 专用，方案外的测试基础设施）。

    ## 为什么需要这个端点

    游客模式把身份来源从 `?child_id=` 改成了 Cookie。而 19 个 E2E spec 通过
    `?child_id=…0099` 表达「我是 QA 池」，docs/governance/QA_DATA_HYGIENE.md
    R1 也要求测试流量必须落在 …0099。两者直接冲突：不给测试一条合法通道，
    测试就只能去改授权逻辑——那才是真正的红线。

    ## 三道限制（缺一不可，任何一道被删都会变成越权后门）

    1. `selection_trace_enabled` 必须为真：生产默认 false → 404，不暴露端点存在性。
    2. `child_id` 必须是 QA 池（`QA_CHILD_ID`）：真实 child 与游客 id 一律 403。
       这一条保证本端点**只能**签发 QA 池的会话，无法借此获得任何真实数据访问权。
    3. 签发的是**长期票**（QA_RETENTION_DAYS），因为 QA 池不是真实儿童数据，
       且需要跨天稳定；不这样 19 个 spec 的基准会某天突然消失。

    注意本端点**不接受任意 child_id 通过**：第 2 条限制使它无法用于冒用游客身份。
    """
    _require_ops_enabled()
    if not is_qa_child(child_id):
        raise HTTPException(status_code=403, detail="qa-session 仅限 QA 测试池 child 使用")

    token = await bootstrap_qa_session(db, child_id=QA_CHILD_ID)
    await db.commit()
    response.set_cookie(value=token, **cookie_kwargs())
    return {"child_id": str(QA_CHILD_ID), "issued": True}


@router.post("/admin/cleanup")
async def admin_cleanup(
    dry_run: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """手动触发一轮清理（验收与运维用）。定时任务走同一函数。"""
    _require_ops_enabled()
    return await run_cleanup(db, dry_run=dry_run)


@router.get("/admin/cleanup-runs")
async def admin_cleanup_runs(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """清理运行记录（方案 4.3「定时任务实际运行」的可核对证据）。"""
    _require_ops_enabled()
    return {"runs": await list_recent_runs(db, limit=limit)}