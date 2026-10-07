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
    {
        # Gate R06（FE-1419）：place-value 位值板链——Gap R06（Batch B 第二题）。
        # 数字卡放进百/十/个框（digit movement）；牌堆=目标数的乱序排列，
        # 孩子只可能"站错位置"——structure evaluator 报 place_confusion，
        # 正是 R06 Diagnosis P0"位值混淆"的原料。app_rd 能力节点首题。
        "ability_id": "app_rd",
        "difficulty": 2,
        "task_type": "number_concept",
        "title": "数字卡回家（V2 链 R06）",
        "ui_schema_version": "2.0",
        "renderer": "place-value",
        "mode": "place_value_build",
        "content": {
            "stem": "数字卡 3、5、2 走丢了。把它们放回百、十、个的框里，组成 352。",
            "answer": 352,
            "goal": "按数位把数字放到正确位置（位值结构感知）",
        },
        "config": {"target": 352, "pool": [2, 5, 3]},
        "initial_state": {"pool": [2, 5, 3], "slots": [None, None, None], "picked": None},
        "capabilities": ["select", "answer_input", "undo", "reset", "highlight", "focus"],
        "constraints": {"pool_multiset_equals_target_digits": True},
        "response_type": "place_value",
        "evidence_targets": ["slots", "structure"],
        "error_models": [
            {"pattern": "place_value_confusion", "code": "modeling"},
            {"pattern": "calc", "code": "calc"},
        ],
        "hint_ladder": [
            "352 的百位是几？把那张卡拿起来。",
            "拿起 3，点百位框。十位和个位还差谁？",
            "十位是 5，个位是 2——顺序别站反啦。",
            "从百位读到个位：三百…再读下去是什么？",
        ],
        "is_transfer": False,
        "context_family": "school_objects",
    },
    {
        # Gate R10（FE-1420）：formula-board 算式填空链之一（未知数）——Gap R10。
        # □ + 4 = 9：equation semantic evaluator 左右求值核对；
        # 答案=未知加数 5。app_strat（策略/列式）能力节点首题。
        "ability_id": "app_strat",
        "difficulty": 2,
        "task_type": "equation_fill",
        "title": "方框里藏了几（V2 链 R10）",
        "ui_schema_version": "2.0",
        "renderer": "formula-board",
        "mode": "unknown_number",
        "content": {
            "stem": "盒子里有一些弹珠，外面又有4颗。一共有9颗。□+4=9，方框里藏了几？点亮圆圈填数字。",
            "answer": 5,
            "goal": "用等式关系求未知加数（方程思想萌芽）",
        },
        "config": {
            "tokens": [
                {"t": "slot", "id": "box", "accept": "number"},
                {"t": "op", "v": "+"},
                {"t": "num", "v": 4},
                {"t": "eq"},
                {"t": "num", "v": 9},
            ],
            "answer_slot": "box",
            "max_number": 20,
        },
        "initial_state": {"filled": {}, "activeSlot": None},
        "capabilities": ["answer_input", "highlight", "focus", "reset", "undo"],
        "constraints": {"equation_sides_max_one_op": True},
        "response_type": "formula_board",
        "evidence_targets": ["filled", "structure"],
        "error_models": [
            {"pattern": "relation", "code": "calc"},
            {"pattern": "calc", "code": "calc"},
        ],
        "hint_ladder": [
            "等号右边一共有9颗，左边要凑出同样多的9。",
            "外面的4颗已经在这儿了，方框要替你补几颗才到9？",
            "想一想：4 加几等于 9？",
            "从4往上数到9，数了几步？",
        ],
        "is_transfer": False,
        "context_family": "school_objects",
    },
    {
        # Gate R10（FE-1420）：formula-board 算式填空链之二（未知运算符）——
        # Gap R10 Diagnosis P0"运算符错误"的专项靶：7○2=5，答案=-。
        # 填成 + 时 evaluator 翻转符号可救 → structure.error=operator 原料。
        "ability_id": "app_strat",
        "difficulty": 2,
        "task_type": "equation_fill",
        "title": "加号还是减号（V2 链 R10）",
        "ui_schema_version": "2.0",
        "renderer": "formula-board",
        "mode": "unknown_operator",
        "content": {
            "stem": "鱼缸里有7条鱼，游走了一些剩下几条？看图列式 7○2=5。圆圈里该点加号还是减号？",
            "answer": "-",
            "goal": "按数量变化选择正确的运算符号",
        },
        "config": {
            "tokens": [
                {"t": "num", "v": 7},
                {"t": "slot", "id": "op0", "accept": "operator"},
                {"t": "num", "v": 2},
                {"t": "eq"},
                {"t": "num", "v": 5},
            ],
            "answer_slot": "op0",
            "max_number": 20,
        },
        "initial_state": {"filled": {}, "activeSlot": None},
        "capabilities": ["answer_input", "highlight", "focus", "reset", "undo"],
        "constraints": {"equation_sides_max_one_op": True},
        "response_type": "formula_board",
        "evidence_targets": ["filled", "structure"],
        "error_models": [
            {"pattern": "operator", "code": "modeling"},
            {"pattern": "relation", "code": "calc"},
        ],
        "hint_ladder": [
            "鱼是变多了还是变少了？",
            "变少要用哪个符号？",
            "7 加 2 是几？和等号右边一样吗？",
            "试试减号：7 减 2 等于几？",
        ],
        "is_transfer": False,
        "context_family": "before_after",
    },
    {
        # Gate R08（FE-1421）：array-board 阵列板链——Gap R08（Batch C 起手）。
        # 3行×4列排队情境；product/structure 解耦是数学点：摆成 4×3 积仍=12
        # （交换律，后端判对），但 structure.error=transpose 留痕（行列概念互换
        # 原料，R08 Diagnosis P0"行列概念错误"）。lineup_position 词表族首题。
        "ability_id": "app_model",
        "difficulty": 1,
        "task_type": "array",
        "title": "排队做操（V2 链 R08）",
        "ui_schema_version": "2.0",
        "renderer": "array-board",
        "mode": "array_structure",
        "content": {
            "stem": "小朋友排队做操，每排站4人，站了3排。用行列把队伍排出来（先想横的几排、竖的几人），数一数一共几人？",
            "answer": 12,
            "goal": "用行列阵列表征几个几（3排×每排4人=12）",
        },
        "config": {"target_rows": 3, "target_cols": 4, "max_rows": 8, "max_cols": 8},
        "initial_state": {"rows": 0, "cols": 0},
        "capabilities": ["add_object", "remove_object", "answer_input", "undo", "reset"],
        "constraints": {"rows_le_max": 8, "cols_le_max": 8},
        "response_type": "array_board",
        "evidence_targets": ["rows", "columns", "structure"],
        "error_models": [
            {"pattern": "transpose", "code": "modeling"},
            {"pattern": "count", "code": "calc"},
        ],
        "hint_ladder": [
            "做操的队：横着一排一排站，有几排？",
            "题目说站了3排——先加到3行。",
            "每排站4人，就是竖着一列一列有4个。",
            "3 行 4 列：一行一行数，4、8、12……",
        ],
        "is_transfer": False,
        "context_family": "lineup_position",
    },
    {
        # Gate R09（FE-1422）：grouping-board 平均分物链——Gap R09（Batch C 第二题）。
        # 12 颗糖分给 3 个小朋友（3组×每组一样多，答案=每组 4）。
        # structure evaluator 二分类各有靶：count（组数≠3）/unequal（不均）。
        # sharing 族第二题；app_rel 节点第四题。
        "ability_id": "app_rel",
        "difficulty": 3,
        "task_type": "word_problem",
        "title": "把糖分给小朋友（V2 链 R09）",
        "ui_schema_version": "2.0",
        "renderer": "grouping-board",
        "mode": "equal_groups",
        "content": {
            "stem": "12颗糖要平均分给3个小朋友。圈出3个组，把糖一颗一颗发完，每人都要一样多。每人几颗？",
            "answer": 4,
            "goal": "主动建组+逐组分发，建立等分（平均）概念",
        },
        "config": {"items": 12, "target_groups": 3, "max_groups": 6},
        "initial_state": {"groups": [], "pool": 12},
        "capabilities": ["grouping", "answer_input", "undo", "reset"],
        "constraints": {"items_equal_groups": True},
        "response_type": "grouping_board",
        "evidence_targets": ["groups", "structure"],
        "error_models": [
            {"pattern": "group_count", "code": "modeling"},
            {"pattern": "unequal_share", "code": "modeling"},
            {"pattern": "calc", "code": "calc"},
        ],
        "hint_ladder": [
            "先圈出3个组——要分给几个小朋友？",
            "从上面的糖堆里发：点一个组的＋号，一颗一颗发。",
            "发完啦？数数每组是不是一样多。",
            "12颗平均分给3人：12÷3=几？",
        ],
        "is_transfer": False,
        "context_family": "sharing",
    },
    {
        # FE-1423 R11 estimation-canvas 金题：近似数估算（38 本≈40），
        # **shopping 族首题**（词表"启用但零覆盖"第二族开始有真实数据）。
        # expected 必须是 actual 四舍五入到最近十（前端 parseEstimationConfig 同守卫）。
        "code": "V2-R11-EST-001",
        "title": "书架上大约有多少本书",
        "ability_id": "app_model",
        "renderer": "estimation-canvas",
        "ui_schema_version": "2.0",
        "mode": "estimation_range",
        "response_type": "estimation_canvas",
        "content": {
            "stem": "书店阿姨数到一半记下了：这一摞是 10 本。整个书架上的书比这一摞多得多。拖动滑条估一估书架上大约有多少本，再选一选你是怎么想的。（答案估到最接近的整十）",
            "answer": 40,
            "actual": 38,
            "goal": "用参照量估算总数并四舍五入到整十",
        },
        "config": {
            "reference": 10,
            "max": 60,
            "expected": 40,
            "actual": 38,
            "tolerance": 6,
        },
        "initial_state": {"estimate": None, "reason": None, "adjust_history": []},
        "constraints": {"round_to_nearest_ten": True},
        "capabilities": ["answer_input", "highlight", "focus", "undo", "reset"],
        "evidence_targets": ["estimate", "reason", "adjust_history", "structure"],
        "hint_ladder": [
            {"level": 1, "text": "先看看那一摞 10 本有多高，再比一比书架上的高度。"},
            {"level": 2, "text": "书架上的书摞起来大约有几个'一摞10本'那么高？"},
            {"level": 3, "text": "比 3 摞多一点、比 4 摞少一点——3 摞是 30，4 摞是 40，你估哪个更接近？"},
            {"level": 4, "text": "估算要估到最接近的整十：想一想 38 离 30 近还是离 40 近？"},
        ],
        "error_models": [
            {"pattern": "no_reference_use", "code": "E-EST-01", "note": "没看参照量随手拖（估算策略错误原料）"},
            {"pattern": "too_high", "code": "E-EST-02", "note": "估得过高（tolerance evaluator 方向原料）"},
            {"pattern": "too_low", "code": "E-EST-03", "note": "估得过低（方向原料，close 分'差一点'与'差很多'）"},
        ],
        "task_type": "estimation",
        "difficulty": 2,
        "is_transfer": False,
        "context_family": "shopping",
    },
]
