#!/usr/bin/env python3
"""FE-1468：语义族判据自测（DB-free，进 pr_gate 可跑）。

为什么需要这个测试：
    分族判据是**纯函数式的启发式**，最容易出的错不是崩溃，而是
    "看起来很合理、实际判错一批题"，而且判错了也不会有任何报错。
    2026-10-21 一轮校准里就连踩三个坑，全部属于"静默判错"：
      · 动词表漏「排好/补上」→ 25 条纯构造题被判成数值题
      · 判断词表含 "×"        → "5×5方格盘" 命中乘号，几何题被判成判断题
      · DRAG_RENDERERS 定义了却从未参与判定 → 死代码伪装成判据
    所以用真实题面做定点回归，而不是只测"函数能跑"。

运行：python3 scripts/iqc/rt1468/test_worklist_family.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_worklist_union as B  # noqa: E402

FAIL: list[str] = []
N = 0


def note(label: str, ok: bool, detail: str = "") -> None:
    global N
    N += 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAIL.append(label)


# ---- T1 「×」不得作为判断词（实测事故：5×5 方格盘被判成判断题）----
_t1 = ("在5×5方格盘中，行和列都从0开始编号。棋子从(2,2)出发，要到(0,1)。"
       "请规划包含行、列两个方向移动的路线，到达后提交终点格编码。")
fam, why = B.semantic_family("direction", "1", _t1, "direction-grid")
note("T1 「5×5方格盘」不因乘号被误判为判断题",
     fam == "numeric_judge" and not why.startswith("R2"), f"{fam} / {why}")

# ---- T2 真正的判断题仍要认出（"检查…正确填1，错误填0"）----
_t2 = ("小美有6支红笔和4支蓝笔。小东说“一共有10支笔”。"
       "请检查：正确填1，错误填0。")
fam, why = B.semantic_family("direct", "1", _t2, "legacy:direct")
note("T2 「请检查：正确填1，错误填0」被 R2 正确识别为判断题",
     fam == "numeric_judge" and why.startswith("R2"), f"{fam} / {why}")

# ---- T3 排序题必须进构造族（动词表漏词事故）----
_t3 = ("桌上有4张数字卡，当前从左到右依次是[4, 9, 1, 6]。"
       "请拖动卡片，把它们按数字从小到大排好，再提交完整顺序。")
fam, why = B.semantic_family("ordering", "1469", _t3, "sorting-board")
note("T3 「从小到大排好…提交完整顺序」进构造族",
     fam == "construct_constraint", f"{fam} / {why}")

# ---- T4 规律延拓必须进构造族（"补上/接下来的"事故）----
_t4 = ("颜色编码规律板的前四格依次是 4、2、4、2。观察两次重复，"
       "再按顺序补上接下来的两格。")
fam, why = B.semantic_family("pattern", "42", _t4, "pattern-board")
note("T4 「补上接下来的两格」进构造族",
     fam == "construct_constraint", f"{fam} / {why}")

# ---- T5 位值拼数必须进构造族（"拖到对应数位…完整数字"）----
_t5 = ("位值卡片[5, 8]已经准备好。请按“十位是5，个位是8”的要求拖到对应数位，"
       "再写出摆好的完整数字。")
fam, why = B.semantic_family("place_value", "58", _t5, "place-value")
note("T5 「拖到对应数位…摆好的完整数字」进构造族",
     fam == "construct_constraint", f"{fam} / {why}")

# ---- T6 纯算术题不得被构造动词误伤 ----
_t6 = "9+9+9="
fam, why = B.semantic_family("arithmetic", "27", _t6, "number-input")
note("T6 「9+9+9=」保持数值族（动词表不误伤）",
     fam == "numeric_judge", f"{fam} / {why}")

# ---- T7 估算题按 task_type 归开放族 ----
_t7 = "拖动滑条估一估书架上大约有多少本，再选一选你是怎么想的。"
fam, why = B.semantic_family("estimation", 40, _t7, "estimation-canvas")
note("T7 task_type=estimation 归 open_estimate",
     fam == "open_estimate" and why.startswith("R1"), f"{fam} / {why}")

# ---- T8 分隔：money-board 是"算总价"不是"摆顺序"，但族相同 ----
# 这条记录一个**已知局限**：两者同族不同求解路径，靠 answer_shape 旁证区分。
# 测试它，是为了让局限被显式承认，而不是假装判据已经完美。
_t8a = ("文具摊上，一件文具标价20角，另一件标价15角。"
        "请用1角、5角、10角和50角币在货币板上凑出两件文具的总价。")
fam_a, _ = B.semantic_family("money", "35", _t8a, "money-board")
note("T8 已知局限：money-board 与 sorting-board 同属构造族（求解路径不同）",
     fam_a == "construct_constraint",
     "两者都进 construct_constraint，但前者求数值、后者求摆位；"
     "Q03 必须分别按「求和」与「枚举合法解+定序」处理，不能一律照 answer 反推")

# ---- T9 布尔歧义标记：值是 1 但问的是数量，必须被标出 ----
_note9 = B.bool_ambiguity("1", "图形盘中有6张图形卡。请把所有“长方形”放进对应的家，"
                               "再数数这一类一共有几张卡。")
note("T9 答案 1 但题面问「几张卡」→ 标 count_like 待人工确认",
     _note9 is not None and "count_like" in _note9, str(_note9))

# ---- T10 布尔歧义标记：真判断题不应被误标 ----
_note10 = B.bool_ambiguity("1", "小美有6支红笔和4支蓝笔。小东说“一共有10支笔”。"
                                "请检查：正确填1，错误填0。")
note("T10 真判断题（含判断词、无数量词）不被误标",
     _note10 is None, str(_note10))

# ---- T11 非 0/1 答案不参与布尔歧义判定 ----
note("T11 答案 35 不参与布尔歧义判定", B.bool_ambiguity("35", "凑出总价") is None)

# ---- T12 死代码检查：DRAG_RENDERERS 已删除 ----
note("T12 上一版的 DRAG_RENDERERS 死代码已移除",
     not hasattr(B, "DRAG_RENDERERS"),
     "它被定义却从未参与判定，等于让读者以为「拖拽形态」是判据的一部分")

# ---- T13 单动词隔离：T3/T4 的题面命中多个词，无法定位是哪条动词在起作用。
# 变异实测（2026-10-21）：把「排好」「补上」从动词表删掉后 T3/T4 仍然 PASS——
# 因为 T3 还被「从小到大」接住、T4 还被当时的 R4「补上」接住。
# 这种"用例通过但判据已坏"的假绿，必须用只命中单一动词的题面才能锁住。
for _v, _r in (("请把这些卡片排好，然后提交。", "sorting-board"),
               ("按顺序补上空格。", "pattern-board")):
    _hit = {v for v in B.CONSTRUCT_VERBS if v in _v}
    _fam, _ = B.semantic_family("x", "12", _v, _r)
    # 注意：不能写 sorted(_hit)[0] 当标签——动词被删空时这里会 IndexError，
    # 测试会崩溃成"rc=1 但没有任何 FAIL 行"，掩盖真实原因（变异实测踩过）。
    _label = ",".join(sorted(_hit)) or "（无命中）"
    note(f"T13-[{_label}] 单动词独立生效",
         _fam == "construct_constraint" and len(_hit) == 1,
         f"命中动词={_hit or '空'} → {_fam}")

# ---- T14 规则编号齐全且与命中统计键一致 ----
# 注意这里**不锁死具体编号集合**，只要求"RULES 里声明的每一条都出现在
# RULE_HITS 里"。否则每次删/加规则都要改测试，测试变成维护负担而非护栏。
rule_ids = [k for k, _ in B.RULES]
note("T14 规则表编号唯一，且每条规则都有命中计数位",
     len(set(rule_ids)) == len(rule_ids)
     and all(k in B.RULE_HITS for k in rule_ids),
     str(rule_ids))

# ---- T15 规则可达性：每条声明的规则都要被本测试的用例触达过 ----
# 注意这条的效力边界：本测试 DB-free，只能证明"规则被用例触达"，
# **不能**证明"规则在 224 条真实语料里有命中"。真实语料命中数由
# build_worklist_union.py 输出的 family_rule_hits / dead_rules 体现，
# 那里命中 0 会显式告警。两处分工不同，不要混说成"已证明无死规则"。
note("T15 规则表每条都能被测试用例触达（真实语料命中数另见 family_rule_hits）",
     all(B.RULE_HITS.get(k, 0) > 0 for k in rule_ids),
     str({k: B.RULE_HITS.get(k, 0) for k in rule_ids}))


print()
if FAIL:
    print(f"FAMILY-GATE: FAIL ({len(FAIL)}/{N})")
    for f in FAIL:
        print("  -", f)
    raise SystemExit(1)
print(f"FAMILY-GATE: PASS ({N}/{N})")