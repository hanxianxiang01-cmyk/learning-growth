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
    """FE-1409：18 V2 组件交付后 23 协议全部 implemented（可渲染，不降级）。"""
    assert IMPLEMENTED_RENDERER_IDS == RENDERER_PROTOCOL_IDS
    assert len(IMPLEMENTED_RENDERER_IDS) == 23
    assert is_implemented("object-counter") is True
    assert is_implemented("ruler") is True  # FE-1409 起全部可下发


def test_all_v4_protocols_assignable():
    """下发门控口径变化：不再有 planned 拒绝，只剩「协议外 ID」拒绝。"""
    from app.content.renderer_protocol import is_implemented as impl
    assert impl("shape-canvas") is True
    assert impl("ruler") is True
    assert impl("data-table") is True
    assert impl("unsupported") is False  # 哨兵不在协议面，仍拒绝
    assert impl("not-a-renderer") is False


def test_all_v13_reuse_implemented():
    for pid, _d, _r, src, st in RENDERER_SPECS:
        if src in ("v1.3_reuse", "base_ui") and pid != "choice-grid":
            assert st == "implemented", pid
