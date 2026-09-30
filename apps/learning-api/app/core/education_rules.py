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
# L1→L2：把冻结基线「可在 Hint≤2 支持下稳定完成」补成可执行规则。
# 阈值是 V1.3 工程默认值（非科学常数），由 rule_version 固化，后续只能新版本校准。
GATE_L1_L2 = {
    "min_eligible_evidence": 5,   # standard/retention 有效证据数
    "min_resource_versions": 3,   # 跨资源多样性
    "min_sessions": 2,            # 跨 Session 多样性
    "correctness": 0.80,
    "independence": 0.50,
    "stability": 0.50,
    # 非补偿门槛：≥ 4/5 任务 max_hint_level ≤ 2，避免几次 Hint0 抵消 Hint4
    "min_low_hint_ratio": 0.80,
    "max_hint_level": 2,
}
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

# Evidence role → evidence_type 映射（role 属于 Task Assignment，不绑死 Resource）
# 证据角色（evidence_role）：standard / transfer / retention / explanation
EVIDENCE_ROLE_TO_TYPE = {
    "standard": "attempt_standard",
    "transfer": "attempt_transfer",
    "retention": "retention_check",
    "explanation": "explanation",
}
# 默认 role：已有资源未配置时兜底 standard
DEFAULT_EVIDENCE_ROLE = "standard"

# Review / Downgrade 策略（B8）：单次失败不降级，近期质量走低先进入 review。
# 阈值进入 rule config，不散落服务代码。
REVIEW_POLICY = {
    "recent_window": 3,          # 用最近 N 条可评分原子证据判定 review
    "min_failures": 2,           # 触发 review 的最少失败次数（跨 N 窗口）
    "downgrade_failures": 3,     # 窗口内 N 条全部失败才真正降 1 级
    "quality_floor": 0.50,       # 低质 correctness 底线（备用判定口径）
}

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