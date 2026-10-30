"""游客模式数据模型（V1.4 纯游客模式设计方案 P1/P2）。

设计约束（重要，改动前必读）：

1. **不修改冻结的 18 张基线表**（baselines/learning-core-v1.3.1/01_schema_postgresql_v1.3.1.sql）。
   `child` 表不加 `is_guest` 列——「这个 child 是游客」这件事由 `guest_identity` 表
   的存在性表达。理由是基线 DDL 受 validate_ddl.py / GATE 约束，加列属基线漂移；
   而新增表不改变任何已有表的语义。

2. **一个游客 = 一行 child + 一行 guardian + 一行 guest_identity**。
   之所以复用 child 表（方案 3.1 原文授权「字段名称可按现有数据库规范调整，不要求
   为了游客模式重建全部业务表」）：9 张表外键指向 child(child_id)，复用后全部
   现有服务层、判分链路、选题链路零改动。若另起 guest 表，这 9 处外键和服务层
   查询都要分叉，改动量翻数倍且长期双身份并存。

3. **guest_id 就是 child_id**，不存在第二个身份标识。方案 2.1「不使用固定的公共
   游客 ID」「不同游客必须拥有不同的身份标识」由「每次创建都 gen_random_uuid()」
   保证。

4. **会话令牌只存哈希**。`guest_session.session_token_hash` 存 sha256(token)，
   数据库泄露不等于会话可被冒用。方案 2.1「guest_id 是系统内部标识，不应被视为
   认证凭证本身」即指此：能证明身份的是 cookie 里的 token，不是 child_id。
"""
import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GuestIdentity(Base):
    """游客身份与生命周期（方案 2.2 / 4.1）。

    `expires_at` = 最后一次有效学习活动 + 保留期（默认 7 天）。
    游客会话失效（guest_session 过期）与学习数据删除（本行被清理）是两个独立
    概念——方案 4.1 明确要求区分，故本表与 guest_session 分开。
    """

    __tablename__ = "guest_identity"
    __table_args__ = (
        CheckConstraint("status IN ('active','expired','purged')", name="guest_identity_status_check"),
        CheckConstraint("expires_at >= created_at", name="guest_identity_expires_after_create"),
        Index(
            "idx_guest_identity_expires",
            "expires_at",
            postgresql_where="status = 'active'",
        ),
    )

    child_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("child.child_id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")


class GuestSession(Base):
    """游客会话（方案 2.1 建议的服务端会话 + 安全 Cookie）。

    主键是 **token 的 sha256 十六进制**，明文 token 只在签发那一次出现在响应里，
    之后仅存在于浏览器 HttpOnly Cookie 中。故本表被读走也无法直接冒用会话。
    """

    __tablename__ = "guest_session"
    __table_args__ = (Index("idx_guest_session_child", "child_id"),)

    session_token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    child_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("guest_identity.child_id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GuestDailyQuota(Base):
    """每日题数台账（方案第五章）。

    一行 = 「某游客在某一天把某道题计为 1 题」。主键 (child_id, task_instance_id)
    让同一道题的重复提交天然幂等——不管重试几次、并发几次，都只会计 1 题；
    `quota_date` 由服务端在**固定时区**换算，不信任客户端时间。

    之所以用台账而不是计数器：计数器无法回答「这道题计过没有」，重复提交/网络
    重试会把计数刷上去，正是方案第五章点名要防的绕过路径。
    """

    __tablename__ = "guest_daily_quota"
    __table_args__ = (Index("idx_guest_quota_day", "child_id", "quota_date"),)

    child_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("guest_identity.child_id", ondelete="CASCADE"),
        primary_key=True,
    )
    task_instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    quota_date: Mapped[date] = mapped_column(Date, nullable=False)
    counted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class GuestCleanupRun(Base):
    """清理任务运行记录（方案 4.2「输出清理数量、执行时间和失败信息」「失败可重试」）。

    没有这张表，「清理任务真实运行过」就只能是口头声明——方案 4.3 要求
    「定时任务实际运行，而不是只通过单元测试」，运行记录是唯一可核对的证据。
    """

    __tablename__ = "guest_cleanup_run"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running','succeeded','partial','failed')",
            name="guest_cleanup_run_status_check",
        ),
        Index("idx_guest_cleanup_run_started", "started_at"),
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scanned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    purged: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    detail: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)