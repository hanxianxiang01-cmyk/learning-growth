"""游客身份与会话服务（V1.4 纯游客模式 P1）。

三条设计红线（方案第二/三章）：

1. **服务端生成、服务端校验**。`guest_id`（= child_id）永远由 `gen_random_uuid()`
   在服务端生成，前端不能指定、不能修改。前端唯一持有的凭证是 HttpOnly Cookie 里
   的随机 token；token → sha256 → 查 guest_session → 得到 child_id。方案 3.2
   「前端传入的 guest_id 不能直接作为授权依据」由此满足。

2. **一个 token 只绑定一个 child**。`resolve_session()` 返回的 child_id 来自
   数据库那一行，调用方无从伪造。

3. **cookie 令牌只以哈希落库**。见 models/guest.py 的数据模型说明。

保留期（方案 4.1）：`last_activity_at` 每次有效学习活动刷新，`expires_at` =
last_activity_at + 保留期。会话有效期与数据保留期分开：会话默认 7 天不活动失效
（与数据保留期一致，避免出现「会话还在、数据没了」的错位体验）。
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import Child, Guardian, GuestIdentity, GuestSession

# 游客在 child 表里的展示名：方案 1.2「不展示登录页、注册弹窗或强制授权」，
# 但 child.nickname / grade 是 NOT NULL，需要一个中性的默认值。
GUEST_NICKNAME = "小朋友"
GUEST_GRADE = "一年级"

SESSION_COOKIE_NAME = "guest_session"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def hash_token(token: str) -> str:
    """令牌的落库形态。数据库泄露者无法由哈希还原出可用的 token。"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_token() -> str:
    """32 字节高熵随机串（方案 2.1「建议使用服务端生成的高熵随机标识」）。"""
    return secrets.token_urlsafe(32)


async def create_guest(
    db: AsyncSession, *, retention_days: int | None = None
) -> tuple[GuestIdentity, str]:
    """创建一个全新游客，返回 (身份行, 明文 token)。

    明文 token 只在这里出现一次，由调用方写入 Set-Cookie；之后系统里只有哈希。
    每个游客一个独立的 guardian + child，**不使用任何固定公共 ID**（方案 2.1）。
    """
    settings = get_settings()
    days = retention_days if retention_days is not None else settings.guest_retention_days
    now = _now()

    guardian = Guardian(display_name=None, status="active")
    db.add(guardian)
    await db.flush()

    child = Child(
        guardian_id=guardian.guardian_id,
        nickname=GUEST_NICKNAME,
        grade=GUEST_GRADE,
        status="active",
    )
    db.add(child)
    await db.flush()

    identity = GuestIdentity(
        child_id=child.child_id,
        created_at=now,
        last_activity_at=now,
        expires_at=now + timedelta(days=days),
        status="active",
    )
    db.add(identity)
    await db.flush()

    token = await _issue_session(db, child_id=child.child_id)
    return identity, token


async def _issue_session(db: AsyncSession, *, child_id: uuid.UUID) -> str:
    settings = get_settings()
    now = _now()
    token = new_token()
    db.add(
        GuestSession(
            session_token_hash=hash_token(token),
            child_id=child_id,
            created_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(days=settings.guest_session_days),
        )
    )
    await db.flush()
    return token


