"""FE-1472｜进度账实核（把「文档里的数字」与「产物 + 并集工件」对上）。

动机：§5.8.5 上一版的三个数字是**按减法外推**的，其中 `Q05_only`
写成「38 + 29 = 67」，而实际它是固定集合归属、一直是 12 且从未被消耗。
这类错误靠人算抓不住，必须由脚本逐条数出来。

本脚本只读，零 DML，不写任何产物；仅打印并对不上时以非零码退出。

用法：
  python scripts/iqc/rt1472/check_progress.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
assert os.path.isdir(os.path.join(REPO, "scripts", "iqc")), f"REPO 层级算错：{REPO}"

UNION = os.path.join(REPO, "scripts/iqc/runs/FE1468_worklist_union.json")
RUNS = os.path.join(REPO, "scripts/iqc/runs")

# 已完成的批次产物（新增批次时在此追加，**不要靠外部传参**，
# 否则「忘了加一个文件」会静默算错完成数）
BATCH_ARTIFACTS = [
    "FE1469_q03_number_input.json",
    "FE1470_q03_batch2.json",
    "FE1471_q03_batch3.json",
    "FE1472_q03_batch4.json",
]

# 文档中声明的数字（改文档时同步改这里，脚本会核对）
EXPECTED = {"union": 224, "in_q03": 212, "in_q05": 209,
            "both": 197, "q03_only": 15, "q05_only": 12}


def main() -> int:
    union = json.load(open(UNION, encoding="utf-8"))
    items = union["items"]
    ids = [i["rvid"] for i in items]

    fails: list[str] = []
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
    per_batch: dict[str, int] = {}
    for fn in BATCH_ARTIFACTS:
        p = os.path.join(RUNS, fn)
        if not os.path.isfile(p):
            fails.append(f"缺少批次产物：{fn}（**缺失即失败，不静默跳过**）")
            continue
        d = json.load(open(p, encoding="utf-8"))
        got = {r["rvid"] for r in d["items"]}
        per_batch[fn] = len(got)
        extra = got - set(ids)
        if extra:
            fails.append(f"{fn} 有 {len(extra)} 题不在并集内（不应发生）")
        # 批次内自重复
        raw = [r["rvid"] for r in d["items"]]
        if len(raw) != len(set(raw)):
            fails.append(f"{fn} 内部有重复 RVID")
        done |= got

    todo_q03 = actual["in_q03"] - len(done & {i["rvid"] for i in items if i["in_Q03"]})
    todo_both = actual["both"] - len(done & {i["rvid"] for i in items if i["in_Q03"] and i["in_Q05"]})

    print("── 集合口径（实测）──")
    for k in ("union", "in_q03", "in_q05", "both", "q03_only", "q05_only"):
        print(f"  {k:10s} {actual[k]:>4}")
    print("\n── 各批完成（去重前）──")
    for fn, n in per_batch.items():
        print(f"  {fn:36s} {n:>3}")
    print(f"\n  去重完成合计: {len(done)}")
    print(f"  Q03 待核验  : {todo_q03}   (in_Q03 {actual['in_q03']} − 已完成 {len(done)})")
    print(f"  both 待核验 : {todo_both}   (both {actual['both']} − 已完成 {len(done)})")

    if fails:
        print("\n**账实不符**：", file=sys.stderr)
        for f in fails:
            print(f"  ✗ {f}", file=sys.stderr)
        return 1
    print("\n账实相符。")
    return 0


if __name__ == "__main__":
    sys.exit(main())