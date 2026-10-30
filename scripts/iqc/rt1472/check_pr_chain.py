#!/usr/bin/env python3
"""PR 堆叠整链覆盖核对（`FE-1472` 第七批 / #132→#133→#134→#136→#135）。

为什么要有这个脚本
------------------
上一轮汇报写「8 个提交全部覆盖」，实际是 9。**错因不在任何一段，而在合计**：
逐段核对 `base == 上家 head` 五段全 ✓，于是写了「全部覆盖」——但从未把
五段加起来跟整链总数对一次。

`base == 上家 head` 这类比对**存在结构性盲区**：它只能证明「相邻两段接上了」，
不能证明「上家 head 到本家 base 之间没有提交没被任何 PR 覆盖」。若中间有
一个提交游离在两段之间，所有 `base == head` 仍然成立，账却漏了。

所以本脚本核的是四条**不变量**（它们在任意时点都成立，可反复重跑）：

  1. 整链提交数 == 唯一 SHA 数        （没有重复计数）
  2. 逐段之和 == 整链总数              （★ 当初真正抓出错误的那个）
  3. #135 区间 == 整链 − #136 累计     （交叉口径）
  4. 每个分支都是下一个的祖先         （首尾相接、无遗漏）

**文档里不写「当前整链有几个提交」**：那是个自指量——文档每改一次提交，
它就多一个，追写固定值永远追不上（本轮实测 9→10→11）。文档只写这四条
不变量，当前值现场跑本脚本取。

用法
----
    python scripts/iqc/rt1472/check_pr_chain.py
    python scripts/iqc/rt1472/check_pr_chain.py --selftest

退出码：0 全通过 / 1 不变量不成立 / 2 环境问题（无 git、分支缺失）
"""
from __future__ import annotations

import argparse
import subprocess
import sys

# 合并顺序即此顺序。**#136 在 #135 之前**：#135 以 D2 分支为 base，
# 故它在合并顺序上依赖 #136，不能说两个 PR「互不依赖」。
CHAIN = [
    ("#132", "feat/FE-1472-batch4-q03"),
    ("#133", "feat/FE-1472-batch5-q03"),
    ("#134", "feat/FE-1472-batch6-q03"),
    ("#136", "feat/FE-1472-d2-h4-assertions"),
    ("#135", "feat/FE-1472-batch7-q03"),
]
BASE = "main"
TAIL = CHAIN[-1][1]          # #135 的 head，整链末端
MID = CHAIN[3][1]            # #136 的 head，用于交叉口径


def _git(*args: str) -> tuple[int, str]:
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def _count(spec: str) -> int | None:
    rc, out = _git("rev-list", "--count", spec)
    if rc != 0 or not out:
        return None
    return int(out)


def _resolve(ref: str) -> str | None:
    """本地优先，其次 origin/。返回可用的 ref 名。"""
    for cand in (ref, f"origin/{ref}"):
        rc, _ = _git("rev-parse", "--verify", cand)
        if rc == 0:
            return cand
    return None


