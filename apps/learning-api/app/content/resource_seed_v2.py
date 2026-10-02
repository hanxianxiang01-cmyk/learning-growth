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
]
