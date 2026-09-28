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