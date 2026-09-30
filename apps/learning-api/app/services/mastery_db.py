"""MasteryService — DB 联表版：从 mastery_evidence + attempt 组装证据并评估。

纯计算在 app/services/mastery.py（可测），这里只负责 DB 加载与组装。
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.education_rules import (
    RULE_VERSION,
    STABILITY_MIN_RESOURCE_VERSIONS,
    STABILITY_MIN_SESSIONS,
    STABILITY_WINDOW,
    TRANSFER_MIN_CONTEXT_FAMILIES,
    TRANSFER_MIN_ROWS,
    TRANSFER_MIN_SESSIONS,
    TRANSFER_WINDOW_MAX,
)
from app.models import AbilityNode, AbilityState, Attempt, MasteryEvidence, TaskInstance
from app.services.mastery import Evidence, decide_review, evaluate_mastery


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


def _window_signature(
    ability_id: str, evidence_type: str, source_ids: list[uuid.UUID]
) -> str:
    """派生窗口的幂等签名：同 signature 不重复写（避免 evaluate 多次产生重复派生记录）。"""
    canon = f"{ability_id}|{evidence_type}|" + ",".join(str(i) for i in sorted(source_ids))
    return hashlib.sha1(canon.encode("utf-8")).hexdigest()


async def _persist_derived_windows(
    db: AsyncSession,
    child_id: uuid.UUID,
    ability_id: str,
    evidences: list[Evidence],
) -> None:
    """B6：满足覆盖后写 stability_window / transfer_window 派生证据（幂等）。

    派生证据带 source_evidence_ids（可追溯）+ metadata.window_signature（幂等）。
    """
    # Stability window：最近 STABILITY_WINDOW 条 standard/retention，需 ≥3 resource、≥2 session
    stability_eligible = [
        e for e in evidences
        if e.evidence_type in ("attempt_standard", "retention_check")
        and e.correctness is not None
    ][:STABILITY_WINDOW]
    if (
        len(stability_eligible) >= STABILITY_WINDOW
        and len({e.resource_version_id for e in stability_eligible if e.resource_version_id}) >= STABILITY_MIN_RESOURCE_VERSIONS
        and len({e.session_id for e in stability_eligible if e.session_id}) >= STABILITY_MIN_SESSIONS
    ):
        src_ids = [e.evidence_id for e in stability_eligible]
        sig = _window_signature(ability_id, "stability_window", src_ids)
        stability_value = sum(e.correctness * e.effective_independence for e in stability_eligible) / len(stability_eligible)
        exists = (
            await db.execute(
                select(MasteryEvidence).where(
                    MasteryEvidence.ability_id == ability_id,
                    MasteryEvidence.evidence_type == "stability_window",
                    MasteryEvidence.metadata_["window_signature"].as_string() == sig,
                    MasteryEvidence.valid.is_(True),
                )
            )
        ).scalar_one_or_none()
        if exists is None:
            db.add(
                MasteryEvidence(
                    child_id=child_id,
                    ability_id=ability_id,
                    evidence_type="stability_window",
                    stability=round(stability_value, 4),
                    source_evidence_ids=src_ids,
                    rule_version=RULE_VERSION,
                    valid=True,
                    metadata_={"window_signature": sig},
                )
            )

    # Transfer window：最近最多 4 条 attempt_transfer，需 ≥2 条、≥2 context、≥2 session
    transfer_eligible = [
        e for e in evidences
        if e.evidence_type == "attempt_transfer" and e.correctness is not None
    ][:TRANSFER_WINDOW_MAX]
    if (
        len(transfer_eligible) >= TRANSFER_MIN_ROWS
        and len({e.context_family for e in transfer_eligible if e.context_family}) >= TRANSFER_MIN_CONTEXT_FAMILIES
        and len({e.session_id for e in transfer_eligible if e.session_id}) >= TRANSFER_MIN_SESSIONS
    ):
        src_ids = [e.evidence_id for e in transfer_eligible]
        sig = _window_signature(ability_id, "transfer_window", src_ids)
        transfer_value = sum(e.correctness * e.effective_independence for e in transfer_eligible) / len(transfer_eligible)
        exists = (
            await db.execute(
                select(MasteryEvidence).where(
                    MasteryEvidence.ability_id == ability_id,
                    MasteryEvidence.evidence_type == "transfer_window",
                    MasteryEvidence.metadata_["window_signature"].as_string() == sig,
                    MasteryEvidence.valid.is_(True),
                )
            )
        ).scalar_one_or_none()
        if exists is None:
            db.add(
                MasteryEvidence(
                    child_id=child_id,
                    ability_id=ability_id,
                    evidence_type="transfer_window",
                    transfer=round(transfer_value, 4),
                    source_evidence_ids=src_ids,
                    rule_version=RULE_VERSION,
                    valid=True,
                    metadata_={"window_signature": sig},
                )
            )


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

    # 节点级 L4 gate 策略（B7）
    node = await db.get(AbilityNode, ability_id)
    node_policy = None
    if node and isinstance(node.level_schema, dict):
        node_policy = node.level_schema.get("l4_gate")

    ev = evaluate_mastery(ability_id, old_level, evidences, node_policy=node_policy)

    # B8：review 判定（单次失败不降级，近期质量走低先 review）
    review = decide_review(evidences, old_level)

    new_level = ev.new_level
    # review 建议降级时，最多降 1 级（不打断升级，只针对质量走低场景）
    if review.status == "downgrade" and old_level > 0:
        new_level = old_level - 1

    # trend 综合判定：降级→down_review；升级→up；review 建议但没真降→watch；
    # 其余→stable
    if new_level < old_level:
        trend = "down_review"
    elif new_level > old_level:
        trend = "up"
    elif review.status in ("review_required", "downgrade"):
        trend = "watch"
    else:
        trend = "stable"

    # B6：满足覆盖后写派生窗口证据（幂等），先 flush 派生，再写能力状态
    await _persist_derived_windows(db, child_id, ability_id, evidences)
    await db.flush()

    evidence_count = len(evidences)

    # confidence 兜底：四维未凑齐时 score 为 None，用 correctness 近似（再有值则 0.0）；
    # 意义是「当前能力状态的置信度」，并非 strict mastery score。
    confidence = ev.score if ev.score is not None else (ev.correctness if ev.correctness is not None else 0.0)

    if state is None:
        state = AbilityState(
            child_id=child_id,
            ability_id=ability_id,
            level=new_level,
            confidence=round(float(confidence), 4),
            evidence_count=evidence_count,
            trend=trend,
        )
        db.add(state)
    else:
        state.level = new_level
        state.confidence = round(float(confidence), 4)
        state.evidence_count = evidence_count
        state.trend = trend
        state.last_evidence_at = (
            datetime.now(timezone.utc) if evidence_count else state.last_evidence_at
        )

    await db.flush()

    return {
        "ability_id": ability_id,
        "old_level": old_level,
        "new_level": new_level,
        "score": round(ev.score, 4) if ev.score is not None else None,
        "decision": ev.decision,
        "missing_evidence": ev.missing_evidence,
        "review_status": review.status,
        "evidence_count": evidence_count,
        "trend": trend,
    }