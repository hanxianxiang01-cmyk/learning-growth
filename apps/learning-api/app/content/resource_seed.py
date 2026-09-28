"""E4-02 数量关系黄金资源包 —— D1-D4 应用题，含答案/错误模型/提示阶梯/迁移。

每个资源是一个 word_problem，带：
- answer: 判分依据
- error_models: 常见错误 → 对应诊断码（calc/modeling/strategy 等）
- hint_ladder: 4 级提示（对应 Hint 状态机）
- transfer_variants: 迁移变式（关联 app_transfer）
"""
from __future__ import annotations

# 资源包：D1(最易) → D4(较难)
GOLD_RESOURCES = [
    {
        "ability_id": "app_rel",
        "difficulty": 1,
        "task_type": "word_problem",
        "title": "加法一（一共）",
        "content": {
            "stem": "小明有 3 个苹果，妈妈又给了他 2 个。小明现在一共有多少个苹果？",
            "answer": 5,
            "goal": "理解「一共」用加法",
        },
        "error_models": [
            {"pattern": "算错", "code": "calc"},
            {"pattern": "用减法", "code": "strategy"},
        ],
        "hint_ladder": [
            "想一想：是变多了还是变少了？",
            "变多了要用什么方法？",
            "把 3 和 2 合在一起，用加法。",
            "3 + 2 等于几？",
        ],
        "transfer_variants": [
            {"stem": "小红有 4 支铅笔，又买了 3 支，一共有几支？", "answer": 7},
        ],
    },
    {
        "ability_id": "app_rel",
        "difficulty": 2,
        "task_type": "word_problem",
        "title": "减法一（还剩）",
        "content": {
            "stem": "树上有 8 只小鸟，飞走了 3 只。树上还剩几只小鸟？",
            "answer": 5,
            "goal": "理解「还剩」用减法",
        },
        "error_models": [
            {"pattern": "算错", "code": "calc"},
            {"pattern": "用加法", "code": "strategy"},
        ],
        "hint_ladder": [
            "想一想：是变多了还是变少了？",
            "变少了要用什么方法？",
            "从 8 里面去掉 3，用减法。",
            "8 - 3 等于几？",
        ],
        "transfer_variants": [
            {"stem": "停车场有 9 辆车，开走了 4 辆，还剩几辆？", "answer": 5},
        ],
    },
    {
        "ability_id": "app_model",
        "difficulty": 3,
        "task_type": "word_problem",
        "title": "比多比少",
        "content": {
            "stem": "小明有 5 个气球，小红比小明多 2 个。小红有多少个气球？",
            "answer": 7,
            "goal": "理解「比…多/少」的数量关系",
        },
        "error_models": [
            {"pattern": "用减法", "code": "strategy"},
            {"pattern": "没找准基准", "code": "modeling"},
        ],
        "hint_ladder": [
            "题目里是「谁比谁多」？",
            "「比…多」一般用什么方法？",
            "先找出基准量，再想多了几个。",
            "5 + 2 等于几？",
        ],
        "transfer_variants": [
            {"stem": "乐乐有 6 块糖，东东比乐乐少 2 块。东东有几块？", "answer": 4},
        ],
    },
    {
        "ability_id": "app_strat",
        "difficulty": 4,
        "task_type": "word_problem",
        "title": "两步应用题",
        "content": {
            "stem": "小华先买了 3 支铅笔，又买了 2 支，用掉了 1 支。他现在还有几支？",
            "answer": 4,
            "goal": "用两步解决复合问题",
        },
        "error_models": [
            {"pattern": "只算一步", "code": "modeling"},
            {"pattern": "顺序错", "code": "check"},
        ],
        "hint_ladder": [
            "这道题要分几步做？",
            "先算出一共买了多少支。",
            "再用总数减掉用掉的。",
            "(3 + 2) - 1 等于几？",
        ],
        "transfer_variants": [
            {"stem": "篮子里有 5 个橘子，吃掉 2 个，又放进 3 个，现在有几个？", "answer": 6},
        ],
    },
]