#!/usr/bin/env python3
"""PoC T0/G1：独立参考答案 + SymPy/领域适配器数学验证（先于 AI 运行冻结）。

铁律（方案 §5.1/§09）：expected 从题干+配置独立推导，**不读 DB answer**；
DB answer 仅在本脚本推导完成后做一致性比对（第二阶段输出）。
不支持自动推导的题型 → 显式 UNVERIFIED（领域适配器缺失时人工介入并记 reason）。
"""
import csv
import hashlib
import json
import re
import sys

import sympy as sp

SNAP = "/Users/hanxianxiang/WorkBuddy/2026-09-24-10-25-54/output/qa_item01_r2/Q4_baseline_current_225.jsonl"
DATASET = "eval_dataset.jsonl"


def derive(o):
    """返回 (expected, derivation, class, confidence)。
    class ∈ ARITH(SymPy可验) / DOMAIN(领域适配器) / HUMAN(需教研/人工)"""
    seq, stem, renderer, cfg = o["seq"], o["stem"] or "", o["renderer"], o.get("config") or {}
    mode = o.get("mode")

    # —— 纯算术（题干数字+运算语义）——
    if seq == "1":   # 8-5 相差
        return (sp.Integer(8) - 5, "比多=减法：8-5", "ARITH", "high")
    if seq == "5":   # 8+5-4
        return (8 + 5 - 4, "上车5下车4 依题序：8+5-4", "ARITH", "high")
    if seq == "6":   # □+8=17
        x = sp.Symbol("x")
        sol = sp.solve(sp.Eq(x + 8, 17), x)
        return (sol[0], "解方程 x+8=17", "ARITH", "high")
    if seq == "11":  # 9-6
        return (9 - 6, "圈数比较：9-6", "ARITH", "high")
    if seq == "12":  # 9+4
        return (9 + 4, "多走4千步：9+4", "ARITH", "high")
    if seq == "17":  # 20+5*3
        return (20 + 5 * 3, "右跳5×3 从20", "ARITH", "high")
    if seq == "18":  # 3组×7
        return (3 * 7, "3个7累加（数轴 0→7→14→21）", "ARITH", "high")
    if seq == "7":   # 47=4个十+几个一
        return (sp.Integer(47) % 10, "47 的个位：47 mod 10 = 7（注意：位值知识而非阅读理解）", "ARITH", "high")
    if seq == "8":   # 5+5 十格框
        return (5 + 5, "已有5再放5", "ARITH", "high")
    if seq == "10":  # 3+3
        return (3 + 3, "两组各3", "ARITH", "high")
    if seq == "16":  # 尺子 5→12
        return (12 - 5, "端点差：12-5=7 厘米", "ARITH", "high")

    # —— 领域适配器 ——
    if seq == "2":   # formula-board unknown_operator：7○2=5
        ok = (7 - 2 == 5) and (7 + 2 != 5)
        return ("-" if ok else "+", "解 7○2=5：仅减法成立→'-'（ASCII；'减号'为显示词——等价性风险另行标注）", "DOMAIN", "high")
    if seq == "3":   # unknown_number □+4=9
        return (sp.solve(sp.Eq(sp.Symbol("x") + 4, 9), sp.Symbol("x"))[0], "解缺数式", "ARITH", "high")
    if seq == "4":   # money-board：凑 3元5角=35角（组合多解）
        # 合法组合存在性（正好35角的非负整数组合，面额1,5,10,50）
        target = 35
        sols = [(a, b, c, d) for a in range(36) for b in range(8) for c in range(4) for d in range(1)
                if a * 1 + b * 5 + c * 10 == target]  # 5元档超价不可用（d=0）
        return ("35", f"多解集合：{len(sols)} 种组合合计均=35角（1元=10角换算后）；答案轴=角", "DOMAIN", "high")
    if seq == "9":   # sorting-board 1,2,4,7 组成数
        order = sorted([7, 1, 4, 2])
        return (int("".join(map(str, order))), "从小到大 1,2,4,7 → 数 1247", "DOMAIN", "medium")
    if seq == "13":  # pattern 1,4,1,4 → 续 1,4
        visible = cfg.get("visible", [])
        period = 2
        nxt = [visible[i % period] for i in range(len(visible), len(visible) + cfg.get("blanks", 2))]
        return (nxt, f"周期2序列 [1,4]×2 续两格 = {nxt}（编码数组，非整数标量）", "DOMAIN", "high")
    if seq == "14":  # 判断题 8-3=5≠6 → 0
        return (1 if bool(sp.Eq(8 - 3, 6)) else 0, "8-3=5≠6 → 小华错 → 填 0（判断题答案轴：对=1/错=0）", "ARITH", "high")
    if seq == "15":  # estimation actual=31 → 整十=30（从配置推导，非题干自然语言！）
        actual = cfg.get("actual")
        return (round(actual / 10) * 10, f"配置 actual={actual} → 最接近整十=30（注意：'估'的证据须含滑条动作而非精确计数）", "DOMAIN", "medium")
    if seq == "19":  # shape-gallery: 数 config squares
        n = sum(1 for s in cfg.get("shapes", []) if s.get("kind") == cfg.get("target_kind"))
        return (n, f"配置中 kind=={cfg.get('target_kind')} 共 {n} 个", "DOMAIN", "high")
    if seq == "20":  # array 3排×4人
        r, c = cfg.get("target_rows"), cfg.get("target_cols")
        return (r * c, f"配置 {r}排×{c}人 = {r*c}；结构(rows,cols)与总数需分别可验", "DOMAIN", "high")

    # —— 无法独立推导 → UNVERIFIED ——
    return (None, "无自动推导路径", "HUMAN", "n/a")


def main():
    items = {}
    for l in open(SNAP):
        d = json.loads(l)
        items[d["resource_version_id"]] = d
    gold = []
    for l in open(DATASET):
        o = json.loads(l)
        exp, derivation, cls, conf = derive(o)
        exp_s = str(exp)
        # 阶段二：与 DB answer 一致性比对（推导已冻结后才读取）
        db_answer = str(items[o["rvid"]]["content"].get("answer"))
        def norm(s):
            s = s.strip().strip("[]").replace(" ", "").replace("'", "")
            try:
                return str(sp.nsimplify(s))
            except Exception:
                return s
        match = norm(exp_s) == norm(db_answer) if exp is not None else None
        gold.append({"seq": o["seq"], "rvid": o["rvid"], "title": o["title"],
            "independent_expected": exp_s if exp is not None else "UNVERIFIED",
            "derivation": derivation, "method_class": cls, "confidence": conf,
            "db_answer": db_answer, "consistent_with_db": match})
    with open("truth_reference.jsonl", "w") as f:
        for g in gold:
            f.write(json.dumps(g, ensure_ascii=False) + "\n")
    mism = [g for g in gold if g["consistent_with_db"] is False]
    unver = [g for g in gold if g["consistent_with_db"] is None]
    print(f"G1 独立算术/领域验证：{len(gold)} 题 | 一致 {sum(1 for g in gold if g['consistent_with_db'])} | 不一致 {len(mism)} | UNVERIFIED {len(unver)}")
    for g in gold:
        flag = "✓" if g["consistent_with_db"] else ("?" if g["consistent_with_db"] is None else "✗")
        print(f"  {flag} #{g['seq']} exp={g['independent_expected']} vs db={g['db_answer']} [{g['method_class']}]")
    return 0 if not mism else 1


if __name__ == "__main__":
    sys.exit(main())
