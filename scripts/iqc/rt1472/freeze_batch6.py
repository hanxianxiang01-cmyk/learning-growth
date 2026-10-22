"""FE-1472 第六批｜**先冻结选题集合，再逐题核验**（沿用第四/五批结构）。

## 本批为什么换维度

第五批的独立性复核（`check_independence.py`）实测得出一个结构性事实：

    已完成 95 题的 semantic_family **全部是 numeric_judge**；
    construct_constraint 54 题 **一题未核**。

所以本批不再在 numeric_judge 里加量（那里还剩 55 题），而是**首次开
construct_constraint 这一整族**——按用户口径「续批应优先补未覆盖的族，
而不是继续在同族里加量」。

## 名额为什么按 solve_path 而不是 renderer

该族内 renderer 与 solve_path 不是一一对应：

    digit_config        {place-value: 9}
    geometry_constraint {shape-canvas: 9}
    numeric_exact       {money-board: 9, array-board: 8, pattern-board: 1}
    sequence_order      {pattern-board: 9, sorting-board: 9}

按 renderer 分名额会让 pattern-board 被切成两半（numeric_exact 1 + sequence_order 9），
统计上看不出覆盖了什么。按 **solve_path** 分名额才能保证「每种求解形态都被核到」。

## 本批的独立性要求（比第五批更严）

第五批的教训：`derivation.expr` 里出现题干没有的数字，就说明推导可能读了 config。
该族题面常常**故意不给那两个数**（例：「位值卡片[5,8]已经准备好」），
因此本批对每题记录 `input_basis` 时必须写明：
`题面给了什么 / config 给了什么 / 哪些数只能来自 config`。

用法：
  export DATABASE_URL="$(security find-generic-password -s iqc-database-url -w)"
  python scripts/iqc/rt1472/freeze_batch6.py           # 选样并写 quota_list
  python scripts/iqc/rt1472/freeze_batch6.py --verify  # 只看已有清单
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
assert os.path.isdir(os.path.join(REPO, "scripts", "iqc")), \
    f"REPO 层级算错：{REPO}"

QUOTA_PATH = os.path.join(HERE, "batch6_quota_list.json")

# 已核批次：**五批**，95 题
DONE_ARTIFACTS = (
    "FE1469_q03_number_input.json",
    "FE1470_q03_batch2.json",
    "FE1471_q03_batch3.json",
    "FE1472_q03_batch4.json",
    "FE1472_q03_batch5.json",
)

SOLVE_PATHS = ("digit_config", "geometry_constraint", "numeric_exact", "sequence_order")

SELECTION_RULE = (
    "候选池 = 并集 224 − 已核 95 = **129**；本批**只取 construct_constraint** "
    "（54 题，其中 both 47 / Q03_only 7）。理由：`check_independence.py` 实测"
    "已完成 95 题的 semantic_family 全部是 numeric_judge，construct_constraint "
    "**0 题完成**——「95/212」不能读作「各类型题都验过」。"
    "名额按 **solve_path** 分配而非 renderer：该族内 renderer 与 solve_path "
    "不一一对应（pattern-board 同时属于 numeric_exact 与 sequence_order），"
    "按 renderer 分会看不出覆盖了什么。四类各取 5 题，共 20。"
    "**不因「难核」排除任何一类**：geometry_constraint 与 digit_config 在 "
    "numeric_judge 批里从未出现，正是本批要验的对象。"
)

# 每类取 5 题。池内实际数：digit_config 9 / geometry_constraint 9 /
# numeric_exact 18 / sequence_order 18。
QUOTA_BY_SOLVE_PATH = {
    "digit_config": 5,
    "geometry_constraint": 5,
    "numeric_exact": 5,
    "sequence_order": 5,
}

# 本批刻意的取样偏好：优先取 both（两处待办都要），并让 renderer 尽量分散
NOT_SELECTED_WHY = {
    "numeric_judge": (
        "本族已核 95/169，剩余 55 题。本批刻意**不加量**——"
        "同一族内继续抽样边际信息量低；先把 0 覆盖的族补上。"
    ),
    "open_estimate": (
        "全量仅 1 题，且属估算类（答案非唯一）。单列待定，不与构造类混批。"
    ),
}


def _sha(obj) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _done_rvids() -> set[str]:
    done: set[str] = set()
    for f in DONE_ARTIFACTS:
        p = os.path.join(REPO, "scripts/iqc/runs", f)
        if not os.path.exists(p):
            print(f"缺少已核批次产物：{f}（不能跳过——会重复核验）", file=sys.stderr)
            sys.exit(2)
        j = json.load(open(p, encoding="utf-8"))
        done |= {x["rvid"] for x in j["items"]}
    return done


def _load_pool() -> dict[str, dict]:
    u = json.load(open(os.path.join(REPO, "scripts/iqc/runs/FE1468_worklist_union.json"),
                       encoding="utf-8"))
    done = _done_rvids()
    pool = {}
    for x in u["items"]:
        if x["rvid"] in done:
            continue
        if x["semantic_family"] != "construct_constraint":
            continue
        pool[x["rvid"]] = x
    return pool


def _fetch(ids: list[str]) -> dict[str, dict]:
    import psycopg
    db = os.environ.get("DATABASE_URL")
    if not db:
        print("缺少 DATABASE_URL（只读账号即可）", file=sys.stderr)
        sys.exit(2)
    with psycopg.connect(db) as conn:       # 只读，零 DML 路径
        rows = conn.execute(
            "select resource_version_id::text, content->>'stem', "
            "content->>'answer', content->>'goal', ui_schema, error_models "
            "from resource_version where resource_version_id = any(%s::uuid[])",
            (ids,)).fetchall()
    return {r[0]: {"stem": r[1], "answer": r[2], "goal": r[3],
                   "ui_schema": r[4], "error_models": r[5]} for r in rows}


def freeze() -> dict:
    pool = _load_pool()
    if os.path.exists(QUOTA_PATH):
        old = json.load(open(QUOTA_PATH, encoding="utf-8"))
        print(f"quota_list 已存在（{old['quota_n']} 题），不覆盖。"
              "如需重选，请先人工删除该文件。")
        return old

    by_path: dict[str, list[dict]] = {}
    for x in pool.values():
        by_path.setdefault(x.get("solve_path") or "UNKNOWN", []).append(x)

    picked: list[dict] = []
    picks_log = []
    for sp, n in QUOTA_BY_SOLVE_PATH.items():
        cand = sorted(by_path.get(sp, []), key=lambda x: x["rvid"])
        if len(cand) < n:
            print(f"{sp} 候选只有 {len(cand)} 题，不足 {n}", file=sys.stderr)
            sys.exit(2)
        # 优先 both（两处待办都覆盖），再按 rvid 稳定排序；
        # 同优先级内先取 renderer 尚未出现过的，使覆盖面更分散。
        both_first = sorted(cand, key=lambda x: (x["priority"] != "both", x["rvid"]))
        chosen, seen_rend = [], set()
        for x in both_first:
            if len(chosen) >= n:
                break
            if x["renderer"] not in seen_rend:
                chosen.append(x)
                seen_rend.add(x["renderer"])
        for x in both_first:
            if len(chosen) >= n:
                break
            if x not in chosen:
                chosen.append(x)
        picked.extend(chosen)
        picks_log.append({
            "solve_path": sp, "pool_n": len(cand), "picked_n": len(chosen),
            "picked": [x["rvid"] for x in chosen],
            "renderers": sorted({x["renderer"] for x in chosen}),
        })

    if len({x["rvid"] for x in picked}) != len(picked):
        print("选题出现重复 RVID", file=sys.stderr)
        sys.exit(2)

    ids = sorted({x["rvid"] for x in picked})
    data = _fetch(ids)
    by_id = {x["rvid"]: x for x in picked}

    items = []
    for rid in ids:
        d = data.get(rid)
        if not d:
            print(f"{rid} 在库里取不到", file=sys.stderr)
            sys.exit(2)
        x = by_id[rid]
        items.append({
            "rvid": rid,
            "title": x.get("title"),
            "renderer": x["renderer"],
            "ability_id": x.get("ability_id"),
            "solve_path": x.get("solve_path"),
            "answer_shape": x.get("answer_shape"),
            "priority": x.get("priority"),
            "stem": d["stem"],
            "answer_raw": d["answer"],
            "goal": d["goal"],
            "ui_schema": d["ui_schema"],
            "error_models": d["error_models"],
            "stem_sha256": _sha(d["stem"]),
            "ui_schema_sha256": _sha(d["ui_schema"]),
        })

    out = {
        "title": "FE-1472 第六批｜Q03 选题集合（construct_constraint 首次开族）",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "why": ("第五批独立性复核实测：已完成 95 题全部是 numeric_judge，"
                "construct_constraint 0 题完成。本批补这一整族，"
                "名额按 solve_path 分配而非 renderer。"),
        "selection_rule": SELECTION_RULE,
        "quota_by_solve_path": QUOTA_BY_SOLVE_PATH,
        "picks_log": picks_log,
        "not_selected_why": NOT_SELECTED_WHY,
        "pool_size": len(pool),
        "quota_n": len(items),
        "quota": [i["rvid"] for i in items],
        "items": items,
    }
    json.dump(out, open(QUOTA_PATH, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"已冻结选题集合：{len(items)} 题 -> {os.path.relpath(QUOTA_PATH, REPO)}")
    from collections import Counter
    print("  solve_path:", dict(Counter(i["solve_path"] for i in items)))
    print("  renderer  :", dict(Counter(i["renderer"] for i in items)))
    print(f"  候选池（construct_constraint 全族）：{len(pool)}")
    return out


def verify() -> None:
    if not os.path.exists(QUOTA_PATH):
        print("未找到 batch6_quota_list.json——必须先冻结选题集合。", file=sys.stderr)
        sys.exit(2)
    q = json.load(open(QUOTA_PATH, encoding="utf-8"))
    print(f"quota_list：{q['quota_n']} 题（{os.path.relpath(QUOTA_PATH, REPO)}）")
    print(f"候选池 {q['pool_size']}；逐 solve_path 名额：{q['quota_by_solve_path']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if a.verify:
        verify()
    else:
        freeze()