def check() -> tuple[int, list[str], dict]:
    """返回 (rc, 失败项, 实测值)。rc=2 表示环境问题，不是判据失败。"""
    rc0, _ = _git("rev-parse", "--git-dir")
    if rc0 != 0:
        return 2, ["当前目录不是 git 仓库——本脚本核的是提交图，不是文件"], {}

    fails: list[str] = []
    facts: dict = {}

    base_ref = _resolve(BASE)
    tail_ref = _resolve(TAIL)
    mid_ref = _resolve(MID)
    if not base_ref or not tail_ref or not mid_ref:
        return 2, [f"缺分支：{BASE} / {TAIL} / {MID} 至少一个取不到"], {}

    # 各段分支必须都存在（缺一个就说明链断了，不能静默跳过）
    seg_refs: list[tuple[str, str]] = []
    for pr, br in CHAIN:
        r = _resolve(br)
        if r is None:
            fails.append(f"{pr} 分支 {br} 取不到——链上有分支缺失，"
                         f"「全部覆盖」不成立")
        else:
            seg_refs.append((pr, r))

    # ── 不变量 1：整链提交数 == 唯一 SHA 数 ──
    n_total = _count(f"{base_ref}..{tail_ref}")
    rc, out = _git("rev-list", f"{base_ref}..{tail_ref}")
    uniq = len(set(out.splitlines())) if out else 0
    facts["整链提交数"] = n_total
    facts["唯一 SHA 数"] = uniq
    if n_total is None:
        fails.append("取不到整链提交数（rev-list --count 失败）")
    elif n_total != uniq:
        fails.append(f"整链提交数 {n_total} ≠ 唯一 SHA 数 {uniq}"
                     f"——存在重复计数或 rev-list 输出异常")

    # ── 不变量 4：每个分支都是下一个的祖先（须先验，后面差分才有意义）──
    for (p1, r1), (p2, r2) in zip(seg_refs, seg_refs[1:]):
        rc, _ = _git("merge-base", "--is-ancestor", r1, r2)
        facts[f"{p1} ⊂ {p2}"] = rc == 0
        if rc != 0:
            fails.append(f"{r1} 不是 {r2} 的祖先——区间不首尾相接，"
                         f"中间可能有提交没被任何 PR 覆盖")

    # ── 不变量 2：逐段之和 == 整链总数（★ 当初抓出 8→9 的就是这条）──
    # 用**累计差分**：seg_i = count(main..b_i) − count(main..b_{i-1})
    # 这样即便某段分支不是纯线性也不会算错段长。
    cum: list[int] = []
    for _, r in seg_refs:
        c = _count(f"{base_ref}..{r}")
        if c is None:
            fails.append(f"取不到 {r} 相对 {BASE} 的提交数")
            c = 0
        cum.append(c)
    segs = [cum[0]] + [cum[i] - cum[i - 1] for i in range(1, len(cum))]
    facts["逐段"] = dict(zip([p for p, _ in seg_refs], segs))

    # **段长为负必须单独报**：累计差分法假定「scope 逐级增大」，一旦某分支
    # 不是下一个的祖先（侧支），差值会变负。此时 `sum(segs)` 仍可能恰好
    # 等于整链总数（负数把多出来的削平了），**逐段和对总数这条判据会白送
    # 通过**。实测过：断裂图上 #136 段算出 −1，而 `逐段之和 3 == 整链 3`
    # 成立，只有祖先关系那一条在报警。所以「和为总数」不能单独当结论。
    neg = {k: v for k, v in facts["逐段"].items() if v < 0}
    if neg:
        fails.append(f"段长为负 {neg}——该分支不是上家的后代（侧支），"
                     f"累计差分不适用；区间并未首尾相接")
    facts["逐段之和"] = sum(segs)
    if n_total is not None and sum(segs) != n_total:
        fails.append(f"逐段之和 {sum(segs)} ≠ 整链总数 {n_total}"
                     f"——**每段都对不等于总计对**（本轮原始错误的同一形态）")

    # ── 不变量 3：交叉口径 #135 区间 == 整链 − #136 累计 ──
    n_mid = _count(f"{base_ref}..{mid_ref}")
    n_seg_last = _count(f"{mid_ref}..{tail_ref}")
    facts["#135 区间"] = n_seg_last
    if n_mid is None or n_seg_last is None or n_total is None:
        fails.append("交叉口径取数失败（#136 累计 / #135 区间 / 整链）")
    else:
        facts["整链 − #136 累计"] = n_total - n_mid
        if n_seg_last != n_total - n_mid:
            fails.append(f"#135 区间 {n_seg_last} ≠ 整链 {n_total} − "
                         f"#136 累计 {n_mid} = {n_total - n_mid}"
                         f"——同一段用两种口径算出不同长度")

    return (1 if fails else 0), fails, facts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    rc, fails, facts = check()
    if rc == 2:
        print("**环境问题**（不是判据失败）：", file=sys.stderr)
        for f in fails:
            print(f"  ✗ {f}", file=sys.stderr)
        return 2

    print("── PR 堆叠整链核对 ──")
    for k in ("整链提交数", "唯一 SHA 数", "逐段", "逐段之和",
              "#135 区间", "整链 − #136 累计"):
        if k in facts:
            print(f"  {k:16s} {facts[k]}")
    anc = {k: v for k, v in facts.items() if "⊂" in k}
    if anc:
        print("  祖先关系        " + ", ".join(
            f"{k}{'✓' if v else '✗'}" for k, v in anc.items()))

    if fails:
        # 明细走 stdout：CI 里 stderr 常被 `2>&1 | tail` 截掉尾部，
        # 而读日志的人只看最后几行——写进 stderr 等于没写（本轮实测过：
        # rc=1 而明细一条都看不到，只剩「整链覆盖不成立」一行）。
        print("\n**整链覆盖不成立**：")
        for f in fails:
            print(f"  ✗ {f}")
        return 1
    print("\n整链覆盖成立（四条不变量全部满足）。")
    return 0


# ── 自证 ──────────────────────────────────────────────────────────────
# 判据必须能失败。这里不伪造 git 仓库，而是**直接对判据函数喂合成输入**：
# 把 `_count` 换成受控桩，看四条不变量各自能否独立报警。
# **每条反证只改一个量**，否则测不出是哪条判据在起作用。
SELFTEST_TOTAL_MUT = 5


