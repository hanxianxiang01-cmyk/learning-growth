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


def evidence_eligible(correct: bool | None, process_validation: dict | None) -> bool:
    """FE-1466 证据资格判定（纯函数，锁测面）：
    - 未判分（None：缺失/不可验证/无答案）→ 不产（决策2）；
    - 终值对+过程矛盾 且 策略不允许负向归因（money/pv）→ 不产（决策3：
      不写未经能力映射确认的负向证据）；
    - 其余已判分结果 → 产（正向=1.0/负向按现行答错规则）。
    未声明过程约束的旧题 process_validation=None → 行为逐比特不变。"""
    if correct is None:
        return False
    if (correct is False and process_validation is not None
            and process_validation.get("status") == "contradiction"
            and not process_validation.get("negative_evidence_allowed", False)):
        return False
    return True


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
    process_validation: dict | None = None,
) -> dict:
    """记录一次作答：写 attempt + event，产出诊断（V2 三段判定）+ next_action。

    FE-1466 Q07（契约 process_contract_frozen_v2.json）：
    - process_validation=统一过程校验结果（无声明题=None，行为逐比特不变）；
    - 证据资格（§三.2/决策2）：仅"已判分且过程合格或按策略允许归因"的结果
      产 Mastery Evidence——missing/unverifiable 调用方已置 correct=None
      天然跳过；contradiction 且 negative_evidence_allowed=False（money/pv）
      的答错**不写负向证据**（Attempt/Event/诊断照常）；
    - correct=null（任务未完成/不可验证）不进入答错 HINT 阶梯（§三.1 breach
      修复：`if not correct`→`if correct is False`）。
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
    # FE-1466 §三.2 证据资格：终值对+过程矛盾但策略不允许负向归因（money/pv）
    # → 不产负向证据（Attempt/Event/反馈照常；correct=False 仅作任务完成态）。
    _neg_gated = (
        correct is False and process_validation is not None
        and process_validation.get("status") == "contradiction"
        and not process_validation.get("negative_evidence_allowed", False)
    )
    if correct is not None and not _neg_gated:
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
    if (correct is None and process_validation is not None
            and process_validation.get("status") in ("missing", "unverifiable")):
        # FE-1466 §三.1 breach 修复：过程缺失/不可验证的 null=任务未完成 ≠ 答错
        # ——不进 decide_hint 阶梯与错因诊断；Retry 原任务继续操作（决策2），
        # 用冻结枚举内 RETRY 码；前端按 process_status 分支（§一边界1）。
        next_action = {
            "type": "RETRY",
            "policy_id": "process_" + process_validation["status"],
            "process_status": process_validation["status"],
        }
    elif not correct:
        # 原语义逐比特保留：答错（False）与既有 undefined-answer（None 且无
        # 过程声明）仍走 HINT 阶梯——新分支只截走 missing/unverifiable null。
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
        **({"process_status": process_validation["status"],
            "process_reason": process_validation.get("reason_code")}
           if process_validation else {}),
    }