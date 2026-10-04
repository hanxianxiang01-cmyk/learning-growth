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
