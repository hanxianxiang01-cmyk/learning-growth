"""FE-1472 第五批｜**先冻结选题集合，再逐题核验**（沿用第四批结构）。

第四批的 `freeze_batch4.py` 已经消除了「额定 vs 实核」差额无法自证的问题，
本批沿用同一结构，只换两处：

  1. 候选池 = 并集 − **四批**已核（前四批 75 题）；
  2. 选题规则改为「按 renderer 的**核验成熟度**分配名额」——
     前四批有 6 类 renderer 从未在 V2 配置下核过（ruler / ten-frame /
     grouping-board 等），本批优先补这些；已核过的同类只做同族一致性复查。

用法：
  export DATABASE_URL="$(cat /tmp/u.txt)"
  python scripts/iqc/rt1472/freeze_batch5.py          # 只选样并写 quota_list
  python scripts/iqc/rt1472/freeze_batch5.py --verify # 只显示已有清单
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

QUOTA_PATH = os.path.join(HERE, "batch5_quota_list.json")

# ── 已核批次（**四批**，第四批 20 题）─────────────────────────────────────
DONE_ARTIFACTS = (
    "FE1469_q03_number_input.json",
    "FE1470_q03_batch2.json",
    "FE1471_q03_batch3.json",
    "FE1472_q03_batch4.json",
)

# ── 选样规则 ──────────────────────────────────────────────────────────────
SELECTION_RULE = (
    "候选池 = 并集 224 − 前四批已核 75 = **149**；本批只取 "
    "priority==both 且 semantic_family==numeric_judge 的 75 题（数值判定类，"
    "独立推导可落成纯算术表达式）。"
    "按「该 renderer 在 V2 配置下是否核过」分配名额："
    "ruler / ten-frame / grouping-board 三类**全取或半数取**（前四批只核过 "
    "legacy 同族，V2 配置字段是否被组件真正读取尚未验）；"
    "bar-model 取 4（第三批只核 2 题且均为 legacy:bar-model，V2 的 "
    "max_blocks 与答案关系未验）；"
    "number-line 取 3（第四批核 2 题，本轮补 jump_count=1 的题看考点是否空转）；"
    "legacy:direct 取 2（无 config，纯题面解析，抽样看阅读理解型的题面是否可独立推导）。"
    "**不因类别名称先行排除**：clock / direction-grid / estimation-canvas / "
    "shape-gallery 已在第四批各核 3 题，结论稳定，本批名额让给未覆盖者。"
)

# 每类取几题：显式写出，便于复核「为什么是这 20 题」
QUOTA_BY_RENDERER = {
    "ruler": 4,            # 池内剩 4，全取
    "ten-frame": 4,        # 池内剩 4，全取
    "bar-model": 4,        # 池内剩 8，取半数
    "grouping-board": 3,   # 池内剩 6，取半数
    "number-line": 3,      # 池内剩 6，取半数
    "legacy:direct": 2,    # 池内剩 10，抽样
}

NOT_SELECTED_WHY = {
    "clock": "第四批已核 3 题（CONFLICT 同值错法已登记），结论稳定，本批不重复",
    "direction-grid": "第四批已核 3 题（编码契约 r*cols+c 三题自证），本批不重复",
    "estimation-canvas": "第四批已核 3 题（严格相等判分已更正），本批不重复",
    "shape-gallery": "第四批已核 3 题（按 kind 精确匹配已确认），本批不重复",
    "column-arithmetic": "第二批核 3 + 第四批核 2，进位/退位两支已覆盖",
    "object-counter": "第二批核 5 + 第四批核 2，config 给数与 expected 给数两支已覆盖",
    "legacy:bar-model": "第三批核 14 题（DEF-D1/D2 全部来源），本批换 V2 bar-model 看差异",
    "legacy:number-line": "第三批核 4 题（DEF-D4 来源），本批换 V2 number-line 看 jumps 字段",
    "legacy:objects": "第三批核 4 题（DEF-D3），本批不重复",
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
            print(f"缺少已核批次产物：{f}（**不能跳过**——会重复核验）",
                  file=sys.stderr)
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
        if x["priority"] != "both" or x["semantic_family"] != "numeric_judge":
            continue
        pool[x["rvid"]] = x
    return pool


def _fetch(ids: list[str]) -> dict[str, dict]:
    import psycopg
    db = os.environ.get("DATABASE_URL")
    if not db:
        print("缺少 DATABASE_URL（只读账号即可）", file=sys.stderr)
        sys.exit(2)
    with psycopg.connect(db) as conn:      # 只读，零 DML 路径
        rows = conn.execute(
            "select resource_version_id::text, content->>'stem', "
            "content->>'answer', content->>'goal', ui_schema, error_models, "
            "task_type from resource_version "
            "where resource_version_id = any(%s::uuid[])", (ids,)).fetchall()
    return {r[0]: {"stem": r[1], "answer": r[2], "goal": r[3],
                   "ui_schema": r[4], "error_models": r[5],
                   "task_type": r[6]} for r in rows}


def freeze() -> dict:
    pool = _load_pool()
    if os.path.exists(QUOTA_PATH):
        old = json.load(open(QUOTA_PATH, encoding="utf-8"))
        print(f"quota_list 已存在（{len(old['quota'])} 题），不覆盖。"
              "如需重选，请先人工删除该文件。")
        return old

    by_renderer: dict[str, list[str]] = {}
    for rid, x in pool.items():
        by_renderer.setdefault(x["renderer"], []).append(rid)

    picked: list[str] = []
    picks_log = []
    for rend, n in QUOTA_BY_RENDERER.items():
        cand = sorted(by_renderer.get(rend, []))
        assert len(cand) >= n, f"{rend} 候选只有 {len(cand)} 题，不足 {n}"
        chosen = cand[:n]
        picked.extend(chosen)
        picks_log.append({"renderer": rend, "pool_n": len(cand),
                          "picked_n": len(chosen), "picked": chosen})

    picked = sorted(set(picked))
    data = _fetch(picked)

    items = []
    for rid in picked:
        d = data.get(rid)
        assert d, f"{rid} 在库里取不到"
        items.append({
            "rvid": rid,
            "title": pool[rid]["title"],
            "renderer": pool[rid]["renderer"],
            "ability_id": pool[rid]["ability_id"],
            "solve_path": pool[rid].get("solve_path"),
            "answer_shape": pool[rid].get("answer_shape"),
            "stem": d["stem"],
            "answer_raw": d["answer"],
            "goal": d["goal"],
            "ui_schema": d["ui_schema"],
            "error_models": d["error_models"],
            "stem_sha256": _sha(d["stem"]),
            "ui_schema_sha256": _sha(d["ui_schema"]),
        })

    out = {
        "title": "FE-1472 第五批｜Q03 选题集合（**先冻结再核验**）",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "why": ("第四批用「先冻结」消除了额定/实核差额；本批沿用。"
                "名额按「该 renderer 在 V2 配置下是否核过」分配，"
                "而不是按类别名称排除。"),
        "selection_rule": SELECTION_RULE,
        "quota_by_renderer": QUOTA_BY_RENDERER,
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
    print("  renderer:", dict(Counter(i["renderer"] for i in items)))
    print(f"  候选池（both ∩ numeric_judge，已排除四批 75 题）：{len(pool)}")
    return out


def verify() -> None:
    if not os.path.exists(QUOTA_PATH):
        print("未找到 batch5_quota_list.json——必须先冻结选题集合。", file=sys.stderr)
        sys.exit(2)
    q = json.load(open(QUOTA_PATH, encoding="utf-8"))
    print(f"quota_list：{q['quota_n']} 题（{os.path.relpath(QUOTA_PATH, REPO)}）")
    print(f"候选池 {q['pool_size']}；逐 renderer 名额：{q['quota_by_renderer']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if a.verify:
        verify()
    else:
        freeze()