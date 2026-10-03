"""Diagnosis V2 + Hint 服务测试（FE-1406：三段判定、兜底移除、NULL 合法）。"""
from app.services.diagnosis import (
    DIAGNOSIS_VERSION,
    diagnose,
    diagnose_v2,
    response_shape,
    response_shape_from_dict,
)
from app.services.hint import decide_hint


# ---- 基本语义 ----

def test_diagnose_correct_returns_none():
    assert diagnose_v2(True) is None


def test_diagnose_unscored_returns_none():
    """correct=None（评分不可用）= 工程异常场景，绝不写儿童数学误解。"""
    assert diagnose_v2(None, error_models=[{"code": "calc"}]) is None


# ---- V2 核心：无证据不猜 ----

def test_no_observation_yields_null_code():
    """答错但无可验证观察 → observation_only，top_level_code=None。

    （V1 兜底"无 error_model 按 hint 给 E01/E05"已移除。）"""
    d = diagnose_v2(False, error_models=[{"code": "calc"}], response={"answer": "7"})
    assert d is not None
    assert d.status == "observation_only"
    assert d.top_level_code is None
    assert d.candidates == []
    # 对外外形：无码结论不下发猜测标签
    assert response_shape(d) is None


def test_high_hint_no_longer_forces_e05():
    """hint 依赖不再决定错因（评审点名移除的兜底路径）。"""
    d = diagnose_v2(False, response={"answer": "7"})  # 无 error_models、无观察
    assert d.top_level_code is None


# ---- 观察 → 候选 ----

def test_v1_representation_missing_supports_modeling():
    """V1 资源 representation_required 但未提交表征 → modeling 观察 + E04 候选。"""
    ui = {"response_schema": {"representation_required": True}}
    d = diagnose_v2(
        False,
        error_models=[{"code": "modeling"}],
        response={"answer": "7"},  # 无 representation
        ui_schema=ui,
    )
    assert d.status == "candidate"
    assert d.top_level_code == "E04"
    assert d.candidates[0].rule_version == DIAGNOSIS_VERSION
    assert "response.representation" in d.candidates[0].evidence_paths
    out = response_shape(d)
    assert out is not None and out["code"] == "E04"


def test_v2_empty_workspaces_supports_strategy():
    """V2 提交 workspaces data 全空 → no_process_data 观察，支持 strategy 候选 E05。"""
    d = diagnose_v2(
        False,
        error_models=[{"code": "strategy"}],
        response={"workspaces": [{"workspace_id": "main", "data": {}}], "answer": {"value": 9}},
        ui_schema={"schema_version": "2.0"},
    )
    assert d.top_level_code == "E05"


def test_tag_without_observation_support_stays_candidate_free():
    """资源规则存在但没有观察指向它 → 不形成候选（不是'第一条错因'）。"""
    d = diagnose_v2(
        False,
        error_models=[{"code": "knowledge"}, {"code": "calc"}],
        response={"answer": "7"},
    )
    assert d.candidates == []
    assert d.top_level_code is None


# ---- 单 answer 提交路径：数学错但过程完整 → 只留评分事实 ----

def test_wrong_but_complete_process_no_guess():
    d = diagnose_v2(
        False,
        error_models=[{"code": "modeling"}],
        response={"answer": "7", "representation": {"type": "bar-model"}},
        ui_schema={"response_schema": {"representation_required": True}},
    )
    # 表征已提交 → 无 representation_missing 观察 → 候选不成立
    assert d.top_level_code is None
    assert d.process_evidence_status == "complete"


# ---- 兼容层与幂等外形 ----

def test_compat_diagnose_signature():
    d = diagnose(False, error_model="modeling", used_hint_levels=[3])
    # hint 不参与判定；无 response 观察 → NULL（兜底移除的证明）
    assert d.top_level_code is None


def test_response_shape_from_dict_null_code():
    assert response_shape_from_dict(None) is None
    assert response_shape_from_dict({"top_level_code": None, "status": "observation_only"}) is None
    out = response_shape_from_dict({"top_level_code": "E04", "label": "modeling_gap", "status": "candidate"})
    assert out["code"] == "E04"


# ---- Hint 服务（V1 行为不变）----

def test_hint_first_error_no_answer_reveal():
    d = decide_hint(attempt_count=1, requested_level=None)
    assert d.answer_revealed is False
    assert d.hint_level == 1


def test_hint_ladder_climbs():
    d3 = decide_hint(attempt_count=3, requested_level=None)
    assert d3.hint_level == 3
    assert d3.answer_revealed is False


def test_hint_cap_at_max():
    d = decide_hint(attempt_count=9, requested_level=None)
    assert d.hint_level == 4
    assert d.answer_revealed is False
