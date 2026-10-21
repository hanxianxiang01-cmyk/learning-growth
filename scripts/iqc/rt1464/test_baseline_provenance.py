#!/usr/bin/env python3
"""FE-1467 基线降级出处回归（DB-free，确定性）。

保护对象：`baseline_downgrade` 里「211/212 是历史基线数量」这句话的**可核验性**，
以及「443 是 findings 数不是题目数」这个**单位口径**。

为什么需要测：
    终审 §五 要求把 211/212 降级。降级本身不需要代码，但「凭什么说它是历史数」
    需要。若出处只写在文档里、或只由脚本作者手写常量断言，那么历史工件被改动、
    或被悄悄重写时，没人会发现——降级说明会变成一句不可证伪的话。

2026-10-21 复审补正（用户 §二.3）：
    ① 单位口径：443 是 **Findings 条数**，不是 443 道 published 题。本测试断言
       该字段名与单位旁证（resources_discovered / findings_total / layering 合计）。
    ② 能力边界：本测试能支持的是
         - 缺字段、合计不一致会被发现
         - 本次运行没有修改历史文件
       它**不能**发现「两个桶一增一减、总数不变」的篡改。因此本测试同时核对
       已冻结的文件哈希（T-* 项）；没有哈希核对时，报告只能声称「结构一致性
       校验」，不得声称「防历史工件被改」。

本测试现已附哈希冻结：若历史工件内容变化，H1/H2 直接 FAIL。
哈希值不是防篡改机制，只是让"文件被换过"这件事在 CI 里可见。
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
# 本文件在 scripts/iqc/rt1464/ 下，仓库根要退三级（少退一级会变成 scripts/ 下，
# 于是工件路径拼成 scripts/scripts/... —— 这类错只在变异段才暴露，需警惕）。
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
fails: list[str] = []

# 历史工件的冻结哈希（2026-10-21 取自提交 bb39044，终审 §五 要求历史报告保持不变）
FROZEN_SHA256 = {
    "scripts/iqc/runs/FE1464_first_full_report.json":
        "36ad8c4f952a07e38a3efb34479a9d51d6968a78d07e9631d4b26c4e12f20a1f",
    "scripts/iqc/runs/findings_fe1460_225.jsonl":
        "527fa2db92ccc947658827b5d1f321074d2922020e127f903e6fca86537ffda5",
}


def note(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        fails.append(name)


def load_module():
    p = os.path.join(HERE, "rebuild_q05_q03_baseline.py")
    spec = importlib.util.spec_from_file_location("rb1470", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)   # 顶层只定义，不连库
    return m


def main() -> int:
    m = load_module()

    # P1 正常读回
    prov = m.read_historical_provenance()
    note("P1 出处从工件读回（非硬编码常量）",
         prov["historical_published_findings"] == 443 and prov["mapping"] == {
             "Q05_211": "status.REVISION_REQUIRED",
             "Q03_212": "status.UNVERIFIED"},
         f"findings={prov['historical_published_findings']} mapping={prov['mapping']}")

    # P1u 单位口径：443 是 findings 条数，不是题目数（用户 §二.3）
    note("P1u 443 被正确标注为 findings 条数而非 published 题目数",
         "historical_published_findings" in prov
         and "historical_published" not in prov
         and "findings" in prov.get("unit_note", ""),
         prov.get("unit_note", "(缺 unit_note)")[:100])

    # P2 211/212 确实是 status 枚举里的两个桶，且各自对得上
    st = prov["historical_status_distribution"]
    note("P2 211=REVISION_REQUIRED / 212=UNVERIFIED 与终审引用一致",
         st.get("REVISION_REQUIRED") == 211 and st.get("UNVERIFIED") == 212,
         f"status={st}")

    # P3 恒等式：四类结论之和 == findings 条数（不是题目数）
    total = sum(st.values())
    note("P3 findings 状态分桶恒等式成立（无重叠无遗漏）",
         total == prov["historical_published_findings"],
         f"sum({total}) == historical_published_findings("
         f"{prov['historical_published_findings']})")

    # P3s 恒等式的效力边界必须写清楚，避免被当成"RVID 去重覆盖正确"的证明
    note("P3s 已声明恒等式效力边界（不证明 RVID 去重覆盖）",
         "不证明" in prov.get("identity_scope", ""),
         prov.get("identity_scope", "(缺 identity_scope)")[:90])

    # P4 字段自描述：出处必须能指回具体工件与路径，否则读者无法复核
    note("P4 出处含工件路径与 JSON pointer",
         prov["source_artifact"].endswith("FE1464_first_full_report.json")
         and prov["source_path"].startswith("fe1464_first_full_baseline"),
         f"{prov['source_artifact']} #{prov['source_path']}")

    # P5–P7 变异对照：篡改历史工件后必须报错，否则说明校验是空跑
    src = os.path.join(REPO, prov["source_artifact"])
    base = json.load(open(src))
    key = "fe1464_first_full_baseline"

    def with_mutated(mutator, label: str, why: str) -> None:
        tmp = tempfile.mkdtemp(prefix="fe1467_prov_")
        try:
            d = json.loads(json.dumps(base))
            mutator(d[key]["current_published_findings"])
            dst = os.path.join(tmp, "scripts/iqc/runs/FE1464_first_full_report.json")
            os.makedirs(os.path.dirname(dst))
            json.dump(d, open(dst, "w"), ensure_ascii=False)
            try:
                m.read_historical_provenance(repo=tmp)
                ok, detail = False, "篡改后仍通过——校验是空跑"
            except ValueError as e:
                ok, detail = True, str(e)[:90]
            note(label, ok, why if ok else detail)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def mutate_211(c):
        c["status"]["REVISION_REQUIRED"] = 210   # 与终审引用的 211 不符

    def mutate_sum(c):
        c["status"]["PASS_RULES"] = 99           # 破坏恒等式但保留 211/212

    def mutate_drop(c):
        c["status"].pop("REVIEW_REQUIRED")       # 少一类结论

    with_mutated(mutate_211, "P5 变异：改 211→210 必须报错（漂移检出）",
                 "REVISION_REQUIRED 被改后拒绝继续降级")
    with_mutated(mutate_sum, "P6 变异：破坏恒等式必须报错（自相矛盾检出）",
                 "status 合计与 findings 数对不上时拒绝")
    with_mutated(mutate_drop, "P7 变异：删一类结论必须报错（覆盖不完整检出）",
                 "少一个 status 桶导致合计不足 findings 数")

    # P7b **能力边界自证**：本测试到底查不出什么。
    #
    # 分两种"一增一减、总数不变"的篡改，如实记录实际能力：
    #   (a) 动到 211/212 自身 → **可**检出（因为对这两个值做了精确锚定）
    #   (b) 只动其它两个桶（PASS_RULES / REVIEW_REQUIRED）→ **查不出**
    #       总数仍 443、211/212 仍正确、字段齐全——这正是用户 §二.3 指出的盲区。
    # (b) 由 H 哈希冻结兜底，而不是靠恒等式。
    def _swap_case(mutator) -> bool:
        """返回 True 表示该篡改被检出。"""
        tmp = tempfile.mkdtemp(prefix="fe1467_swap_")
        try:
            d = json.loads(json.dumps(base))
            mutator(d[key]["current_published_findings"])
            dst = os.path.join(tmp, "scripts/iqc/runs/FE1464_first_full_report.json")
            os.makedirs(os.path.dirname(dst))
            json.dump(d, open(dst, "w"), ensure_ascii=False)
            try:
                m.read_historical_provenance(repo=tmp)
                return False
            except ValueError:
                return True
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def swap_anchored(c):
        c["status"]["REVISION_REQUIRED"] -= 1
        c["status"]["UNVERIFIED"] += 1          # 动到锚定值

    def swap_unanchored(c):
        c["status"]["PASS_RULES"] -= 1
        c["status"]["REVIEW_REQUIRED"] += 1     # 避开 211/212，总数不变

    anchored_detected = _swap_case(swap_anchored)
    unanchored_detected = _swap_case(swap_unanchored)

    note("P7b-1 篡改锚定值(211/212)时可检出（精确锚定的作用）",
         anchored_detected is True,
         "命中 drift 检查" if anchored_detected else "漏检——锚定失效")
    note("P7b-2 已知盲区：仅动其它桶的一增一减**查不出**（须靠哈希兜底）",
         unanchored_detected is False,
         "确认不可检出——故报告只能称『结构一致性校验』，不得称『防历史工件被改』"
         if not unanchored_detected else
         "意外可检出——需复核：是否新增了全桶锚定")

    # P8 缺工件必须报错，不能静默返回空/默认值
    empty = tempfile.mkdtemp(prefix="fe1467_empty_")
    try:
        try:
            m.read_historical_provenance(repo=empty)
            ok, detail = False, "工件缺失却未报错"
        except ValueError as e:
            ok, detail = True, str(e)[:90]
        note("P8 工件缺失必须显式报错（不静默降级）", ok,
             "缺件时拒绝产出降级说明" if ok else detail)
    finally:
        shutil.rmtree(empty, ignore_errors=True)

    # P9 只读纪律：本测试与其被测函数都不得改写历史工件
    after = json.load(open(src))
    note("P9 历史工件未被本次运行改动（终审 §五：历史报告保持不变）",
         after == base, "前后逐字段一致" if after == base else "工件被改动了")

    # H1/H2 哈希冻结：这是"文件被换过"唯一能被 CI 看见的证据。
    # P7b 已证明结构校验查不出一增一减，故必须有这一层。
    for rel, want in FROZEN_SHA256.items():
        p = os.path.join(REPO, rel)
        got = hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else "(缺件)"
        note(f"H 历史工件哈希冻结 {os.path.basename(rel)}", got == want,
             "未变" if got == want else f"got={got[:16]}… want={want[:16]}…")

    print()
    if fails:
        print(f"BASELINE-PROVENANCE-GATE: FAIL ({len(fails)}) — " + "; ".join(fails))
        return 1
    print("BASELINE-PROVENANCE-GATE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())