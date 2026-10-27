"""FE-1472｜进度账实核（把「文档里的数字」与「产物 + 并集工件」对上）。

动机：§5.8.5 上一版的三个数字是**按减法外推**的，其中 `Q05_only`
写成「38 + 29 = 67」，而实际它是固定集合归属、一直是 12 且从未被消耗。
这类错误靠人算抓不住，必须由脚本逐条数出来。

本脚本只读，零 DML，不写任何产物；仅打印并对不上时以非零码退出。

用法：
  python scripts/iqc/rt1472/check_progress.py
  python scripts/iqc/rt1472/check_progress.py --selftest

退出码：0 账实相符 / 1 账实不符 / 2 环境·工件·布局问题

**「2」为什么必须单独存在**：本脚本原先用模块级 `assert` 校验仓库层级，
`assert` 触发时进程以 **1** 结束——与「账实不符」撞码。这正是项目已记的
铁律：「退出码 0/1/2=环境·工件·布局；assert 触发即 rc=1 会撞码」。
同理，缺批次产物也**不能**记成 `fails`：那是依赖没齐，不是数字对不上。
把这两类混进 rc=1，会让「少了一个文件」看起来像「进度数字算错了」。
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


def _check_layout() -> int:
    """布局不对返回 2（而不是让 assert 以 1 掉出去）。"""
    if not os.path.isdir(os.path.join(REPO, "scripts", "iqc")):
        print(f"REPO 推导错误：{REPO}", file=sys.stderr)
        print(f"  本脚本预期位于 <repo>/scripts/iqc/rt1472/，实际在 {HERE}",
              file=sys.stderr)
        print("  请保持仓库目录结构后重跑（扁平解压交付件不满足布局）。",
              file=sys.stderr)
        print("  退出码 2 = 环境/工件问题，**不是账实不符**。", file=sys.stderr)
        return 2
    return 0


_L = _check_layout()
if _L:
    sys.exit(_L)


UNION = os.path.join(REPO, "scripts/iqc/runs/FE1468_worklist_union.json")
RUNS = os.path.join(REPO, "scripts/iqc/runs")

# 已完成的批次产物（新增批次时在此追加，**不要靠外部传参**，
# 否则「忘了加一个文件」会静默算错完成数）
BATCH_ARTIFACTS = [
    "FE1469_q03_number_input.json",
    "FE1470_q03_batch2.json",
    "FE1471_q03_batch3.json",
    "FE1472_q03_batch4.json",
    "FE1472_q03_batch5.json",
    "FE1472_q03_batch6.json",
    "FE1472_q03_batch7.json",
]

# 文档中声明的数字（改文档时同步改这里，脚本会核对）
EXPECTED = {"union": 224, "in_q03": 212, "in_q05": 209,
            "both": 197, "q03_only": 15, "q05_only": 12}

# 文档声明的「去重完成合计」与由此推出的两个待办数。
# **这三项必须显式声明**——第五批态下若仍用 75 就说明文档没同步，
# 而此前正是「靠人算减法」把 Q05_only 写成 67 的。
#
# 第七批（2026-10-26）由 115 → 150：35 题（34 构造族 + 1 估算族），
# 与既有 115 题实测重叠 0，故 115 + 35 = 150 是**数出来的**不是外推的。
EXPECTED_DONE = 150
EXPECTED_TODO_Q03 = 62       # 212 − 150
EXPECTED_TODO_BOTH = 55      # 197 − 142
EXPECTED_TODO_Q03_ONLY = 7   # 15 − 8

# ── 已完成题的**集合归属分解**（2026-10-26 补，修正一处真实账目错误）──
#
# 原先的写法是 `both 待核 = 197 − 150`，隐含前提是「150 题全部来自 both」。
# 这个前提在前六批成立（115 题全是 both），**第七批破了它**：
# 第七批 35 题 = 27 both + 8 Q03_only。
#
# 于是 `both 待核 = 197 − 150 = 55` 这个**值**是错的（真值 55 靠的是
# 集合交集运算，不是这个减法），而 `Q03_only` 待核被完全漏掉（15 未被扣）。
# 仲裁口径：**both 待核只能由 both 集合的交集算，不能拿『both 总数 − 完成总数』**。
#
# 关键是：这种错误的**方向是「看起来更接近做完」**——它把 8 道已做的
# Q03_only 题从 both 里白扣了，同时又没从 Q03_only 里扣，两个错互相抵消
# 在 Q03 总数上（62 仍是对的），所以只看 Q03 总数永远发现不了。
EXPECTED_DONE_BOTH = 142      # both 已完成（六批 115 + 七批 27）
EXPECTED_DONE_Q03_ONLY = 8    # Q03_only 已完成（全部来自第七批）
EXPECTED_DONE_Q05_ONLY = 0    # Q05 仍 0 题完成处置（明确不动的边界）

# ── 「已审查」与「独立 MATCH」必须分两个数（2026-10-26 补）──
#
# 「150 题已审查」≠「150 题独立答案验证通过」。第七批 35 题里有 3 题
# **不是**独立 MATCH：
#   - 2 题 STEM_GIVEN_ANSWER_AGREES：题面直接给出答案，只能核「题面值 ==
#     存储答案」，没有"独立推导出答案"这一步；
#   - 1 题 UNVERIFIABLE_FROM_STEM：答案所需事实（actual=38）不在题面。
# 让「覆盖完成」的标签替代实际结论，是这一节要防的事。
EXPECTED_INDEPENDENT_MATCH = 147          # 150 − 3
EXPECTED_SPECIAL_VERDICTS = {             # 特殊结论（已审查但非独立 MATCH）
    "STEM_GIVEN_ANSWER_AGREES": 2,
    "UNVERIFIABLE_FROM_STEM": 1,
}

# 语义族覆盖（第六批新增）。动机：`check_independence.py` 实测前五批 95 题
# **全部是 numeric_judge**，construct_constraint 54 题 0 完成——「95/212」
# 这个数字会把「某族一题未核」这件事完全掩盖。故把族覆盖也纳入账实核对：
# 每族的「已完成」数与文档声明不符即失败。
EXPECTED_BY_FAMILY = {
    "numeric_judge": 95,
    "construct_constraint": 54,   # 六批 20 + 七批 34，本条即「族级清零」
    "open_estimate": 1,           # 第七批单列 1 题（UNVERIFIABLE_FROM_STEM）
}

# 全族总量也必须声明并与并集实测相符。
#
# 为什么只看 `EXPECTED_BY_FAMILY`（分子）不够：把 construct_constraint 的
# **全量**从 54 悄悄改成 54 的已完成数，覆盖率会显示成 100%，而分子分母
# 都对得上——这是「改分母洗白」通道，与「改分子」一样能骗过只核分子的判据。
# 而全量来自并集工件，本来就不该由人填；这里声明一次，是为了让「分母被改动」
# 这件事必须显式留痕，而不是悄悄发生。
EXPECTED_FAMILY_TOTAL = {
    "numeric_judge": 169,
    "construct_constraint": 54,
    "open_estimate": 1,
}


def main() -> int:
    union = json.load(open(UNION, encoding="utf-8"))
    items = union["items"]
    ids = [i["rvid"] for i in items]
    u03 = {i["rvid"]: i for i in items}

    fails: list[str] = []
    # `missing` 与 `fails` **必须分开**：
    #   缺产物 = 依赖没齐（rc=2），数字对不上 = 账实不符（rc=1）。
    # 混在一起时，「少带一个批次产物」会被读成「进度算错了」。
    missing: list[str] = []
    if len(ids) != len(set(ids)):
        fails.append(f"并集工件自身有重复 RVID（{len(ids)} 行 / "
                     f"{len(set(ids))} 唯一）")

    actual = {
        "union": len(items),
        "in_q03": sum(1 for i in items if i["in_Q03"]),
        "in_q05": sum(1 for i in items if i["in_Q05"]),
        "both": sum(1 for i in items if i["in_Q03"] and i["in_Q05"]),
        "q03_only": sum(1 for i in items if i["in_Q03"] and not i["in_Q05"]),
        "q05_only": sum(1 for i in items if i["in_Q05"] and not i["in_Q03"]),
    }
    for k, want in EXPECTED.items():
        if actual[k] != want:
            fails.append(f"{k}: 实测 {actual[k]}，文档声明 {want}")
    # 结构恒等式
    if actual["both"] + actual["q03_only"] != actual["in_q03"]:
        fails.append("both + q03_only ≠ in_q03")
    if actual["both"] + actual["q05_only"] != actual["in_q05"]:
        fails.append("both + q05_only ≠ in_q05")

    done: set[str] = set()
    per_batch: dict[str, int] = {}       # 去重后（同一批内可能重复）
    per_batch_raw: dict[str, int] = {}   # 去重前（产物里的条目数）
    for fn in BATCH_ARTIFACTS:
        p = os.path.join(RUNS, fn)
        if not os.path.isfile(p):
            # 缺产物 → 依赖问题，走 rc=2，**不记进 fails**
            missing.append(f"{fn}（批次产物，期望路径 {p}）")
            continue
        d = json.load(open(p, encoding="utf-8"))
        raw = [r["rvid"] for r in d["items"]]
        got = set(raw)
        per_batch[fn] = len(got)
        per_batch_raw[fn] = len(raw)
        extra = got - set(ids)
        if extra:
            fails.append(f"{fn} 有 {len(extra)} 题不在并集内（不应发生）")
        # 批次内自重复
        if len(raw) != len(set(raw)):
            fails.append(f"{fn} 内部有重复 RVID")

        # 本批必须全部落在 `in_Q03` 内。
        # 为什么单列：`done` 只用来算「完成总数」，若某批混进了 Q05_only 的题，
        # 总数照样 +1，而「212 − 完成」会**少算待核**——错误方向是「看起来更接近做完」。
        off = [r for r in got if not (u03.get(r) or {}).get("in_Q03")]
        if off:
            fails.append(f"{fn} 有 {len(off)} 题不在 in_Q03 内："
                         f"{[x[:8] for x in off]}——会虚增 Q03 完成数")
        done |= got

    if missing:
        print(f"\n**工件缺失 {len(missing)} 项**（这是依赖没齐，不是账实不符）：",
              file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        print("  退出码 2。", file=sys.stderr)
        return 2

    # ── 待办数必须由**集合交集**算，不能拿「集合总数 − 完成总数」──
    #
    # 原写法 `todo_both = actual["both"] - len(done & in_q03∩in_q05)` 本身是对的
    # （交集运算），但**推导标注**写成 `197 − 150`，把「150 全属 both」这个
    # 前六批的偶然前提当成了恒等式。第七批 8 道 Q03_only 一进来，这个标注
    # 就是错的，且**错误方向是「看起来更接近做完」**。
    # 故此处把三类分别入账，并在输出里逐项打印，不再给单条减法。
    done_q03 = done & {i["rvid"] for i in items if i["in_Q03"]}
    done_both = done & {i["rvid"] for i in items if i["in_Q03"] and i["in_Q05"]}
    done_q03_only = done & {i["rvid"] for i in items
                            if i["in_Q03"] and not i["in_Q05"]}
    done_q05_only = done & {i["rvid"] for i in items
                            if i["in_Q05"] and not i["in_Q03"]}

    todo_q03 = actual["in_q03"] - len(done_q03)
    todo_both = actual["both"] - len(done_both)
    todo_q03_only = actual["q03_only"] - len(done_q03_only)

    # 归属分解的三个数必须与声明一致（这是本轮整改的核心判据）
    if len(done_both) != EXPECTED_DONE_BOTH:
        fails.append(f"both 已完成: 实测 {len(done_both)}，"
                     f"声明 {EXPECTED_DONE_BOTH}"
                     f"——若用「both 总数 − 完成总数」会得到 "
                     f"{actual['both'] - len(done)}")
    if len(done_q03_only) != EXPECTED_DONE_Q03_ONLY:
        fails.append(f"Q03_only 已完成: 实测 {len(done_q03_only)}，"
                     f"声明 {EXPECTED_DONE_Q03_ONLY}"
                     f"——这一项漏算时 Q03 总数仍可能对得上")
    if len(done_q05_only) != EXPECTED_DONE_Q05_ONLY:
        fails.append(f"Q05_only 已完成: 实测 {len(done_q05_only)}，"
                     f"声明 {EXPECTED_DONE_Q05_ONLY}"
                     f"——Q05 本阶段应为 0 题处置")
    # 三者相加必须等于去重完成总数（防「多了 8 题不落任何一类」）
    if len(done_both) + len(done_q03_only) + len(done_q05_only) != len(done):
        fails.append(f"归属分解不等: both {len(done_both)} + "
                     f"Q03_only {len(done_q03_only)} + "
                     f"Q05_only {len(done_q05_only)} ≠ 合计 {len(done)}")

    # 文档声明的完成数与三个待办数必须与实测相等（防「文档没同步」与「减法外推」）
    if len(done) != EXPECTED_DONE:
        fails.append(f"去重完成合计: 实测 {len(done)}，文档声明 {EXPECTED_DONE}")
    if todo_q03 != EXPECTED_TODO_Q03:
        fails.append(f"Q03 待核验: 实测 {todo_q03}，文档声明 {EXPECTED_TODO_Q03}")
    if todo_both != EXPECTED_TODO_BOTH:
        fails.append(f"both 待核验: 实测 {todo_both}，文档声明 {EXPECTED_TODO_BOTH}")
    if todo_q03_only != EXPECTED_TODO_Q03_ONLY:
        fails.append(f"Q03_only 待核验: 实测 {todo_q03_only}，"
                     f"文档声明 {EXPECTED_TODO_Q03_ONLY}——"
                     f"上版漏了这一项，15 道从未被扣减")
    # 恒等式：both 待核 + Q03_only 待核 == Q03 待核
    # 这条正是用户验算出来的 `55 + 7 = 62`；把它写成判据而不是文档注释。
    if todo_both + todo_q03_only != todo_q03:
        fails.append(f"both {todo_both} + Q03_only {todo_q03_only} "
                     f"≠ Q03 待核 {todo_q03}——Q03 口径内部不自洽")

    # ── 「已审查」与「独立 MATCH」分两个数 ──
    #
    # 覆盖完成（150）与独立验证通过（147）混成一个数，就是让标签替代结论。
    # 从八批产物里**逐题读 verdict**，不按批次数减去 3：「第七批有 3 题非
    # MATCH」是事实，但「全七批只有 3 题非 MATCH」需要实测才能说。
    verdict_counts: dict[str, int] = {}
    for fn in BATCH_ARTIFACTS:
        p = os.path.join(RUNS, fn)
        if not os.path.isfile(p):
            continue                      # 缺件已在上面记入 missing
        for r in json.load(open(p, encoding="utf-8"))["items"]:
            v = r.get("verdict") or "UNKNOWN"
            verdict_counts[v] = verdict_counts.get(v, 0) + 1
    independent = verdict_counts.get("MATCH", 0)
    special = {v: n for v, n in verdict_counts.items() if v != "MATCH"}
    if independent != EXPECTED_INDEPENDENT_MATCH:
        fails.append(f"独立 MATCH: 实测 {independent}，"
                     f"声明 {EXPECTED_INDEPENDENT_MATCH}"
                     f"——「已审查 {len(done)}」不能替代这一个数")
    if special != EXPECTED_SPECIAL_VERDICTS:
        fails.append(f"特殊结论分布: 实测 {special}，"
                     f"声明 {EXPECTED_SPECIAL_VERDICTS}")
    if independent + sum(special.values()) != len(done):
        fails.append(f"独立 MATCH {independent} + 特殊 {sum(special.values())} "
                     f"≠ 已审查 {len(done)}")

    # 语义族覆盖核对（缺族 / 多族 / 数量不符都算账实不符）
    fam_total: dict[str, int] = {}
    fam_done: dict[str, int] = {}
    for it in items:
        f = it.get("semantic_family")
        fam_total[f] = fam_total.get(f, 0) + 1
        if it["rvid"] in done:
            fam_done[f] = fam_done.get(f, 0) + 1
    for f in sorted(set(fam_total) | set(EXPECTED_BY_FAMILY)):
        want = EXPECTED_BY_FAMILY.get(f)
        got = fam_done.get(f, 0)
        if want is None:
            fails.append(f"语义族 {f} 未在 EXPECTED_BY_FAMILY 声明（实测完成 {got}）")
        elif got != want:
            fails.append(f"语义族 {f}: 实测完成 {got}，文档声明 {want}")
    if sum(EXPECTED_BY_FAMILY.values()) != EXPECTED_DONE:
        fails.append(f"EXPECTED_BY_FAMILY 合计 {sum(EXPECTED_BY_FAMILY.values())} "
                     f"≠ 去重完成合计 {EXPECTED_DONE}")

    # 分母核对：全族总量来自并集工件，**声明值必须与实测一致**。
    # 只核分子而不核分母，就能把「54 的全量改成 54 的完成数」洗成 100% 覆盖。
    for f in sorted(set(fam_total) | set(EXPECTED_FAMILY_TOTAL)):
        want = EXPECTED_FAMILY_TOTAL.get(f)
        got = fam_total.get(f, 0)
        if want is None:
            fails.append(f"语义族 {f} 的全量未在 EXPECTED_FAMILY_TOTAL 声明"
                         f"（并集实测 {got}）——分母未经登记，覆盖率不可引用")
        elif got != want:
            fails.append(f"语义族 {f} 全量: 并集实测 {got}，声明 {want}"
                         f"（**分母被改动**会让覆盖率高估）")

    fam_q03_total = {f: sum(1 for i in items
                            if i.get("semantic_family") == f and i["in_Q03"])
                     for f in fam_total}

    # 族级覆盖状态：**两侧都必须取实测，且必须取同一个口径的实测**。
    #
    # 沿革（同一个错型换了三次外衣，每次都是"分母来源不对"）：
    #   ① 最初：两侧都用人工声明 `EXPECTED_FAMILY_TOTAL`
    #      → 声明被同步改小时把未完成标成「覆盖完成」；
    #   ② 上一步：两侧都改成实测 `fam_total`（并集全量 169）
    #      → 当前 150 题时看不出问题（numeric_judge 95≠169，两侧结论一致），
    #        但**终态会炸**：Q03 的 157 题全审完后，fam_done=157 == fam_total(169)
    #        不成立 → 被判为「未覆盖完成」，于是印出
    #        「未覆盖完成：numeric_judge 157/157（尚余 0 题）」，rc=1。
    #        即在最该庆祝的那一天，门禁反而红。
    #   ③ 现在：两侧都取 **Q03 范围实测**（`fam_q03_total`），与输出栏一致。
    #
    # **"都是实测值"不等于"可以互换"**：并集实测 169 与 Q03 实测 157 是两个
    # 不同母体的实测值。`cleared` 用 169、缺口栏用 157，就又是一次"两侧不同源"，
    # 只是这次两边都写着"实测"，比第一次更难看出来。
    #
    # 这不是缺陷修补，是**终态可达性**问题：判据必须能在"全部做完"那天仍然为真。
    # 一个永远不可能为真的判据，等于永远拦着不放行。
    def _q03_denom(f: str) -> int:
        """某族的 Q03 范围内实测题数（分母）。这是状态判定的唯一口径。"""
        return fam_q03_total.get(f, 0)

    cleared = sorted(f for f in fam_total
                     if _q03_denom(f) > 0
                     and fam_done.get(f, 0) == _q03_denom(f))
    # 反向：从**实测全集**枚举，避免漏掉"声明表没有但并集里有"的族。
    not_cleared = sorted(f for f in fam_total if f not in cleared)

    # 终态一致性：**两栏的判定结果必须与"尚余 N 题"互相对应**。
    #
    # 不能写成「比较 cleared 用的分母与缺口栏用的分母」——那两个值都来自
    # `_q03_denom(f)`，自己比自己恒相等，是恒真式（本项目已踩过多次）。
    # 唯一有区分力的写法是**拿两个栏的成员关系去对账剩余题数**：
    #   在 not_cleared 的族，剩余必须 > 0；
    #   在 cleared 的族，剩余必须 == 0。
    # 任一侧不成立，就说明"状态"与"数字"不同源。
    _state_bad = []
    for f in fam_total:
        rem = _q03_denom(f) - fam_done.get(f, 0)
        if f in not_cleared and rem <= 0:
            _state_bad.append(f"{f}: 在未覆盖栏但剩余 {rem}")
        if f in cleared and rem != 0:
            _state_bad.append(f"{f}: 在覆盖完成栏但剩余 {rem}")
    if _state_bad:
        fails.append("族状态与剩余题数不同源: " + "；".join(_state_bad)
                     + "——两侧分母口径不一致（并集实测 vs Q03 实测）")

    print("── 集合口径（实测）──")
    for k in ("union", "in_q03", "in_q05", "both", "q03_only", "q05_only"):
        print(f"  {k:10s} {actual[k]:>4}")
    print("\n── 各批完成（去重前 / 去重后）──")
    for fn in per_batch_raw:
        raw, uniq = per_batch_raw[fn], per_batch[fn]
        dup = "" if raw == uniq else f"  （批内重复 {raw - uniq}）"
        print(f"  {fn:36s} {raw:>3} / {uniq:<3}{dup}")
    print(f"  合计（七批相加）{sum(per_batch_raw.values()):>3} / "
          f"去重后 {len(done):<3}（跨批重叠 "
          f"{sum(per_batch_raw.values()) - len(done)}）")

    # 归属分解逐项打印。**不再给「both 待核 = 197 − 150」这种单条减法**：
    # 那条减法把「150 全属 both」当地前提，第七批一破，`both 待核` 的标注
    # 就是错的，且错法让账目「看起来更接近做完」。
    print(f"\n  去重完成合计: {len(done)}")
    print(f"    其中 both 已完成      : {len(done_both):>3}  (both {actual['both']})")
    print(f"    其中 Q03_only 已完成  : {len(done_q03_only):>3}  "
          f"(Q03_only {actual['q03_only']})")
    print(f"    其中 Q05_only 已完成  : {len(done_q05_only):>3}  "
          f"(Q05_only {actual['q05_only']})")
    print(f"\n  Q03 待核验    : {todo_q03:>3}   = both {todo_both} + "
          f"Q03_only {todo_q03_only}   (恒等式 {'成立' if todo_both + todo_q03_only == todo_q03 else '不成立'})")
    print(f"  both 待核验   : {todo_both:>3}   "
          f"(both {actual['both']} − both 已完成 {len(done_both)})")
    print(f"  Q03_only 待核 : {todo_q03_only:>3}   "
          f"(Q03_only {actual['q03_only']} − Q03_only 已完成 {len(done_q03_only)})")
    print(f"  Q05_only     : {actual['q05_only']:>3}   （固定归属，本阶段 0 题处置）")

    print(f"\n── 结论分级（「已审查」≠「独立验证通过」）──")
    print(f"  已审查（覆盖完成）  : {len(done):>3}")
    print(f"  独立 MATCH          : {independent:>3}")
    for v, n in sorted(special.items()):
        print(f"  特殊结论 {v:24s}: {n:>3}")
    print(f"  尚未审查            : {todo_q03:>3}")
    print(f"  尚未取得独立 MATCH  : {todo_q03 + sum(special.values()):>3}"
          f"   (= 尚未审查 {todo_q03} + 特殊结论 {sum(special.values())})")

    # 语义族覆盖。**必须同时给「独立 MATCH」**：只给「已完成/全量」会让
    # 「覆盖完成」被读成「结论通过」——第七批有 3 题已审查但非独立 MATCH。
    fam_match: dict[str, int] = {}
    by_rvid_fam = {i["rvid"]: i.get("semantic_family") for i in items}
    for fn in BATCH_ARTIFACTS:
        p = os.path.join(RUNS, fn)
        if not os.path.isfile(p):
            continue
        for r in json.load(open(p, encoding="utf-8"))["items"]:
            if (r.get("verdict") or "") == "MATCH":
                f = by_rvid_fam.get(r["rvid"])
                fam_match[f] = fam_match.get(f, 0) + 1

    print("\n── 语义族覆盖（已审查 / Q03应审 · 独立MATCH / 备注）──")
    for f in sorted(fam_total):
        d = fam_done.get(f, 0)
        m = fam_match.get(f, 0)
        q3 = fam_q03_total.get(f, 0)
        note = []
        if d != m:
            note.append(f"{d - m} 道已审查但非独立 MATCH")
        if q3 != fam_total[f]:
            note.append(f"另有 {fam_total[f] - q3} 道属 Q05_only（不在 Q03 范围）")
        mark = "  <<< 0 题完成" if d == 0 else ""
        print(f"  {f:24s} {d:>3} / {q3:<3} · {m:>3}"
              f"{'  (' + '；'.join(note) + ')' if note else ''}{mark}")

    # 族级清零单独印一行，且**必须与上面那两列同源**（都从 fam_done/fam_total 取）。
    # 不手写「54/54、1/1」——那两个数字若在别处被改，这里会跟着一起错。
    # 分子取 `fam_done`、分母取 `fam_total`（并集实测），**都不取声明表**：
    # 若两边都取 EXPECTED_FAMILY_TOTAL，这行就退化成 `n/n` 的恒真式。
    #
    # **措辞必须写「审查覆盖」不写「清零」**：这两族仍有 3 题非独立 MATCH，
    # 「清零」会被读成「结论全部通过」。
    if cleared:
        # **展示分母也必须与判定同源（Q03 口径）**。终态时若这里用并集全量，
        # 会印出 `numeric_judge 157/169`——判断已经正确（已进"覆盖完成"栏），
        # 但数字读起来像"还差 12 题"，而那 12 道根本不属 Q03。
        # 与缺口栏同理：分母换口径时，同一行会自我否证。
        print("\n  族级审查覆盖完成: " + ", ".join(
            f"{f} {fam_done.get(f, 0)}/{_q03_denom(f)}" for f in cleared))
        ok = [f for f in cleared if fam_match.get(f, 0) == _q03_denom(f)]
        notok = [f for f in cleared if f not in ok]
        if ok:
            print(f"    其中独立 MATCH 全通过: " + ", ".join(
                f"{f} {fam_match.get(f, 0)}/{_q03_denom(f)}" for f in ok))
        if notok:
            print(f"    其中**未全部独立 MATCH**: " + ", ".join(
                f"{f} {fam_match.get(f, 0)}/{_q03_denom(f)}"
                for f in notok) + "（覆盖完成 ≠ 结论全部通过）")
    else:
        print("\n  族级审查覆盖完成: 无")
    if not_cleared:
        # **分母必须用 Q03 应审数（fam_q03_total），不能用并集全量（fam_total）。**
        # 用并集分母会印出 `numeric_judge 95/169`，缺口读起来是 74 题——而
        # 169 里有 12 道属 Q05_only，不在 Q03 范围。用户专门纠正过：
        # 「不是 74 道，是 62 道」。这一行若印 169，就等于把并集口径
        # 当成 Q03 缺口写进终态输出，账目本身没错但**结论会被误读**。
        parts = ", ".join(
            f"{f} {fam_done.get(f, 0)}/{fam_q03_total.get(f, 0)}"
            f"（尚余 {fam_q03_total.get(f, 0) - fam_done.get(f, 0)} 题）"
            for f in not_cleared)
        print(f"  未覆盖完成（Q03 口径）: {parts}")
        # 自相矛盾的自检：同一族不得同时出现在「覆盖完成」与「未覆盖完成」，
        # 也不得在未覆盖栏里显示「尚余 0 题」。这只可能来自两侧分母不同源
        # （历史上正是 `cleared` 取声明分母、`not_cleared` 取实测全集的组合）。
        both_sides = sorted(set(cleared) & set(not_cleared))
        if both_sides:
            fails.append(f"族同时被标为「覆盖完成」与「未覆盖完成」: "
                         f"{both_sides}——两侧分母不同源")
        zero_left = sorted(f for f in not_cleared
                           if fam_q03_total.get(f, 0) - fam_done.get(f, 0) == 0)
        if zero_left:
            fails.append(f"族在「未覆盖完成」栏却显示尚余 0 题: {zero_left}"
                         f"——状态判定与数字自相矛盾")
        _u = [f"{f} 并集全量 {fam_total.get(f, 0)}" for f in not_cleared
              if fam_total.get(f, 0) != fam_q03_total.get(f, 0)]
        if _u:
            print(f"    （{'；'.join(_u)}——其中不属 Q03 的部分不计入本阶段缺口）")

    if fails:
        print("\n**账实不符**：", file=sys.stderr)
        for f in fails:
            print(f"  ✗ {f}", file=sys.stderr)
        return 1
    print("\n账实相符。")
    return 0


# ════════════════════════════════════════════════════════════════════════
# 自证：本脚本此前**从未自证过**，而第七批新增的「族级清零」恰恰是
# 最容易被读成「已核完」的一句。不清零也必须能 FAIL，否则那行只是装饰。
#
# 六类变异，逐条对应一种真实可发生的失效：
#   P1 漏一批产物      → 必须 rc=2（不是 rc=1）：「少了个文件」≠「账算错了」
#   P2 完成数声明虚增  → 必须 rc=1（改数字洗白）
#   P3 族完成数虚增    → 必须 rc=1（把 62 待核说成做完）
#   P4 分母被改小      → 必须 rc=1（54 的全量改成 34 就显示 34/34）
#   P5 混进 Q03 外的题 → 必须 rc=1（Q05_only 混进来会虚增 Q03 完成数）
#   P6 清零行同源      → 打印的分子分母必须来自产物，不是声明表
# ════════════════════════════════════════════════════════════════════════


def selftest() -> int:
    import contextlib
    import copy
    import io
    import shutil
    import tempfile

    print("\n── 进度账实核自证 ──")
    caught = 0

    def _run(runs_dir: str, union_path: str):
        """用临时工程目录跑一次 main()，返回 (rc, stdout+stderr)。"""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = _run_with(runs_dir, union_path)
        return rc, buf.getvalue()

    # P1：漏一批产物 → rc=2（依赖没齐），且**不得**混成 rc=1
    with tempfile.TemporaryDirectory() as td:
        runs = os.path.join(td, "runs")
        shutil.copytree(RUNS, runs)
        os.remove(os.path.join(runs, "FE1472_q03_batch7.json"))
        rc, out = _run(runs, UNION)
        # 关键：此时 EXPECTED_DONE=150 而实测 115，**两个判据都会响**。
        # 必须让「缺件」优先返回 2，否则「少了个文件」会被读成「进度算错了」。
        if rc == 2:
            caught += 1
            print("  ✓ P1 删除 batch7 产物 → rc=2（缺件不当成账实不符）")
        else:
            print(f"  ✗ P1 删除 batch7 产物后 rc={rc}（应为 2）——"
                  f"缺件会被读成账实不符")

    # P2：完成数声明虚增 35 → 必须 rc=1
    with tempfile.TemporaryDirectory() as td:
        runs = os.path.join(td, "runs")
        shutil.copytree(RUNS, runs)
        saved = globals()["EXPECTED_DONE"]
        globals()["EXPECTED_DONE"] = saved + 35
        try:
            rc, out = _run(runs, UNION)
        finally:
            globals()["EXPECTED_DONE"] = saved
        if rc == 1 and "去重完成合计" in out:
            caught += 1
            print(f"  ✓ P2 完成数声明 {saved}→{saved + 35} → rc=1 并点名")
        else:
            print(f"  ✗ P2 完成数虚增后 rc={rc}（应为 1）——"
                  f"改个数字就能洗白完成度")

    # P3：族完成数虚增（construct_constraint 54 → 60）→ 必须 rc=1
    with tempfile.TemporaryDirectory() as td:
        runs = os.path.join(td, "runs")
        shutil.copytree(RUNS, runs)
        saved_map = dict(globals()["EXPECTED_BY_FAMILY"])
        globals()["EXPECTED_BY_FAMILY"] = dict(saved_map,
                                               construct_constraint=60)
        try:
            rc, out = _run(runs, UNION)
        finally:
            globals()["EXPECTED_BY_FAMILY"] = saved_map
        if rc == 1 and "construct_constraint" in out:
            caught += 1
            print("  ✓ P3 族完成数 54→60 → rc=1 并点名")
        else:
            print(f"  ✗ P3 族完成数虚增后 rc={rc}（应为 1）")

    # P4：分母被改小（全量 54 → 34）→ 必须 rc=1
    #
    # 这是「改分母洗白」：若只核分子，34/34 与 54/54 都会被读成「清零」。
    with tempfile.TemporaryDirectory() as td:
        runs = os.path.join(td, "runs")
        shutil.copytree(RUNS, runs)
        saved_tot = dict(globals()["EXPECTED_FAMILY_TOTAL"])
        globals()["EXPECTED_FAMILY_TOTAL"] = dict(saved_tot,
                                                  construct_constraint=34)
        try:
            rc, out = _run(runs, UNION)
        finally:
            globals()["EXPECTED_FAMILY_TOTAL"] = saved_tot
        if rc == 1 and "全量" in out:
            caught += 1
            print("  ✓ P4 分母 54→34 → rc=1（改分母不被当成清零）")
        else:
            print(f"  ✗ P4 分母改小后 rc={rc}（应为 1）——"
                  f"只核分子时改分母可洗成 100%")

    # P5：把一道 Q05_only 的题塞进批次产物 → 必须 rc=1
    with tempfile.TemporaryDirectory() as td:
        runs = os.path.join(td, "runs")
        shutil.copytree(RUNS, runs)
        union = json.load(open(UNION, encoding="utf-8"))
        q05_only = [i["rvid"] for i in union["items"]
                    if i["in_Q05"] and not i["in_Q03"]]
        p = os.path.join(runs, "FE1472_q03_batch7.json")
        d = json.load(open(p, encoding="utf-8"))
        if q05_only:
            d["items"].append(dict(d["items"][0], rvid=q05_only[0]))
            json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False)
            rc, out = _run(runs, UNION)
            if rc == 1 and "不在 in_Q03" in out:
                caught += 1
                print(f"  ✓ P5 塞入 Q05_only 题（{q05_only[0][:8]}）→ rc=1")
            else:
                print(f"  ✗ P5 塞入 Q05_only 题后 rc={rc}（应为 1）")
        else:
            print("  ✗ P5 并集里找不到 Q05_only 的题——样本缺失，无法验证")

    # P6：清零行必须同源，且**必须落到正确的状态栏**。
    #
    # 首版的失败有两层：
    #   ① 判据只问「输出里有没有 `53/54`」。可 `未覆盖完成` 那一行也会印
    #      `53/54`——于是即使该族被错误塞进「覆盖完成」栏，判据照样命中、
    #      记 PASS。**这是「判据问错了问题」**，不是文档或实现的问题。
    #   ② 配套的实现漏洞：`cleared` 取 `EXPECTED_FAMILY_TOTAL`（人工声明）
    #      当分母。声明被同步改小时 `fam_done == t` 成立，该族就进了
    #      「覆盖完成」栏；而 `not_cleared` 取实测全集，于是同一族**同时
    #      出现在两栏**，还印出「未覆盖完成 … 尚余 0 题」。
    #
    # 故判据必须是**双向 + 定向**：
    #   - `53/54` 必须出现在「未覆盖完成」行（暴露真实缺口）
    #   - `53/54` 不得出现在「族级审查覆盖完成」行（不得错标完成）
    #   - `53/53` 不得出现（取声明表会退化成恒真式 n/n）
    # 三个条件缺一，都能被"改对了分母但标错状态"或"标对了状态但分母造假"绕开。
    with tempfile.TemporaryDirectory() as td:
        runs = os.path.join(td, "runs")
        shutil.copytree(RUNS, runs)
        p = os.path.join(runs, "FE1472_q03_batch7.json")
        d = json.load(open(p, encoding="utf-8"))
        idx = next(i for i, it in enumerate(d["items"])
                   if it.get("semantic_family") == "construct_constraint")
        dropped = d["items"].pop(idx)
        json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False)

        saved_map = dict(globals()["EXPECTED_BY_FAMILY"])
        saved_tot = dict(globals()["EXPECTED_FAMILY_TOTAL"])
        globals()["EXPECTED_BY_FAMILY"] = dict(saved_map, construct_constraint=53)
        globals()["EXPECTED_FAMILY_TOTAL"] = dict(saved_tot,
                                                  construct_constraint=53)
        try:
            _rc, out = _run(runs, UNION)
        finally:
            globals()["EXPECTED_BY_FAMILY"] = saved_map
            globals()["EXPECTED_FAMILY_TOTAL"] = saved_tot

        cc = "construct_constraint"
        tgt = f"{cc} 53/54"
        # 按行切出两栏，**只在栏内找**，不做全文搜索
        line_cleared = next((ln for ln in out.splitlines()
                             if "族级审查覆盖完成" in ln), "")
        line_gap = next((ln for ln in out.splitlines()
                         if "未覆盖完成" in ln), "")
        in_gap = tgt in line_gap
        in_cleared = tgt in line_cleared
        degenerate = f"{cc} 53/53" in out
        if degenerate:
            print(f"  ✗ P6 出现 `{cc} 53/53`——状态栏取的是声明表，"
                  f"退化成恒真式 n/n，看不出实际只做了 "
                  f"53/{saved_tot[cc]}")
        elif in_cleared:
            print(f"  ✗ P6 `{tgt}` 出现在「族级审查覆盖完成」栏——"
                  f"**未完成被标成覆盖完成**（分母对了但状态错了）")
        elif in_gap and line_gap:
            caught += 1
            print(f"  ✓ P6 清零行取自产物且状态栏正确"
                  f"（`{tgt}` 落在「未覆盖完成」、未落入「覆盖完成」；"
                  f"删的是 {dropped.get('rvid', '')[:8]}）")
        else:
            print(f"  ✗ P6 找不到 `{tgt}` 于「未覆盖完成」栏，判据无法验证"
                  f"（该栏={line_gap[:120]!r}；输出片段：{out[-200:]!r}）")

    # P6b：**「未覆盖完成」栏也必须从实测全集枚举**。
    #
    # 这是 P6 的另一半，单独构造才能验证：若 `not_cleared` 退回声明表
    # （`EXPECTED_FAMILY_TOTAL`），那么一个**只存在于并集里、未在声明表登记**
    # 的族会从缺口栏整个消失——数字全对、rc 仍 0，但少报一族未完成。
    # 反过来 `cleared` 退回声明表时，该族会被错标完成（P6 已覆盖）。
    #
    # 构造：往并集工件里新增一道 `<未登记族>` 的题（不登记进声明表），
    # 则该族应出现在「未覆盖完成」栏。取声明表 → 它根本不出现 → FAIL。
    with tempfile.TemporaryDirectory() as td:
        runs = os.path.join(td, "runs")
        shutil.copytree(RUNS, runs)
        u = json.load(open(UNION, encoding="utf-8"))
        uitems = u["items"] if isinstance(u, dict) else u
        # 克隆一条 Q03 题，改 RVID + 族名，且**不完成**（不在任何批次产物里）
        src = next(i for i in uitems if i.get("in_Q03"))
        ghost = dict(src)
        ghost["rvid"] = "deadbeef-0000-4000-8000-00000000beef"
        ghost["semantic_family"] = "unregistered_family_zzz"
        uitems2 = list(uitems) + [ghost]
        if isinstance(u, dict):
            u = dict(u, items=uitems2)
        else:
            u = uitems2
        up = os.path.join(td, "union.json")
        json.dump(u, open(up, "w", encoding="utf-8"), ensure_ascii=False)
        try:
            _rcb, outb = _run(runs, up)
        except Exception:                        # noqa: BLE001
            outb = ""
        line_gapb = next((ln for ln in outb.splitlines()
                          if "未覆盖完成" in ln), "")
        if "unregistered_family_zzz" in line_gapb:
            caught += 1
            print("  ✓ P6b 未在声明表登记的族仍出现在「未覆盖完成」栏"
                  "（缺口枚举起于实测全集，不是声明表）")
        else:
            print("  ✗ P6b 未登记族未进入「未覆盖完成」栏"
                  f"——缺口枚举取的是声明表，会少报未完成族"
                  f"（该栏={line_gapb[:120]!r}）")

    # P7：**归属分解判据**（本轮整改新增，对应第七批真实发生的错）
    #
    # 前五批 + 第六批 115 题**全是 both**，于是「both 待核 = both 总数 − 完成总数」
    # 这个公式一直碰巧成立。第七批 27 both + 8 Q03_only 一进来，它就不成立了。
    #
    # 真实发生的两个错值，各自单点注入（**只改一个声明，不动任何产物**）：
    #   P7a  Q03_only 待核 声明成 15（文档 §13.8 的原值，即「本批未消耗」）
    #   P7b  both 待核 声明成 47（`197 − 150` 的字面结果；真值 55）
    #
    # **为什么不用「往批次里挪题」来构造**：那样会同时打断族统计、verdict 统计、
    # 并集一致性等若干条判据，rc=1 了但**说不清是哪条判据抓到的**——
    # 判据失效也会因为别的判据响了而显示 PASS（本项目已踩过多次的
    # 「变异无效 ≠ 检测器失效」）。单点改声明可以精确归因。
    #
    # 每条都断言**具体报错文字**，而不是只断言 rc==1 或「输出里有某个词」。
    for label, name, wrong, want_hit in (
            ("P7a", "EXPECTED_TODO_Q03_ONLY", 15, "Q03_only 待核验"),
            ("P7b", "EXPECTED_TODO_BOTH", 47, "both 待核验"),
    ):
        with tempfile.TemporaryDirectory() as td:
            runs = os.path.join(td, "runs")
            shutil.copytree(RUNS, runs)
            saved = globals()[name]
            globals()[name] = wrong
            try:
                rc, out = _run(runs, UNION)
            finally:
                globals()[name] = saved
            # 必须命中「<name>: 实测 X，文档声明 <wrong>」这一行
            hit = any(("✗" in ln and want_hit in ln and f"文档声明 {wrong}" in ln)
                      for ln in out.splitlines())
            if rc == 1 and hit:
                caught += 1
                print(f"  ✓ {label} {name} 声明成 {wrong}（真实错值）"
                      f" → rc=1 且点名该判据")
            else:
                print(f"  ✗ {label} {name} 声明成 {wrong} 后 rc={rc} "
                      f"命中={hit}——「总数对、分类错」会漏过")

    # P8：**缺口分母口径**（**正向对照**，不是变异）。
    #
    # 用户专门纠正过「不是 74 道，是 62 道」——74 是并集口径（169 − 95）里
    # 未被审查的数，其中 12 道属 Q05_only，不在 Q03 范围。这条容易在一次
    # 「顺手统一分母」的重构里悄悄退回 169：输出仍自洽、rc 仍 0，但读者会把
    # 下一批范围理解成 74 题。
    #
    # **注意这是正向断言（合法样本必须 PASS），不是变异检出**。上面 P1–P7
    # 证明的是「错了会响」，这一条证明的是「对了不会被误判」——两类证据缺一
    # 不可（只有检出不报错的是误拦，只有正向的是空转）。
    with tempfile.TemporaryDirectory() as td:
        runs = os.path.join(td, "runs")
        shutil.copytree(RUNS, runs)
        rc, out = _run(runs, UNION)
        ok62 = "尚余 62 题" in out
        ok157 = "numeric_judge 95/157" in out
        no169 = "95/169" not in out
        if rc == 0 and ok62 and ok157 and no169:
            caught += 1
            print("  ✓ P8〔正向对照〕缺口分母为 Q03 应审数"
                  "（numeric_judge 95/157、尚余 62 题、不出现 95/169）")
        else:
            print(f"  ✗ P8〔正向对照〕rc={rc} 尚余62={ok62} "
                  f"95/157={ok157} 无95/169={no169}——缺口会被读成 74 题")

    # P9：**终态回归（合成数据，不代表已核验）**。
    #
    # 判据必须能在「全部做完」那天仍然为真。前一步把两侧都改成"实测"后，
    # `cleared` 取的是并集实测 169，而 Q03 应审只有 157：
    # 等剩余 62 题真审完，fam_done=157 != 169 → 该族被判「未覆盖完成」，
    # 于是印出「未覆盖完成：numeric_judge 157/157（尚余 0 题）」、rc=1。
    # **在最该庆祝的那天，门禁反而变红**。
    #
    # 根因与 P6 完全同构：两侧"都取实测"不等于"取同一个口径的实测"。
    # 并集实测 169 与 Q03 实测 157 是两个不同母体的实测值。
    #
    # 本条用**合成产物**把 62 道待审题临时标成 MATCH，其余真实工件不动，
    # 验证终态下 rc=0 且该族进入「覆盖完成」栏。
    # **合成终态只测"未来状态能否通过"，不表示这 62 题已完成核验**。
    with tempfile.TemporaryDirectory() as td:
        runs = os.path.join(td, "runs")
        shutil.copytree(RUNS, runs)
        u9 = json.load(open(UNION, encoding="utf-8"))
        uitems = u9["items"] if isinstance(u9, dict) else u9
        q3ids = {i["rvid"] for i in uitems if i.get("in_Q03")}
        done_now = set()
        for fn in BATCH_ARTIFACTS:
            p9 = os.path.join(runs, fn)
            if os.path.isfile(p9):
                for r in json.load(open(p9, encoding="utf-8"))["items"]:
                    done_now.add(r["rvid"])
        todo9 = [i for i in uitems
                 if i["rvid"] in q3ids and i["rvid"] not in done_now]
        synth9 = {"items": [
            {"rvid": i["rvid"], "renderer": i.get("renderer"),
             "semantic_family": i.get("semantic_family"),
             "verdict": "MATCH"} for i in todo9]}
        json.dump(synth9, open(os.path.join(runs, "SYNTH_final.json"),
                               "w", encoding="utf-8"), ensure_ascii=False)
        # 声明同步到终态（合成产物 + 终态声明，其余不动）
        saved_bat = list(globals()["BATCH_ARTIFACTS"])
        saved = {k: globals()[k] for k in
                 ("EXPECTED_DONE", "EXPECTED_INDEPENDENT_MATCH",
                  "EXPECTED_TODO_Q03", "EXPECTED_TODO_BOTH",
                  "EXPECTED_TODO_Q03_ONLY", "EXPECTED_DONE_BOTH",
                  "EXPECTED_DONE_Q03_ONLY")}
        saved_map = dict(globals()["EXPECTED_BY_FAMILY"])
        try:
            globals()["BATCH_ARTIFACTS"] = saved_bat + ["SYNTH_final.json"]
            globals()["EXPECTED_DONE"] = 212
            globals()["EXPECTED_INDEPENDENT_MATCH"] = 209
            globals()["EXPECTED_TODO_Q03"] = 0
            globals()["EXPECTED_TODO_BOTH"] = 0
            globals()["EXPECTED_TODO_Q03_ONLY"] = 0
            globals()["EXPECTED_DONE_BOTH"] = 197
            globals()["EXPECTED_DONE_Q03_ONLY"] = 15
            globals()["EXPECTED_BY_FAMILY"] = dict(saved_map,
                                                   numeric_judge=157)
            rc9, out9 = _run(runs, UNION)
        finally:
            globals()["BATCH_ARTIFACTS"] = saved_bat
            for k, v in saved.items():
                globals()[k] = v
            globals()["EXPECTED_BY_FAMILY"] = saved_map

        line_ok9 = next((ln for ln in out9.splitlines()
                         if "族级审查覆盖完成" in ln), "")
        line_gap9 = next((ln for ln in out9.splitlines()
                          if "未覆盖完成" in ln), "")
        nj_in_ok = "numeric_judge" in line_ok9
        nj_in_gap = "numeric_judge" in line_gap9
        no_zero = "尚余 0 题" not in out9
        no169ok = "157/169" not in line_ok9
        if rc9 == 0 and nj_in_ok and not nj_in_gap and no_zero and no169ok:
            caught += 1
            print(f"  ✓ P9〔合成终态〕62 题全审完后 rc=0，numeric_judge 进入"
                  f"「覆盖完成」栏且显示 157/157（分母取 Q03 实测量）")
        else:
            print(f"  ✗ P9〔合成终态〕rc={rc9} 进完成栏={nj_in_ok} "
                  f"仍在缺口栏={nj_in_gap} 无尚余0={no_zero} "
                  f"无157/169={no169ok}——终态反而拦着不放行"
                  f"（完成栏={line_ok9[:110]!r}）")

    total = 11
    print(f"\nPROGRESS-SELFTEST: {'PASS' if caught == total else 'FAIL'}"
          f"（{caught}/{total} 检出）")
    return 0 if caught == total else 1


def _run_with(runs_dir: str, union_path: str) -> int:
    """`main()` 的参数化版本：临时替换模块级 RUNS / UNION 后调用。"""
    g = globals()
    old_runs, old_union = g["RUNS"], g["UNION"]
    g["RUNS"], g["UNION"] = runs_dir, union_path
    try:
        return main()
    finally:
        g["RUNS"], g["UNION"] = old_runs, old_union


def _main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if not os.path.isdir(RUNS):
        print(f"缺少 {RUNS}（退出码 2 = 环境问题）", file=sys.stderr)
        return 2
    if not os.path.isfile(UNION):
        print(f"缺少 {UNION}（退出码 2 = 工件问题）", file=sys.stderr)
        return 2
    return selftest() if a.selftest else main()


if __name__ == "__main__":
    sys.exit(_main())