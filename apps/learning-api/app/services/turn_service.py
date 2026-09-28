"""LearningTurnService —— 一次学习回合的编排（真实落库）。

链路：提交作答 → 写 Attempt → 写 LearningEvent → 诊断 → 写 MasteryEvidence → 更新 AbilityState。

这是 Sprint 2 纵向闭环的"骨架"，Sprint 1 先打通落库能力。
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AbilityState,
    Attempt,
    LearningEvent,
    MasteryEvidence,
    TaskInstance,
)
from app.services.diagnosis import diagnose
from app.services.hint import decide_hint


async def record_attempt(
    db: AsyncSession,
    *,
    child_id: uuid.UUID,
    task_instance_id: uuid.UUID,
    attempt_no: int,
    response: dict,
    correct: bool | None,
    max_hint_level: int,
    client_elapsed_ms: int | None = None,
    error_model: str | None = None,
    used_hint_levels: list[int] | None = None,
    agent_turn_id: str | None = None,
) -> dict:
    """记录一次作答：写 attempt + event，产出诊断 + next_action。"""
    used = used_hint_levels or []

    # 1. 查 task_instance（拿 ability_id / resource_version_id / session_id）
    task = await db.get(TaskInstance, task_instance_id)
    if task is None:
        raise ValueError(f"task_instance {task_instance_id} 不存在")
    ability_id = task.ability_id
    session_id = task.session_id

    # 1.5 幂等：同一 (task_instance_id, attempt_no) 重复提交时，直接返回已存在的 attempt，
    #     避免撞 attempt_task_instance_id_attempt_no_key 唯一约束（前端偶发连点/重试）。
    existing = (
        await db.execute(
            select(Attempt).where(
                Attempt.task_instance_id == task_instance_id,
                Attempt.attempt_no == attempt_no,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        event = (
            await db.execute(
                select(LearningEvent).where(LearningEvent.attempt_id == existing.attempt_id)
            )
        ).scalar_one_or_none()
        diagnosis_dict = None
        if event and isinstance(event.payload, dict):
            d_payload = event.payload.get("diagnosis")
            if isinstance(d_payload, dict):
                diagnosis_dict = d_payload
        next_action = (
            {"type": "HINT", "hint_level": existing.max_hint_level, "policy_id": f"hint-{existing.max_hint_level}"}
            if existing.correct is False
            else {"type": "NEXT_TASK", "policy_id": None}
        )
        return {
            "attempt_id": existing.attempt_id,
            "correct": existing.correct,
            "diagnosis": diagnosis_dict,
            "evidence_id": None,
            "next_action": next_action,
        }

    # 2. 写 attempt
    attempt = Attempt(
        task_instance_id=task_instance_id,
        attempt_no=attempt_no,
        response=response,
        correct=correct,
        client_elapsed_ms=client_elapsed_ms,
        max_hint_level=max_hint_level,
        submitted_at=None,  # 用 server_default
    )
    db.add(attempt)
    await db.flush()

    # 3. 诊断
    d = diagnose(
        correct,
        error_model=error_model,
        used_hint_levels=used,
        repeated_pattern=attempt_no > 1 and not correct,
    )

    # 4. 写 learning_event
    event = LearningEvent(
        child_id=child_id,
        session_id=session_id,
        task_instance_id=task_instance_id,
        attempt_id=attempt.attempt_id,
        agent_turn_id=agent_turn_id,
        event_type="attempt_submitted",
        seq_no=attempt_no,
        payload={
            "correct": correct,
            "diagnosis": d.to_dict() if d else None,
            "max_hint_level": max_hint_level,
        },
    )
    db.add(event)

    # 5. 若可评分，写原子 mastery_evidence
    evidence_id = None
    if correct is not None:
        independence = {0: 1.0, 1: 0.75, 2: 0.5, 3: 0.25, 4: 0.0}[max_hint_level]
        evidence = MasteryEvidence(
            child_id=child_id,
            ability_id=ability_id,
            task_instance_id=task_instance_id,
            attempt_id=attempt.attempt_id,
            evidence_type="attempt_standard",
            correctness=1.0 if correct else 0.0,
            independence=independence,
            rule_version="mastery-v1.3",
            valid=True,
        )
        db.add(evidence)
        await db.flush()
        evidence_id = evidence.evidence_id

    await db.flush()

    # 6. 决定 next_action —— 只返回「下一步做什么」的控制信号（对齐前端 NextAction 契约）。
    #    HINT 的详细内容（text/ladder）由 /v1/learning/hints 接口单独返回，不塞在这里。
    next_action = None
    if not correct:
        na = decide_hint(attempt_count=attempt_no, requested_level=None)
        next_action = {
            "type": "HINT",
            "hint_level": na.hint_level,
            "policy_id": na.policy_id,
        }

    return {
        "attempt_id": attempt.attempt_id,
        "correct": correct,
        "diagnosis": d.to_dict() if d else None,
        "evidence_id": evidence_id,
        "next_action": next_action,
    }