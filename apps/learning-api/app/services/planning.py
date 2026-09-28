"""CurriculumPlanningService —— learning_plan 最小 create / get-current。"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LearningPlan


async def create_plan(
    db: AsyncSession,
    *,
    child_id: uuid.UUID,
    subject: str,
    plan_type: str = "adaptive",
    target_ability_ids: list[str] | None = None,
    fit_band: dict | None = None,
    rationale: dict | None = None,
    generated_by: str = "curriculum_engine",
    rule_version: str = "curriculum-v1.3",
) -> LearningPlan:
    plan = LearningPlan(
        child_id=child_id,
        subject=subject,
        plan_type=plan_type,
        target_ability_ids=target_ability_ids or [],
        fit_band=fit_band or {},
        rationale=rationale or {},
        generated_by=generated_by,
        rule_version=rule_version,
    )
    db.add(plan)
    await db.flush()
    return plan


async def get_current_plan(
    db: AsyncSession,
    *,
    child_id: uuid.UUID,
    subject: str,
) -> LearningPlan | None:
    """返回当前 active 计划（按创建时间倒序取最新一条 active）。"""
    result = await db.execute(
        select(LearningPlan)
        .where(
            LearningPlan.child_id == child_id,
            LearningPlan.subject == subject,
            LearningPlan.status == "active",
        )
        .order_by(LearningPlan.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def plan_to_dict(p: LearningPlan) -> dict:
    return {
        "plan_id": p.plan_id,
        "child_id": p.child_id,
        "subject": p.subject,
        "status": p.status,
        "target_ability_ids": p.target_ability_ids,
        "fit_band": p.fit_band,
        "rationale": p.rationale,
        "rule_version": p.rule_version,
        "valid_from": p.valid_from,
        "valid_until": p.valid_until,
    }