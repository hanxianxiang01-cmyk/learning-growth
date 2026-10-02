"""FE-1403 Renderer Registry Contract 单测（协议冻结 + 入口校验，CI 门禁）。"""
import pytest

from app.content.renderer_protocol import (
    IMPLEMENTED_RENDERER_IDS,
    RENDERER_PROTOCOL_IDS,
    RENDERER_SPECS,
    is_implemented,
    validate_renderer_id,
)


def _kebab(name: str) -> str:
    """PascalCase → kebab-case（连续大写不拆：ColumnArithmetic→column-arithmetic）。"""
    out = []
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0 and not name[i - 1].isupper():
            out.append("-")
        out.append(ch.lower())
    return "".join(out)


def test_protocol_enum_frozen_23():
    """P0-01：23 项冻结，且显示名→kebab-case 映射无错位（§3.1 命名规则自检）。"""
    assert len(RENDERER_PROTOCOL_IDS) == 23
    assert len(RENDERER_SPECS) == 23
    for pid, display, _rid, _src, _st in RENDERER_SPECS:
        assert pid == _kebab(display), f"{display} 应映射 {_kebab(display)}，实际 {pid}"


def test_validate_rejects_illegal():
    assert validate_renderer_id("column-arithmetic") == "column-arithmetic"
    assert validate_renderer_id(" place-value ") == "place-value"
    assert validate_renderer_id(None) is None
    assert validate_renderer_id("") is None
    for bad in ["ColumnArithmetic", "column_arithmetic", "unsupported", "placevalue", "学校"]:
        with pytest.raises(ValueError, match="UNKNOWN_RENDERER_ID"):
            validate_renderer_id(bad)


def test_unsupported_not_in_protocol():
    """前端哨兵 unsupported 明确不在协议面（契约 §4）。"""
    assert "unsupported" not in RENDERER_PROTOCOL_IDS


def test_implemented_subset():
    assert IMPLEMENTED_RENDERER_IDS == {
        "object-counter", "bar-model", "number-line", "number-input"
    }
    assert is_implemented("object-counter") is True
    assert is_implemented("ruler") is False  # planned：协议合法但不可下发


def test_all_v13_reuse_implemented():
    for pid, _d, _r, src, st in RENDERER_SPECS:
        if src in ("v1.3_reuse", "base_ui") and pid != "choice-grid":
            assert st == "implemented", pid
