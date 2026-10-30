"""每日题数配额（V1.4 纯游客模式 P2，方案第五章）。

方案点名的绕过路径与处理：

| 绕过方式 | 处理 |
|---|---|
| 刷新页面 | 计数与页面无关，只在「首题有效提交」时记一笔 |
| 改前端状态 | 计数在服务端，客户端没有任何可改的开关 |
| 重复提交同一题 | 台账主键 (child_id, task_instance_id)，天然幂等 |
| 网络重试 | 同上，重试落同一行，不增计数 |
| 同一题多次作答 | 同上（一题只计一次，与方案「首次有效提交一题」一致） |
| 并发请求 | 台账主键冲突即视为已计；`ON CONFLICT DO NOTHING` 原子去重 |
| 跨日边界 | quota_date 由服务端按固定时区换算，不信任客户端时间 |
| 客户端时间与服务端不一致 | 完全不用客户端时间 |
| 统计时区不固定 | `guest_quota_timezone`（默认 Asia/Shanghai），IANA 名称不随夏令时漂 |

**「计入每日题数」的口径**（方案原文「首次有效提交一题」）：本文把
「该题在本游客名下第一次进入计分阶段」记为 1 题。判定点是提交作答（submit），
不是取题（tasks/next）——取题未作答不算学习，这一点与方案原文一致。

为何用台账而不是计数器：计数器回答不了「这道题计过没有」，上表前两行
（重复提交、网络重试）就会被刷开。台账让每次计数先过唯一键。
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import GuestDailyQuota


def quota_date_for(now: datetime | None = None, *, tz_name: str | None = None) -> date:
    """把一个时刻换算成「统计时区下的日期」。

    纯函数、显式时区——不接受客户端传入的任何时间。测试可直接传 now 覆盖。
    """
    settings = get_settings()
    tz = ZoneInfo(tz_name or settings.guest_quota_timezone)
    moment = now if now is not None else datetime.now(tz)
    if moment.tzinfo is None:
        # 无时区的裸时间不可解释（是哪个时区的 23:30？），直接拒绝比猜测安全。
        raise ValueError("quota_date_for 需要带时区的 datetime")
    return moment.astimezone(tz).date()


async def count_for_day(db: AsyncSession, *, child_id: uuid.UUID, day: date) -> int:
    return int(
        (
            await db.execute(
                select(func.count())
                .select_from(GuestDailyQuota)
                .where(
                    GuestDailyQuota.child_id == child_id,
                    GuestDailyQuota.quota_date == day,
                )
            )
        ).scalar_one()
    )


async def remaining(db: AsyncSession, *, child_id: uuid.UUID, day: date | None = None) -> int:
    settings = get_settings()
    d = day or quota_date_for()
    used = await count_for_day(db, child_id=child_id, day=d)
    return max(0, settings.guest_daily_task_limit - used)


async def is_over_limit(
    db: AsyncSession, *, child_id: uuid.UUID, task_instance_id: uuid.UUID
) -> bool:
    """是否应当拒绝这次提交。

    **已经计过的题不受上限拦截**——否则恰好卡在 30 题边界时，第 30 题的
    重试/幂等重放会被误拒，把「重试不能算新题」变成「重试直接失败」。
    这个判断顺序是有意的：先看是不是老题，再判断新题有没有额度。
    """
    settings = get_settings()
    day = quota_date_for()

    already = (
        await db.execute(
            select(GuestDailyQuota.task_instance_id).where(
                GuestDailyQuota.child_id == child_id,
                GuestDailyQuota.task_instance_id == task_instance_id,
            )
        )
    ).scalar_one_or_none()
    if already is not None:
        return False

    return await count_for_day(db, child_id=child_id, day=day) >= settings.guest_daily_task_limit


async def record_task_consumed(
    db: AsyncSession, *, child_id: uuid.UUID, task_instance_id: uuid.UUID
) -> bool:
    """记一题。返回 True = 本次新计入，False = 之前已计过（幂等命中）。

    `on_conflict_do_nothing` 让并发重复提交只有一方能插入成功，另一方不增计数。
    """
    day = quota_date_for()
    result = await db.execute(
        pg_insert(GuestDailyQuota)
        .values(
            child_id=child_id,
            task_instance_id=task_instance_id,
            quota_date=day,
        )
        .on_conflict_do_nothing(
            index_elements=[GuestDailyQuota.child_id, GuestDailyQuota.task_instance_id]
        )
        .returning(GuestDailyQuota.task_instance_id)
    )
    return result.scalar_one_or_none() is not None


async def usage_summary(db: AsyncSession, *, child_id: uuid.UUID) -> dict:
    """首页展示用（方案第五章「达到上限时，显示清晰提示，并允许查看已产生的学习记录」）。"""
    settings = get_settings()
    day = quota_date_for()
    used = await count_for_day(db, child_id=child_id, day=day)
    return {
        "date": day.isoformat(),
        "timezone": settings.guest_quota_timezone,
        "limit": settings.guest_daily_task_limit,
        "used": used,
        "remaining": max(0, settings.guest_daily_task_limit - used),
        "exhausted": used >= settings.guest_daily_task_limit,
    }