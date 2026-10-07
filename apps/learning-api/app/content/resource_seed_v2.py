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
    {
        # Gate R01（FE-1414）：object-counter 数量关系链——SEM-1410 / Gap R01
        # 语义：add/remove 往组放取、compose 合入 locked 盒、count=总数即答案。
        "ability_id": "app_rel",
        "difficulty": 1,
        "task_type": "word_problem",
        "title": "气球合起来（V2 链 R01）",
        "ui_schema_version": "2.0",
        "renderer": "object-counter",
        "mode": "count_compose",
        "content": {
            "stem": "小雨有4个红气球，又拿来了3个蓝气球。把两堆合起来数一数，一共有多少个气球？",
            "answer": 7,
            "goal": "用物体组表征部分-整体合成（先摆后合，答案=总数）",
        },
        "config": {
            "groups": [
                {"group_id": "g1", "label": "红气球", "symbol": "🎈", "count": 0, "locked": False},
                {"group_id": "g2", "label": "蓝气球", "symbol": "🎈", "count": 0, "locked": False},
            ],
            "expected": [
                {"group_id": "g1", "min_count": 4},
                {"group_id": "g2", "min_count": 3},
            ],
            "max_total_count": 12,
        },
        "initial_state": {
            "groups": [
                {"group_id": "g1", "label": "红气球", "symbol": "🎈", "count": 0},
                {"group_id": "g2", "label": "蓝气球", "symbol": "🎈", "count": 0},
            ]
        },
        "capabilities": ["add_object", "remove_object", "compose_groups", "decompose_group", "undo", "reset"],
        "constraints": {"max_total_count": 12},
        "response_type": "object_count",
        "evidence_targets": ["groups", "total"],
        "error_models": [
            {"pattern": "modeling", "code": "modeling"},
            {"pattern": "calc", "code": "calc"},
        ],
        "hint_ladder": [
            "先数一数题里的红气球有几个。",
            "在红气球组里按 4 下「＋1」。",
            "蓝气球也要摆出来，再合起来数。",
            "4 加 3 等于几？",
        ],
        "is_transfer": False,
        "context_family": "school_objects",
    },
    {
        # Gate R04（FE-1415）：number-input 数字答案链——SEM-1413 / Gap R04。
        # submission_id 幂等契约（FE-1410）的专项验证入口：EMPTY 拦提交、
        # 错误答案可达后端、同 submission_id 重放不产生重复证据。
        "ability_id": "app_rel",
        "difficulty": 1,
        "task_type": "word_problem",
        "title": "还剩几只鸟（V2 链 R04）",
        "ui_schema_version": "2.0",
        "renderer": "number-input",
        "mode": "numeric_answer",
        "content": {
            "stem": "树枝上停着7只小鸟，扑棱棱飞走了2只。还剩几只？把答案写在框里。",
            "answer": 5,
            "goal": "从动作情境抽象出减法并直接给出数量答案",
        },
        "config": {"min": 0, "max": 20, "integer_only": True},
        "initial_state": {"answer": None},
        "capabilities": ["answer_input"],
        "constraints": {"integer_only": True},
        "response_type": "number_input",
        "evidence_targets": ["answer"],
        "error_models": [
            {"pattern": "strategy", "code": "strategy"},
            {"pattern": "calc", "code": "calc"},
        ],
        "hint_ladder": [
            "飞走了，鸟是变多了还是变少了？",
            "从7里面拿走2，用什么方法？",
            "7 - 2 等于几？",
            "伸出7根手指，弯下2根，还剩几根？",
        ],
        "is_transfer": False,
        "context_family": "before_after",
    },
    {
        # Gate R07（FE-1416）：ten-frame 数量结构链——SEM-1416 / Gap R07。
        # 20 以内结构：摆 13 = 满框打包成一袋（MAKE_TEN_COMPLETED）+ 活动框 3。
        "ability_id": "app_rel",
        "difficulty": 2,
        "task_type": "word_problem",
        "title": "把糖果装进袋（V2 链 R07）",
        "ui_schema_version": "2.0",
        "renderer": "ten-frame",
        "mode": "quantity_structure",
        "content": {
            "stem": "妈妈买了13颗糖。先在十格框里摆出来，摆满十个就打包装成一袋，剩下的散着放。摆好后提交。",
            "answer": 13,
            "goal": "用十格框表征 20 以内数的十与一结构（补十打包）",
        },
        "config": {"target_count": 13, "max_frames": 2},
        "initial_state": {"tens": 0, "count": 0},
        "capabilities": ["fill", "grouping", "undo", "reset"],
        "constraints": {"continuous_fill": True},
        "response_type": "ten_frame",
        "evidence_targets": ["tens", "current_frame_count"],
        "error_models": [
            {"pattern": "modeling", "code": "modeling"},
            {"pattern": "calc", "code": "calc"},
        ],
        "hint_ladder": [
            "先一颗一颗摆，摆满十个框。",
            "满十个了！点打包，把它们装成一袋。",
            "还剩 3 颗，在新框里摆 3 个。",
            "一袋是 10，再加 3，一共是几？",
        ],
        "is_transfer": False,
        "context_family": "sharing",
    },
    {
        # Gate R02（FE-1418）：bar-model 条形模型链——SEM / Gap R02。
        # part_whole 模式：部分 5+3，答案条=整体（c=a+b）。核心验证模型结构
        # evaluator：已知条摆错=modeling、整体不比部分长=relation、数错=calc。
        "ability_id": "app_model",
        "difficulty": 1,
        "task_type": "word_problem",
        "title": "画条形图算一共（V2 链 R02）",
        "ui_schema_version": "2.0",
        "renderer": "bar-model",
        "mode": "part_whole",
        "content": {
            "stem": "小雨有5颗红星星，又画了3颗黄星星。把两根部分条摆出来，再把整体条摆得和加起来一样长。一共几颗？",
            "answer": 8,
            "goal": "用条形图表征部分-整体关系（先摆已知，再摆整体）",
        },
        "config": {"mode": "part_whole", "known": {"a": 5, "b": 3}, "answer_bar": "c", "max_blocks": 12},
        "initial_state": {"bars": {"a": 0, "b": 0, "c": 0}, "answerTouched": False},
        "capabilities": ["add_object", "remove_object", "answer_input", "undo", "reset"],
        "constraints": {"structure": "whole_gt_parts"},
        "response_type": "bar_model",
        "evidence_targets": ["bars", "structure"],
        "error_models": [
            {"pattern": "modeling", "code": "modeling"},
            {"pattern": "calc", "code": "calc"},
        ],
        "hint_ladder": [
            "题目里红星星和黄星星各有几颗？先把这两根条摆出来。",
            "整体条要跟什么一样长？和两根部分加起来一样长。",
            "5 加 3 等于几？整体条就摆几格。",
            "数一数你的整体条：是不是从开头到末尾正好 8 格？",
        ],
        "is_transfer": False,
        "context_family": "school_objects",
    },
]
