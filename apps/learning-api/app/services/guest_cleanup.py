"""过期游客数据清理（V1.4 纯游客模式 P2，方案 4.2/4.3）。

方案 4.2 要求逐条做，本文对应关系：

| 方案要求 | 实现 |
|---|---|
| 查找已过期的游客学习数据 | `expires_at <= now AND status='active'` |
| 按游客身份清理作答、错题、提示、学习证据及相关进度 | 见下方 `_PURGE_ORDER`（按外键拓扑顺序） |
| 清理不再需要的游客会话 | guest_session 随 guest_identity 级联 |
| 处理关联记录和孤立记录 | 顶层按 child_id 精确删除；外键顺序保证无残留 |
| 输出清理数量、执行时间和失败信息 | 写 `guest_cleanup_run`（scanned/purged/failed/detail） |
| 对失败任务提供可重试机制 | 每次运行独立事务、逐游客提交；失败者保持 active，下次自动重试 |

**为什么写运行记录表而不是只打日志**：方案 4.3 要求「定时任务实际运行，而不是
只通过单元测试」。日志在滚动/tmp 里会消失，`guest_cleanup_run` 是可 SQL 核对的
证据——验收时 `SELECT * FROM guest_cleanup_run` 就能看到每次真实执行。

**删除顺序**（依据 pg_constraint 的真实外键图拓扑排序，不是凭记忆）：
learning_event / mastery_evidence（都外键引用 attempt，必须先删）→ attempt
→ task_instance → learning_session → growth_report（引用 growth_snapshot）
→ growth_snapshot → textbook_profile / ability_state / audio_asset（引用
consent_record）/ consent_record / learning_plan（被 learning_session RESTRICT
引用，须在 session 之后）→ guest_daily_quota / guest_session → guest_identity
→ child → guardian。

**10-29 实测教训**：本函数初版把 attempt 排在 learning_event 之前，真实库上
`DELETE FROM attempt` 直接撞 `learning_event_attempt_id_fkey`。单元测试没抓到
（没造 event→attempt 的真实关联），只有对真库跑才暴露。后果严重：生产上任何
有作答记录的游客清理 100% 失败，且失败者保持 active 自动重试 → 永远失败永远
重试。删表顺序这类约束**必须以数据库外键图为唯一事实源**。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.qa import QA_CHILD_ID
from app.models import (
    AbilityState,
    Attempt,
    AudioAsset,
    Child,
    ConsentRecord,
    GrowthReport,
    GrowthSnapshot,
    Guardian,
    GuestCleanupRun,
    GuestDailyQuota,
    GuestIdentity,
    GuestSession,
    LearningEvent,
    LearningPlan,
    LearningSession,
    MasteryEvidence,
    TaskInstance,
    TextbookProfile,
)

# **仅第 5 层**：只引用 child/guardian、且不引用其他业务表的表。
# learning_event / mastery_evidence / audio_asset / growth_report 已在
# purge_one_guest 的第 1~3 层显式删（它们引用 attempt / task_instance /
# growth_snapshot / consent_record）。**不能在这里重复列**——重复 delete 会把
# counts 覆盖成 0，清理报告的数字就说谎了（形态 40：同一个键两处赋值）。
_PURGE_BY_CHILD = [
    (GrowthSnapshot, "child_id"),
    (TextbookProfile, "child_id"),
    (AbilityState, "child_id"),
    (ConsentRecord, "child_id"),
    (LearningPlan, "child_id"),
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def purge_one_guest(db: AsyncSession, *, child_id: uuid.UUID) -> dict:
    """清理单个游客的全部个人数据。调用方负责 commit。

    顺序 = pg_constraint 外键图的拓扑序（10-29 对真库实测后修正）：
      learning_event / mastery_evidence（引用 attempt）
      → attempt（引用 task_instance）
      → audio_asset（引用 task_instance、consent_record）/ growth_report（引用
        growth_snapshot）/ task_instance（引用 learning_session）
      → learning_session（RESTRICT 引用 learning_plan）
      → learning_plan / ability_state / consent_record / growth_snapshot /
        textbook_profile
      → guest_daily_quota / guest_session / guest_identity → child → guardian
    """
    counts: dict[str, int] = {}

    task_ids = (
        await db.execute(select(TaskInstance.task_instance_id).where(TaskInstance.child_id == child_id))
    ).scalars().all()
    session_ids = (
        await db.execute(select(LearningSession.session_id).where(LearningSession.child_id == child_id))
    ).scalars().all()

    # 第 1 层：引用 attempt 的表必须先删
    r = await db.execute(delete(LearningEvent).where(LearningEvent.child_id == child_id))
    counts["learning_event"] = r.rowcount or 0
    r = await db.execute(delete(MasteryEvidence).where(MasteryEvidence.child_id == child_id))
    counts["mastery_evidence"] = r.rowcount or 0

    # 第 2 层：attempt
    if task_ids:
        r = await db.execute(delete(Attempt).where(Attempt.task_instance_id.in_(task_ids)))
        counts["attempt"] = r.rowcount or 0

    # 第 3 层：引用 task_instance / growth_snapshot / consent_record 的表
    r = await db.execute(delete(AudioAsset).where(AudioAsset.child_id == child_id))
    counts["audio_asset"] = r.rowcount or 0
    r = await db.execute(delete(GrowthReport).where(GrowthReport.child_id == child_id))
    counts["growth_report"] = r.rowcount or 0
    if task_ids:
        r = await db.execute(
            delete(TaskInstance).where(TaskInstance.task_instance_id.in_(task_ids))
        )
        counts["task_instance"] = r.rowcount or 0

    # 第 4 层：learning_session（被 task_instance 引用，且 RESTRICT 引用 learning_plan）
    if session_ids:
        r = await db.execute(
            delete(LearningSession).where(LearningSession.session_id.in_(session_ids))
        )
        counts["learning_session"] = r.rowcount or 0

    # 第 5 层：其余只引用 child/guardian 的表
    for model, col in _PURGE_BY_CHILD:
        r = await db.execute(delete(model).where(getattr(model, col) == child_id))
        counts[model.__tablename__] = r.rowcount or 0

    # 第 6 层：游客模式自有表（对 guest_identity 是 CASCADE，显式删更可读）
    r = await db.execute(delete(GuestDailyQuota).where(GuestDailyQuota.child_id == child_id))
    counts["guest_daily_quota"] = r.rowcount or 0
    r = await db.execute(delete(GuestSession).where(GuestSession.child_id == child_id))
    counts["guest_session"] = r.rowcount or 0

    # 第 7 层：身份与 child/guardian
    guardian_id = (
        await db.execute(select(Child.guardian_id).where(Child.child_id == child_id))
    ).scalar_one_or_none()

    await db.execute(delete(GuestIdentity).where(GuestIdentity.child_id == child_id))
    await db.execute(delete(Child).where(Child.child_id == child_id))
    if guardian_id is not None:
        # 只删「名下已无孩子」的 guardian——演示家长等其他记录不受影响
        still = (
            await db.execute(select(Child.child_id).where(Child.guardian_id == guardian_id).limit(1))
        ).scalar_one_or_none()
        if still is None:
            await db.execute(delete(Guardian).where(Guardian.guardian_id == guardian_id))
            counts["guardian"] = 1

    counts["child"] = 1
    return counts


async def run_cleanup(
    db: AsyncSession, *, dry_run: bool = False, batch_limit: int = 500
) -> dict:
    """执行一轮清理，返回本次运行摘要（同时写入 guest_cleanup_run）。

    `dry_run=True` 只统计不删除，用于验收时先对账再动手。
    """
    started = _now()
    run = GuestCleanupRun(started_at=started, status="running")
    if not dry_run:
        db.add(run)
        await db.commit()
        await db.refresh(run)

    expired_ids = (
        await db.execute(
            select(GuestIdentity.child_id)
            .where(
                GuestIdentity.status == "active",
                GuestIdentity.expires_at <= started,
                # **绝不清 QA 测试池**：…0099 是 19 个 E2E spec 的基准数据，
                # docs/governance/QA_DATA_HYGIENE.md 明确它归测试池、由 QA 脚本管理。
                # 清理任务若把它删掉，E2E 会以「找不到 child」整片失败，
                # 且现场看起来像「清理功能有 bug」，排查方向完全错。
                GuestIdentity.child_id != QA_CHILD_ID,
            )
            .limit(batch_limit)
        )
    ).scalars().all()

    purged = 0
    failed = 0
    failures: list[dict] = []
    detail: dict[str, int] = {}

    for cid in expired_ids:
        if dry_run:
            continue
        try:
            counts = await purge_one_guest(db, child_id=cid)
            await db.commit()
            purged += 1
            for k, v in counts.items():
                detail[k] = detail.get(k, 0) + int(v)
        except Exception as e:  # noqa: BLE001 —— 单个游客失败不能拖垮整轮
            await db.rollback()
            failed += 1
            # 失败者保持 active，下一轮自动重试（方案 4.2「对失败任务提供可重试机制」）
            failures.append({"child_id": str(cid), "error": f"{type(e).__name__}: {e}"})

    finished = _now()
    summary = {
        "run_id": str(run.run_id) if not dry_run else None,
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "duration_ms": int((finished - started).total_seconds() * 1000),
        "scanned": len(expired_ids),
        "purged": purged,
        "failed": failed,
        "dry_run": dry_run,
        "rows_by_table": detail,
        "failures": failures,
    }

    if not dry_run:
        if failed == 0:
            status = "succeeded"
        elif purged > 0:
            status = "partial"
        else:
            status = "failed"
        run.finished_at = finished
        run.scanned = len(expired_ids)
        run.purged = purged
        run.failed = failed
        run.status = status
        run.detail = {"rows_by_table": detail, "failures": failures}
        await db.commit()
        summary["status"] = status

    return summary


async def list_recent_runs(db: AsyncSession, *, limit: int = 20) -> list[dict]:
    """验收用：证明清理真的跑过（方案 4.3）。"""
    rows = (
        await db.execute(
            select(GuestCleanupRun).order_by(GuestCleanupRun.started_at.desc()).limit(limit)
        )
    ).scalars().all()
    return [
        {
            "run_id": str(r.run_id),
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "scanned": r.scanned,
            "purged": r.purged,
            "failed": r.failed,
            "status": r.status,
            "detail": r.detail,
        }
        for r in rows
    ]


async def assert_guest_tables_exist(db: AsyncSession) -> bool:
    """自检：增量 DDL 是否已执行。缺失时给明确 500 而不是让查询以怪异方式失败。"""
    res = await db.execute(
        text(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_name IN ('guest_identity','guest_session',"
            "'guest_daily_quota','guest_cleanup_run')"
        )
    )
    return int(res.scalar_one()) == 4