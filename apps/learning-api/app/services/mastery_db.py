"""MasteryService — DB 联表版：从 mastery_evidence + attempt 组装证据并评估。

纯计算在 app/services/mastery.py（可测），这里只负责 DB 加载与组装。
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AbilityState, Attempt, MasteryEvidence, TaskInstance
from app.services.mastery import Evidence, evaluate_mastery


async def _load_evidences(
    db: AsyncSession, child_id: uuid.UUID, ability_id: str
) -> list[Evidence]:
    """从 DB 加载某能力全部有效原子证据，组装为纯计算用的 Evidence。

    resource_version_id / session_id 用于 L1→L2 的跨资源/跨 Session 多样性 Gate。
    """
    ev_rows = (
        await db.execute(
            select(MasteryEvidence).where(
                MasteryEvidence.child_id == child_id,
                MasteryEvidence.ability_id == ability_id,
                MasteryEvidence.valid.is_(True),
            )
        )
    ).scalars().all()

    attempt_ids = [e.attempt_id for e in ev_rows if e.attempt_id]
    hint_map: dict[uuid.UUID, int] = {}
    task_map: dict[uuid.UUID, TaskInstance] = {}
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
            task_map = {t.task_instance_id: t for t in task_rows}

    evidences = [
        Evidence(
            evidence_id=e.evidence_id,
            evidence_type=e.evidence_type,
            correctness=float(e.correctness) if e.correctness is not None else None,
            independence=float(e.independence) if e.independence is not None else None,
            max_hint_level=hint_map.get(e.attempt_id, 0) if e.attempt_id else 0,
            context_family=e.context_family,
            resource_version_id=(
                task_map[e.task_instance_id].resource_version_id
                if e.task_instance_id in task_map
                else None
            ),
            session_id=(
                task_map[e.task_instance_id].session_id
                if e.task_instance_id in task_map
                else None
            ),
        )
        for e in ev_rows
    ]
    return evidences


def _derive_trend(old_level: int, new_level: int) -> str:
    if new_level > old_level:
        return "up"
    if new_level < old_level:
        return "down_review"
    return "stable"


async def evaluate_mastery_from_db(
    db: AsyncSession,
    child_id: uuid.UUID,
    ability_id: str,
) -> dict:
    """从 DB 加载有效证据组装为 Evidence 后走纯计算（只读，不回写）。"""
    evidences = await _load_evidences(db, child_id, ability_id)

    state = await db.get(AbilityState, {"child_id": child_id, "ability_id": ability_id})
    old_level = state.level if state else 0

    return evaluate_mastery(ability_id, old_level, evidences).to_dict()


async def persist_mastery_state(
    db: AsyncSession,
    child_id: uuid.UUID,
    ability_id: str,
) -> dict:
    """证据消化 → 能力升级：加载证据、评估、回写 AbilityState。

    这是「学习闭环」的落点——孩子做完题后，把 mastery_evidence 汇总成
    能力等级/置信度/证据数/趋势，写回 ability_state 供画像与选题使用。
    """
    evidences = await _load_evidences(db, child_id, ability_id)

    state = await db.get(AbilityState, {"child_id": child_id, "ability_id": ability_id})
    old_level = state.level if state else 0

    ev = evaluate_mastery(ability_id, old_level, evidences)

    evidence_count = len(evidences)

    # confidence 兜底：四维未凑齐时 score 为 None，用 correctness 近似（再有值则 0.0）；
    # 意义是「当前能力状态的置信度」，并非 strict mastery score。
    confidence = ev.score if ev.score is not None else (ev.correctness if ev.correctness is not None else 0.0)

    if state is None:
        state = AbilityState(
            child_id=child_id,
            ability_id=ability_id,
            level=ev.new_level,
            confidence=round(float(confidence), 4),
            evidence_count=evidence_count,
            trend=_derive_trend(old_level, ev.new_level),
        )
        db.add(state)
    else:
        state.level = ev.new_level
        state.confidence = round(float(confidence), 4)
        state.evidence_count = evidence_count
        state.trend = _derive_trend(old_level, ev.new_level)
        state.last_evidence_at = (
            datetime.now(timezone.utc) if evidence_count else state.last_evidence_at
        )

    await db.flush()

    return {
        "ability_id": ability_id,
        "old_level": old_level,
        "new_level": ev.new_level,
        "score": round(ev.score, 4) if ev.score is not None else None,
        "decision": ev.decision,
        "missing_evidence": ev.missing_evidence,
        "evidence_count": evidence_count,
        "trend": _derive_trend(old_level, ev.new_level),
    }