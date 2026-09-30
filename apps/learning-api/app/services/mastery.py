"""MasteryService —— L0-L4 状态机 + 四维证据派生（冻结基线 V1.3.1）。

设计：核心计算是纯函数（可独立单测），DB 加载在 repository 层完成。
阈值集中在 app/core/education_rules.py，禁止散落硬编码。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.core.education_rules import (
    GATE_L1_L2,
    GATE_L2_L3,
    GATE_L3_L4,
    HINT_LEVEL_TO_INDEPENDENCE,
    MASTERY_WEIGHTS,
    STABILITY_WINDOW,
    TRANSFER_MIN_ROWS,
    TRANSFER_WINDOW_MAX,
)


@dataclass
class Evidence:
    """一条已组装的证据（供纯计算使用）。"""

    evidence_id: uuid.UUID
    evidence_type: str  # attempt_standard / attempt_transfer / retention_check / explanation
    correctness: float | None = None
    independence: float | None = None
    max_hint_level: int = 0
    context_family: str | None = None
    resource_version_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None

    @property
    def effective_independence(self) -> float:
        """优先用已存 independence，缺则用 max_hint_level 映射。"""
        if self.independence is not None:
            return self.independence
        return HINT_LEVEL_TO_INDEPENDENCE.get(int(self.max_hint_level), 0.0)


def independence_from_hint_level(hint_level: int) -> float:
    return HINT_LEVEL_TO_INDEPENDENCE.get(int(hint_level), 0.0)


def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def compute_mastery_score(c: float, i: float, s: float, t: float) -> float:
    return (
        MASTERY_WEIGHTS["correctness"] * c
        + MASTERY_WEIGHTS["independence"] * i
        + MASTERY_WEIGHTS["stability"] * s
        + MASTERY_WEIGHTS["transfer"] * t
    )


# ---- 四维派生（纯函数） ----


def derive_correctness(evidences: list[Evidence], window: int = 8) -> float:
    scorable = [
        e for e in evidences
        if e.evidence_type in ("attempt_standard", "attempt_transfer", "retention_check")
        and e.correctness is not None
    ][:window]
    return _mean([e.correctness for e in scorable])


def derive_independence(evidences: list[Evidence], window: int = 8) -> float:
    scorable = [
        e for e in evidences
        if e.evidence_type in ("attempt_standard", "attempt_transfer", "retention_check")
    ][:window]
    return _mean([e.effective_independence for e in scorable])


def derive_stability(evidences: list[Evidence]) -> float:
    eligible = [
        e for e in evidences
        if e.evidence_type in ("attempt_standard", "retention_check")
        and e.correctness is not None
    ][:STABILITY_WINDOW]
    if not eligible:
        return 0.0
    return _mean([e.correctness * e.effective_independence for e in eligible])


def derive_transfer(evidences: list[Evidence]) -> float:
    eligible = [
        e for e in evidences
        if e.evidence_type == "attempt_transfer" and e.correctness is not None
    ][:TRANSFER_WINDOW_MAX]
    if len(eligible) < TRANSFER_MIN_ROWS:
        return 0.0
    return _mean([e.correctness * e.effective_independence for e in eligible])


@dataclass
class MasteryEvaluation:
    ability_id: str
    old_level: int
    new_level: int
    decision: str
    score: float
    correctness: float
    independence: float
    stability: float
    transfer: float
    reason_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ability_id": self.ability_id,
            "old_level": self.old_level,
            "new_level": self.new_level,
            "decision": self.decision,
            "score": round(self.score, 4),
            "dimensions": {
                "correctness": round(self.correctness, 4),
                "independence": round(self.independence, 4),
                "stability": round(self.stability, 4),
                "transfer": round(self.transfer, 4),
            },
            "reason_codes": self.reason_codes,
        }


def evaluate_mastery(
    ability_id: str,
    old_level: int,
    evidences: list[Evidence],
) -> MasteryEvaluation:
    """从证据推导四维 + 决策（L0→L4 状态机，纯函数）。"""
    c = derive_correctness(evidences)
    i = derive_independence(evidences)
    s = derive_stability(evidences)
    t = derive_transfer(evidences)
    score = compute_mastery_score(c, i, s, t)

    total_atomic = sum(
        1 for e in evidences
        if e.evidence_type in ("attempt_standard", "attempt_transfer", "retention_check", "explanation")
    )

    new_level, decision, reasons = _decide(old_level, c, i, s, t, total_atomic, evidences)

    return MasteryEvaluation(
        ability_id=ability_id,
        old_level=old_level,
        new_level=new_level,
        decision=decision,
        score=score,
        correctness=c,
        independence=i,
        stability=s,
        transfer=t,
        reason_codes=reasons,
    )


def _decide(
    old_level: int,
    c: float,
    i: float,
    s: float,
    t: float,
    total_atomic: int,
    evidences: list[Evidence],
) -> tuple[int, str, list[str]]:
    # L0→L1：首次有效证据即升级，不用四维 masteryscore
    if old_level == 0:
        if total_atomic >= 1:
            return 1, "upgraded", ["first_evidence"]
        return 0, "unchanged", ["insufficient_evidence"]

    # L1→L2：冻结基线「可在 Hint≤2 支持下稳定完成」的可执行 Gate。
    # eligible = attempt_standard / retention_check（本档不要求 transfer）。
    # 多样性：≥3 resource_version、≥2 session；非补偿门槛：≥4/5 任务 hint≤2。
    if old_level == 1:
        eligible = [
            e for e in evidences
            if e.evidence_type in ("attempt_standard", "retention_check")
        ]
        if len(eligible) < GATE_L1_L2["min_eligible_evidence"]:
            return 1, "collect_evidence", ["l1_l2_not_enough_evidence"]

        resource_versions = {e.resource_version_id for e in eligible if e.resource_version_id is not None}
        if len(resource_versions) < GATE_L1_L2["min_resource_versions"]:
            return 1, "collect_evidence", ["l1_l2_resource_diversity_insufficient"]

        sessions = {e.session_id for e in eligible if e.session_id is not None}
        if len(sessions) < GATE_L1_L2["min_sessions"]:
            return 1, "collect_evidence", ["l1_l2_session_diversity_insufficient"]

        if c < GATE_L1_L2["correctness"]:
            return 1, "unchanged", ["l1_l2_correctness_not_met"]
        if i < GATE_L1_L2["independence"]:
            return 1, "unchanged", ["l1_l2_independence_not_met"]
        if s < GATE_L1_L2["stability"]:
            return 1, "unchanged", ["l1_l2_stability_not_met"]

        # 非补偿门槛：≥4/5 有效任务 max_hint_level ≤ 2
        low_hint = sum(1 for e in eligible if e.max_hint_level <= GATE_L1_L2["max_hint_level"])
        if low_hint / max(1, len(eligible)) < GATE_L1_L2["min_low_hint_ratio"]:
            return 1, "unchanged", ["l1_l2_hint_threshold_not_met"]

        return 2, "upgraded", ["l1_l2_gate_met"]

    # L2→L3：四维 Gate 全部满足
    if old_level == 2:
        score = compute_mastery_score(c, i, s, t)
        if (
            score >= GATE_L2_L3["score"]
            and c >= GATE_L2_L3["correctness"]
            and i >= GATE_L2_L3["independence"]
            and s >= GATE_L2_L3["stability"]
            and t >= GATE_L2_L3["transfer"]
        ):
            return 3, "upgraded", ["l2_l3_gate_met"]
        return 2, "unchanged", ["l2_l3_gate_not_met"]

    # L3→L4：Transfer gate
    if old_level == 3:
        if t >= GATE_L3_L4["transfer"]:
            return 4, "upgraded", ["l3_l4_transfer_met"]
        return 3, "unchanged", ["l3_l4_transfer_not_met"]

    return old_level, "unchanged", ["no_level_change"]