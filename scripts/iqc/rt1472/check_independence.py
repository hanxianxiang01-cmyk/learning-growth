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

    # B 语义族覆盖
    u = {x["rvid"]: x for x in json.load(
        open(os.path.join(RUNS, "FE1468_worklist_union.json"),
             encoding="utf-8"))["items"]}
    fam_all = Counter(x["semantic_family"] for x in u.values())

    # 两个口径必须分开算、分开印。
    #   done_a  = 前五批（A 段口径，可用于「expr 是否含题干外数字」的结论）
    #   done_b  = 前五批 + 第六批（B 段口径，用于「这一族核过多少题」）
    # 只用其中一个去填另一个的分母，就会得到「construct_constraint 0/54」这种
    # 与同包内 check_batch6_ledger.py 直接矛盾的结论。
    done_a = {r["rvid"] for b in batches for r in b["rows"]}
    done_b = set(done_a)
    b6_path = os.path.join(RUNS, BATCH6)
    b6_loaded = os.path.exists(b6_path)
    if b6_loaded:
        done_b |= {r["rvid"] for r in check_batch(b6_path)["rows"]}

    fam_a = Counter(u[r]["semantic_family"] for r in done_a if r in u)
    fam_b = Counter(u[r]["semantic_family"] for r in done_b if r in u)

    print("\n  ── B 已完成题按语义族 ──")
    if b6_loaded:
        print("     口径 = 前五批 + 第六批（第六批 %d 题）；"
              "A 段仍只统计前五批，两处分母不同，勿互相引用"
              % len(check_batch(b6_path)["rows"]))
    else:
        print(f"     口径 = 仅前五批（**{BATCH6} 不在，第六批未计入**）")
        print("     注意：此时 construct_constraint 显示 0 只代表"
              "「前五批没做这族」，不代表全项目一题未核。")
    for fam, n_all in fam_all.most_common():
        n_a, n_b = fam_a.get(fam, 0), fam_b.get(fam, 0)
        if b6_loaded:
            extra = f"（其中第六批 +{n_b - n_a}）" if n_b != n_a else ""
            print(f"    {fam:<24} 完成 {n_b:>2} / 全量 {n_all:>2}"
                  + extra
                  + ("   ← 仍未开族" if n_b == 0 else ""))
        else:
            print(f"    {fam:<24} 完成 {n_a:>2} / 全量 {n_all:>2}"
                  + ("   ← 前五批未开族" if n_a == 0 else ""))

    zero = [f for f in fam_all if fam_b.get(f, 0) == 0]
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

    # M4：B 段必须把第六批计入（2026-10-23 交付缺陷的回归闸门）。
    #
    # 缺陷复现：原实现 B 段只用 `batches`（前五批），于是打印
    #     construct_constraint  完成 0 / 全量 54   ← **0 题完成**
    # 而第六批 20 题正是该族且已 20/20 核验。同包内 check_batch6_ledger.py
    # 报的是「本批 20 / 全族 54」——两个脚本公开互相矛盾。
    #
    # 判据不能写「必须 == 20」：那样第六批换成别的族就会误报。正确做法是
    # **独立重算**：直接从第六批产物取 rvid，经 union 映射成族，再看 audit 的
    # 输出里该族完成数是否 > 前五批口径。两个数不一致 = B 段没读第六批。
    b6p = os.path.join(RUNS, BATCH6)
    if not os.path.exists(b6p):
        print(f"  ✗ M4 缺 {BATCH6}，无法验证 B 段是否计入第六批")
    else:
        b6_rows = check_batch(b6p)["rows"]
        u = {x["rvid"]: x for x in json.load(
            open(os.path.join(RUNS, UNION), encoding="utf-8"))["items"]}
        fam_b6 = Counter(u[r["rvid"]]["semantic_family"]
                         for r in b6_rows if r["rvid"] in u)
        # 第六批里占比最大的那个族，B 段口径必须比 A 段口径多出正好这么多
        if not fam_b6:
            print("  ✗ M4 第六批 rvid 全部无法映射到语义族——映射本身有问题")
        else:
            target, n_b6 = fam_b6.most_common(1)[0]
            done_a = {r["rvid"] for b in batches for r in b["rows"]}
            n_a = sum(1 for r in done_a if r in u
                      and u[r]["semantic_family"] == target)
            buf2 = io.StringIO()
            with contextlib.redirect_stdout(buf2):
                audit()
            out = buf2.getvalue()
            # 从 audit 输出里读该族的完成数（B 段口径）
            import re as _re
            m = _re.search(rf"{_re.escape(target)}\s+完成\s+(\d+)\s+/\s+全量", out)
            got = int(m.group(1)) if m else -1
            if got == n_a + n_b6 and got > n_a:
                caught += 1
                print(f"  ✓ M4 B 段计入第六批：{target} 前五批 {n_a} + 第六批 "
                      f"{n_b6} = {got}（B 段实际输出一致）")
            else:
                print(f"  ✗ M4 B 段未正确计入第六批：{target} 期望 "
                      f"{n_a}+{n_b6}={n_a + n_b6}，B 段实际 {got}"
                      f"——这会让「本批做了 20 题」被读成「一题未核」")

    print(f"\nINDEPENDENCE-SELFTEST: {'PASS' if caught == 4 else 'FAIL'}"
          f"（{caught}/4 检出）")
    return 0 if caught == 4 else 1


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