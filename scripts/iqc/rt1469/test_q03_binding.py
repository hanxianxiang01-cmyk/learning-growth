#!/usr/bin/env python3
"""FE-1469 定点回归：核验链的三条纪律不能被后续改动悄悄破坏。

DB-free。锁的是**判定逻辑**，不是某次运行的数字结果——后者会随题库变动，
前者是"结论还能不能用"的判据。

2026-10-21 用户复审 §一.1 要求补齐「结果与输入的绑定」，并说「引用既有
冻结原件和哈希即可」。这里锁住的就是绑定是否真的建立了：
  T1 引用哈希 == 重算哈希 → 不漂移
  T2 引用哈希 ≠ 重算哈希 → 漂移（题目被改过，旧结论作废）
  T3 引用缺失（None）→ 漂移（不能"没原件就当通过"）
  T4 重算缺失（题目已不在库里）→ 漂移
  T5 q05_note 不得越权写成结论（"无法区分"是结论，"尚待验证"是候选）
"""
from __future__ import annotations

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# HERE = <repo>/scripts/iqc/rt1469 → 退三级。
# 2026-10-21：这个坑已经踩过三次（test_baseline_provenance / q03_number_input
# 首版 / 本文件草稿），所以统一在这里 assert 一次。
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
assert os.path.isdir(os.path.join(REPO, "scripts", "iqc")), \
    f"REPO 层级算错：{REPO} 下没有 scripts/iqc"

fails: list[str] = []


def note(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        fails.append(name)


def load():
    p = os.path.join(HERE, "q03_number_input.py")
    spec = importlib.util.spec_from_file_location("q03_1469", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)   # 顶层只定义，不连库
    return m


def main() -> int:
    m = load()

    # T1 相同哈希不漂移
    note("T1 引用值与重算值一致 → 不漂移",
         m.judge_binding("a" * 64, "a" * 64) is False,
         repr(m.judge_binding("a" * 64, "a" * 64)))

    # T2 不同哈希 → 漂移
    note("T2 引用值与重算值不同 → 漂移（题目在快照后被改，旧结论作废）",
         m.judge_binding("a" * 64, "b" * 64) is True)

    # T3/T4 缺失不能算通过
    note("T3 引用哈希缺失 → 漂移（没有冻结原件可引，不得视为通过）",
         m.judge_binding(None, "a" * 64) is True)
    note("T4 重算哈希缺失（题已不在库）→ 漂移",
         m.judge_binding("a" * 64, None) is True)
    note("T4b 两者都缺失 → 漂移（不能 None == None 就算一致）",
         m.judge_binding(None, None) is True)

    # T5 口径：q05 表述不得越权成结论
    out = os.path.join(REPO, "scripts/iqc/runs/FE1469_q03_number_input.json")
    if os.path.exists(out):
        import json
        d = json.load(open(out))
        notes = {i.get("q05_note", "") for i in d["items"]}
        banned = ("无法区分", "不能区分", "已确认", "已证明")
        bad = [n for n in notes if any(b in n for b in banned)]
        note("T5 q05_note 只写候选不写结论（不出现「无法区分/已确认」等断言）",
             not bad, str(bad) if bad else " | ".join(sorted(notes)))
        note("T5b 每处 drift 都有对应 input_binding 哈希，不存在无数可查的结论",
             all(i.get("input_binding", {}).get("audit_input_sha256")
                 or i.get("verdict") == "RVID_NOT_FOUND" for i in d["items"]))
    else:
        note("T5 产物存在（否则无法校核口径）", False, f"缺 {out}")

    print()
    if fails:
        print(f"BINDING-GATE: FAIL ({len(fails)}) → {fails}")
        return 1
    print("BINDING-GATE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())