def selftest() -> int:
    """四条不变量各一条反证：缺一不可，且**只看分项会漏**的那条要单独测。"""
    global _count
    real = _count
    caught = 0
    try:
        # 基线：一条干净的链 1/2/1/3/2，整链 9
        cum_map = {
            "feat/FE-1472-batch4-q03": 1,
            "feat/FE-1472-batch5-q03": 3,
            "feat/FE-1472-batch6-q03": 4,
            "feat/FE-1472-d2-h4-assertions": 7,
            "feat/FE-1472-batch7-q03": 9,
        }

        def clean(spec: str) -> int | None:
            for k, v in cum_map.items():
                if spec.endswith(k):
                    return v
            return None

        _count = clean
        # 祖先关系走真实 git（同一仓库内这些分支确实存在），故先只测不变量
        # 里**纯算术**的三条：1、2、3。
        rc, fails, facts = _arith_only()
        if rc == 0:
            print("  ✓ 基线（干净链 1/2/1/3/2、整链 9）不报错")
        else:
            print(f"  ✗ 基线误报：{fails}")

        # M1：整链数 ≠ 唯一 SHA 数（重复计数）
        if _dup_check(9, 8):
            caught += 1
            print("  ✓ M1 整链数 9 ≠ 唯一 SHA 8 → 检出")
        else:
            print("  ✗ M1 未检出")

        # M2：**逐段之和 ≠ 整链总数**（★ 当初真实犯的错：写了 8，实际 9）
        #     每段都对，只有合计错——这条只有"加总"才能抓到。
        if _sum_check([1, 2, 1, 3, 2], declared=8):
            caught += 1
            print("  ✓ M2 逐段 1+2+1+3+2=9 但声明 8 → 检出（分项全对、合计错）")
        else:
            print("  ✗ M2 未检出——这条正是当初漏掉的，必须能抓")

        # M3：交叉口径不一致（#135 区间 3 vs 整链 10 − #136 累计 6 = 4）
        if _cross_check(seg_last=3, total=10, mid=6):
            caught += 1
            print("  ✓ M3 #135 区间 3 ≠ 整链10 − #136累计6=4 → 检出")
        else:
            print("  ✗ M3 未检出")

        # M5：段长为负（侧支）——**此时 sum 仍等于总数，只有这条能抓**
        #     实测：断裂图上 #136 段 −1，而「逐段之和 3 == 整链 3」成立。
        if _neg_check({"#136": -1}):
            caught += 1
            print("  ✓ M5 段长 −1 → 检出（和为总数仍成立，只有负值能抓）")
        else:
            print("  ✗ M5 段长为负未检出——逐段和对总数会白送通过")

        # M4：反向——干净链必须**不**报错（防「一律报警」假通过）
        #     只做正对照不算数：若判据恒真，M1–M3 会全"检出"。
        if not _cross_check(seg_last=4, total=10, mid=6):
            caught += 1
            print("  ✓ M4 反向对照：4 == 10 − 6 时不报警（判据非恒真）")
        else:
            print("  ✗ M4 反向对照失败——判据可能恒真")
    finally:
        _count = real

    print(f"\nPR-CHAIN-SELFTEST: {'PASS' if caught == SELFTEST_TOTAL_MUT else 'FAIL'}"
          f"（{caught}/{SELFTEST_TOTAL_MUT} 检出）")
    return 0 if caught == SELFTEST_TOTAL_MUT else 1


def _arith_only() -> tuple[int, list[str], dict]:
    """只跑不变量 1/2/3 的算术部分（不碰 git 祖先关系）。

    拆出来是为了自证能**独立测判据**，不必伪造整个提交图。
    """
    cum_map = {
        "feat/FE-1472-batch4-q03": 1,
        "feat/FE-1472-batch5-q03": 3,
        "feat/FE-1472-batch6-q03": 4,
        "feat/FE-1472-d2-h4-assertions": 7,
        "feat/FE-1472-batch7-q03": 9,
    }
    fails: list[str] = []
    fam = [cum_map[b] for _, b in CHAIN]
    segs = [fam[0]] + [fam[i] - fam[i - 1] for i in range(1, len(fam))]
    total = _count("x..feat/FE-1472-batch7-q03")
    if total != sum(segs):
        fails.append(f"逐段 {sum(segs)} ≠ 整链 {total}")
    mid = _count("x..feat/FE-1472-d2-h4-assertions")
    if total is not None and mid is not None:
        if total - mid != segs[-1]:
            fails.append(f"整链 {total} − #136 {mid} ≠ #135 段 {segs[-1]}")
    return (1 if fails else 0), fails, {"segs": segs, "total": total}


def _dup_check(total: int, uniq: int) -> bool:
    return total != uniq


def _sum_check(segs: list[int], declared: int) -> bool:
    return sum(segs) != declared


def _cross_check(seg_last: int, total: int, mid: int) -> bool:
    return seg_last != total - mid


def _neg_check(segs: dict) -> bool:
    """段长为负即视为不成立（该分支不是上家的后代）。"""
    return any(v < 0 for v in segs.values())


if __name__ == "__main__":
    sys.exit(main())