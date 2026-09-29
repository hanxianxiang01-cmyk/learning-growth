"""把「应用题完整题库 Excel」转成 GOLD_RESOURCES 结构。

输入：应用题完整题库_v1.1_三批共50题.xlsx（33 列）
输出：app/content/.question_bank_generated.py（GOLD_RESOURCES list）

映射规则：
- content = { stem, answer, goal }
- error_models = [{pattern, code} for common_error_1/2/3]
- hint_ladder = [hint_l1..l4]
- ui_actions = [hint_l1_ui_action..l4]
- visual（manipulative 题）按 relation_type 语义 + 题干数字生成

visual 语义（已按本题库样本验证）：
- objects: 题干前两个数字 = 两组实体数量
- bar-model compare_difference: 两个数字都是实体数量（求差）
- bar-model compare_more/less_unknown / derived_compare_total: 大数字=已知实体, 小数字=差
- number-line: 起点用题干明确位置或第一个数字
"""
from __future__ import annotations

import re
import sys

import openpyxl

# 默认输入 Excel 路径（可用命令行参数覆盖：python convert_question_bank.py <xlsx路径>）
EXCEL = sys.argv[1] if len(sys.argv) > 1 else "/Users/hanxianxiang/Downloads/学习/儿童学习成长系统/应用题完整题库_v1.1_三批共50题.xlsx"
OUT = "app/content/resource_seed.py"

SYMBOL_MAP = {
    "气球": "🎈", "小鸟": "🐦", "饼干": "🍪", "彩笔": "🖍", "铅笔": "✏️",
    "贴纸": "⭐", "故事书": "📖", "珠子": "🔮", "棋子": "⚫", "球": "⚽",
    "积木": "🧱", "花": "🌸", "糖": "🍬", "杯子": "🥛", "椅子": "🪑",
    "星星": "⭐", "贝壳": "🐚", "卡片": "🃏", "书": "📚", "彩纸": "🎨",
    "苹果": "🍎", "梨": "🍐", "橘子": "🍊", "车": "🚗", "笔": "🖊",
}

# 人名黑名单：非人名的提取结果
_NAME_BLACKLIST = {
    "一共", "现在", "原来", "其余", "其中", "旁边", "后来", "题目", "老师",
    "左边", "右边", "树上", "盘子", "盒子", "书包", "篮子", "餐桌", "操场",
    "停车场", "玩具", "教室", "书架", "公交车", "每盒", "盒一", "的棋",
    "雨今", "晨练", "又", "每盒都", "盒一共", "的棋子", "雨今天", "小宇",
    "第一", "第二", "书本", "彩纸", "彩笔",
}

# relation_type 分类
COMPARE_UNKNOWN = {"compare_more_unknown", "compare_less_unknown", "derived_compare_total"}
COMPARE_DIFF = {"compare_difference"}
PART_WHOLE = {"part_whole_part", "part_whole_total"}
BAR_TYPES = COMPARE_UNKNOWN | COMPARE_DIFF | PART_WHOLE | {"check_equation"}
NL_TYPES = {"change_increase_result", "change_decrease_result", "change_inverse_original",
            "equal_groups_total", "two_step_change", "condition_filter_decrease",
            "condition_filter_two_step", "condition_filter_total"}


