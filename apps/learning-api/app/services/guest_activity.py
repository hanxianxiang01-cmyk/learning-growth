"""作答台账（原「每日配额」，2026-11-01 起取消每日上限）。

## 为什么还留着这张表

产品决策取消了「每天最多 30 道题」的硬限制，但**「今天真实做了几道题」**
本身仍有价值：首页说「今天已经答了 3 道」、结果页说「作答尝试 4 次」，
都是孩子看得到的真实记录。台账负责回答这个计数，**不再参与准入判断**。

界线必须分清（否则很容易把取消的限制偷偷加回来）：

- 台账 = **记录**。它只增不改，谁也不能因为台账数字去拒绝一次正常作答。
- 频率限流 = **准入**。防脚本刷接口，见 `services/rate_limit.py`，
  与学习量无关（正常作答一分钟到不了 20 次提交）。
- 掌握程度 = **mastery 四维**（正确率/独立性/稳定性/迁移）。
  「做了 30 道」不是掌握的证据，`education_rules.MASTERY_WEIGHTS` 里
  没有任何一项可以由题数直接推出。

## 计一题的口径

「该题在本游客名下第一次进入计分阶段」记为 1 题。判定点是提交作答（submit），
不是取题（tasks/next）——取题未作答不算学习。

## 为什么用台账而不是计数器

计数器回答不了「这道题计过没有」，重复提交、网络重试、并发请求都会被重复计数。
台账主键 (child_id, task_instance_id) + `ON CONFLICT DO NOTHING` 让这些问题
一起消失：重试落同一行，不增计数。

跨日边界：`activity_date_for` 由服务端按固定时区换算，完全不用客户端时间。
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


def activity_date_for(now: datetime | None = None, *, tz_name: str | None = None) -> date:
    """把一个时刻换算成「统计时区下的日期」。

    纯函数、显式时区——不接受客户端传入的任何时间。测试可直接传 now 覆盖。
    """
    settings = get_settings()
    tz = ZoneInfo(tz_name or settings.guest_quota_timezone)
    moment = now if now is not None else datetime.now(tz)
    if moment.tzinfo is None:
        # 无时区的裸时间不可解释（是哪个时区的 23:30？），直接拒绝比猜测安全。
        raise ValueError("activity_date_for 需要带时区的 datetime")
    return moment.astimezone(tz).date()


async def count_for_day(db: AsyncSession, *, child_id: uuid.UUID, day: date) -> int:
    """该游客在某一天**真实作答过**的题数（去重后）。"""
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


async def record_task_consumed(
    db: AsyncSession, *, child_id: uuid.UUID, task_instance_id: uuid.UUID
) -> bool:
    """记一题。返回 True = 本次新计入，False = 之前已计过（幂等命中）。

    `on_conflict_do_nothing` 让并发重复提交只有一方能插入成功，另一方不增计数。
    这里**不返回、也不判断任何上限**：记录归记录，准入归限流。
    """
    day = activity_date_for()
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


async def activity_summary(db: AsyncSession, *, child_id: uuid.UUID) -> dict:
    """今天的学习活动摘要（**不含** limit / remaining / exhausted）。

    这三个字段曾经是「每日 30 题」的载体。产品取消上限后它们没有意义：
    留着 `remaining: 999999` 之类的假值，会让下一个人以为上限还在、只是很大。
    需要「还能不能继续学」的判断在别处——答案是永远可以，只有休息提醒。
    """
    settings = get_settings()
    day = activity_date_for()
    used = await count_for_day(db, child_id=child_id, day=day)
    return {
        "date": day.isoformat(),
        "timezone": settings.guest_quota_timezone,
        "answered_today": used,
    }
