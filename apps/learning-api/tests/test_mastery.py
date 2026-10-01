"""MasteryService 单元测试 —— 验证冻结的四维派生与升级 Gate。"""
import uuid

from app.services.mastery import (
    Evidence,
    compute_mastery_score,
    decide_review,
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


def _mk_with_span(type_, correctness, hint_level, rv_idx, sess_idx, ctx=None):
    """造带 resource_version_id / session_id / context 的证据，用于多样性 Gate。"""
    return Evidence(
        evidence_id=uuid.uuid4(),
        evidence_type=type_,
        correctness=correctness,
        max_hint_level=hint_level,
        resource_version_id=uuid.UUID(int=rv_idx),
        session_id=uuid.UUID(int=sess_idx),
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
    # 构造满足 Gate 的证据：8 条满分标准证据（≥3资源、≥2session）+ 3 条 transfer（≥2 context、≥2 session）
    std = [
        _mk_with_span("attempt_standard", 1.0, 0, i % 3, i % 2) for i in range(8)
    ]
    transfers = [
        _mk_with_span("attempt_transfer", 1.0, 0, i % 3, i % 2, ctx=f"c{i % 2}")
        for i in range(3)
    ]
    ev = evaluate_mastery("a1", 2, std + transfers)
    assert ev.new_level == 3
    assert ev.decision == "upgraded"


def test_l2_l3_insufficient_transfer():
    # C/I/S 达标但 transfer 缺失 → collect_evidence（不重归一化、不把 T 当 0）
    std = [
        _mk_with_span("attempt_standard", 1.0, 0, i % 3, i % 2) for i in range(8)
    ]
    ev = evaluate_mastery("a1", 2, std)
    assert ev.decision == "collect_evidence"
    assert ev.new_level == 2
    assert "transfer" in ev.missing_evidence


def test_transfer_requires_min_two_rows():
    # 只有 1 条 transfer → value=None（insufficient），不是 0.0
    one_transfer = [_mk_with_span("attempt_transfer", 1.0, 0, 0, 0, ctx="c1")]
    result = derive_transfer(one_transfer)
    assert result.value is None
    assert result.sufficient is False


def test_stability_source_quality():
    # stability = mean(correctness * independence)，需 ≥3 resource、≥2 session
    evs = [
        _mk_with_span("attempt_standard", 1.0, 0, i % 3, i % 2) for i in range(5)
    ]
    result = derive_stability(evs)
    assert result.sufficient is True
    # 全部 hint=0 → independence=1.0，source_quality=1.0，mean=1.0
    assert abs(result.value - 1.0) < 1e-9


# ---- B1: L1→L2 真实 Gate ----

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


# ---- B4/B5: Coverage + NULL 语义 ----

def test_transfer_missing_returns_none_not_zero():
    # 没有 transfer 证据 → value=None（insufficient），不是 0.0（区分"没测"vs"测了不会"）
    evs = [_mk_with_span("attempt_standard", 1.0, 0, i % 3, i % 2) for i in range(5)]
    result = derive_transfer(evs)
    assert result.value is None
    assert result.sufficient is False
    assert result.reason == "too_few_transfer_rows"


def test_transfer_single_context_insufficient():
    # 3 条 transfer 但全在 1 个 context → few_context_families
    evs = [
        _mk_with_span("attempt_transfer", 1.0, 0, i % 3, i % 2, ctx="same")
        for i in range(3)
    ]
    result = derive_transfer(evs)
    assert result.value is None
    assert result.reason == "few_context_families"


def test_correctness_coverage_insufficient():
    # 5 条全对但只 1 个 resource → correctness insufficient
    evs = [_mk_with_span("attempt_standard", 1.0, 0, 0, i % 2) for i in range(5)]
    result = derive_correctness(evs)
    assert result.value is None
    assert result.reason == "few_resource_versions"


def test_mastery_score_none_when_dimension_missing():
    # 四维任一缺失 → score=None（不重归一化、不把缺当 0）
    assert compute_mastery_score(None, 0.9, 0.9, 0.9) is None
    assert compute_mastery_score(0.9, 0.9, 0.9, 0.9) is not None


def test_l2_l3_collect_evidence_when_stability_missing():
    # C/I 充分但 S/T 覆盖不足 → collect_evidence + missing 含 stability/transfer
    std = [_mk_with_span("attempt_standard", 1.0, 0, i % 3, i % 2) for i in range(2)]
    ev = evaluate_mastery("a1", 2, std)
    assert ev.decision == "collect_evidence"
    assert ev.score is None
    assert "stability" in ev.missing_evidence


# ---- B7: L3→L4 完整 Gate（node policy）----

def _transfer_evs(n, contexts, sessions):
    return [
        _mk_with_span("attempt_transfer", 1.0, 0, i % 3, i % sessions, ctx=f"c{i % contexts}")
        for i in range(n)
    ]


def test_l3_l4_gate_met():
    # 3 条 transfer、3 context、2 session、T≥0.80 → L4
    evs = _transfer_evs(3, contexts=3, sessions=2)
    node_policy = {"requires_explanation": False, "min_transfer_contexts": 3}
    ev = evaluate_mastery("app_rel", 3, evs, node_policy=node_policy)
    assert ev.decision == "upgraded"
    assert ev.new_level == 4


def test_l3_l4_transfer_count_insufficient():
    # 只有 2 条 transfer（<3）→ collect_evidence
    evs = _transfer_evs(2, contexts=2, sessions=2)
    node_policy = {"requires_explanation": False, "min_transfer_contexts": 3}
    ev = evaluate_mastery("app_rel", 3, evs, node_policy=node_policy)
    assert ev.decision == "collect_evidence"
    assert "l3_l4_transfer_count_insufficient" in ev.reason_codes


def test_l3_l4_context_diversity_insufficient():
    # 3 条 transfer 但只 2 context（<3）→ collect_evidence
    evs = _transfer_evs(3, contexts=2, sessions=2)
    node_policy = {"requires_explanation": False, "min_transfer_contexts": 3}
    ev = evaluate_mastery("app_rel", 3, evs, node_policy=node_policy)
    assert ev.decision == "collect_evidence"
    assert "l3_l4_context_diversity_insufficient" in ev.reason_codes


def test_l3_l4_explanation_required_missing():
    # 节点要求 explanation，但无 explanation 证据 → collect_evidence
    evs = _transfer_evs(3, contexts=3, sessions=2)
    node_policy = {"requires_explanation": True, "min_transfer_contexts": 3}
    ev = evaluate_mastery("app_rel", 3, evs, node_policy=node_policy)
    assert ev.decision == "collect_evidence"
    assert "l3_l4_explanation_missing" in ev.reason_codes


def test_l3_l4_explanation_required_met():
    # 节点要求 explanation 且提供了 → 升 L4
    evs = _transfer_evs(3, contexts=3, sessions=2) + [
        _mk_with_span("explanation", 1.0, 0, 0, 0)
    ]
    node_policy = {"requires_explanation": True, "min_transfer_contexts": 3}
    ev = evaluate_mastery("app_rel", 3, evs, node_policy=node_policy)
    assert ev.decision == "upgraded"
    assert ev.new_level == 4


# ---- B8: Review / Downgrade 状态机 ----

def test_review_ok_on_all_correct():
    # 最近 3 条全对 → ok（不 review 不降级）
    evs = [_mk_with_span("attempt_standard", 1.0, 0, i % 3, i % 2) for i in range(3)]
    assert decide_review(evs, 2).status == "ok"


def test_review_single_failure_no_review():
    # 最近 3 条仅 1 错 → ok（单次失败不 review）
    evs = [
        _mk_with_span("attempt_standard", 0.0, 0, 0, 0),
        _mk_with_span("attempt_standard", 1.0, 0, 1, 1),
        _mk_with_span("attempt_standard", 1.0, 0, 2, 0),
    ]
    assert decide_review(evs, 2).status == "ok"


def test_review_required_on_two_failures():
    # 最近 3 条 2 错 → review_required（不降级）
    evs = [
        _mk_with_span("attempt_standard", 0.0, 0, 0, 0),
        _mk_with_span("attempt_standard", 0.0, 0, 1, 1),
        _mk_with_span("attempt_standard", 1.0, 0, 2, 0),
    ]
    assert decide_review(evs, 2).status == "review_required"


def test_review_downgrade_on_all_failures():
    # 最近 3 条全错 → downgrade（最多降 1 级）
    evs = [_mk_with_span("attempt_standard", 0.0, 0, i % 3, i % 2) for i in range(3)]
    assert decide_review(evs, 2).status == "downgrade"


def test_review_ignored_at_level_zero():
    # L0 不入 review（无级可降）
    evs = [_mk_with_span("attempt_standard", 0.0, 0, i % 3, i % 2) for i in range(3)]
    assert decide_review(evs, 0).status == "ok"


# ---- V1.4 P0 Governance Closure: context_family 受控词表 ----

def test_context_family_canonical_pass():
    from app.content.context_family import canonicalize_context_family
    assert canonicalize_context_family("school_objects") == "school_objects"
    assert canonicalize_context_family(" comparison ") == "comparison"  # trim
    assert canonicalize_context_family(None) is None  # NULL 合法 = 未判定
    assert canonicalize_context_family("") is None


def test_context_family_illegal_rejected():
    import pytest as _pt
    from app.content.context_family import canonicalize_context_family
    for bad in ["school", "学校物品", "School_Objects", "buying", "purchase",
                "everyday_objects"]:  # everyday_objects 未批准（§10 协议）
        with _pt.raises(ValueError, match="UNKNOWN_CONTEXT_FAMILY"):
            canonicalize_context_family(bad)


def test_backfill_map_covers_50_and_transfer_diversity():
    """AC-04 硬检查：映射50题全覆盖；迁移题 PASS 族 distinct≥2（L2→L3 可达路径存在）。"""
    from app.content.context_family import CONTEXT_FAMILY_VOCABULARY
    from app.content.context_family_map import STEM_CONTEXT_FAMILY
    assert len(STEM_CONTEXT_FAMILY) == 50
    fams = {v for v in STEM_CONTEXT_FAMILY.values() if v is not None}
    assert fams <= set(CONTEXT_FAMILY_VOCABULARY)
    review = sum(1 for v in STEM_CONTEXT_FAMILY.values() if v is None)
    assert review == 6  # REVIEW 三态如实留 NULL，不硬猜
    # 迁移题（app_transfer 5题，显式列出）中 PASS 族 distinct≥2（L2→L3 可达路径存在）
    transfer_stems = [
        "晨练时，小海跑了9圈，小森跑了6圈。小海比小森多跑几圈？",
        "教室里原来摆了12把椅子，老师又搬来4把。现在一共有多少把椅子？",
        "小雨今天走了9千步，小安比小雨多走4千步。小安今天走了多少千步？",
        "餐桌上共有18个杯子，其中7个是蓝色的，其余是白色的。白色杯子有多少个？",
        "书架上原来有8本新书，老师又放上5本，后来同学借走4本。现在书架上有多少本书？",
    ]
    transfer_fams = {STEM_CONTEXT_FAMILY[s] for s in transfer_stems} - {None}
    assert len(transfer_fams) >= 2