def _nums(prompt: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", prompt)]


def _names(prompt: str) -> list[str]:
    """提取真实人名（主语），清洗误匹配。"""
    found = []
    for m in re.finditer(r"([\u4e00-\u9fa5]{1,3})(?=有|比|跑|走|画|带|买|送|吃|拿|摆|搬|借|放)", prompt):
        name = m.group(1)
        if name in _NAME_BLACKLIST:
            continue
        if name not in found:
            found.append(name)
    # 若无干净人名，返回空
    return [n for n in found if n not in _NAME_BLACKLIST]


def _symbol(prompt: str) -> str:
    for item, emoji in SYMBOL_MAP.items():
        if item in prompt:
            return emoji
    return "●"


def _build_visual(rid, prompt, answer, relation_type, visual_type, task_kind):
    if task_kind != "manipulative":
        return None

    nums = _nums(prompt)
    names = _names(prompt)

    # ---- object-counter / objects → type "objects" ----
    if visual_type in ("object-counter", "objects"):
        sym = _symbol(prompt)
        counts = nums[:2]
        groups = []
        for i, c in enumerate(counts):
            # object-counter 是「合起来数」，分组名用中性「第i组」最通用（避免人名误提取）
            groups.append({"id": f"g{i+1}", "label": f"第{i+1}组", "count": c, "symbol": sym})
        return {"type": "objects", "groups": groups}

    # ---- number-line ----
    if visual_type == "number-line":
        start = None
        m = re.search(r"(?:数轴的?|位置|从)(\d+)", prompt)
        if m:
            start = int(m.group(1))
        elif nums:
            start = nums[0]
        maxv = max(nums) if nums else 10
        line_max = max(maxv + 3, (answer if isinstance(answer, int) else 0) + 2)
        return {"type": "number-line", "min": 0, "max": line_max, "step": 1, "start": start}

    # ---- bar-model ----
    if visual_type == "bar-model":
        # 决定 relationship
        rel = "part-whole" if relation_type in PART_WHOLE else "compare"
        maxv = max(nums) if nums else 10

        # 已知主体名
        base_label = names[0] if names else "已知"

        if relation_type in PART_WHOLE:
            # 整体 + 部分
            total = nums[0] if nums else 0
            part = nums[1] if len(nums) > 1 else 0
            bars = [
                {"id": "total", "label": "一共", "value": total, "min": 0, "max": total},
                {"id": "known", "label": "已知部分", "value": part, "min": 0, "max": total},
                {"id": "unknown", "label": "未知部分", "min": 0, "max": total, "unknown": True},
            ]
            return {"type": "bar-model", "relationship": rel, "bars": bars, "max_value": total + 2}

        if relation_type in COMPARE_DIFF:
            # 两个实体数量都已知，求差
            a = nums[0] if nums else 0
            b = nums[1] if len(nums) > 1 else 0
            bars = [
                {"id": "a", "label": "已知一", "value": a, "min": 0, "max": max(a, b)},
                {"id": "b", "label": "已知二", "value": b, "min": 0, "max": max(a, b)},
            ]
            return {"type": "bar-model", "relationship": rel, "bars": bars, "max_value": max(a, b) + 2}

        if relation_type in COMPARE_UNKNOWN:
            # 大数字=已知实体，小数字=差；未知是另一条
            big = max(nums) if nums else 0
            small = min(nums) if nums else 0
            bars = [
                {"id": "base", "label": "已知", "value": big, "min": 0, "max": big + small},
                {"id": "unknown", "label": "未知", "min": 0, "max": big + small, "unknown": True},
            ]
            return {"type": "bar-model", "relationship": rel, "bars": bars, "max_value": big + small + 2}

        if relation_type == "check_equation":
            a = nums[0] if nums else 0
            bars = [{"id": "a", "label": "已知", "value": a, "min": 0, "max": maxv}]
            return {"type": "bar-model", "relationship": rel, "bars": bars, "max_value": maxv + 2}

        # fallback
        bars = [{"id": "a", "label": "已知", "value": nums[i] if i < len(nums) else 0,
                 "min": 0, "max": maxv} for i in range(min(len(nums), 2))]
        return {"type": "bar-model", "relationship": rel, "bars": bars, "max_value": maxv + 2}

    return None


def convert() -> list[dict]:
    wb = openpyxl.load_workbook(EXCEL, data_only=True)
    ws = wb["完整题库_50题"]
    rows = list(ws.iter_rows(values_only=True))
    header_idx = next(i for i, r in enumerate(rows) if r and r[0] == "batch")
    header = rows[header_idx]
    idx = {h: i for i, h in enumerate(header)}
    data = [r for r in rows[header_idx + 1:] if r and r[0] and str(r[0]).startswith("Batch")]

    out = []
    for r in data:
        g = lambda k: r[idx[k]] if k in idx else None
        prompt = g("prompt")
        answer = g("answer")
        errors = [g("common_error_1"), g("common_error_2"), g("common_error_3")]
        errors = [e for e in errors if e]
        ladder = [g("hint_l1"), g("hint_l2"), g("hint_l3"), g("hint_l4")]
        ui_types = [g("hint_l1_ui_action"), g("hint_l2_ui_action"), g("hint_l3_ui_action"), g("hint_l4_ui_action")]

        visual = _build_visual(
            g("resource_id"), prompt, answer, g("relation_type"), g("visual_type"), g("task_kind")
        )

        item = {
            "ability_id": g("ability_id"),
            "difficulty": g("difficulty"),
            "task_type": "word_problem",
            "title": g("title"),
            "content": {
                "stem": prompt,
                "answer": answer,
                "goal": g("learning_goal"),
            },
            "error_models": [{"pattern": e, "code": e} for e in errors],
            "hint_ladder": [h for h in ladder],
            "ui_actions": ui_types,
            "is_transfer": bool(g("is_transfer_task")),
        }
        if visual is not None:
            item["visual"] = visual
            item["tools"] = [t.strip() for t in (g("tools") or "").split(",") if t.strip()]
        out.append(item)

    return out


if __name__ == "__main__":
    items = convert()
    body = repr(items)
    header = '''"""应用题黄金资源包 v1.1 —— 三批共 50 题（由 scripts/convert_question_bank.py 从 Excel 生成）。

每个资源带：
- content.stem / answer / goal
- error_models：常见错误 → 诊断码
- hint_ladder：4 级提示阶梯
- ui_actions：逐级 hint 对应的 WorkspaceUiAction（可空）
- visual / tools：TaskUISchema V1 可视化结构
- is_transfer：是否迁移变式题
"""
'''
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(body)
        f.write("\n")
    print(f"生成 {len(items)} 题 → {OUT}")
    from collections import Counter
    print("能力分布:", dict(Counter(i["ability_id"] for i in items)))
    mv = [i for i in items if "visual" in i]
    print("manipulative(有 visual):", len(mv))
    print("number(无 visual):", len(items) - len(mv))