#!/usr/bin/env python3
"""FE-1467 基线降级出处回归（DB-free，确定性）。

保护对象：`baseline_downgrade` 里「211/212 是历史基线数量」这句话的**可核验性**。

为什么需要测：
    终审 §五 要求把 211/212 降级。降级本身不需要代码，但「凭什么说它是历史数」
    需要。若出处只写在文档里、或只由脚本作者手写常量断言，那么历史工件被改动、
    或被悄悄重写时，没人会发现——降级说明会变成一句不可证伪的话。
    本测试锁三件事：
      (a) 出处确实从历史工件读回（不是硬编码）；
      (b) 历史工件自带恒等式成立（四类结论覆盖每一条 published）；
      (c) 工件被篡改时**必须报错**（变异对照：只证明"能读"等于零保护）。

不做：不写库、不跑 scan、不改任何工件。
"""
from __future__ import annotations

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
         prov["historical_published"] == 443 and prov["mapping"] == {
             "Q05_211": "status.REVISION_REQUIRED",
             "Q03_212": "status.UNVERIFIED"},
         f"published={prov['historical_published']} mapping={prov['mapping']}")

    # P2 211/212 确实是 status 枚举里的两个桶，且各自对得上
    st = prov["historical_status_distribution"]
    note("P2 211=REVISION_REQUIRED / 212=UNVERIFIED 与终审引用一致",
         st.get("REVISION_REQUIRED") == 211 and st.get("UNVERIFIED") == 212,
         f"status={st}")

    # P3 恒等式：四类结论之和 == published
    total = sum(st.values())
    note("P3 历史工件恒等式成立（无重叠无遗漏）", total == prov["historical_published"],
         f"sum({total}) == published({prov['historical_published']})")

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
                 "status 合计与 published 对不上时拒绝")
    with_mutated(mutate_drop, "P7 变异：删一类结论必须报错（覆盖不完整检出）",
                 "少一个 status 桶导致合计不足 published")

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
    note("P9 历史工件未被改动（终审 §五：历史报告保持不变）",
         after == base, "前后逐字段一致" if after == base else "工件被改动了")

    print()
    if fails:
        print(f"BASELINE-PROVENANCE-GATE: FAIL ({len(fails)}) — " + "; ".join(fails))
        return 1
    print("BASELINE-PROVENANCE-GATE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())