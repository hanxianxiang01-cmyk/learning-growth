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

本脚本把「独立性」拆成三条**可机器判定**的口径，并逐个产物复算：

  A 表达式数字来源（前五批，**人工分诊**）：`derivation.expr` 里每个数字，
    是否都能在题干中找到。
     - 若不能，说明推导引用了题干没有的数（可能来自 config，或来自编码常量）。
     - **注意**：这条只是线索，不是判决。编码常量（如 clock 的 ×60）与
       「从 config 抄数」在数字层面无法区分，必须人工分诊（见 CLASSIFY）。

  A2 表达式数字来源（六、七批，**机器可核**）：这两批在 `derivation` 里新增了
     结构化字段 `encoding_constants`（`[{value, purpose}, ...]`），于是
     「题干外数字是否来自编码规则」不再只能靠人判，可以逐条机器核：
       ① 有题干外数字 → 必须声明常量，否则 UNCLASSIFIED；
       ② 题干外数字 ⊆ 已声明常量；
       ③ 已声明常量 ⊆ 该答案的十进制位权集合  ← 这条是关键；
       ④ 每条 `purpose` 非空且不是 `UNCLASSIFIED`。

     **为什么 ③ 才是重点**：只做 ② 的话，把答案本身写成一条"常量"就能覆盖
     题干外数字（expr 里出现答案 → 声明 answer 为常量 → ② 通过）。而 ③ 要求
     常量必须落在 `{1,10,100,...}` 里，且按 `computed` 的位数算出来——编造的
     常量过不去。这是「用结构约束代替人工判断」，不是「把人工判断自动化」。

  B 语义族覆盖（七批全部）：已完成题的 `semantic_family` 分布。若某一族 0 题
     完成，则「150/212 完成」不能读作「各类型题都验过」。

**三个口径的分母不同，输出里必须分开印，不得互相引用。**
A 段只覆盖前五批 95 题，A2 段覆盖六、七批 55 题，B 段覆盖七批 150 题。
用 A 段的分母去填 B 段的分子，就会得到「construct_constraint 0/54」这种
与同包内 `check_batch6_ledger.py` 直接矛盾的结论（2026-10-23 已踩过）。

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

## 前置工件（缺一即退出码 2，不产出任何结论）

本脚本**只读离线产物、不连库**，因此必须把这六个文件一并带到运行目录：

    scripts/iqc/runs/FE1469_q03_number_input.json   第一批
    scripts/iqc/runs/FE1470_q03_batch2.json         第二批
    scripts/iqc/runs/FE1471_q03_batch3.json         第三批
    scripts/iqc/runs/FE1472_q03_batch4.json         第四批
    scripts/iqc/runs/FE1472_q03_batch5.json         第五批
    scripts/iqc/runs/FE1468_worklist_union.json     rvid → semantic_family 映射（B 段用）

六个文件都不含凭据、不含库连接串，可直接随包交付。缺件时脚本会逐项打印
「缺哪个 / 用途 / 期望路径」，并以 2 退出——**2 表示没跑起来，不是核验失败**。
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


def _check_layout() -> int:
    """确认脚本位于仓库内的 `scripts/iqc/rt1472/`，否则以 2 退出。

    为什么不能只写一句 `assert`：`assert` 触发时进程以 **1** 结束，与「1 断言
    失败」撞码。2026-10-23 验收方在扁平目录（直接解压交付件）里跑，
    得到 rc=1，看起来像「独立性核验不通过」——实际只是路径布局不对，
    与题目结论毫无关系。**"跑不起来" 和 "核验失败" 必须是两个码。**
    """
    if not os.path.isdir(os.path.join(REPO, "apps")):
        print(f"REPO 推导错误：{REPO}", file=sys.stderr)
        print(f"  本脚本预期位于 <repo>/scripts/iqc/rt1472/，"
              f"由当前文件位置推出 repo={REPO}，但其下没有 apps/。",
              file=sys.stderr)
        print(f"  当前文件实际在：{HERE}", file=sys.stderr)
        print(f"  请保持仓库目录结构后重跑（扁平解压交付件不满足布局）。",
              file=sys.stderr)
        print(f"  退出码 2 = 环境/工件问题，**不是核验失败**。", file=sys.stderr)
        return 2
    return 0


