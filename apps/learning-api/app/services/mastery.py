"""MasteryService —— L0-L4 状态机 + 四维证据派生（冻结基线 V1.3.1）。

设计：核心计算是纯函数（可独立单测），DB 加载在 repository 层完成。
阈值集中在 app/core/education_rules.py，禁止散落硬编码。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.core.education_rules import (
    CI_MIN_RESOURCE_VERSIONS,
    CI_MIN_SESSIONS,
    CI_WINDOW,
    GATE_L1_L2,
    GATE_L2_L3,
    GATE_L3_L4,
    HINT_LEVEL_TO_INDEPENDENCE,
    MASTERY_WEIGHTS,
    REVIEW_POLICY,
    STABILITY_MIN_RESOURCE_VERSIONS,
    STABILITY_MIN_SESSIONS,
    STABILITY_WINDOW,
    TRANSFER_MIN_CONTEXT_FAMILIES,
    TRANSFER_MIN_ROWS,
    TRANSFER_MIN_SESSIONS,
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


@dataclass
class DimensionResult:
    """一个 Mastery 维度的派生结果：值 + 覆盖是否充分。

    - value 为 None：该维度尚未被充分测量（insufficient），不是 0。
    - coverage 描述覆盖缺口，供 Curriculum 判断是缺题量/缺资源多样/缺 session/缺 context。
    """

    value: float | None
    sufficient: bool
    reason: str | None = None  # insufficient 时的原因码

    @staticmethod
    def sufficient(value: float) -> "DimensionResult":
        return DimensionResult(value=value, sufficient=True, reason=None)

    @staticmethod
    def insufficient(reason: str) -> "DimensionResult":
        return DimensionResult(value=None, sufficient=False, reason=reason)


def _distinct_resource_versions(evidences: list[Evidence]) -> int:
    return len({e.resource_version_id for e in evidences if e.resource_version_id is not None})


def _distinct_sessions(evidences: list[Evidence]) -> int:
    return len({e.session_id for e in evidences if e.session_id is not None})


def _distinct_contexts(evidences: list[Evidence]) -> int:
    return len({e.context_family for e in evidences if e.context_family is not None})


def compute_mastery_score(c: float | None, i: float | None, s: float | None, t: float | None) -> float | None:
    """四维加权；任一维度缺失则返回 None（禁止对剩余维度重归一化、禁止把缺失当 0）。"""
    if c is None or i is None or s is None or t is None:
        return None
    return (
        MASTERY_WEIGHTS["correctness"] * c
        + MASTERY_WEIGHTS["independence"] * i
        + MASTERY_WEIGHTS["stability"] * s
        + MASTERY_WEIGHTS["transfer"] * t
    )


# ---- 四维派生（纯函数） ----

def _scorable(evidences: list[Evidence]) -> list[Evidence]:
    """可评分证据：correctness 非空的标准/迁移/保持证据。"""
    return [
        e for e in evidences
        if e.evidence_type in ("attempt_standard", "attempt_transfer", "retention_check")
        and e.correctness is not None
    ]


def derive_correctness(evidences: list[Evidence], window: int = CI_WINDOW) -> DimensionResult:
    """正确率：最近 window 条可评分证据，要求 ≥3 resource、≥2 session。"""
    scorable = _scorable(evidences)[:window]
    if not scorable:
        return DimensionResult.insufficient("no_scorable_evidence")
    rv = _distinct_resource_versions(scorable)
    sess = _distinct_sessions(scorable)
    if rv < CI_MIN_RESOURCE_VERSIONS:
        return DimensionResult.insufficient("few_resource_versions")
    if sess < CI_MIN_SESSIONS:
        return DimensionResult.insufficient("few_sessions")
    return DimensionResult.sufficient(_mean([e.correctness for e in scorable if e.correctness is not None]))


def derive_independence(evidences: list[Evidence], window: int = CI_WINDOW) -> DimensionResult:
    """独立性：最近 window 条可评分证据的 effective_independence 均值，同 C 的覆盖要求。"""
    scorable = _scorable(evidences)[:window]
    if not scorable:
        return DimensionResult.insufficient("no_scorable_evidence")
    rv = _distinct_resource_versions(scorable)
    sess = _distinct_sessions(scorable)
    if rv < CI_MIN_RESOURCE_VERSIONS:
        return DimensionResult.insufficient("few_resource_versions")
    if sess < CI_MIN_SESSIONS:
        return DimensionResult.insufficient("few_sessions")
    return DimensionResult.sufficient(_mean([e.effective_independence for e in scorable]))


def derive_stability(evidences: list[Evidence]) -> DimensionResult:
    """稳定性：最近 STABILITY_WINDOW 条 standard/retention，要求 ≥3 resource、≥2 session。"""
    eligible = [
        e for e in evidences
        if e.evidence_type in ("attempt_standard", "retention_check")
        and e.correctness is not None
    ][:STABILITY_WINDOW]
    if not eligible:
        return DimensionResult.insufficient("no_eligible_evidence")
    rv = _distinct_resource_versions(eligible)
    sess = _distinct_sessions(eligible)
    if rv < STABILITY_MIN_RESOURCE_VERSIONS:
        return DimensionResult.insufficient("few_resource_versions")
    if sess < STABILITY_MIN_SESSIONS:
        return DimensionResult.insufficient("few_sessions")
    return DimensionResult.sufficient(_mean([e.correctness * e.effective_independence for e in eligible]))


def derive_transfer(evidences: list[Evidence]) -> DimensionResult:
    """迁移：最近最多 4 条 transfer 证据，要求 ≥2 条、≥2 context、≥2 session。

    不足返回 insufficient（value=None），不与「测了但失败」混淆。
    """
    eligible = [
        e for e in evidences
        if e.evidence_type == "attempt_transfer" and e.correctness is not None
    ][:TRANSFER_WINDOW_MAX]
    if len(eligible) < TRANSFER_MIN_ROWS:
        return DimensionResult.insufficient("too_few_transfer_rows")
    if _distinct_contexts(eligible) < TRANSFER_MIN_CONTEXT_FAMILIES:
        return DimensionResult.insufficient("few_context_families")
    if _distinct_sessions(eligible) < TRANSFER_MIN_SESSIONS:
        return DimensionResult.insufficient("few_sessions")
    return DimensionResult.sufficient(_mean([e.correctness * e.effective_independence for e in eligible]))


@dataclass
class MasteryEvaluation:
    ability_id: str
    old_level: int
    new_level: int
    decision: str
    score: float | None
    correctness: float | None
    independence: float | None
    stability: float | None
    transfer: float | None
    reason_codes: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        def _round(v: float | None) -> float | None:
            return round(v, 4) if v is not None else None

        return {
            "ability_id": self.ability_id,
            "old_level": self.old_level,
            "new_level": self.new_level,
            "decision": self.decision,
            "score": _round(self.score),
            "dimensions": {
                "correctness": _round(self.correctness),
                "independence": _round(self.independence),
                "stability": _round(self.stability),
                "transfer": _round(self.transfer),
            },
            "missing_evidence": self.missing_evidence,
            "reason_codes": self.reason_codes,
        }


def evaluate_mastery(
    ability_id: str,
    old_level: int,
    evidences: list[Evidence],
    node_policy: dict | None = None,
) -> MasteryEvaluation:
    """从证据推导四维（Optional，覆盖不足=missing）+ 决策（L0→L4 状态机，纯函数）。

    node_policy：来自 ability_node.level_schema.l4_gate，供 L3→L4 的节点级 gate 使用。
    """
    c_dim = derive_correctness(evidences)
    i_dim = derive_independence(evidences)
    s_dim = derive_stability(evidences)
    t_dim = derive_transfer(evidences)

    c, i, s, t = c_dim.value, i_dim.value, s_dim.value, t_dim.value
    score = compute_mastery_score(c, i, s, t)

    missing: list[str] = []
    if c_dim.value is None:
        missing.append("correctness")
    if i_dim.value is None:
        missing.append("independence")
    if s_dim.value is None:
        missing.append("stability")
    if t_dim.value is None:
        missing.append("transfer")

    total_atomic = sum(
        1 for e in evidences
        if e.evidence_type in ("attempt_standard", "attempt_transfer", "retention_check", "explanation")
    )

    # transfer 覆盖率（L3→L4 还需 ≥3 条 transfer、≥3 context 的节点级 gate）
    transfer_evidences = [
        e for e in evidences
        if e.evidence_type == "attempt_transfer" and e.correctness is not None
    ]
    transfer_count = len(transfer_evidences)
    transfer_contexts = len({e.context_family for e in transfer_evidences if e.context_family})

    new_level, decision, reasons = _decide(
        old_level, c, i, s, t, total_atomic, evidences, missing, score,
        node_policy=node_policy,
        transfer_count=transfer_count,
        transfer_contexts=transfer_contexts,
    )

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
        missing_evidence=missing,
    )


def _decide(
    old_level: int,
    c: float | None,
    i: float | None,
    s: float | None,
    t: float | None,
    total_atomic: int,
    evidences: list[Evidence],
    missing: list[str],
    score: float | None,
    node_policy: dict | None = None,
    transfer_count: int = 0,
    transfer_contexts: int = 0,
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

        # 三档门槛：维度 None 也算未达标
        if c is None or c < GATE_L1_L2["correctness"]:
            return 1, "unchanged", ["l1_l2_correctness_not_met"]
        if i is None or i < GATE_L1_L2["independence"]:
            return 1, "unchanged", ["l1_l2_independence_not_met"]
        if s is None or s < GATE_L1_L2["stability"]:
            return 1, "unchanged", ["l1_l2_stability_not_met"]

        # 非补偿门槛：≥4/5 有效任务 max_hint_level ≤ 2
        low_hint = sum(1 for e in eligible if e.max_hint_level <= GATE_L1_L2["max_hint_level"])
        if low_hint / max(1, len(eligible)) < GATE_L1_L2["min_low_hint_ratio"]:
            return 1, "unchanged", ["l1_l2_hint_threshold_not_met"]

        return 2, "upgraded", ["l1_l2_gate_met"]

    # L2→L3：四维 Gate 全部满足。任一维度 missing → collect_evidence（不重归一化）。
    if old_level == 2:
        if missing or score is None:
            return 2, "collect_evidence", ["l2_l3_coverage_insufficient"]
        if (
            score >= GATE_L2_L3["score"]
            and c is not None and c >= GATE_L2_L3["correctness"]
            and i is not None and i >= GATE_L2_L3["independence"]
            and s is not None and s >= GATE_L2_L3["stability"]
            and t is not None and t >= GATE_L2_L3["transfer"]
        ):
            return 3, "upgraded", ["l2_l3_gate_met"]
        return 2, "unchanged", ["l2_l3_gate_not_met"]

    # L3→L4：Transfer gate + 节点级验证（B7）
    if old_level == 3:
        if t is None:
            return 3, "collect_evidence", ["l3_l4_transfer_insufficient"]

        # 数量/情境门槛（冻结基线）
        l4_gate = node_policy or {}
        min_transfer_contexts = l4_gate.get("min_transfer_contexts", GATE_L3_L4["min_context_families"])
        requires_explanation = l4_gate.get("requires_explanation", False)

        if transfer_count < GATE_L3_L4["min_transfer_evidence"]:
            return 3, "collect_evidence", ["l3_l4_transfer_count_insufficient"]
        if transfer_contexts < min_transfer_contexts:
            return 3, "collect_evidence", ["l3_l4_context_diversity_insufficient"]
        if requires_explanation:
            has_explanation = any(
                e.evidence_type == "explanation" for e in evidences
            )
            if not has_explanation:
                return 3, "collect_evidence", ["l3_l4_explanation_missing"]

        if t >= GATE_L3_L4["transfer"]:
            return 4, "upgraded", ["l3_l4_transfer_met"]
        return 3, "unchanged", ["l3_l4_transfer_not_met"]

    return old_level, "unchanged", ["no_level_change"]


@dataclass
class ReviewDecision:
    """Review / Downgrade 判定结果（B8）：单次失败不降级，只给信号。"""

    status: str  # "ok" | "review_required" | "downgrade"
    reason_codes: list[str] = field(default_factory=list)


def decide_review(evidences: list[Evidence], current_level: int) -> ReviewDecision:
    """近期质量走低判定（纯函数）。

    - 用最近 REVIEW_POLICY.recent_window 条可评分证据；
    - 单次/少量失败 → ok（Level 不变，trend 由上层标 down_review）；
    - 窗口内 ≥ min_failures 失败 → review_required（安排 validation/retention）；
    - 窗口内 ≥ downgrade_failures（且已达窗口上限）全失败 → downgrade（最多降 1 级）。
    """
    if current_level <= 0:
        return ReviewDecision(status="ok")

    scorable = [
        e for e in evidences
        if e.evidence_type in ("attempt_standard", "attempt_transfer", "retention_check")
        and e.correctness is not None
    ]
    recent = scorable[-REVIEW_POLICY["recent_window"]:]
    if not recent:
        return ReviewDecision(status="ok")

    failures = sum(1 for e in recent if e.correctness == 0.0)
    min_fail = REVIEW_POLICY["min_failures"]
    down_fail = REVIEW_POLICY["downgrade_failures"]

    if failures >= down_fail and failures == len(recent):
        return ReviewDecision(status="downgrade", reason_codes=["review_downgrade"])

    if failures >= min_fail:
        return ReviewDecision(status="review_required", reason_codes=["review_low_quality"])

    return ReviewDecision(status="ok")