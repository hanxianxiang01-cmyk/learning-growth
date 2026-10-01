"""context_family 受控词表校验（V1.4 P0 Governance Closure）。

唯一事实源：docs/governance/CONTEXT_FAMILY_VOCABULARY.md（本模块是其机器可读镜像）。
契约（治理文档 §4）：raw → trim → canonical validation → Vocabulary lookup → PASS / ERROR。
非法值一律 ValueError("UNKNOWN_CONTEXT_FAMILY: ...")，不得进入正式 Seed。

职责分离（§9）：DDL 管类型、本模块管入口值域、Engine 只消费 canonical ID。
"""
from __future__ import annotations

# V1.4 初始词表（snake_case canonical ID）
# - lineup_position / shopping / sharing：启用但当前题库零覆盖（如实记录，不伪装）
# - time_schedule：启用（有 2 题真实覆盖，AC-04 评审通过后生效）
# - everyday_objects：未批准——按 §10 协议，批准前不得写入数据
CONTEXT_FAMILY_VOCABULARY: frozenset[str] = frozenset({
    "school_objects",
    "comparison",
    "before_after",
    "lineup_position",
    "shopping",
    "sharing",
    "time_schedule",
})


def canonicalize_context_family(raw: object) -> str | None:
    """校验并返回 canonical context_family；None/空串表示未判定（合法 NULL）。

    非法值抛 ValueError，消息含 UNKNOWN_CONTEXT_FAMILY 标记，供 seed / API 拒绝。
    """
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ValueError(f"UNKNOWN_CONTEXT_FAMILY: not a string: {raw!r}")
    value = raw.strip()
    if value == "":
        return None
    if value not in CONTEXT_FAMILY_VOCABULARY:
        raise ValueError(
            f"UNKNOWN_CONTEXT_FAMILY: {value!r} not in controlled vocabulary "
            f"{sorted(CONTEXT_FAMILY_VOCABULARY)}"
        )
    return value
