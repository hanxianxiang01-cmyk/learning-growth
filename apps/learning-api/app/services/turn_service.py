"""LearningTurnService —— 一次学习回合的编排（真实落库）。

链路：提交作答 → 写 Attempt → 写 LearningEvent → 诊断 → 写 MasteryEvidence → 更新 AbilityState。

这是 Sprint 2 纵向闭环的"骨架"，Sprint 1 先打通落库能力。
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.content.context_family import canonicalize_context_family
from app.models import (
    AbilityState,
    Attempt,
    LearningEvent,
    MasteryEvidence,
    ResourceVersion,
    TaskInstance,
)
from app.core.education_rules import (
    ATOMIC_EVIDENCE_TYPES,
    DEFAULT_EVIDENCE_ROLE,
    EVIDENCE_ROLE_TO_TYPE,
    RULE_VERSION,
)
from app.services.diagnosis import diagnose_v2, response_shape, response_shape_from_dict
from app.services.hint import decide_hint
from app.services.mastery_db import persist_mastery_state


class SubmissionConflict(ValueError):
    """docs/frontend/29 §3 幂等契约：同 submission_id 携带不同内容 → 409。"""


def _replay_shape(existing: Attempt, event: LearningEvent | None) -> dict:
    """重放既有 Attempt：与首发同一外形规则（V2 完整三段判定不外发）。"""
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
        "diagnosis": response_shape_from_dict(diagnosis_dict),
        "evidence_id": None,
        "next_action": next_action,
    }


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
    error_models: list | None = None,
    ui_schema: dict | None = None,
    resource_version_id: uuid.UUID | None = None,
    used_hint_levels: list[int] | None = None,
    agent_turn_id: str | None = None,
    submission_id: uuid.UUID | None = None,
) -> dict:
    """记录一次作答：写 attempt + event，产出诊断（V2 三段判定）+ next_action。

    幂等（docs/frontend/29 §3）：
    - 有 submission_id：同 ID 同内容 → 重放原 Attempt；同 ID 异内容 → SubmissionConflict(409)；
    - 无 submission_id（V1 提交）：回落到 (task_instance_id, attempt_no) 顺序号幂等（旧轨不变）。
    """

    # 1. 查 task_instance（拿 ability_id / resource_version_id / session_id）
    task = await db.get(TaskInstance, task_instance_id)
    if task is None:
        raise ValueError(f"task_instance {task_instance_id} 不存在")
    ability_id = task.ability_id
    session_id = task.session_id

    # 1.5 幂等 —— 权威轨：submission_id（V2 提交必带）
    if submission_id is not None:
        by_sub = (
            await db.execute(select(Attempt).where(Attempt.submission_id == submission_id))
        ).scalar_one_or_none()
        if by_sub is not None:
            # 同 ID 不同内容 = 客户端把一次提交改了答案又用旧 ID 重发 → 幂等契约禁止，409
            if by_sub.response != response:
                raise SubmissionConflict(
                    f"submission_id {submission_id} 已存在且内容不同（重试必须同内容）"
                )
            event = (
                await db.execute(
                    select(LearningEvent).where(LearningEvent.attempt_id == by_sub.attempt_id)
                )
            ).scalar_one_or_none()
            return _replay_shape(by_sub, event)

    # 1.6 幂等 —— 兼容轨：(task_instance_id, attempt_no)（无 submission_id 的 V1 提交，
    #     或 submission_id 新但 attempt_no 已被占用的边界；行为与旧轨一致，不 500）
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
        return _replay_shape(existing, event)

    # 2. 写 attempt
    attempt = Attempt(
        task_instance_id=task_instance_id,
        attempt_no=attempt_no,
        submission_id=submission_id,
        response=response,
        correct=correct,
        client_elapsed_ms=client_elapsed_ms,
        max_hint_level=max_hint_level,
        submitted_at=None,  # 用 server_default
    )
    db.add(attempt)
    await db.flush()

    # 3. 诊断（V2 三段判定：观察→候选→top_level_code 可为 NULL；hint 不再兜底错因）
    d = diagnose_v2(
        correct,
        error_models=error_models,
        response=response,
        ui_schema=ui_schema,
        resource_version_id=str(resource_version_id) if resource_version_id else None,
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
            # V2 完整三段判定入 event（审计/confirmed 聚合用）；对外响应只暴露有码结论
            "diagnosis": d.to_dict() if d else None,
            "max_hint_level": max_hint_level,
        },
    )
    db.add(event)

    # 5. 单 Task 单证据（B3）：首个可评分 Attempt 是该 Task 唯一的 Mastery 原子证据。
    #    后续 Retry 仍完整写 Attempt / LearningEvent（用于诊断、Hint、行为分析），
    #    但不再产/覆盖这条能力测量证据——Mastery 测"这次是否已会"，Retry 测"经教学是否学会"。
    evidence_id = None
    if correct is not None:
        existing_evidence = (
            await db.execute(
                select(MasteryEvidence).where(
                    MasteryEvidence.task_instance_id == task_instance_id,
                    MasteryEvidence.valid.is_(True),
                    MasteryEvidence.evidence_type.in_(ATOMIC_EVIDENCE_TYPES),
                )
            )
        ).scalar_one_or_none()

        if existing_evidence is None:
            # 证据角色（B2）：由 Task Assignment 决定，读 task.strategy_policy.evidence_role
            sp = task.strategy_policy if isinstance(task.strategy_policy, dict) else {}
            evidence_role = sp.get("evidence_role") or DEFAULT_EVIDENCE_ROLE
            evidence_type = EVIDENCE_ROLE_TO_TYPE.get(evidence_role, EVIDENCE_ROLE_TO_TYPE[DEFAULT_EVIDENCE_ROLE])

            # context_family（V1.4 P0 Governance Closure）：唯一来源
            # resource_version.mastery_rule.context_family（受控词表 canonical ID）。
            # Engine 只消费该值做 distinct 计数；NULL 不计入 transfer diversity。
            rv = await db.get(ResourceVersion, task.resource_version_id)
            ctx_family = None
            if rv and isinstance(rv.mastery_rule, dict):
                # 非法历史值在此被拒（UNKNOWN_CONTEXT_FAMILY），防止污染证据表
                ctx_family = canonicalize_context_family(rv.mastery_rule.get("context_family"))

            independence = {0: 1.0, 1: 0.75, 2: 0.5, 3: 0.25, 4: 0.0}[max_hint_level]
            evidence = MasteryEvidence(
                child_id=child_id,
                ability_id=ability_id,
                task_instance_id=task_instance_id,
                attempt_id=attempt.attempt_id,
                evidence_type=evidence_type,
                correctness=1.0 if correct else 0.0,
                independence=independence,
                context_family=ctx_family,
                rule_version=RULE_VERSION,
                valid=True,
            )
            db.add(evidence)
            await db.flush()
            evidence_id = evidence.evidence_id

        # 5.5 证据消化 → 能力升级：回写 AbilityState（学习闭环落点）。
        #     只有新写了证据才重算；retry 不产证据时仍可重算（幂等，成本可接受）。
        await persist_mastery_state(db, child_id=child_id, ability_id=ability_id)

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
        "diagnosis": response_shape(d),  # V2 外形：top_level_code=None → 不下发猜测标签
        "evidence_id": evidence_id,
        "next_action": next_action,
    }