"""MasteryService 单元测试 —— 验证冻结的四维派生与升级 Gate。"""
import uuid

from app.services.mastery import (
    Evidence,
    compute_mastery_score,
    derive_correctness,
    derive_independence,
    derive_stability,
    derive_transfer,
    evaluate_mastery,
    independence_from_hint_level,
)


def _mk(type_: str, correctness: float | None, hint_level: int = 0, ctx: str | None = None) -> Evidence:
    return Evidence(
        evidence_id=uuid.uuid4(),
        evidence_type=type_,
        correctness=correctness,
        max_hint_level=hint_level,
        context_family=ctx,
    )


def test_independence_mapping():
    assert independence_from_hint_level(0) == 1.00
    assert independence_from_hint_level(1) == 0.75
    assert independence_from_hint_level(4) == 0.00


def test_mastery_score_weights():
    score = compute_mastery_score(0.8, 0.75, 0.75, 0.6)
    expected = 0.35 * 0.8 + 0.25 * 0.75 + 0.20 * 0.75 + 0.20 * 0.6
    assert abs(score - expected) < 1e-9


def test_l0_l1_first_evidence():
    ev = evaluate_mastery("a1", 0, [_mk("attempt_standard", 1.0, hint_level=0)])
    assert ev.decision == "upgraded"
    assert ev.new_level == 1


def test_l2_l3_gate_met():
    # 构造满足 Gate 的证据：8 条满分标准证据 + 足够 transfer
    std = [_mk("attempt_standard", 1.0, hint_level=0) for _ in range(8)]
    transfers = [_mk("attempt_transfer", 1.0, hint_level=0, ctx=f"c{i}") for i in range(3)]
    ev = evaluate_mastery("a1", 2, std + transfers)
    assert ev.new_level == 3
    assert ev.decision == "upgraded"


def test_l2_l3_gate_not_met():
    # 证据不足（correctness 低）
    std = [_mk("attempt_standard", 0.5, hint_level=3) for _ in range(3)]
    ev = evaluate_mastery("a1", 2, std)
    assert ev.decision == "unchanged"
    assert ev.new_level == 2


def test_transfer_requires_min_two_rows():
    # 只有 1 条 transfer，不应产出 transfer 维度
    one_transfer = [_mk("attempt_transfer", 1.0, hint_level=0, ctx="c1")]
    assert derive_transfer(one_transfer) == 0.0


def test_stability_source_quality():
    # stability = mean(correctness * independence)
    evs = [
        _mk("attempt_standard", 1.0, hint_level=0),  # ind=1.0 -> q=1.0
        _mk("attempt_standard", 1.0, hint_level=1),  # ind=0.75 -> q=0.75
    ]
    assert abs(derive_stability(evs) - (1.0 + 0.75) / 2) < 1e-9


# ---- B1: L1→L2 真实 Gate ----

def _mk_with_span(type_, correctness, hint_level, rv_idx, sess_idx):
    """造带 resource_version_id / session_id 的证据，用于 L1→L2 多样性 Gate。"""
    return Evidence(
        evidence_id=uuid.uuid4(),
        evidence_type=type_,
        correctness=correctness,
        max_hint_level=hint_level,
        resource_version_id=uuid.UUID(int=rv_idx),
        session_id=uuid.UUID(int=sess_idx),
    )


def test_l1_l2_not_enough_evidence():
    # 只有 4 条标准证据（<5），不应升 L2
    evs = [_mk_with_span("attempt_standard", 1.0, 0, i, 1) for i in range(4)]
    ev = evaluate_mastery("a1", 1, evs)
    assert ev.decision == "collect_evidence"
    assert ev.new_level == 1


def test_l1_l2_resource_diversity_insufficient():
    # 5 条全对、但只来自 2 个 resource（<3），不升
    evs = [_mk_with_span("attempt_standard", 1.0, 0, i % 2, 1) for i in range(5)]
    ev = evaluate_mastery("a1", 1, evs)
    assert ev.decision == "collect_evidence"
    assert ev.new_level == 1
    assert "l1_l2_resource_diversity_insufficient" in ev.reason_codes


def test_l1_l2_session_diversity_insufficient():
    # 5 条、3 资源、但全在同一个 session（<2），不升
    evs = [_mk_with_span("attempt_standard", 1.0, 0, i % 3, 1) for i in range(5)]
    ev = evaluate_mastery("a1", 1, evs)
    assert ev.decision == "collect_evidence"
    assert "l1_l2_session_diversity_insufficient" in ev.reason_codes


def test_l1_l2_hint_threshold_not_met():
    # 5 任务满足数量/多样性/C/I/S，但只有 3/5 任务 hint≤2（<0.8），不升
    evs = [
        _mk_with_span("attempt_standard", 1.0, 0, i % 3, i % 2) for i in range(5)
    ]
    # 前两个 hint=0（≤2），后三个 hint_level 需 >2 —— 但这里全部 hint=0，
    # 需要单独构造：3 个 hint≤2，2 个 hint=4
    evs = [
        _mk_with_span("attempt_standard", 1.0, 0, i % 3, 1) for i in range(3)
    ] + [
        _mk_with_span("attempt_standard", 1.0, 4, (i + 1) % 3, 2) for i in range(2)
    ]
    # 3/5 hint≤2 → ratio 0.6 < 0.8
    ev = evaluate_mastery("a1", 1, evs)
    assert ev.decision == "unchanged"
    assert "l1_l2_hint_threshold_not_met" in ev.reason_codes


def test_l1_l2_gate_met():
    # 满足全部：5 条标准证据、3 资源、2 session、hint≤2 占比≥0.8
    evs = [
        _mk_with_span("attempt_standard", 1.0, 0, i % 3, i % 2) for i in range(5)
    ]
    ev = evaluate_mastery("a1", 1, evs)
    assert ev.decision == "upgraded"
    assert ev.new_level == 2