_L = _check_layout()
if _L:
    sys.exit(_L)

RUNS = os.path.join(REPO, "scripts", "iqc", "runs")

BATCHES = (
    "FE1469_q03_number_input.json",
    "FE1470_q03_batch2.json",
    "FE1471_q03_batch3.json",
    "FE1472_q03_batch4.json",
    "FE1472_q03_batch5.json",
)

# 第六批产物：**只进 B 段（语义族覆盖），不进 A 段**。
#
# 为什么必须加它进来（2026-10-23 交付缺陷，验收方复跑时暴露）：
#   本脚本原先只看前五批，于是 B 段打印
#       construct_constraint   完成  0 / 全量 54   ← **0 题完成**
#   而**第六批 20 题恰好全属 construct_constraint 且已 20/20 核验**
#   （同包内 check_batch6_ledger.py 明确报「本批 20 / 全族 54」）。
#   同一个交付包里两个脚本对同一事实给出相反数字——前者是错的。
#   这正是项目铁律「看起来正常的数字掩盖缺项」的变体：分母是全量 54，
#   分子却只统计了前五批，看上去像「这族一题没做」。
#
# 为什么不进 A 段：A 段判据是「expr 里的数字是否都在题干中」，第六批 11 题
# 会报出 10/100/1000 这类**位权编码常量**——项目已裁定「编码常量 ≠ 抄 config」，
#   必须人工分诊（`purpose` 逐条写）而非自动判 FAIL。把未经分诊的批次塞进
#   A 段，会让审计直接 rc=1，等于用「未分诊」冒充「核验失败」。
#   故 A 段口径维持「前五批」，B 段口径扩到「前五批 + 第六批」，并在输出里
#   **显式标注两个分母**，不让读者自己去猜。
BATCH6 = "FE1472_q03_batch6.json"

# 除五个批次产物之外还依赖的工件（B 语义族覆盖要用它把 rvid 映射到 semantic_family）
UNION = "FE1468_worklist_union.json"

# ── A2 段：六、七批（结构化常量声明，机器可核）────────────────────────
#
# 为什么这两批要单列一个口径，而不是并进 A 段：
#
#   A 段判据是「expr 里的数字是否都在题干中」，命中的题**必须人工分诊**。
#   前五批 10 道命中题各写一条 CLASSIFY —— 因为那时产物里**没有任何结构化
#   字段**说明「10 是位权还是抄来的」，人判是唯一办法。
#
#   六、七批改了口径：每题在 `derivation.encoding_constants` 里显式写下
#   「哪个数是常量、为什么是常量」。于是同一件事变成可机器判的：
#   常量必须落在该答案的十进制位权集合内（detail 见 `check_structured()`）。
#
#   若把这两批塞进 A 段而不加分诊，会让 audit 直接 rc=1——等于用
#   「未分诊」冒充「核验失败」，错误方向是「看起来题目有问题」。
#   若为了让 rc=0 而把 55 题逐条补进 CLASSIFY，那张表就退化成产物字段的副本，
#   既没有独立信息量、又无法发现「常量声明本身是编的」。
#
#   故：A 段口径维持「前五批」，A2 段口径为「六、七批」，两个口径分开印。
STRUCTURED_BATCHES = (
    "FE1472_q03_batch6.json",
    "FE1472_q03_batch7.json",
)


def _weights_of_answer(n: object) -> set[int] | None:
    """答案的十进制位权集合，如 352 → {1,10,100}；1407 → {1,10,100,1000}。

    取不到整数（答案不是数）返回 None —— 此时 ③ 判据不可判定，
    必须显式记成 `UNDECIDABLE` 而不是默认通过。
    """
    try:
        v = abs(int(str(n).strip()))
    except (TypeError, ValueError):
        return None
    return {10 ** i for i in range(len(str(v)))}


