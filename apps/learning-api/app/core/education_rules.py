"""冻结基线 V1.3.1 的教育规则常量（唯一真相源，禁止在服务里散落硬编码）。

对应基线 docx 第 5 节 + DDL 注释的 V1.3 mastery derivation contract。
"""
from __future__ import annotations

# Mastery 四维权重（缺维度禁止重归一化）
MASTERY_WEIGHTS = {
    "correctness": 0.35,
    "independence": 0.25,
    "stability": 0.20,
    "transfer": 0.20,
}
RULE_VERSION = "mastery-v1.3"

# Independence：由 max_hint_level 映射（0~4）
HINT_LEVEL_TO_INDEPENDENCE = {0: 1.00, 1: 0.75, 2: 0.50, 3: 0.25, 4: 0.00}

# C/I 评估窗口：最近 8 条有效可评分原子证据
CI_WINDOW = 8
CI_MIN_RESOURCE_VERSIONS = 3
CI_MIN_SESSIONS = 2

# Stability 派生：最近 5 条 standard/retention
STABILITY_WINDOW = 5
STABILITY_MIN_RESOURCE_VERSIONS = 3
STABILITY_MIN_SESSIONS = 2

# Transfer 派生：最近最多 4 条，最少 2 条
TRANSFER_WINDOW_MAX = 4
TRANSFER_MIN_ROWS = 2
TRANSFER_MIN_CONTEXT_FAMILIES = 2
TRANSFER_MIN_SESSIONS = 2

# 升级 Gate（MVP 默认冻结）
GATE_L2_L3 = {
    "score": 0.80,
    "correctness": 0.80,
    "independence": 0.75,
    "stability": 0.75,
    "transfer": 0.60,
}
GATE_L3_L4 = {
    "transfer": 0.80,
    "min_transfer_evidence": 3,
    "min_context_families": 3,
}

# 原子证据类型（source_evidence_ids 为空）
ATOMIC_EVIDENCE_TYPES = ("attempt_standard", "attempt_transfer", "retention_check", "explanation")
# 派生证据类型（source_evidence_ids 非空）
DERIVED_EVIDENCE_TYPES = ("stability_window", "transfer_window")

# 诊断分类 E01~E07
DIAGNOSIS_LABELS = {
    "E01": "knowledge_gap",
    "E02": "reading_comprehension_gap",
    "E03": "math_language_gap",
    "E04": "modeling_gap",
    "E05": "strategy_selection_gap",
    "E06": "calculation_error",
    "E07": "checking_validation_gap",
}