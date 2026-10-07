"""V2 金资源防漂移单测（FE-1414）：R01 object-counter 结构契约。

不连库：校验 GOLD_RESOURCES_V2 的数据形态与 _build_ui_schema_v2 产物
始终满足 docs/frontend/29 可执行契约 + 前端 objectCounterV2.ts readConfig 口径。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.content.renderer_protocol import is_implemented, validate_renderer_id
from app.content.resource_seed_v2 import GOLD_RESOURCES_V2

R01 = next(r for r in GOLD_RESOURCES_V2 if r.get("renderer") == "object-counter")


def test_r01_exists_and_implemented():
    assert R01 is not None
    validate_renderer_id(R01["renderer"])
    assert is_implemented(R01["renderer"])
    assert R01["ui_schema_version"] == "2.0"
    assert R01["mode"] == "count_compose"


def test_r01_answer_is_scalar_total():
    # 判分走 content.answer 标量（总数）；answer 必须等于 expected min_count 之和
    c = R01["content"]
    assert isinstance(c["answer"], (int, float))
    expected = R01["config"]["expected"]
    assert sum(e["min_count"] for e in expected) == c["answer"]


def test_r01_config_shape_matches_frontend_guard():
    groups = R01["config"]["groups"]
    assert len(groups) >= 2
    for g in groups:
        assert isinstance(g["group_id"], str) and isinstance(g["label"], str)
        assert isinstance(g["count"], int) and g["count"] >= 0
    ids = {g["group_id"] for g in groups}
    for e in R01["config"]["expected"]:
        assert e["group_id"] in ids
        assert isinstance(e["min_count"], int) and e["min_count"] >= 1
    assert R01["config"]["max_total_count"] >= sum(e["min_count"] for e in R01["config"]["expected"])


def test_r01_capabilities_declared():
    # 前端 readConfig / E2E 依赖这四个能力 + undo/reset
    for cap in ("add_object", "remove_object", "compose_groups", "decompose_group", "undo", "reset"):
        assert cap in R01["capabilities"]


def test_r01_context_family_and_evidence():
    assert R01["context_family"] == "school_objects"
    assert R01["response_type"] == "object_count"
    assert set(R01["evidence_targets"]) >= {"groups", "total"}
    assert R01["is_transfer"] is False


def test_v2_renderer_coverage_at_least_two_quantity():
    # V2 链至少覆盖 column-arithmetic(B5) 与 object-counter(R01)（Vertical Gate 两个实例）
    renderers = {r["renderer"] for r in GOLD_RESOURCES_V2}
    assert {"column-arithmetic", "object-counter"} <= renderers


R04 = next(r for r in GOLD_RESOURCES_V2 if r.get("renderer") == "number-input")


def test_r04_exists_and_shape():
    validate_renderer_id(R04["renderer"])
    assert is_implemented(R04["renderer"])
    assert R04["ui_schema_version"] == "2.0"
    assert R04["mode"] == "numeric_answer"
    assert R04["response_type"] == "number_input"
    # 答案在 config 值域内
    c = R04["config"]
    assert c["integer_only"] is True
    assert c["min"] <= R04["content"]["answer"] <= c["max"]
    assert "answer" in R04["evidence_targets"]
    assert R04["capabilities"] == ["answer_input"]


R07 = next(r for r in GOLD_RESOURCES_V2 if r.get("renderer") == "ten-frame")


def test_r07_exists_and_shape():
    validate_renderer_id(R07["renderer"])
    assert is_implemented(R07["renderer"])
    assert R07["mode"] == "quantity_structure"
    assert R07["response_type"] == "ten_frame"
    # 20 以内：answer = tens*10 + remainder 唯一分解
    ans = R07["content"]["answer"]
    assert 1 <= ans <= 20
    assert R07["config"]["target_count"] == ans
    assert R07["config"]["max_frames"] == 2
    assert {"fill", "grouping"} <= set(R07["capabilities"])
    assert set(R07["evidence_targets"]) == {"tens", "current_frame_count"}
    assert R07["context_family"] == "sharing"


R02 = next(r for r in GOLD_RESOURCES_V2 if r.get("renderer") == "bar-model")


def test_r02_exists_and_shape():
    validate_renderer_id(R02["renderer"])
    assert is_implemented(R02["renderer"])
    assert R02["ui_schema_version"] == "2.0"
    assert R02["mode"] == "part_whole"
    assert R02["response_type"] == "bar_model"
    c = R02["config"]
    # 恰好两根已知条，答案条唯一未知；答案=结构关系可解
    known = c["known"]
    assert set(known.keys()) == {"a", "b"}
    assert c["answer_bar"] == "c"
    assert known["a"] + known["b"] == R02["content"]["answer"]
    assert c["max_blocks"] >= R02["content"]["answer"]
    # 金题的 error_models 必须含模型结构错分类原料（R02 P0 Diagnosis 条目）
    codes = {e["code"] for e in R02["error_models"]}
    assert {"modeling", "calc"} <= codes
    assert "structure" in R02["evidence_targets"]
    assert R02["context_family"] == "school_objects"


R06 = next(r for r in GOLD_RESOURCES_V2 if r.get("renderer") == "place-value")


def test_r06_exists_and_shape():
    validate_renderer_id(R06["renderer"])
    assert is_implemented(R06["renderer"])
    assert R06["mode"] == "place_value_build"
    assert R06["response_type"] == "place_value"
    c = R06["config"]
    # 牌堆必须与目标数字 multiset 相等（前端 parser 同款守卫——不一致则题不可解）
    assert sorted(c["pool"]) == sorted(int(d) for d in str(c["target"]))
    assert c["target"] == R06["content"]["answer"]
    assert 10 <= c["target"] <= 999
    # R06 Diagnosis P0：位值混淆原料必须在 error_models
    patterns = {e["pattern"] for e in R06["error_models"]}
    assert "place_value_confusion" in patterns
    assert {"slots", "structure"} <= set(R06["evidence_targets"])
    assert "select" in R06["capabilities"]


R10 = next(r for r in GOLD_RESOURCES_V2 if r.get("mode") == "unknown_number")
R10OP = next(r for r in GOLD_RESOURCES_V2 if r.get("mode") == "unknown_operator")


def test_r10_number_slot_gold():
    validate_renderer_id(R10["renderer"])
    assert is_implemented(R10["renderer"])
    assert R10["response_type"] == "formula_board"
    tokens = R10["config"]["tokens"]
    assert sum(1 for t in tokens if t["t"] == "eq") == 1
    slots = [t for t in tokens if t["t"] == "slot"]
    assert len(slots) == 1 and slots[0]["accept"] == "number"
    assert R10["config"]["answer_slot"] == slots[0]["id"]
    # 等式语义可解：□+4=9 → 5（与 evaluator 同口径核对）
    assert R10["content"]["answer"] == 9 - 4
    assert R10["ability_id"] == "app_strat"  # 节点首题
    assert {"filled", "structure"} <= set(R10["evidence_targets"])


def test_r10_operator_gold():
    tokens = R10OP["config"]["tokens"]
    slots = [t for t in tokens if t["t"] == "slot"]
    assert len(slots) == 1 and slots[0]["accept"] == "operator"
    assert R10OP["config"]["answer_slot"] == slots[0]["id"]
    # 7○2=5 的唯一解是 "-"
    assert R10OP["content"]["answer"] == "-"
    assert 7 - 2 == 5 and 7 + 2 != 5
    # Gap R10 Diagnosis P0"运算符错误"原料
    assert "operator" in {e["pattern"] for e in R10OP["error_models"]}
    assert R10OP["context_family"] == "before_after"