def check_structured(path: str) -> dict:
    """A2 段：逐题核 `encoding_constants` 是否**结构上**成立（四条判据）。"""
    items = json.load(open(path, encoding="utf-8")).get("items") or []
    rows = []
    for it in items:
        der = it.get("derivation") or {}
        expr = der.get("expr") or ""
        stem_nums = set(_nums(it.get("stem") or ""))
        outside = sorted({n for n in _nums(expr) if n not in stem_nums})
        consts = der.get("encoding_constants") or []
        declared = {c.get("value") for c in consts
                    if isinstance(c.get("value"), int)}
        purposes = [str(c.get("purpose") or "").strip() for c in consts]
        ans = it.get("computed")
        weights = _weights_of_answer(ans)

        issues: list[str] = []
        # ① 有题干外数字却没声明常量
        if outside and not declared:
            issues.append(f"题干外数字 {outside} 无任何常量声明")
        # ② 题干外数字必须被已声明常量覆盖
        uncovered = sorted(set(outside) - declared)
        if uncovered:
            issues.append(f"题干外数字 {uncovered} 未被任何已声明常量覆盖")
        # ③ 已声明常量必须落在该答案的位权集合内
        if declared:
            if weights is None:
                issues.append(f"答案 computed={ans!r} 非整数，位权判据不可判定")
            else:
                bogus = sorted(declared - weights)
                if bogus:
                    issues.append(f"常量 {bogus} 不在答案 {ans} 的位权集合 "
                                  f"{sorted(weights)} 内——疑为编造或抄 config")
        # ④ purpose 必须非空、且不是 UNCLASSIFIED
        for i, p in enumerate(purposes):
            if not p or p.upper() == "UNCLASSIFIED":
                issues.append(f"第 {i + 1} 条常量 purpose 为空或 UNCLASSIFIED")
        # ⑤ 答案本身不得被伪装成常量
        #    否则「expr 里出现答案 → 声明答案为常量」即可通过 ②
        if declared and ans in declared and ans not in stem_nums:
            issues.append(f"答案 {ans} 被声明为编码常量——这是把答案当常量，"
                          f"会使 ② 形同虚设")

        rows.append({
            "rvid": it.get("rvid"),
            "renderer": it.get("renderer"),
            "expr": expr,
            "outside": outside,
            "declared": sorted(declared),
            "weights": sorted(weights) if weights else [],
            "computed": ans,
            "issues": issues,
        })
    return {"file": os.path.basename(path), "n": len(items), "rows": rows}

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


