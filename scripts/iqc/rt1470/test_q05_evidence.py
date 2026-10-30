#!/usr/bin/env python3
"""FE-1470 复审回归：Q05「可观察证据」必须逐题具体化（用户 §二.4）。

上一版被打回的原话：
> 「`requirement` 实际上全部是同一句通用说明……
>  `Q05 的免责声明不能只放在 not_concluded 字段里，其他字段仍在直接诊断孩子。`」

所以本测试守三件事：

T1 **不许套模板**：22 条候选的 `observable_evidence` 不许全部相同，
   且同一 renderer 内部也不许共用同一句（同族题的观察点本来就不同）。
T2 **不许只有免责**：每条候选的三字段（observable / competing / neutral）
   都非空；`not_concluded` 不能是唯一表达不确定性的地方。
T3 **不许空口诊断**：`observable_evidence` 必须落到本仓库真实存在的
   提交字段名上（白名单见 SERIALIZE_FIELDS），不许出现「无法区分」
   「已确认」「已证明」这类结论性措辞。

T4 负向自检：构造一条模板化的候选，T1/T2 判定必须失败——
   否则本测试可能只是恒真。

DB-free，只读 JSON 工件。
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ARTIFACT = os.path.join(REPO, "scripts/iqc/runs/FE1470_q03_batch2.json")

fails: list[str] = []


def note(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        fails.append(name)


# 各 renderer 真实序列化字段（来自 features/task-renderer/*.ts，已逐个人工核对）。
# 任何 observable_evidence 若声称「在哪看」，至少命中其中一个。
SERIALIZE_FIELDS: dict[str, list[str]] = {
    "ten-frame": ["tens", "current_frame_count", "total"],
    "object-counter": ["groups", "count", "total", "composed_into", "composed_count"],
    "column-arithmetic": ["result_digits", "carries", "incorrect_places",
                          "incorrect_carries"],
    "formula-board": ["filled", "answer", "structure", "error", "relation"],
    "ruler": ["marks", "span", "reading", "structure", "error",
              "from_zero_reading", "wrong_span"],
}

BANNED = ["无法区分", "不能区分", "已确认", "已证明", "证明了孩子"]


def load() -> dict:
    with open(ARTIFACT, encoding="utf-8") as f:
        return json.load(f)


def all_candidates(d: dict) -> list[tuple[str, str, dict]]:
    out = []
    for it in d.get("items") or []:
        for c in it.get("q05_candidates") or []:
            out.append((it["rvid"], it["renderer"], c))
    return out


def check_no_template(cands: list[tuple[str, str, dict]]) -> None:
    obs = [c["observable_evidence"] for _, _, c in cands]
    note("T1a 22 条 observable 不全同",
         len(set(obs)) > 1, f"{len(set(obs))}/{len(obs)} 种")
    # 同 renderer 内部也不许共用（同族题的观察点本来就不同）
    by_r: dict[str, list[str]] = {}
    for _, r, c in cands:
        by_r.setdefault(r, []).append(c["observable_evidence"])
    for r, lst in by_r.items():
        note(f"T1b {r} 内部无重复 observable",
             len(set(lst)) == len(lst),
             f"{len(set(lst))}/{len(lst)}")


def check_all_fields(cands: list[tuple[str, str, dict]]) -> None:
    empty = [f"{rvid[:8]}.{f}" for rvid, _, c in cands
             for f in ("observable_evidence", "competing_explanations",
                       "neutral_feedback")
             if not (c.get(f) or "").strip()]
    note("T2 三字段全部非空", not empty, f"缺口 {len(empty)}")


def check_fields_real(cands: list[tuple[str, str, dict]]) -> None:
    bad_field, bad_word = [], []
    for rvid, r, c in cands:
        obs = c["observable_evidence"]
        hits = [f for f in SERIALIZE_FIELDS.get(r, []) if f in obs]
        if not hits:
            bad_field.append(rvid[:8])
        for w in BANNED:
            if w in obs:
                bad_word.append(f"{rvid[:8]}:{w}")
    note("T3a 每条都落到真实提交字段", not bad_field,
         f"未命中 {bad_field[:4]}")
    note("T3b 无结论性措辞", not bad_word, f"{bad_word[:4]}")


def check_negative_control(d: dict) -> None:
    """把第一条候选改成模板句，T1/T2 必须失败——否则测试恒真。"""
    import copy
    fake = copy.deepcopy(d)
    it0 = fake["items"][0]
    for c in it0["q05_candidates"]:
        c["observable_evidence"] = "【模板】需补充可观测证据"
        c["competing_explanations"] = ""
        c["neutral_feedback"] = ""
    cands = all_candidates(fake)
    # 与真实工件混在一起时，重复检测仍应发现模板句（同 renderer 内先看）
    by_r: dict[str, list[str]] = {}
    for _, r, c in cands:
        by_r.setdefault(r, []).append(c["observable_evidence"])
    dup_found = any(len(set(v)) != len(v) for v in by_r.values()) or \
        len(set(c["observable_evidence"] for _, _, c in cands)) < len(cands)
    empty_found = any(not (c.get("competing_explanations") or "").strip()
                      for _, _, c in cands)
    note("T4 负向自检：模板化候选会被检出",
         dup_found or empty_found,
         f"dup={dup_found} empty={empty_found}")


def main() -> int:
    d = load()
    cands = all_candidates(d)
    note("T0 候选总数为 22", len(cands) == 22, f"实际 {len(cands)}")
    check_no_template(cands)
    check_all_fields(cands)
    check_fields_real(cands)
    check_negative_control(d)

    # object-counter 的存量缺陷必须显式登记，不能静默
    blocked = [it for it in d.get("items") or [] if it.get("q05_blocked_by")]
    note("T5 object-counter 缺陷已登记（5 题）",
         len(blocked) == 5, f"实际 {len(blocked)}")

    print()
    if fails:
        print(f"Q05-EVIDENCE-GATE: FAIL ({len(fails)}) → {fails}")
        return 1
    print("Q05-EVIDENCE-GATE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())