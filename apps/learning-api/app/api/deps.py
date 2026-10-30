"""游客会话的 FastAPI 依赖（V1.4 纯游客模式 P1）。

**这是全项目唯一允许产生「当前是谁」的地方。** 任何路由想知道操作者身份，
只能依赖 `current_guest_child_id`，不得从 body / query / path 读 child_id 当授权依据
（方案 3.2「前端传入的 guest_id 不能直接作为授权依据」）。

两类依赖：
- `current_guest()`：没有有效会话就**自动创建**一个新游客（首次访问即入学，
  方案 1.2「不展示登录页、注册弹窗或强制授权流程」）。仅用于首页这类入口。
- `require_guest()`：没有有效会话一律 401。所有涉及个人数据的读写都用它——
  入口可以自动建号，但数据接口不能因为「没会话」而静默换一个游客给他看。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.guest import (
    SESSION_COOKIE_NAME,
    cookie_kwargs,
    create_guest,
    resolve_session,
)


@dataclass(frozen=True)
class GuestContext:
    """一次请求解析出的游客上下文。

    `token` 只在本次请求新签发时有值（需要回写 Set-Cookie），否则为 None。
    """

    child_id: uuid.UUID
    token: str | None = None
    is_new: bool = False


def _read_token(request: Request) -> str | None:
    return request.cookies.get(SESSION_COOKIE_NAME)


async def current_guest(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> GuestContext:
    """有会话就复用，没有就新建一个游客并把 token 写进 Cookie。"""
    token = _read_token(request)
    child_id = await resolve_session(db, token=token)
    if child_id is not None:
        return GuestContext(child_id=child_id)

    identity, new_token = await create_guest(db)
    await db.commit()
    response.set_cookie(value=new_token, **cookie_kwargs())
    return GuestContext(child_id=identity.child_id, token=new_token, is_new=True)


async def require_guest(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> GuestContext:
    """必须已有有效会话，否则 401（不自动建号）。"""
    from fastapi import HTTPException

    token = _read_token(request)
    child_id = await resolve_session(db, token=token)
    if child_id is None:
        raise HTTPException(status_code=401, detail="游客会话无效或已过期，请重新进入学习首页")
    return GuestContext(child_id=child_id)


async def assert_owns_child(
    db: AsyncSession, *, guest_child_id: uuid.UUID, target_child_id: uuid.UUID
) -> None:
    """归属校验（方案 3.2「创建、修改、删除记录时，必须验证记录归属」）。

    不一致就 404 而不是 403：403 会告诉攻击者「这个 id 存在但不是你的」，
    等于提供枚举能力；404 让「不存在」与「不属于你」不可区分。
    """
    from fastapi import HTTPException

    if guest_child_id != target_child_id:
        raise HTTPException(status_code=404, detail="资源不存在")