def require_artifacts() -> list[str]:
    """前置工件检查：返回缺失的工件路径（空列表=齐备）。

    为什么必须单独做这一步，而不是等到 read 的时候再炸：
      本脚本开头就承诺「退出码：0 通过 / 1 断言失败 / 2 工件缺失」。但第一版
      只在 `audit()` 里查了五个批次，`selftest()` 直接 `check_batch()` → 缺件
      时抛 `FileNotFoundError`（未捕获异常），实际退出码既不是 2 也不是 1，
      与文档承诺不符。2026-10-23 验收方在隔离目录实测踩到这一条。

      现在的口径：**两个入口都先过这里**。缺件一律返回 2，并逐个打印缺哪个、
      以及为什么需要它——因为「缺件」和「核验失败」是两件事，不能混成一个
      FAIL 让人以为题目有问题。
    """
    needed: list[tuple[str, str]] = [(b, "批次产物（逐题 derivation/expr 与 stem）")
                                     for b in BATCHES]
    needed.append((UNION, "语义族映射（rvid → semantic_family，B 段要用）"))
    needed += [(b, "结构化常量声明（A2 段要用）") for b in STRUCTURED_BATCHES]
    missing = []
    for name, why in needed:
        p = os.path.join(RUNS, name)
        if not os.path.exists(p):
            missing.append(p)
            print(f"  缺少工件：{name}\n      用途：{why}\n      期望路径：{p}",
                  file=sys.stderr)
    if missing:
        print(f"\n工件缺失 {len(missing)}/{len(needed)} 项——**这是交付依赖未齐，"
              f"不是核验失败**。本脚本无法在缺件状态下给出任何结论，"
              f"退出码 2。", file=sys.stderr)
    return missing


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
    if require_artifacts():
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

    # ── A2 段：六、七批的结构化常量声明（机器判据，不需人工分诊）──
    #
    # 这一段**取代**了「把 55 题逐条补进 CLASSIFY」的做法。理由见
    # `STRUCTURED_BATCHES` 处的注释：人工表会退化成产物字段的副本。
    st = [check_structured(os.path.join(RUNS, b)) for b in STRUCTURED_BATCHES]
    st_n = sum(x["n"] for x in st)
    st_clean = sum(1 for x in st for r in x["rows"] if not r["issues"])
    st_with = sum(1 for x in st for r in x["rows"] if r["outside"])
    st_bad = [(x["file"], r) for x in st for r in x["rows"] if r["issues"]]

    print()
    print(f"  ── A2 结构化常量声明（六、七批，机器判据）──")
    print(f"     题目数 {st_n}；含题干外数字 {st_with} 题（均须由常量声明覆盖）")
    for x in st:
        bad = sum(1 for r in x["rows"] if r["issues"])
        print(f"     {x['file']:<32} n={x['n']:<3} 违规={bad}")
    if st_bad:
        print(f"  ✗ A2 有 {len(st_bad)} 题常量声明不成立：")
        for f, r in st_bad:
            print(f"     {r['rvid'][:8]} {r['renderer']:<18} expr={r['expr']}")
            for i in r["issues"]:
                print(f"        · {i}")
        return 1
    print(f"     ✓ {st_clean}/{st_n} 题常量声明结构成立"
          f"（常量 ⊆ 答案位权集合，答案未被伪装成常量）")

    # B 语义族覆盖
    u = {x["rvid"]: x for x in json.load(
        open(os.path.join(RUNS, "FE1468_worklist_union.json"),
             encoding="utf-8"))["items"]}
    fam_all = Counter(x["semantic_family"] for x in u.values())

    # 两个口径必须分开算、分开印。
    #   done_a  = 前五批（A 段口径，可用于「expr 是否含题干外数字」的结论）
    #   done_b  = 七批全部（B 段口径，用于「这一族核过多少题」）
    # 只用其中一个去填另一个的分母，就会得到「construct_constraint 0/54」这种
    # 与同包内 check_batch6_ledger.py 直接矛盾的结论。
    #
    # 第七批（2026-10-26）：由「前六批」扩到「七批全部」。
    # 本批把 construct_constraint 从 20 补到 54、open_estimate 从 0 补到 1，
    # 若不并入，B 段会打印「construct_constraint 20/54」——而族级已清零。
    # 这是同一类错误的第三次复现（前两次：95 题时 construct_constraint 0/54、
    # 第六批后仍只看前五批），故这里改成**按 STRUCTURED_BATCHES + BATCHES
    # 全量重算**，不再靠「记得再加一个常量」。
    done_a = {r["rvid"] for b in batches for r in b["rows"]}
    b_all = sorted(set(BATCHES) | set(STRUCTURED_BATCHES))
    done_b = {r["rvid"] for b in b_all
              for r in check_batch(os.path.join(RUNS, b))["rows"]}
    skipped = [b for b in b_all if not os.path.exists(os.path.join(RUNS, b))]

    fam_a = Counter(u[r]["semantic_family"] for r in done_a if r in u)
    fam_b = Counter(u[r]["semantic_family"] for r in done_b if r in u)

    print("\n  ── B 已完成题按语义族（审查覆盖 / 独立 MATCH 分开记）──")
    print(f"     口径 = 七批全部（{len(done_b)} 题）；"
          f"A 段仍只统计前五批（{len(done_a)} 题）、A2 段 {st_n} 题，"
          f"三处分母不同，勿互相引用")
    if skipped:
        print(f"     ⚠ 有 {len(skipped)} 个批次产物缺失，B 段口径不完整：{skipped}")

    # **「已审查」与「独立 MATCH」是两个数，不能互相替代。**
    # 第七批 35 题里有 3 题不是独立 MATCH（2 题面直给答案、1 题题干不可核），
    # 所以 construct_constraint 54/54 只说明「每道都看过了」，不说明
    # 「54 道答案全被独立复算确认」。把覆盖完成标成「全族清零」，会让读者
    # 把「看过了」当成「结论通过」——这是本轮被指出的第二处问题。
    #
    # 注意：**不能从 `check_batch()["rows"]` 取 verdict**——那些行只有
    # `rvid/renderer/expr/outside/classified` 五个键，没有 verdict。
    # 首版正是从那里取，`.get("verdict")` 恒为 None，于是打印出
    # 「已审查 54 / 独立 MATCH 0」，把 54 道全 MATCH 说成一道都没过。
    # 结论字段必须直接从产物 JSON 读。
    fam_match: Counter = Counter()
    for b in b_all:
        fp = os.path.join(RUNS, b)
        if not os.path.exists(fp):
            continue
        for r in json.load(open(fp, encoding="utf-8"))["items"]:
            if (r.get("verdict") or "") == "MATCH" and r.get("rvid") in u:
                fam_match[u[r["rvid"]]["semantic_family"]] += 1

    for fam, n_all in fam_all.most_common():
        n_b = fam_b.get(fam, 0)
        n_m = fam_match.get(fam, 0)
        extra = ""
        if fam_a.get(fam, 0) != n_b:
            extra = f"（前五批 {fam_a.get(fam, 0)}，本批新增 +{n_b - fam_a.get(fam, 0)}）"
        # 措辞改为「审查覆盖完成」，「清零」一律不出现在这条输出里
        flag = ""
        if n_b == n_all and n_all:
            flag = ("   ← 审查覆盖完成"
                    + ("" if n_m == n_all else f"，独立 MATCH {n_m}/{n_all}"))
        print(f"    {fam:<24} 已审查 {n_b:>2} / 全量 {n_all:>2} · "
              f"独立 MATCH {n_m:>2}{extra}{flag}"
              + ("   ← 仍未开族" if n_b == 0 else ""))

    zero = [f for f in fam_all if fam_b.get(f, 0) == 0]
    gap = [(f, fam_b.get(f, 0), fam_match.get(f, 0))
           for f in fam_all if fam_b.get(f, 0) > fam_match.get(f, 0)]
    print()
    if gap:
        print("  ⚠ 以下语义族**已审查但未全部独立 MATCH**"
              "（覆盖完成 ≠ 结论全部通过）：")
        for f, n_b, n_m in gap:
            print(f"    {f:<24} 已审查 {n_b} / 独立 MATCH {n_m}"
                  f"（差 {n_b - n_m} 题：题面直给答案或题干不可核）")
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

    2026-10-23 补：**入口先过 `require_artifacts()`**。第一版 `selftest()` 直接
    读 `BATCHES`，缺件时抛 `FileNotFoundError`（退出码既非 2 也非 1），与文末
    「退出码：2 工件缺失」的承诺不符。现改为缺件明确返回 2。
    """
    import copy
    import tempfile

    missing = require_artifacts()
    if missing:
        print(f"INDEPENDENCE-SELFTEST: NOT_RUN（缺 {len(missing)} 项工件）",
              file=sys.stderr)
        return 2

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

    # M4：B 段必须把**全部批次**计入，而不是只算前五批（2026-10-23 交付缺陷的
    # 回归闸门，2026-10-26 扩到七批）。
    #
    # 缺陷复现：原实现 B 段只用 `batches`（前五批），于是打印
    #     construct_constraint  完成 0 / 全量 54   ← **0 题完成**
    # 而第六批 20 题正是该族且已 20/20 核验。同包内 check_batch6_ledger.py
    # 报的是「本批 20 / 全族 54」——两个脚本公开互相矛盾。
    #
    # 判据不能写「必须 == 20」：那样批次换族、或族被补齐（54/54）都会误报。
    # 正确做法是**独立重算**：从所有批次产物取 rvid，经 union 映射成族，
    # 看 audit 输出的完成数是否等于「独立重算值」。两个数不一致 = B 段口径错。
    #
    # 特别注意：第七批把 construct_constraint 补到 54/54 后，
    # 若判据仍写 `got > n_a`（要求新增量 > 0）或「+n_b6」，会因族已清零而
    # 误判——故这里改成**比对全量独立重算值**，与批次构成无关。
    u_all = {x["rvid"]: x for x in json.load(
        open(os.path.join(RUNS, UNION), encoding="utf-8"))["items"]}
    b_all = sorted(set(BATCHES) | set(STRUCTURED_BATCHES))
    missing_b = [b for b in b_all if not os.path.exists(os.path.join(RUNS, b))]
    if missing_b:
        print(f"  ✗ M4 缺批次产物 {missing_b}，无法验证 B 段口径")
    else:
        done_all: set[str] = set()
        for b in b_all:
            done_all |= {r["rvid"] for r in check_batch(os.path.join(RUNS, b))["rows"]}
        fam_expect = Counter(u_all[r]["semantic_family"]
                             for r in done_all if r in u_all)
        buf2 = io.StringIO()
        with contextlib.redirect_stdout(buf2):
            audit()
        out = buf2.getvalue()
        import re as _re
        mismatched = []
        # 输出格式改为 `已审查 N / 全量 M · 独立 MATCH K`，故正则随之改成锚
        # `已审查`。**这不是为了迁就新格式**：若仍匹配 `完成 (\d+) / 全量`，
        # 新格式下会全部匹配失败（got=-1），于是「全部不符」被误读成
        # 「B 段口径全错」——判据锚点写错会误报，比漏报更危险。
        for fam, n_exp in fam_expect.items():
            m = _re.search(rf"{_re.escape(fam)}\s+已审查\s+(\d+)\s+/\s+全量", out)
            got = int(m.group(1)) if m else -1
            if got != n_exp:
                mismatched.append((fam, n_exp, got))
        if mismatched:
            print("  ✗ M4 B 段口径与独立重算不符："
                  + "; ".join(f"{f} 期望 {e} 实际 {g}" for f, e, g in mismatched)
                  + "——分母/分子不同源会把「已核完」读成「一题未核」")
        else:
            caught += 1
            print(f"  ✓ M4 B 段口径 == 独立重算（{len(done_all)} 题 / "
                  f"{len(fam_expect)} 族全部一致）")

    # M5：A2 段必须能抓出「编造的常量」。
    #
    # A2 段唯一有区分力的判据是 ③（常量 ⊆ 答案位权集合）与 ⑤（答案不得被
    # 声明为常量）。只做 ②（题干外数字被常量覆盖）是不够的：把答案本身写成
    # 常量就能覆盖，A2 会全绿。
    #
    # **第一版变异是无效的，已修**：第一版把 `encoding_constants` **整体替换**
    # 成一个编造值，结果 ② 立刻报「题干外数字未被覆盖」——检出了，但检出的
    # 是 ② 而不是 ③。判据 ③/⑤ 是否有效**根本没被验证**。
    # 这正是项目已记的铁律「变异无效 ≠ 检测器失效」：变异没有改到**被观察量**。
    #
    # 修法：**保留原有常量**（让 ② 保持通过），只**追加**一个越权常量，
    # 并断言报出的是 ③/⑤ 那条具体信息，而不是只看 `issues` 非空。
    import copy as _copy
    import tempfile as _tempfile

    b7p = os.path.join(RUNS, STRUCTURED_BATCHES[-1])
    if not os.path.exists(b7p):
        print(f"  ✗ M5 缺 {STRUCTURED_BATCHES[-1]}，无法验证 A2 判据")
    else:
        src = json.load(open(b7p, encoding="utf-8"))
        # 挑一道：expr 有题干外数字、常量已覆盖（② 本来通过）、且答案是整数
        tgt = None
        for it in src["items"]:
            der = it.get("derivation") or {}
            consts = der.get("encoding_constants") or []
            if not consts:
                continue
            expr = der.get("expr") or ""
            sn = set(_nums(it.get("stem") or ""))
            outside = {n for n in _nums(expr) if n not in sn}
            decl = {c["value"] for c in consts}
            ans = it.get("computed")
            w = _weights_of_answer(ans)
            if outside and outside <= decl and w and decl <= w and ans is not None:
                tgt = it
                break
        if tgt is None:
            print("  ✗ M5 找不到「② 已通过」的题做底稿——样本缺失，无法隔离 ③/⑤")
        else:
            base_consts = _copy.deepcopy(
                (tgt["derivation"] or {}).get("encoding_constants") or [])
            ans = tgt.get("computed")
            w = sorted(_weights_of_answer(ans) or [])

            def _mutate_and_check(extra: int, want_word: str) -> bool:
                mut = _copy.deepcopy(src)
                mm = next(it for it in mut["items"] if it["rvid"] == tgt["rvid"])
                mm["derivation"]["encoding_constants"] = base_consts + [
                    {"value": extra, "purpose": "人为构造：验证 A2 判据"}]
                with _tempfile.TemporaryDirectory() as td:
                    p = os.path.join(td, "mut.json")
                    json.dump(mut, open(p, "w", encoding="utf-8"),
                              ensure_ascii=False)
                    rows = check_structured(p)["rows"]
                    hit = next(r for r in rows if r["rvid"] == tgt["rvid"])
                # ① 必须确认 ② 仍通过（否则这次变异同样没隔离到目标判据）
                covered = not any("未被任何已声明常量覆盖" in i
                                  for i in hit["issues"])
                ok = covered and any(want_word in i for i in hit["issues"])
                if not covered:
                    print(f"  ✗ 变异未隔离：② 也报了（说明变异改错了量）")
                elif ok:
                    print(f"  ✓ 追加常量 {extra} → 命中判据「{want_word}」")
                else:
                    print(f"  ✗ 追加常量 {extra} 未命中「{want_word}」，"
                          f"实际：{hit['issues']}")
                return ok

            # M5a：追加一个非位权的数（7）→ 必须只由 ③ 报出
            ok_a = _mutate_and_check(7, "不在答案")

            # M5b：把答案本身追加进去 → 必须由 ⑤ 报出
            #
            # **这一条在真实产物上隔离不了，故用合成样本**：
            # 要隔离 ⑤，需要「答案本身是 10 的幂，且答案不在题干里」，
            # 这样 ③（答案 ∈ 位权集合）不响、只有 ⑤ 能拦。
            # 实测七批产物里唯一答案为 10 的幂的题是 `cd7f008d`（答案 10），
            # 但它的题面就写着「这一摞是 10 本」，于是 ⑤ 的
            # `ans not in stem_nums` 条件也不成立——在真实数据上
            # 「⑤ 独立生效」这一路径**不可达**。
            #
            # 用合成样本**只为验证检测器本身**有区分力，不声称生产题里发生过
            # 这种情况，也不把它写进任何产物或汇总。这与「合成负例不得冒充
            # 生产事实」并不冲突：这里没有把合成结果做成结论，只做自证。
            synth = {
                "items": [{
                    "rvid": "00000000-0000-0000-0000-0000000000b5",
                    "renderer": "synthetic",
                    "stem": "题面刻意不含任何一个数字（合成样本）",
                    "derivation": {
                        "expr": "100",
                        "encoding_constants": [
                            {"value": 100, "purpose": "合成样本：把答案伪装成常量"}],
                    },
                    "computed": 100,
                }]
            }
            with _tempfile.TemporaryDirectory() as td:
                p = os.path.join(td, "synth.json")
                json.dump(synth, open(p, "w", encoding="utf-8"), ensure_ascii=False)
                hit = check_structured(p)["rows"][0]
            # 合成样本下 ② 必须通过（100 已被"覆盖"）、③ 必须通过（100 是位权），
            # 只有 ⑤ 能报——若 ⑤ 被停用，这条就变成空过。
            covered = not any("未被任何已声明常量覆盖" in i for i in hit["issues"])
            only5 = covered and any("被声明为编码常量" in i for i in hit["issues"])
            if only5:
                print("  ✓ 合成样本（答案 100 = 位权，② ③ 均放行）"
                      "→ 仅判据 ⑤ 报出")
            else:
                print(f"  ✗ 合成样本未隔离判据 ⑤，实际：{hit['issues']}"
                      f"（covered={covered}）")

            if ok_a and only5:
                caught += 1
                print(f"  ✓ M5 A2 判据 ③/⑤ 均已隔离验证（答案 {ans}，"
                      f"位权 {w}）")
            else:
                print("  ✗ M5 A2 判据 ③/⑤ 区分力不足")

    # M6：「已审查」与「独立 MATCH」必须真的是两个数。
    #
    # 这条防的是本轮被指出的第二个问题——用「覆盖完成」替代「结论通过」。
    # 判据不能只查「独立 MATCH 这个词出现在输出里」：那样恒真。
    # 必须锚到**真实差额**：construct_constraint 54 已审查 / 52 独立 MATCH
    # （差 2 道 STEM_GIVEN_ANSWER_AGREES），open_estimate 1 / 0（差 1 道
    # UNVERIFIABLE_FROM_STEM）。差额恰好等于这两族的特殊 verdict 数。
    #
    # 同时验证它**没有退化成恒真式**：若两列永远相等，那这条输出就是装饰。
    # 用「差额必须 > 0 且等于特殊 verdict 数」做双向约束。
    try:
        buf3 = io.StringIO()
        with contextlib.redirect_stdout(buf3):
            audit()
        out3 = buf3.getvalue()
        import re as _re3
        pair = {}
        for fam in ("construct_constraint", "open_estimate", "numeric_judge"):
            m = _re3.search(
                rf"{_re.escape(fam)}\s+已审查\s+(\d+)\s+/\s*全量\s+\d+\s*·\s*"
                rf"独立 MATCH\s+(\d+)", out3)
            if m:
                pair[fam] = (int(m.group(1)), int(m.group(2)))
        # 从产物独立算出各族「非 MATCH」数，作为差额的期望
        exp_gap: Counter = Counter()
        for b in sorted(set(BATCHES) | set(STRUCTURED_BATCHES)):
            fp = os.path.join(RUNS, b)
            if not os.path.exists(fp):
                continue
            for r in json.load(open(fp, encoding="utf-8"))["items"]:
                if (r.get("verdict") or "") != "MATCH" and r.get("rvid") in u_all:
                    exp_gap[u_all[r["rvid"]]["semantic_family"]] += 1
        ok6 = True
        for fam, (n_rev, n_match) in pair.items():
            if n_rev - n_match != exp_gap.get(fam, 0):
                print(f"  ✗ M6 {fam}: 已审查 {n_rev} − 独立 MATCH {n_match} "
                      f"≠ 特殊 verdict {exp_gap.get(fam, 0)}"
                      f"——两列没真正区分「看过」与「通过」")
                ok6 = False
        # 反向对照：必须至少有一族两列不等，否则「分两列」是装饰
        if pair and all(a_ == b_ for a_, b_ in pair.values()):
            print("  ✗ M6 所有族「已审查」都等于「独立 MATCH」——"
                  "分两列没有实际区分力（可能是恒真式）")
            ok6 = False
        if ok6 and pair:
            caught += 1
            detail = ", ".join(f"{f} {a_}/{b_}" for f, (a_, b_) in
                               sorted(pair.items()))
            print(f"  ✓ M6 已审查 ≠ 独立 MATCH 且差额 == 特殊 verdict 数"
                  f"（{detail}）")
    except Exception as e:      # noqa: BLE001
        print(f"  ✗ M6 无法验证：{type(e).__name__}: {e}")

    print(f"\nINDEPENDENCE-SELFTEST: {'PASS' if caught == 6 else 'FAIL'}"
          f"（{caught}/6 检出）")
    return 0 if caught == 6 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if not os.path.isdir(RUNS):
        print(f"缺少 {RUNS}", file=sys.stderr)
        return 2
    try:
        return selftest() if a.selftest else audit()
    except Exception as e:      # noqa: BLE001
        # **未捕获异常必须 rc=2**。Python 默认退出码是 1，与「断言失败/核验
        # 不通过」撞码：一次 KeyError 会被读成「独立性核验没通过」。
        # 项目铁律：0 通过 / 1 结论不成立 / 2 环境·工件·脚本自身问题。
        import traceback
        traceback.print_exc()
        print(f"\n脚本自身异常（{type(e).__name__}）——"
              f"这**不是**核验结论，退出码 2。", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())