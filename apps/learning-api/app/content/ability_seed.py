"""E4-01 应用题能力节点 + 依赖边（RD/COND/REL/MODEL/STRAT/CHECK/TRANSFER）。

小学低年级「应用题解决能力」的纵向切片，按 Backlog E4-01 冻结的 7 个节点。
"""
from __future__ import annotations

# 能力节点（ability_id 前缀统一 app_，domain_code 用 word_problem）
# level_schema.l4_gate：L3→L4 的节点级验证门槛（node policy），
# 禁止在 mastery.py 里写 if ability_id == ... 的硬编码。
# 不同节点可配置不同的 L4 收口要求：
#  - requires_explanation：是否需要「解释/说明」类证据
#  - min_transfer_contexts：最少迁移情境数（默认 3）
ABILITY_NODES = [
    {
        "ability_id": "app_rd",
        "subject": "math",
        "domain_code": "word_problem",
        "name": "读题理解",
        "definition": "能读清题目已知条件与所求问题。",
        "level_schema": {
            "levels": ["L0", "L1", "L2", "L3", "L4"],
            "l4_gate": {"requires_explanation": False, "min_transfer_contexts": 3},
        },
    },
    {
        "ability_id": "app_cond",
        "subject": "math",
        "domain_code": "word_problem",
        "name": "条件识别",
        "definition": "能识别题目中的数量与关系词（一共/还剩/比…多/少）。",
        "level_schema": {
            "levels": ["L0", "L1", "L2", "L3", "L4"],
            "l4_gate": {"requires_explanation": False, "min_transfer_contexts": 3},
        },
    },
    {
        "ability_id": "app_rel",
        "subject": "math",
        "domain_code": "word_problem",
        "name": "数量关系",
        "definition": "能把文字条件转化为加减数量关系。",
        "level_schema": {
            "levels": ["L0", "L1", "L2", "L3", "L4"],
            "l4_gate": {"requires_explanation": True, "min_transfer_contexts": 3},
        },
    },
    {
        "ability_id": "app_model",
        "subject": "math",
        "domain_code": "word_problem",
        "name": "建模表征",
        "definition": "能用图/线段/算式表征问题结构。",
        "level_schema": {
            "levels": ["L0", "L1", "L2", "L3", "L4"],
            "l4_gate": {"requires_explanation": True, "min_transfer_contexts": 3},
        },
    },
    {
        "ability_id": "app_strat",
        "subject": "math",
        "domain_code": "word_problem",
        "name": "策略选择",
        "definition": "能选择正确的运算策略（加减法）。",
        "level_schema": {
            "levels": ["L0", "L1", "L2", "L3", "L4"],
            "l4_gate": {"requires_explanation": True, "min_transfer_contexts": 3},
        },
    },
    {
        "ability_id": "app_check",
        "subject": "math",
        "domain_code": "word_problem",
        "name": "检查验算",
        "definition": "能回代检验结果是否合理。",
        "level_schema": {
            "levels": ["L0", "L1", "L2", "L3", "L4"],
            "l4_gate": {"requires_explanation": False, "min_transfer_contexts": 3},
        },
    },
    {
        "ability_id": "app_transfer",
        "subject": "math",
        "domain_code": "word_problem",
        "name": "迁移变式",
        "definition": "能把已会的关系迁移到新情境（变式题）。",
        "level_schema": {
            "levels": ["L0", "L1", "L2", "L3", "L4"],
            "l4_gate": {"requires_explanation": False, "min_transfer_contexts": 3},
        },
    },
]

# 依赖边（prerequisite 前置）
ABILITY_EDGES = [
    ("app_rd", "app_cond", "prerequisite"),
    ("app_cond", "app_rel", "prerequisite"),
    ("app_rel", "app_model", "prerequisite"),
    ("app_model", "app_strat", "prerequisite"),
    ("app_strat", "app_check", "prerequisite"),
    ("app_strat", "app_transfer", "supports"),
]