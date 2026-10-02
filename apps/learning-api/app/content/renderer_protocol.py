"""Renderer Registry Protocol V1.4（FE-1403）—— 23 个 Renderer 的协议级枚举与校验。

唯一事实源：docs/governance/（治理冻结项）+ docs/frontend/28；本模块是其机器可读镜像。
依据：《V1.4 P0 Architecture Contract》P0-01 冻结 R-001~R-023；
     《V1.4评审V0.2》§3.1 命名规则：PascalCase 显示名 → kebab-case 协议 ID。

职责边界（对齐 context_family 四分离模式）：
- 本模块 = 协议值域 + 入口校验（seed / 资源审核用）；
- Engine 不解释 Renderer 语义；
- 前端 RENDERER_REGISTRY = 已实现子集（implemented），未实现的合法 ID 受控拒绝下发。
"""
from __future__ import annotations

# (协议 ID[kebab-case], 显示名[PascalCase], R-ID, 来源, 实现状态)
# source: v1.3_reuse（V1.3 已有三件套）/ base_ui（通用输入/选择）/ v1.4_new（新组件）
# status: implemented（前端已可渲染）/ planned（协议已冻结、组件未交付）
RENDERER_SPECS: tuple[tuple[str, str, str, str, str], ...] = (
    ("object-counter",    "ObjectCounter",    "R-001", "v1.3_reuse", "implemented"),
    ("bar-model",         "BarModel",         "R-002", "v1.3_reuse", "implemented"),
    ("number-line",       "NumberLine",       "R-003", "v1.3_reuse", "implemented"),
    ("number-input",      "NumberInput",      "R-004", "base_ui",    "implemented"),
    ("choice-grid",       "ChoiceGrid",       "R-005", "base_ui",    "planned"),
    ("place-value",       "PlaceValue",       "R-006", "v1.4_new",   "planned"),
    ("ten-frame",         "TenFrame",         "R-007", "v1.4_new",   "planned"),
    ("column-arithmetic", "ColumnArithmetic", "R-008", "v1.4_new",   "planned"),
    ("array-board",       "ArrayBoard",       "R-009", "v1.4_new",   "planned"),
    ("grouping-board",    "GroupingBoard",    "R-010", "v1.4_new",   "planned"),
    ("formula-board",     "FormulaBoard",     "R-011", "v1.4_new",   "planned"),
    ("estimation-canvas", "EstimationCanvas", "R-012", "v1.4_new",   "planned"),
    ("shape-gallery",     "ShapeGallery",     "R-013", "v1.4_new",   "planned"),
    ("shape-canvas",      "ShapeCanvas",      "R-014", "v1.4_new",   "planned"),
    ("sorting-board",     "SortingBoard",     "R-015", "v1.4_new",   "planned"),
    ("direction-grid",    "DirectionGrid",    "R-016", "v1.4_new",   "planned"),
    ("ruler",             "Ruler",            "R-017", "v1.4_new",   "planned"),
    ("clock",             "Clock",            "R-018", "v1.4_new",   "planned"),
    ("timeline",          "Timeline",         "R-019", "v1.4_new",   "planned"),
    ("money-board",       "MoneyBoard",       "R-020", "v1.4_new",   "planned"),
    ("data-table",        "DataTable",        "R-021", "v1.4_new",   "planned"),
    ("pictograph",        "Pictograph",       "R-022", "v1.4_new",   "planned"),
    ("pattern-board",     "PatternBoard",     "R-023", "v1.4_new",   "planned"),
)

RENDERER_PROTOCOL_IDS: frozenset[str] = frozenset(s[0] for s in RENDERER_SPECS)
IMPLEMENTED_RENDERER_IDS: frozenset[str] = frozenset(s[0] for s in RENDERER_SPECS if s[4] == "implemented")

assert len(RENDERER_PROTOCOL_IDS) == 23, "P0-01 冻结：协议枚举必须恰好 23 项"


def validate_renderer_id(raw: object) -> str | None:
    """trim → 协议枚举 lookup；非法值 ValueError(UNKNOWN_RENDERER_ID)。

    None/空 = 未声明（仅允许出现在 V1 schema：由 kind/visual 推导，见契约文档分流规则）。
    """
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ValueError(f"UNKNOWN_RENDERER_ID: not a string: {raw!r}")
    value = raw.strip()
    if value == "":
        return None
    if value not in RENDERER_PROTOCOL_IDS:
        raise ValueError(
            f"UNKNOWN_RENDERER_ID: {value!r} not in frozen protocol "
            f"({len(RENDERER_PROTOCOL_IDS)} ids, kebab-case)"
        )
    return value


def is_implemented(renderer_id: str) -> bool:
    """协议合法 ≠ 可下发。V2 资源下发前必须校验 implemented（planned 受控拒绝）。"""
    return renderer_id in IMPLEMENTED_RENDERER_IDS
