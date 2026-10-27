#!/usr/bin/env python3
"""FE-1472｜文档数字可复现性核对（离线，不连库）。

## 为什么要做这件事

项目已记铁律：

    「产物里的分析结论若不能由脚本重现，就只是某次人工编辑的快照」

第七批写完第十三章后，`docs/qa/FE1469_FE1470_Q03_BATCHES.md` 里散落着
几十个数字（35 题 / 32 MATCH / 54/54 / 150 / 62 / 42 条常量 / 9/9 检出…）。
它们**全部写在正文里**，没有任何脚本核过。而本批已实测到一次真实事故：

  §13.3.2 第一版写「按容差判会变成 **33** MATCH」，实际是 **35**（32 + 3）。
  同一个句子还错了两处——分子算错、且把容差说成对三题都适用。

这类错误靠通读发现不了（33 在上下文中毫不刺眼）。故本脚本把文档里
**可核的那些数字**逐条对回产物与脚本输出的实测值。

## 核对口径（只核「有唯一实测值」的数字）

  D1 批次规模       35 / 32 MATCH / 0 MISMATCH / 3 非 MATCH
  D2 非 MATCH 分解  2 题题面直给 + 1 题不可核
  D3 族级清零       54/54、1/1、numeric_judge 95/169
  D4 进度           完成 150、待核 62、both 待核 55
  D5 名额表         5 个 solve_path 的名额 == 池内实有数
  D6 常量声明       单批 42 条 / 六批 24 条 / 合计 66 条
  D7 自证检出数     selftest 的分子分母（9/9、6/6、5/5）

**不核**「叙述性数字」（如「四次判据错误」「16 个模板」里的人工归纳），
因为那些没有唯一实测来源；本脚本宁可少核，也不编一个来源去凑。

## 用法

    python scripts/iqc/rt1472/check_doc_claims.py
    python scripts/iqc/rt1472/check_doc_claims.py --selftest

退出码：0 全部一致 / 1 有数字对不上 / 2 工件缺失或布局不对
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


def _check_layout() -> int:
    if not os.path.isdir(os.path.join(REPO, "scripts", "iqc")):
        print(f"REPO 推导错误：{REPO}（实际在 {HERE}）", file=sys.stderr)
        print("  退出码 2 = 环境问题，**不是数字对不上**。", file=sys.stderr)
        return 2
    return 0


_L = _check_layout()
if _L:
    sys.exit(_L)

RUNS = os.path.join(REPO, "scripts", "iqc", "runs")
DOC = os.path.join(REPO, "docs", "qa", "FE1469_FE1470_Q03_BATCHES.md")
B7 = "FE1472_q03_batch7.json"
B6 = "FE1472_q03_batch6.json"
UNION = "FE1468_worklist_union.json"

# 第十三章（第七批）的起点标记。文档还有前十、十一、十二章，那些是历史记录，
# **不参与本脚本核对**——历史章节里的数字是当时的实测值，改成今天的值反而是错的。
CH13_START = "## 十三、"

# 变异总数：`selftest()` 与 D7 自证**共用同一个常量**。
# 以前 `total_mut` 是 selftest() 内的局部变量（还残留过一个 5 的旧赋值），
# D7 若另抄一个数字，两处会各自漂移——这正是「判据与文档同错」的温床。
SELFTEST_TOTAL_MUT = 13


def _nums(s: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", s or "")]


def _weights(n: object) -> set[int] | None:
    try:
        v = abs(int(str(n).strip()))
    except (TypeError, ValueError):
        return None
    return {10 ** i for i in range(len(str(v)))}


def compute_facts() -> dict:
    """从产物重算所有「可核数字」。这是**唯一事实源**，文档必须与它一致。"""
    b7 = json.load(open(os.path.join(RUNS, B7), encoding="utf-8"))
    b6 = json.load(open(os.path.join(RUNS, B6), encoding="utf-8"))
    union = json.load(open(os.path.join(RUNS, UNION), encoding="utf-8"))["items"]
    u = {x["rvid"]: x for x in union}

    s7 = b7["summary"]
    vc = s7["verdict_counts"]

    # 六、七批常量条数
    def _const_stats(doc) -> tuple[int, int]:
        n_with = sum(1 for it in doc["items"]
                     if (it.get("derivation") or {}).get("encoding_constants"))
        total = sum(len((it.get("derivation") or {}).get("encoding_constants") or [])
                    for it in doc["items"])
        return n_with, total

    w7, t7 = _const_stats(b7)
    w6, t6 = _const_stats(b6)

    # 进度
    batch_files = ["FE1469_q03_number_input.json", "FE1470_q03_batch2.json",
                   "FE1471_q03_batch3.json", "FE1472_q03_batch4.json",
                   "FE1472_q03_batch5.json", B6, B7]
    done: set[str] = set()
    for f in batch_files:
        done |= {r["rvid"] for r in
                 json.load(open(os.path.join(RUNS, f), encoding="utf-8"))["items"]}
    in03 = {x["rvid"] for x in union if x["in_Q03"]}
    both = {x["rvid"] for x in union if x["in_Q03"] and x["in_Q05"]}
    q03only = {x["rvid"] for x in union if x["in_Q03"] and not x["in_Q05"]}

    fam_total: dict[str, int] = {}
    fam_done: dict[str, int] = {}
    for x in union:
        f = x["semantic_family"]
        fam_total[f] = fam_total.get(f, 0) + 1
        if x["rvid"] in done:
            fam_done[f] = fam_done.get(f, 0) + 1

    # 各族的「独立 MATCH」数（与「已审查」分开）：
    # 覆盖完成不等于结论通过，第七批有 3 题已审查但非独立 MATCH。
    fam_match: dict[str, int] = {}
    fam_of = {x["rvid"]: x["semantic_family"] for x in union}
    for fp in batch_files:
        for r in json.load(open(os.path.join(RUNS, fp), encoding="utf-8"))["items"]:
            if (r.get("verdict") or "") == "MATCH":
                fam_match[fam_of[r["rvid"]]] = fam_match.get(fam_of[r["rvid"]], 0) + 1

    # 各族的 Q03 应审数（排除 Q05_only 那些不在 Q03 范围的题）
    fam_q03_total: dict[str, int] = {}
    for x in union:
        if x["in_Q03"]:
            f = x["semantic_family"]
            fam_q03_total[f] = fam_q03_total.get(f, 0) + 1

    # 名额：池内实有（按 solve_path 数本批题数）
    by_sp: dict[str, int] = {}
    for it in b7["items"]:
        sp = it.get("solve_path")
        by_sp[sp] = by_sp.get(sp, 0) + 1

    return {
        "total": s7["total"],
        "match": s7["match"],
        "mismatch": s7["mismatch"],
        "not_match": s7["not_match_total"],
        "given": vc.get("STEM_GIVEN_ANSWER_AGREES", 0),
        "unverifiable": vc.get("UNVERIFIABLE_FROM_STEM", 0),
        "cc_done": fam_done.get("construct_constraint", 0),
        "cc_total": fam_total.get("construct_constraint", 0),
        "cc_match": fam_match.get("construct_constraint", 0),
        "oe_done": fam_done.get("open_estimate", 0),
        "oe_total": fam_total.get("open_estimate", 0),
        "oe_match": fam_match.get("open_estimate", 0),
        "nj_done": fam_done.get("numeric_judge", 0),
        "nj_total": fam_total.get("numeric_judge", 0),
        "nj_match": fam_match.get("numeric_judge", 0),
        "nj_q03": fam_q03_total.get("numeric_judge", 0),
        "done": len(done),
        "both_total": len(both),
        "q03_only_total": len(q03only),
        "todo_q03": len(in03 - done),
        "todo_both": len(both - done),
        "todo_q03_only": len(q03only - done),
        "done_both": len(both & done),
        "done_q03_only": len(q03only & done),
        "independent": sum(1 for fp in batch_files
                           for r in json.load(
                               open(os.path.join(RUNS, fp), encoding="utf-8"))["items"]
                           if (r.get("verdict") or "") == "MATCH"),
        "const7": t7,
        "const6": t6,
        "const_both": t7 + t6,
        "const_with7": w7,
        "const_with_both": w7 + w6,
        "by_solve_path": by_sp,
        "match_plus_not": s7["match"] + s7["not_match_total"],
    }


def audit() -> int:
    missing = [p for p in (os.path.join(RUNS, f) for f in (B7, B6, UNION))
               if not os.path.isfile(p)]
    if missing or not os.path.isfile(DOC):
        for p in missing:
            print(f"  缺少工件：{p}", file=sys.stderr)
        if not os.path.isfile(DOC):
            print(f"  缺少文档：{DOC}", file=sys.stderr)
        print("  退出码 2 = 工件问题，**不是数字对不上**。", file=sys.stderr)
        return 2

    f = compute_facts()
    text = open(DOC, encoding="utf-8").read()
    i = text.find(CH13_START)
    if i < 0:
        print(f"文档里找不到起点「{CH13_START}」——章节结构变了，"
              f"本核对器无法定位，退出码 2。", file=sys.stderr)
        return 2
    ch = text[i:]

    fails: list[str] = []
    checked = 0

    def must(cond: bool, msg: str) -> None:
        nonlocal checked
        checked += 1
        if not cond:
            fails.append(msg)

    # ── D1 批次规模 ──
    must(f"| **{f['match']}** |" in ch,
         f"D1 未找到「MATCH 题数 = {f['match']}」的粗体声明")
    must(f"| `MISMATCH` | **{f['mismatch']}** |" in ch,
         f"D1 未找到「MISMATCH = {f['mismatch']}」")
    must(f"| 合计 | {f['total']} | **{f['total']}** |" in ch,
         f"D1 未找到名额表合计 {f['total']}")

    # ── D2 非 MATCH 分解 ──
    must(f"| `STEM_GIVEN_ANSWER_AGREES` | {f['given']} |" in ch,
         f"D2 题面直给应为 {f['given']} 题")
    must(f"| `UNVERIFIABLE_FROM_STEM` | {f['unverifiable']} |" in ch,
         f"D2 不可核应为 {f['unverifiable']} 题")
    must(f["given"] + f["unverifiable"] == f["not_match"],
         f"D2 内部不守恒：{f['given']} + {f['unverifiable']} "
         f"≠ {f['not_match']}（产物自身有问题）")

    # ── D3 族级审查覆盖（**不是「清零」**）──
    #
    # 措辞在 2026-10-26 由「族级清零」改为「族级审查覆盖完成」：
    # 这两族共 55 题里有 3 题已审查但**非独立 MATCH**，说「清零」会被
    # 读成「结论全部通过」。判据因此锚到新措辞，并**额外核独立 MATCH 数**。
    import re as _re
    must(_re.search(rf"construct_constraint\s+{f['cc_done']}\s*/\s*{f['cc_total']}"
                    rf"\s*·\s*{f['cc_match']}\b", ch) is not None,
         f"D3 construct_constraint 应为 已审查 {f['cc_done']}/{f['cc_total']}"
         f"、独立 MATCH {f['cc_match']}")
    must(_re.search(rf"open_estimate\s+{f['oe_done']}\s*/\s*{f['oe_total']}"
                    rf"\s*·\s*{f['oe_match']}\b", ch) is not None,
         f"D3 open_estimate 应为 已审查 {f['oe_done']}/{f['oe_total']}"
         f"、独立 MATCH {f['oe_match']}")
    # numeric_judge 的行里分母是 **Q03 应审数 157**（不是并集 169）——
    # 169 里有 12 道 Q05_only，不属 Q03 范围。用 169 当分母会把「不在本次
    # 范围」的 12 题算成缺口，这正是用户指出「不是 74 道而是 62 道」的同一处。
    must(_re.search(rf"numeric_judge\s+{f['nj_done']}\s*/\s*{f['nj_q03']}"
                    rf"\s*·\s*{f['nj_match']}\b", ch) is not None,
         f"D3 numeric_judge 应为 已审查 {f['nj_done']}/{f['nj_q03']}"
         f"（Q03 应审）、独立 MATCH {f['nj_match']}")
    # 全量 169 在第十三章里**不必出现**：章内族表已统一改用 Q03 应审数（157）。
# 169 只出现在第十二章的历史表（历史章节不参与核对）。
    # 首版这里写 must("95 / 169" in ch) 直接 FAIL——是**判据锚到了旧结构**，
    # 不是文档错。已删除，不改成"要求文档补一句 169"：那会为了迁就判据
    # 去增加一句没有信息量的内容。
    # 措辞判据（**窄口径**）。
    #
    # 不能直接禁「族级清零」四个字：第十三章正文有多处**历史叙述**引用这个
    # 词（「最初想把族级清零做成终态」「P4 改分母不被当成清零」），那些引用
    # 是准确的记录，**禁掉就是逼内容说错话**（项目铁律）。
    #
    # 真正要防的是它**被当作当前结论标签**回来——那一定长成
    # `族级清零: construct_constraint 54/54` 这个带冒号的形式（脚本原来
    # 就是这么打印的）。故只禁这个形态，并正向要求新措辞与限定表存在。
    must("族级清零: construct_constraint" not in ch,
         "D3 文档仍把「族级清零」当当前结论标签（`族级清零: construct_constraint...`）"
         "——该措辞会把「已审查」读成「结论全部通过」，应为「族级审查覆盖完成」")
    must("族级审查覆盖完成" in ch,
         "D3 缺少「族级审查覆盖完成」表述")
    must("其中**未全部独立 MATCH**" in ch,
         "D3 缺少「其中未全部独立 MATCH」一行——"
         "这正是「覆盖完成 ≠ 结论通过」的落点，不能省")
    # 独立 MATCH 与已审查必须分列（防用一个数替代两个数）。
    #
    # **不能用「某一行字面存在」当判据**：第十三章把这个数写了三处
    # （分级块的 `独立 MATCH  : 147`、13.13.2 的 `独立 MATCH      147`、
    # 13.13.5 的同一行）。只锚一处的写法，改掉另外任一处都照样 PASS。
    #
    # 但也不能「扫全文所有 独立 MATCH <数字>」——族表里还有
    # `独立 MATCH 52`（construct_constraint）、`0`（open_estimate）、
    # `95`（numeric_judge），以及「尚未取得独立 MATCH 65」。首版这么写直接
    # 误报 7 处。**判据必须窄到「累计总量」这一个语义**，否则它是错的判据。
    #
    # 收紧为：族表里的数一律不算。族表行的特征是「族名 + 已审查 + 数字 + · +
    # 独立 MATCH + 数字」，而累计量的写法是「独立 MATCH + 冒号/空白 + 数字」且
    # **行内没有族名**。故用「按行判断 + 行内不得含族名」这两个条件交集。
    #
    # 第三类例外：**引用既往错误值**的叙述。13.13.2 记录 M6 首版 bug 时写
    # 「打印出『已审查 54 / 独立 MATCH 0』」——这个 0 是 bug 的证据，删掉
    # 就把「当初错在哪」抹掉了（逼内容说错话）。但也不能像首版那样一律跳过
    # 带引号的，否则把错误值写进引号就能绕过判据。
    #
    # 故：**只有「引用标记 + 该值确实与当前结论不符」两个条件同时成立才放行**。
    # 标记限定为「打印出 / 恒为 / 曾 / 报出」——都是"当时发生了什么"的叙述，
    # 不是"现在是什么"的结论。放行的项单独计数、打印出来，可人工复核。
    _fams = ("construct_constraint", "open_estimate", "numeric_judge")
    _QUOTE_MARKS = ("打印出", "恒为", "曾", "报出")
    _im: list[str] = []
    _quoted: list[str] = []
    for _line in ch.splitlines():
        if any(fm in _line for fm in _fams):
            continue                      # 族表行，不计入累计量
        for _m in _re.finditer(r"独立 MATCH\s*:?\s*(\d+)", _line):
            _pre = _line[max(0, _m.start() - 12):_m.start()]
            if any(k in _pre for k in ("尚未", "未全部", "其中", "尚有")):
                continue
            # 引用既往错误值：标记在前文、且与被引值不同（引的是旧值）
            _head = _line[:max(0, _m.start())]
            if any(k in _head for k in _QUOTE_MARKS) and int(_m.group(1)) != f["independent"]:
                _quoted.append(_m.group(1))
                continue
            _im.append(_m.group(1))
    bad_im = [x for x in _im if int(x) != f["independent"]]
    must(not bad_im and len(_im) >= 2,
         f"D3 累计「独立 MATCH」的每一处都应为 {f['independent']}"
         f"（已审查 {f['done']}），实取 {_im or '缺失'}"
         + (f"，其中 {bad_im} 不符" if bad_im else "")
         + ("" if len(_im) >= 2 else "（少于 2 处，某段被删了）")
         + (f"；另有引用既往错误值 {_quoted} 已放行（须带「打印出/恒为/曾/报出」标记）"
            if _quoted else ""))
    # 注意反引号：文档里是「| `numeric_judge` 仍 74 题未核 |」。
    # 第一版判据漏了反引号，于是报「文档与实测不一致」——而文档其实是对的，
    # **是判据的锚点写错了**。这类误报比漏报更危险：它会让人去改对的文档。
    #
    # 同一处还有第二个错，且更严重：原判据期望值取的是
    # `nj_total - nj_done` = 169 − 95 = **74**，即**并集口径**。而这段登记
    # 说的是 Q03 范围内还剩多少，应为 157 − 95 = **62**。169 里有 12 道属
    # Q05_only，不在 Q03 范围——把 74 写进缺口登记，会让下一批范围说大 12 题。
    # 用户已明确指出「不是 74 道而是 62 道」。此处改为 Q03 口径，并**额外禁止**
    # 「仍 74 题未核」这个旧值回来。
    must(f"| `numeric_judge` 仍 {f['nj_q03'] - f['nj_done']} 题未核 |" in ch,
         f"D3 缺口登记应为「| `numeric_judge` 仍 "
         f"{f['nj_q03'] - f['nj_done']} 题未核 |」（Q03 口径 "
         f"{f['nj_q03']} − {f['nj_done']}；并集口径的 "
         f"{f['nj_total'] - f['nj_done']} 不是本阶段缺口）")
    must(f"仍 {f['nj_total'] - f['nj_done']} 题未核" not in ch,
         f"D3 文档仍有并集口径的「仍 "
         f"{f['nj_total'] - f['nj_done']} 题未核」——该数含 12 道 Q05_only，"
         f"会被读成 Q03 缺口")

    # ── D4 进度（**归属分解必须逐项对**）──
    must(f"| Q03 完成（去重 RVID） | 115 | **{f['done']}** |" in ch,
         f"D4 Q03 完成应为 {f['done']}")
    must(f"| ‣ 其中 `both` 已完成 | 115 | **{f['done_both']}** |" in ch,
         f"D4 both 已完成应为 {f['done_both']}——"
         f"用「both 总数 − 完成总数」会得到 {f['both_total'] - f['done']}")
    must(f"| ‣ 其中 `Q03_only` 已完成 | 0 | **{f['done_q03_only']}** |" in ch,
         f"D4 Q03_only 已完成应为 {f['done_q03_only']}（第七批用掉的量）")
    must(f"| Q03 待核验（`in_Q03`=212） | 97 | **{f['todo_q03']}** |" in ch,
         f"D4 Q03 待核应为 {f['todo_q03']}")
    must(f"| `both` 待核验（`both`=197） | 82 | **{f['todo_both']}** |" in ch,
         f"D4 both 待核应为 {f['todo_both']}")
    must(f"| `Q03_only` 待核验 | 15 | **{f['todo_q03_only']}** |" in ch,
         f"D4 Q03_only 待核应为 {f['todo_q03_only']}——"
         f"原文档写「15，本批未消耗」是错的")
    # 恒等式：both 待核 + Q03_only 待核 == Q03 待核（用户验算的 55+7=62）
    must(f['todo_both'] + f['todo_q03_only'] == f['todo_q03'],
         f"D4 归属分解不自洽：both {f['todo_both']} + "
         f"Q03_only {f['todo_q03_only']} ≠ Q03 {f['todo_q03']}")
    must(f"**both {f['todo_both']} + Q03_only {f['todo_q03_only']}**" in ch,
         f"D4 Q03 待核的算法列应写「both {f['todo_both']} + "
         f"Q03_only {f['todo_q03_only']}」，不能写成单一减法")
    must(f"去重后 {f['done']}（跨批重叠 0）" in ch,
         f"D4 实测块应写「去重后 {f['done']}（跨批重叠 0）」")

    # ── D5 名额表 ──
    for sp, n in f["by_solve_path"].items():
        must(f"| `{sp}` | {n} | **{n}** |" in ch,
             f"D5 solve_path {sp} 的「池内实有 / 名额」应为 {n} / {n}")

    # ── D6 常量声明（**三个数都必须对，最容易混**）──
    must(f"| **仅第七批** | {f['const_with7']} / {f['total']} | **{f['const7']}** |" in ch,
         f"D6 第七批常量条数应为 {f['const7']}（有声明常量 {f['const_with7']} 题）")
    must(f"| 仅第六批 | {f['const_with_both'] - f['const_with7']} / 20 | {f['const6']} |" in ch,
         f"D6 第六批常量条数应为 {f['const6']}")
    must(f"| 六 + 七批合计 | **{f['const_with_both']} / 55** | **{f['const_both']}** |" in ch,
         f"D6 六、七批合计应为 {f['const_both']} 条（{f['const_with_both']} 题）")
    # 反向：单批数不得被当成合计数（本项目已出现过「两个分母强行相等」）
    must(f["const7"] != f["const_both"] or f["const_with7"] == f["const_with_both"],
         f"D6 单批 {f['const7']} 与合计 {f['const_both']} 相同但题数不同——"
         f"文档必须分三行列出，不能只写一个总数")

    # ── D7 自证检出数（**文档头承诺过、此前并未实现**）──
    #
    # 脚本头部「核对口径」里写着 `D7 自证检出数 selftest 的分子分母`，但代码
    # 从未实现过这一条。后果是：自证从 9/9 扩到 10/10、再扩到 11/11 时，
    # 文档里那句「PROGRESS N/N」**没有任何东西核它**，写错了不会响。
    # 这与本项目已记的「文档声明了判据、代码没实现」是同一类失效——
    # 读者会以为这些数被核过。
    #
    # 取值方式：**实跑各脚本的 selftest，解析它自己打印的分母**，
    # 不与文档互抄（否则两边一起错，判据自我印证）。
    #
    # **本脚本自己不能出现在这张表里**：`--selftest` 会再调本脚本
    # `--selftest`，无限递归（实测直接挂死）。故 DOC-CLAIMS 的分母由
    # 变异总数 `total_mut` 提供——它就在同一个文件里，且是上面
    # `selftest()` 真正循环的那个数。
    import re as _re2
    import subprocess as _sp

    _SELF_DENOM = SELFTEST_TOTAL_MUT   # 与 selftest() 共用，不另抄

    def _selftest_denom(script: str, tag: str) -> tuple[int, int] | None:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), script)
        if not os.path.isfile(p):
            return None
        r = _sp.run([sys.executable, p, "--selftest"],
                    capture_output=True, text=True, timeout=600)
        mm = _re2.search(rf"{tag}:\s*(PASS|FAIL)（(\d+)/(\d+) 检出）",
                         r.stdout)
        if not mm:
            return None
        return int(mm.group(2)), int(mm.group(3))

    # **脚本必须一一对上台上的那一个**。第一版把 BATCH7 接到
    # `q03_batch7.py`（题级核验器，输出是「答案篡改 32/32；题干数字变异
    # 16/16 模板…」，**没有** `（N/N 检出）` 这个形态），于是 D7 取不到分母、
    # 直接 FAIL——而文档里那个 `BATCH7 9/9` 真正来自
    # `check_batch7_ledger.py`（账实核区分力自证）。
    # 这两个脚本名字都带 batch7，接错了照样"看起来对"：**判据接错源，
    # 与文档写错数字是同一种病**，只是错在判据这一侧。
    _d7 = [("check_progress.py", "PROGRESS-SELFTEST", "PROGRESS", None),
           ("check_independence.py", "INDEPENDENCE-SELFTEST", "INDEPENDENCE",
            None),
           ("check_doc_claims.py", "DOC-CLAIMS-SELFTEST", "DOC-CLAIMS",
            _SELF_DENOM),
           ("check_batch7_ledger.py", "BATCH7-LEDGER-SELFTEST", "BATCH7",
            None)]
    _d7_parts = []
    _d7_bad = []
    for _f, _tag, _label, _fixed in _d7:
        if _fixed is not None:
            # 本脚本**不能**实跑自己的 `--selftest`（再调本脚本 → 递归挂死），
            # 故分子分母都取 `SELFTEST_TOTAL_MUT`。这一栏的证据不由本判据
            # 提供，而由 `pr_gate.py` 第 24 项提供：它要求
            # `check_doc_claims.py --selftest` 的 **rc==0 且** 输出
            # `DOC-CLAIMS-SELFTEST: PASS`，而 PASS 只在
            # `caught == total_mut` 时才打印——即「分子等于分母」已被
            # 门禁独立证明。这里若假装自己能验，反而是自我印证。
            _d7_parts.append(f"{_label} {_fixed}/{_fixed}")
            continue
        _r = _selftest_denom(_f, _tag)
        if _r is None:
            fails.append(f"D7 取不到 {_f} 的 selftest 分母——"
                         f"文档里的自证计数没有实测来源")
            continue
        # **分子必须取实测检出数，不能把分母回填成分子**。
        # 首版写成 `_r[1]/_r[1]`，等于断言「分母/分母」——自证真跑出
        # 10/13 时，文档照写 13/13 仍然 PASS，判据对检出数完全不敏感，
        # 是又一个恒真式（自己和自己比）。
        _d7_parts.append(f"{_label} {_r[0]}/{_r[1]}")
        if _r[0] != _r[1]:
            _d7_bad.append(f"{_label} {_r[0]}/{_r[1]}")
    if _d7_bad:
        fails.append("D7 下列自证实跑未全过（" + "、".join(_d7_bad)
                     + "）——文档不得记成 N/N 全过")
    if _d7_parts:
        # 文档里那句必须是「四项自证：PROGRESS 11/11、INDEPENDENCE 6/6、…」
        _want = "四项自证：" + "、".join(_d7_parts)
        must(_want in ch,
             f"D7 文档自证计数应为「{_want}」——"
             f"分母取各脚本 selftest 实跑结果，不取文档自述")
        # D7 末两字必须是句号收尾的独立行（防「11/11」被追加成「11/110」）
        must(_want + "。" in ch, f"D7 自证计数行应以句号收尾：{_want}。")

    # **门禁行数不在这里核**（曾试过，`pr_gate → 本脚本 → pr_gate` 递归，
    # 实测直接 SIGTERM 137）。它是「门禁自己打印了多少行」这个属性，
    # 由**产出这些行的 pr_gate.py 在收尾时自数自核**（见该脚本末尾
    # 「门禁行数与文档对账」一段）——计数主体自己数，才不循环。

    print("── 文档数字可复现性核对（第十三章）──")
    print(f"  实测事实：")
    for k in ("total", "match", "mismatch", "not_match", "given", "unverifiable",
              "cc_done", "cc_total", "oe_done", "oe_total", "nj_done", "nj_total",
              "done", "todo_q03", "todo_both", "const7", "const6", "const_both"):
        print(f"    {k:16s} {f[k]}")
    print(f"  名额：{f['by_solve_path']}")
    print(f"\n  核对项 {checked} 条")

    if fails:
        print("\n**文档与实测不一致**：", file=sys.stderr)
        for m in fails:
            print(f"  ✗ {m}", file=sys.stderr)
        return 1
    print("\n文档数字与产物一致。")
    return 0


def selftest() -> int:
    """证明本核对器能失败。

    关键：**必须改到被核对的那个数字本身**。
    若只改文档里的叙述文字，本脚本不读叙述，自然无反应——那不是判据失效。
    """
    import shutil
    import tempfile

    print("\n── 文档数字核对器自证 ──")
    caught = 0

    base = open(DOC, encoding="utf-8").read()
    b7 = json.load(open(os.path.join(RUNS, B7), encoding="utf-8"))
    s = b7["summary"]
    cc_total = 54

    muts = [
        ("MATCH 32→31", f"| **{s['match']}** |", "| **31** |"),
        ("合计 35→34", "| 合计 | 35 | **35** |", "| 合计 | 35 | **34** |"),
        ("族级审查覆盖 54/54→53/54",
         "construct_constraint      54 / 54  ·  52",
         "construct_constraint      53 / 54  ·  52"),
        ("族独立 MATCH 52→54（等于已审查）",
         "construct_constraint      54 / 54  ·  52",
         "construct_constraint      54 / 54  ·  54"),
        ("常量单批 42→66（把合计当单批）",
         "| **仅第七批** | 19 / 35 | **42** |",
         "| **仅第七批** | 19 / 35 | **66** |"),
        ("待核 62→60", f"| Q03 待核验（`in_Q03`=212） | 97 | **62** |",
         "| Q03 待核验（`in_Q03`=212） | 97 | **60** |"),
        # ── 以下两条对应本轮被指出的两处真实错误 ──
        # ① Q03_only 待核写回 15（「本批未消耗」的原值）
        ("Q03_only 待核 7→15（原错误值）",
         "| `Q03_only` 待核验 | 15 | **7** |",
         "| `Q03_only` 待核验 | 15 | **15** |"),
        # ② both 已完成写回「both 总数 − 完成总数」的结果（143）
        ("both 已完成 142→143（减法外推）",
         "| ‣ 其中 `both` 已完成 | 115 | **142** |",
         "| ‣ 其中 `both` 已完成 | 115 | **143** |"),
        # ③ 把「族级清零」当结论标签写回来（措辞回归）
        ("措辞回归：审查覆盖完成→族级清零",
         "  族级审查覆盖完成: construct_constraint 54/54, open_estimate 1/1",
         "  族级清零: construct_constraint 54/54, open_estimate 1/1"),
        # ④ 独立 MATCH 被抹成与已审查相同
        ("独立 MATCH 147→150（等于已审查）",
         "  独立 MATCH          : 147",
         "  独立 MATCH          : 150"),
        # ⑤ 试绕过「引用既往错误值」豁免：把 13.13.2 里那句引用**改成结论式
        # 陈述**（去掉「打印出/恒为」标记、保留错误值 0）。若仍 PASS，说明
        # 豁免是「看到引号就放行」——那它就是个免费的后门，判据等于失效。
        # 反向要求：**错误值本身不能靠引号过关，只能靠"这是历史叙述"过关**。
        ("引用句改成结论句（保留错误值 0，去掉引用标记）",
         "恒为 None，打印出「已审查 54 / 独立 MATCH 0」",
         "仍为 None；累计独立 MATCH 0（覆盖完成却无结论）"),
        # ⑥ 缺口分母退回并集口径：62 → 74。
        # 62 是 Q03 缺口（157 − 95），74 是并集缺口（169 − 95），后者含 12 道
        # Q05_only。退回 74 后文档内部仍自洽、看不出矛盾，但下一批范围会大 12 题。
        ("缺口 62→74（并集口径回填）",
         "| `numeric_judge` 仍 62 题未核 |",
         "| `numeric_judge` 仍 74 题未核 |"),
    ]

    with tempfile.TemporaryDirectory() as td:
        tp = os.path.join(td, "doc.md")
        g = globals()
        old_doc = g["DOC"]
        try:
            for label, old, new in muts:
                if old not in base:
                    print(f"  ✗ 变异「{label}」锚点不存在——变异构造错误，"
                          f"不是判据失效")
                    continue
                # **必须替换全部出现处**。第十三章为了「读者能对上脚本输出」
                # 会把同一行贴两遍（一处是叙述、一处是实测块）。只替第一处时，
                # 第二处仍然满足判据，rc 保持 0——这会显示成「判据失效」，
                # 实际是**变异没改干净**（本项目反复踩的同一坑）。
                open(tp, "w", encoding="utf-8").write(base.replace(old, new))
                g["DOC"] = tp
                import contextlib
                import io
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf), \
                        contextlib.redirect_stderr(buf):
                    rc = audit()
                if rc == 1:
                    caught += 1
                    print(f"  ✓ 变异「{label}」→ rc=1")
                else:
                    print(f"  ✗ 变异「{label}」后 rc={rc}（应为 1）")
        finally:
            g["DOC"] = old_doc

    # 额外：文档缺失时必须 rc=2，不能是 rc=1
    g = globals()
    old_doc = g["DOC"]
    try:
        g["DOC"] = os.path.join("/nonexistent", "doc.md")
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = audit()
        if rc == 2:
            caught += 1
            print("  ✓ 文档缺失 → rc=2（不是 rc=1）")
        else:
            print(f"  ✗ 文档缺失后 rc={rc}（应为 2）")
    finally:
        g["DOC"] = old_doc

    total_mut = SELFTEST_TOTAL_MUT
    print(f"\nDOC-CLAIMS-SELFTEST: {'PASS' if caught == total_mut else 'FAIL'}"
          f"（{caught}/{total_mut} 检出）")
    return 0 if caught == total_mut else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    try:
        return selftest() if a.selftest else audit()
    except Exception as e:      # noqa: BLE001
        import traceback
        traceback.print_exc()
        print(f"\n脚本自身异常（{type(e).__name__}）——这**不是**「数字对不上」，"
              f"退出码 2。", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())