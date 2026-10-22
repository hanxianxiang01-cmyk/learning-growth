"""FE-1472｜Q03 第四批：**先冻结选题集合，再逐题核验**。

复审（2026-10-22 §四）硬要求：
  > 先冻结实际选题集合，再逐题核验。记录完整 RVID、输入来源、题干与必要配置、
  > 输入哈希；扩样时追加原因，不补造历史选样名单。约 20 题是批次尺度，
  > 不是必须凑齐的指标。

所以本脚本分两段并可单独执行：

  python freeze_batch4.py          # 只做选样并写 quota_list 工件（不核验）
  python freeze_batch4.py --verify # 核验：要求 quota_list 已存在

第三批的教训（初始选样名单未落盘，导致「29 实核 vs 20 计划」的差额只能靠
事后推断解释）在这里被结构性地消除：**没有 quota_list 就不允许核验**。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
assert os.path.isdir(os.path.join(REPO, "scripts", "iqc")), \
    f"REPO 层级算错：{REPO}"

QUOTA_PATH = os.path.join(HERE, "batch4_quota_list.json")

# ── 选样规则（写死在此，避免"事后看起来像随便挑的"）────────────────────
# 复审 §四：不永久排除时钟、方向格、估算或图形计数题；有明确契约、输入完整
# 就可以核验；只有同类代表样本的，不替其他 RVID 自动给通过。
SELECTION_RULE = (
    "从 numeric_judge ∩ both 剩余候选中取约 20 题，优先**本批之前从未覆盖的 "
    "renderer**（第三批 29 题里 27 是 legacy:*，V2 只覆盖 bar-model 2 题）。"
    "同一 renderer 最多取 3 题（够看同族一致性，又不把名额吃光）。"
    "四类曾被怀疑「不可核验」的 renderer（clock / direction-grid / "
    "estimation-canvas / shape-gallery）各取 2–3 题，用实际题面判断契约是否完整，"
    "不因类别名称先行排除。"
)

# 每类取几题：显式写出来，便于复核「为什么是这 20 题」
QUOTA_BY_RENDERER = {
    "clock": 3,
    "direction-grid": 3,
    "estimation-canvas": 3,
    "shape-gallery": 3,
    "grouping-board": 2,
    "column-arithmetic": 2,
    "number-line": 2,
    "object-counter": 2,
}

NOT_SELECTED_WHY = {
    "legacy:direct": ("纯数字输入、无表征；本批优先补 V2 renderer 覆盖，"
                      "legacy:direct 已在第二批核过 5 题，样本足够"),
    "legacy:number-line": ("同 legacy 族，第三批已核 4 题（含 DEF-D4 相关）；"
                           "本批用 V2 number-line 替代，验证 V2 配置是否同样只记终点"),
    "legacy:objects": "第三批已核 4 题（DEF-D3），本批换 object-counter 看 V2 侧差异",
    "legacy:bar-model": "第三批已核 14 题（DEF-D1/D2 全部来源），本批不必再加",
    "bar-model": ("第二批与第三批共核 4 题；本批名额让给未覆盖的 renderer，"
                  "同族结论已有代表性样本"),
    "ruler": "第二批已核 4 题（两端刻度差），契约已确认可独立推导",
    "ten-frame": "第二批已核 5 题（initial_count + 题面再放 N），结论稳定",
    "money-board": "第二批已核 5 题",
    "formula-board": "第二批已核 3 题",
    "array-board": "第二批已核 5 题",
    "sorting-board": "第二批已核（sequence_order 路径）",
    "place-value": "第二批已核（digit_config 路径）",
    "pattern-board": "第二批已核",
    "shape-canvas": "第二批已核 10 题（含容差类）",
    "number-input": "首批已核 6 题",
}


def _sha(obj) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _load_pool() -> dict[str, dict]:
    """候选池 = 并集工件 − 前三批已核 RVID（按 RVID 计一次）。"""
    u = json.load(open(os.path.join(REPO, "scripts/iqc/runs/FE1468_worklist_union.json"),
                       encoding="utf-8"))
    done: set[str] = set()
    for f in ("FE1469_q03_number_input.json", "FE1470_q03_batch2.json",
              "FE1471_q03_batch3.json"):
        j = json.load(open(os.path.join(REPO, "scripts/iqc/runs", f), encoding="utf-8"))
        done |= {x["rvid"] for x in j["items"]}
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
    for rend, n in QUOTA_BY_RENDERER.items():
        cand = sorted(by_renderer.get(rend, []))
        assert len(cand) >= n, f"{rend} 候选只有 {len(cand)} 题，不足 {n}"
        picked.extend(cand[:n])

    # 多取几题作为「核验时发现缺契约」的替补，但**先全部落盘**
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
            "solve_path": pool[rid]["solve_path"],
            "answer_shape": pool[rid]["answer_shape"],
            "stem": d["stem"],
            "answer_raw": d["answer"],
            "goal": d["goal"],
            "ui_schema": d["ui_schema"],
            "error_models": d["error_models"],
            "stem_sha256": _sha(d["stem"]),
            "ui_schema_sha256": _sha(d["ui_schema"]),
        })

    out = {
        "title": "FE-1472｜Q03 第四批选题集合（**先冻结再核验**）",
        "generated_at": None,
        "why": ("第三批的「29 实核 vs 约 20 计划」差额只能事后推断，根因是初始选样"
                "名单从未落盘。本批把选题集合**先**写进工件，核验只针对这份名单。"),
        "selection_rule": SELECTION_RULE,
        "quota_by_renderer": QUOTA_BY_RENDERER,
        "not_selected_why": NOT_SELECTED_WHY,
        "pool_size": len(pool),
        "quota_n": len(items),
        "quota": [i["rvid"] for i in items],
        "items": items,
    }
    from datetime import datetime, timezone
    out["generated_at"] = datetime.now(timezone.utc).isoformat()
    json.dump(out, open(QUOTA_PATH, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"已冻结选题集合：{len(items)} 题 -> {os.path.relpath(QUOTA_PATH, REPO)}")
    from collections import Counter
    print("  renderer:", dict(Counter(i["renderer"] for i in items)))
    return out


def verify() -> None:
    if not os.path.exists(QUOTA_PATH):
        print("未找到 quota_list——必须先运行 `freeze_batch4.py` 冻结选题集合。",
              file=sys.stderr)
        print("第三批的教训：没有先落盘的选样名单，差额就无法自证。", file=sys.stderr)
        sys.exit(2)
    q = json.load(open(QUOTA_PATH, encoding="utf-8"))
    print(f"quota_list：{q['quota_n']} 题（{os.path.relpath(QUOTA_PATH, REPO)}）")
    print("核验入口尚未接入：本脚本当前只负责「先冻结」这一步。")
    print("下一批核验模块将直接读取 batch4_quota_list.json，不再重新选样。")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if a.verify:
        verify()
    else:
        freeze()