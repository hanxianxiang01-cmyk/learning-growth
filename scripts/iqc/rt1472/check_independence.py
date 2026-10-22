#!/usr/bin/env python3
"""Q03 已完成核验的**独立性口径**复核（离线，不连库）。

## 为什么要做这件事

用户 2026-10-22 明确要求：「成功标准不是新增 20 个 MATCH，而是新增一批能
**独立解释、重复计算**、明确例外的题目结论。」以及「数据库答案只能用于
最后比较」。

但前五批的核验器彼此不同（`q03_*.py` 各写各的 `derive()`），所以
「95 题都做了独立推导」这句话**不能被任何单一脚本复现**——它只是汇总
文档里的说法。这违反项目已记的铁律：

    「产物里的分析结论若不能由脚本重现，就只是某次人工编辑的快照」

本脚本把「独立性」拆成两条**可机器判定**的口径，并逐个产物复算：

  A 表达式数字来源：`derivation.expr` 里每个数字，是否都能在题干中找到。
     - 若不能，说明推导引用了题干没有的数（可能来自 config，或来自编码常量）。
     - **注意**：这条只是线索，不是判决。编码常量（如 clock 的 ×60）与
       「从 config 抄数」在数字层面无法区分，必须人工分诊（见 CLASSIFY）。

  B 语义族覆盖：已完成题的 `semantic_family` 分布。若某一族 0 题完成，
     则「95/212 完成」不能读作「各类型题都验过」。

## 为什么必须人工分诊而不是自动判定

我第一版用 A 直接判定「10 题不独立」，实测发现至少四类不同性质：

  · `clock`: `5 * 60 + 0` —— 60 是「分↔时」单位换算常量，**不是抄 config**。
    题面「4点半→5点整」确实给不出 5，5 来自 config.target。
    → 真问题是**题面不含目标值**，而非「读了 config」。
  · `estimation-canvas`: `((18+5)//10)*10` —— 18 来自 config.actual，
    题面「估一估」刻意不给实际个数（考点就是不许数）。
    → 属**设计意图**，但推导确实是 config 驱动的，不能称「从题面推出」。
  · `shape-gallery`: `expr=1` —— 1 是「正方形有几张」的计数结果，
    输入是 config.shapes 里 kind 的分布，题面只说「有6张卡」。
    → 属**必须读 config**（图形种类只在 config 里），题面不足以判定。
  · `ten-frame fea38e2d`: `10 * 1 + 3` —— 13 来自 config.target_count。

因此本脚本**只报告，不下终局判决**，把分诊结果写进 `CLASSIFY` 供人复核。

## 用法

    python scripts/iqc/rt1472/check_independence.py
    python scripts/iqc/rt1472/check_independence.py --selftest

退出码：0 通过 / 1 断言失败 / 2 工件缺失
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
assert os.path.isdir(os.path.join(REPO, "apps")), f"REPO 推导错误：{REPO}"

RUNS = os.path.join(REPO, "scripts", "iqc", "runs")

BATCHES = (
    "FE1469_q03_number_input.json",
    "FE1470_q03_batch2.json",
    "FE1471_q03_batch3.json",
    "FE1472_q03_batch4.json",
    "FE1472_q03_batch5.json",
)

# 分诊表：把「表达式里有题干外的数字」按**真实原因**分类。
# key = rvid 前 8 位；值 = (类别, 说明)
# 这张表必须由人写——机器分不清「单位换算常量」和「抄 config」。
CLASSIFY: dict[str, tuple[str, str]] = {
    "031fb221": ("ENCODING_CONSTANT",
                 "clock 5*60：60 是分↔时换算常量；但目标值 5 来自 config.target，"
                 "题面「4点半→5点整」不含 5"),
    "09f916e8": ("ENCODING_CONSTANT",
                 "clock 11*60：同上，11 来自 config.target"),
    "17599601": ("ENCODING_CONSTANT",
                 "clock 4*60+30：30/60 为换算常量，4 来自 config.target"),
    "13c3b756": ("CONFIG_ONLY_BY_DESIGN",
                 "estimation-canvas：actual=18 只在 config 里；题面刻意不给实际个数"
                 "（考点是不许逐个数）"),
    "46b80862": ("CONFIG_ONLY_BY_DESIGN", "estimation-canvas：actual=47 同上"),
    "48817fba": ("CONFIG_ONLY_BY_DESIGN", "estimation-canvas：actual=31 同上"),
    "31554b60": ("CONFIG_ONLY_UNAVOIDABLE",
                 "shape-gallery：正方形张数只能在 config.shapes 的 kind 分布里数出来，"
                 "题面只说「有6张卡」"),
    "3f97f749": ("CONFIG_ONLY_UNAVOIDABLE", "shape-gallery：长方形张数同上"),
    "4821e8a3": ("CONFIG_ONLY_UNAVOIDABLE", "shape-gallery：三角形张数同上"),
    "fea38e2d": ("CONFIG_ONLY_AVOIDABLE",
                 "ten-frame：13 来自 config.target_count；题面「买了13颗糖」其实含 13，"
                 "但推导写成 10*1+3 绕开了题面直读"),
}


def _nums(s: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", s or "")]


def check_batch(path: str) -> dict:
    j = json.load(open(path, encoding="utf-8"))
    items = j.get("items") or []
    rows = []
    for it in items:
        expr = (it.get("derivation") or {}).get("expr") or ""
        stem_nums = set(_nums(it.get("stem") or ""))
        expr_nums = _nums(expr)
        outside = sorted({n for n in expr_nums if n not in stem_nums})
        rows.append({
            "rvid": it.get("rvid"),
            "renderer": it.get("renderer"),
            "expr": expr,
            "outside": outside,
            "classified": CLASSIFY.get((it.get("rvid") or "")[:8]),
        })
    return {"file": os.path.basename(path), "n": len(items), "rows": rows}


def audit() -> int:
    missing = [b for b in BATCHES
               if not os.path.exists(os.path.join(RUNS, b))]
    if missing:
        print(f"缺少批次产物：{missing}", file=sys.stderr)
        return 2

    batches = [check_batch(os.path.join(RUNS, b)) for b in BATCHES]
    total = sum(b["n"] for b in batches)

    outside_rows = [(b["file"], r) for b in batches for r in b["rows"] if r["outside"]]
    clean = total - len(outside_rows)

    print(f"\nQ03 独立性口径复核：{total} 题（5 批去重前合计）")
    print(f"  A 表达式数字全在题干内：{clean} 题")
    print(f"  A 表达式含题干外数字 ：{len(outside_rows)} 题")
    print()

    print("  ── 逐批 ──")
    for b in batches:
        out = sum(1 for r in b["rows"] if r["outside"])
        print(f"    {b['file']:<32} n={b['n']:<3} 题干外数字题数={out}")
    print()

    print("  ── 含题干外数字的题（分诊，非终局判决）──")
    unclassified = []
    by_cat: Counter[str] = Counter()
    for f, r in outside_rows:
        cat = r["classified"][0] if r["classified"] else "UNCLASSIFIED"
        by_cat[cat] += 1
        print(f"    {r['rvid'][:8]} {r['renderer']:<18} expr={r['expr']:<24}"
              f" 缺{sorted(set(r['outside']))} → {cat}")
        print(f"        {r['classified'][1] if r['classified'] else '**未分诊，必须补**'}")
        if not r["classified"]:
            unclassified.append(r["rvid"])

    print()
    print("  分类汇总：", dict(by_cat))
    if unclassified:
        print(f"  ✗ 有 {len(unclassified)} 题未分诊："
              f"{[x[:8] for x in unclassified]}")
        return 1

    # B 语义族覆盖
    u = {x["rvid"]: x for x in json.load(
        open(os.path.join(RUNS, "FE1468_worklist_union.json"),
             encoding="utf-8"))["items"]}
    done = {r["rvid"] for b in batches for r in b["rows"]}
    fam_done = Counter(u[r]["semantic_family"] for r in done if r in u)
    fam_all = Counter(x["semantic_family"] for x in u.values())

    print("\n  ── B 已完成题按语义族 ──")
    for fam, n_all in fam_all.most_common():
        print(f"    {fam:<24} 完成 {fam_done.get(fam, 0):>2} / 全量 {n_all:>2}"
              + ("   ← **0 题完成**" if fam_done.get(fam, 0) == 0 else ""))

    zero = [f for f in fam_all if fam_done.get(f, 0) == 0]
    print()
    if zero:
        print(f"  ⚠ 以下语义族 **一题未核**：{zero}")
        print("    含义：「95/212 完成」不能读作「各类型题都验过」；"
              "续批应优先补这些族，而不是继续在同族里加量。")

    return 0


def selftest() -> int:
    """证明本复核器能失败。三种篡改必须检出。

    第一版 M2 只查 `BATCHES[-1]`（batch5）而 fea38e2d 在 batch2，
    于是报「未被检出」——**是变异构造错了，不是判据失效**
    （2026-10-22 已记铁律：变异无效 ≠ 检测器失效）。
    修法是让 M2 在全批次里查，而不是放宽判据。
    """
    import copy
    import tempfile

    print("\n── 独立性复核器自证 ──")
    caught = 0

    batches = [check_batch(os.path.join(RUNS, b)) for b in BATCHES]

    # M1：**真的注入**一个题干外的数字，而不是"断言 999 不在题干里"（那样恒真，
    # 等于什么都没测）。做法：复制 batch5 产物，把第一题的 expr 改成含 999，
    # 落临时文件后跑 check_batch，必须能报出 outside=999。
    with tempfile.TemporaryDirectory() as td:
        src = json.load(open(os.path.join(RUNS, BATCHES[-1]), encoding="utf-8"))
        mut = copy.deepcopy(src)
        mut["items"][0]["derivation"] = dict(mut["items"][0].get("derivation") or {})
        mut["items"][0]["derivation"]["expr"] = "999 + 1"
        p = os.path.join(td, "mut.json")
        json.dump(mut, open(p, "w", encoding="utf-8"), ensure_ascii=False)
        got = check_batch(p)
        hit = got["rows"][0]["outside"]
        if 999 in hit:
            caught += 1
            print(f"  ✓ M1 注入 expr=999+1 → 检出 outside={hit}")
        else:
            print(f"  ✗ M1 注入 999 未被检出（得到 outside={hit}）——判据失效")

    # M2：已知题 fea38e2d（batch2）必须被检出。**全批次搜索**，不指定单批。
    all_rows = [r for b in batches for r in b["rows"]]
    known = [r for r in all_rows if (r["rvid"] or "")[:8] == "fea38e2d"]
    if not known:
        print("  ✗ M2 全批次里找不到 fea38e2d——样本缺失，无法验证")
    elif known[0]["outside"]:
        caught += 1
        print(f"  ✓ M2 已知题 fea38e2d（{known[0]['expr']}）被检出，"
              f"缺 {sorted(set(known[0]['outside']))}")
    else:
        print("  ✗ M2 已知题 fea38e2d **未**被检出——判据失效")

    # M3：分诊表缺失必须让审计失败（不能静默放过）
    global CLASSIFY
    saved = CLASSIFY
    CLASSIFY = {}
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = audit()
    CLASSIFY = saved
    if rc == 1:
        caught += 1
        print("  ✓ M3 清空分诊表 → 审计 FAIL（未分诊不会被静默放过）")
    else:
        print(f"  ✗ M3 清空分诊表后审计仍返回 {rc}——未分诊被静默放过")

    print(f"\nINDEPENDENCE-SELFTEST: {'PASS' if caught == 3 else 'FAIL'}"
          f"（{caught}/3 检出）")
    return 0 if caught == 3 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if not os.path.isdir(RUNS):
        print(f"缺少 {RUNS}", file=sys.stderr)
        return 2
    return selftest() if a.selftest else audit()


if __name__ == "__main__":
    sys.exit(main())