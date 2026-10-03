"""V2 纵向链资源（FE-1405 后端切片）。

与 GOLD_RESOURCES（50 题 V1）分文件：V2 资源显式声明 ui_schema_version="2.0"，
seed 按此字段分流 _build_ui_schema_v2；context_family 显式声明（仍过词表校验）。

A5 链：number-line jump_sequence——number-line 是 implemented renderer，
V2 契约可立即端到端验证（评审 §3.2 五代表链之一）。
"""
from __future__ import annotations

# 结构约定：
# - stem/answer/goal 进 content（判分答案 = content.answer，标量）
# - ui_schema_version:"2.0" + mode/config/initial_state/capabilities/constraints 进 V2 schema
# - context_family 显式声明（canonical，seed 校验）
GOLD_RESOURCES_V2: list[dict] = [
    {
        "ability_id": "app_rel",
        "difficulty": 3,
        "task_type": "word_problem",
        "title": "数轴跳跳跳（V2链）",
        "ui_schema_version": "2.0",
        "renderer": "number-line",
        "mode": "jump_sequence",
        "content": {
            "stem": "从20出发，每次向右跳5，跳3次，终点是多少？",
            "answer": 35,
            "goal": "用数轴跳步表征等步长连续增加",
        },
        "config": {
            "scale": {"min": 0, "max": 50, "tick_step": 5},
            "start_marker": {"marker_id": "start", "value": 20},
        },
        "initial_state": {"jumps": []},
        "capabilities": ["jump", "place_marker", "undo", "reset"],
        "constraints": {"snap_to_tick": True, "auto_complete_jumps": False},
        "response_type": "number_line",
        "evidence_targets": ["jumps"],
        "error_models": [
            {"pattern": "strategy", "code": "strategy"},
            {"pattern": "calc", "code": "calc"},
        ],
        "hint_ladder": [
            "先在数轴上找到起点20。",
            "向右跳一步是变多还是变少？一步跳几？",
            "连续跳3次相同步长，可以用加法。",
            "20 + 5 + 5 + 5 等于几？",
        ],
        "is_transfer": False,
        "context_family": "before_after",
    },
    {
        # Gate B5（FE-1403 契约 §19）：column-arithmetic 竖式链
        "ability_id": "app_rel",
        "difficulty": 4,
        "task_type": "word_problem",
        "title": "图书馆的新书（竖式 V2 链）",
        "ui_schema_version": "2.0",
        "renderer": "column-arithmetic",
        "mode": "addition",
        "content": {
            "stem": "图书角原来有47本书，这周又买来28本。现在一共有多少本书？用竖式算，填好进位。",
            "answer": 75,
            "goal": "用竖式表征两位数进位加法的过程与结果",
        },
        "config": {
            "operands": [47, 28],
            "places": ["ones", "tens", "hundreds"],
            "operand_layout": "fixed",
        },
        "initial_state": {"result_digits": [], "carries": []},
        "capabilities": ["input_digit", "place_carry", "edit_carry", "step_submit", "undo", "reset"],
        "constraints": {"digit_min": 0, "digit_max": 9, "carry_autofill": False},
        "response_type": "column_arithmetic",
        "evidence_targets": ["result_digits", "carries"],
        "error_models": [
            {"pattern": "calc", "code": "calc"},
            {"pattern": "strategy", "code": "strategy"},
        ],
        "hint_ladder": [
            "先看看个位：7加8够不够十？",
            "个位满十要向十位进1。",
            "7 + 8 = 15，个位写5，向前进1。",
            "十位 4 + 2 再加进上来的1，等于几？",
        ],
        "is_transfer": False,
        "context_family": "before_after",
    },
]
