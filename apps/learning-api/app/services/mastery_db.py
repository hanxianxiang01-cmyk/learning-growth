"""MasteryService — DB 联表版：从 mastery_evidence + attempt 组装证据并评估。

纯计算在 app/services/mastery.py（可测），这里只负责 DB 加载与组装。
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AbilityState, Attempt, MasteryEvidence, TaskInstance
from app.services.mastery import Evidence, evaluate_mastery


async def evaluate_mastery_from_db(
    db: AsyncSession,
    child_id: uuid.UUID,
    ability_id: str,
) -> dict:
    """从 DB 加载有效证据（含 attempt 的 max_hint_level / task 的 resource_version），
    组装为 Evidence 后走纯计算。"""

    # 1. 有效证据
    ev_rows = (
        await db.execute(
            select(MasteryEvidence).where(
                MasteryEvidence.child_id == child_id,
                MasteryEvidence.ability_id == ability_id,
                MasteryEvidence.valid.is_(True),
            )
        )
    ).scalars().all()

    # 2. 关联 attempt / task 补充 max_hint_level / resource_version_id
    attempt_ids = [e.attempt_id for e in ev_rows if e.attempt_id]
    hint_map: dict[uuid.UUID, int] = {}
    rv_map: dict[uuid.UUID, uuid.UUID] = {}
    if attempt_ids:
        att_rows = (
            await db.execute(select(Attempt).where(Attempt.attempt_id.in_(attempt_ids)))
        ).scalars().all()
        hint_map = {a.attempt_id: a.max_hint_level for a in att_rows}

        task_ids = [a.task_instance_id for a in att_rows]
        if task_ids:
            task_rows = (
                await db.execute(
                    select(TaskInstance).where(TaskInstance.task_instance_id.in_(task_ids))
                )
            ).scalars().all()
            rv_map = {t.task_instance_id: t.resource_version_id for t in task_rows}

    evidences = [
        Evidence(
            evidence_id=e.evidence_id,
            evidence_type=e.evidence_type,
            correctness=float(e.correctness) if e.correctness is not None else None,
            independence=float(e.independence) if e.independence is not None else None,
            max_hint_level=hint_map.get(e.attempt_id, 0) if e.attempt_id else 0,
            context_family=e.context_family,
        )
        for e in ev_rows
    ]

    # 3. 当前能力等级
    state = await db.get(AbilityState, {"child_id": child_id, "ability_id": ability_id})
    old_level = state.level if state else 0

    return evaluate_mastery(ability_id, old_level, evidences).to_dict()