async def resolve_session(db: AsyncSession, *, token: str | None) -> uuid.UUID | None:
    """把 cookie token 解析成 child_id；无效/过期/已撤销一律返回 None。

    **不接受 child_id 作为输入**——这是方案 3.2 的落点：身份只能从这里来。
    """
    if not token:
        return None
    row = (
        await db.execute(
            select(GuestSession).where(GuestSession.session_token_hash == hash_token(token))
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    if row.revoked_at is not None:
        return None
    now = _now()
    if row.expires_at <= now:
        return None

    # 数据保留期已过的游客，会话即使没过期也不该再访问（方案 4.3「清理完成后，
    # 旧会话无法重新访问已删除的数据」）。
    identity = await db.get(GuestIdentity, row.child_id)
    if identity is None or identity.status != "active" or identity.expires_at <= now:
        return None
    return row.child_id


async def touch_activity(db: AsyncSession, *, child_id: uuid.UUID) -> None:
    """刷新「最后一次有效学习活动」与保留期（方案 4.1）。

    调用时机严格限定为**一次有效学习活动**（首题提交），不是打开页面/看讲解——
    方案第五章对「计入每日题数」的事件定义与此一致。
    """
    settings = get_settings()
    now = _now()
    identity = await db.get(GuestIdentity, child_id)
    if identity is None or identity.status != "active":
        return
    identity.last_activity_at = now
    identity.expires_at = now + timedelta(days=settings.guest_retention_days)

    session_row = (
        await db.execute(select(GuestSession).where(GuestSession.child_id == child_id))
    ).scalars().first()
    if session_row is not None:
        session_row.last_seen_at = now
        session_row.expires_at = now + timedelta(days=settings.guest_session_days)


async def revoke_session(db: AsyncSession, *, token: str | None) -> bool:
    """主动登出（方案虽不提供登录，但用户清除本地记录需要服务端配合）。"""
    if not token:
        return False
    row = await db.get(GuestSession, hash_token(token))
    if row is None or row.revoked_at is not None:
        return False
    row.revoked_at = _now()
    return True


async def get_identity(db: AsyncSession, *, child_id: uuid.UUID) -> GuestIdentity | None:
    return await db.get(GuestIdentity, child_id)


# ---- QA 测试通道（受控口子）----

# QA 池数据的保留期设为远期：它不是真实儿童数据，且 docs/governance/QA_DATA_HYGIENE.md
# 规定 …0099 归测试池、可随时重建。若让它按 7 天过期，19 个 E2E spec 的基准数据
# 会在某天毫无预兆地消失，表现为「昨天全绿今天全红」这种最难查的故障。
QA_RETENTION_DAYS = 36500  # 100 年 ≈ 永不过期


async def bootstrap_qa_session(db: AsyncSession, *, child_id: uuid.UUID) -> str:
    """为 QA 测试池 child 签发会话（仅 E2E 用）。

    **调用方必须已校验这是 QA child 且 QA 开关已开**（见 api/guest.py）。
    本函数只负责「给已授权的 QA child 发一张长期票」，不做任何授权判断——
    授权判断留在路由层单点，避免同一条红线在两个地方各写一遍、日后改一处漏一处。
    """
    now = _now()
    identity = await db.get(GuestIdentity, child_id)
    if identity is None:
        identity = GuestIdentity(
            child_id=child_id,
            created_at=now,
            last_activity_at=now,
            expires_at=now + timedelta(days=QA_RETENTION_DAYS),
            status="active",
        )
        db.add(identity)
    else:
        identity.status = "active"
        identity.expires_at = now + timedelta(days=QA_RETENTION_DAYS)
    await db.flush()
    return await _issue_session(db, child_id=child_id)


def cookie_kwargs(*, max_age_days: int | None = None) -> dict:
    """会话 Cookie 的安全属性（方案 2.1「应采用安全的 Cookie 设置」）。

    - httponly：JS 读不到，XSS 拿不走会话；
    - samesite=lax：跨站的 POST 不带 cookie，挡掉最基础的 CSRF；
    - secure：仅在 HTTPS 部署时开启（本地 http 调试必须为 False，否则浏览器
      直接不保存 cookie，表现为「每次刷新都变新游客」这种最难查的故障）。
    """
    settings = get_settings()
    days = max_age_days if max_age_days is not None else settings.guest_session_days
    return {
        "key": SESSION_COOKIE_NAME,
        "httponly": True,
        "samesite": "lax",
        "secure": settings.guest_cookie_secure,
        "path": "/",
        "max_age": days * 24 * 3600,
    }