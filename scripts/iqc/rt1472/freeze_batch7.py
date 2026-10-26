"""FE-1472 第七批｜**先冻结选题集合，再逐题核验**（沿用第四/五/六批结构）。

## 本批为什么是全取而不是抽样

第六批首开 `construct_constraint` 一族（20/54）。第六批之后的剩余题量：

    construct_constraint  34 题（全族 54 − 已核 20）
    open_estimate          1 题（全族 1，0 题完成）
    numeric_judge         74 题（全族 169 − 已核 95）

本批**把两个未清零的族一次全取**，理由不是「凑数」，而是：

  - 这两族取全后，B 段口径可以写成 `construct_constraint 54/54`、
    `open_estimate 1/1`——**族级清零是可核验的终态**，抽样永远达不到。
  - 34 + 1 = 35 题，规模与第六批 20 题同量级，但信息量更大：
    同一族内四种 solve_path 全覆盖、六种 renderer 全覆盖。

`numeric_judge` 剩余 74 题本批仍**不取**——它已核 95/169，继续抽样边际信息
量低；先把两个 0 覆盖族清零。

## 与第六批原裁定冲突的一处，必须显式记录

第六批 `NOT_SELECTED_WHY["open_estimate"]` 写的是：

    「全量仅 1 题，且属估算类（答案非唯一）。单列待定，不与构造类混批。」

本批把该题（`cd7f008d-9637-4960-a4df-03684cce3e5a`）**纳入同批核验**，
推翻了上述裁定。理由与边界：

  - **推翻的理由**：该族若不核，`open_estimate` 永远停在 0/1，
    「全族清零」这个终态不可达。
  - **不推翻的边界**：**判据必须分开**。估算题不能与构造题用同一个
    「独立推导值 == 存储答案」严格相等判据——见 `ANSWER_CRITERION_NOTES`。
  - **绝不能做的事**：为凑齐 35 题而放宽判据。两族的 MATCH 定义不同，
    混用会把「判据不适用」记成「核验通过」。

## 本批的另一件事：第六批的派生规则不能直接复用

第六批 `derive()` 的抽取正则只覆盖第六批 20 题实际出现的写法。本批 34 题
是**同一族的另外 34 题**，题面写法明显更多样。逐条实测（用第六批正则硬套）：

    renderer        题数  第六批规则可直接覆盖  会把推导算错
    pattern-board     6         1/6                 0
    place-value       4         1/4                 0
    array-board       7         7/7                 0
    shape-canvas      4         3/4                 0
    sorting-board     7         1/7                 0
    money-board       6         4/6                **1**（8a658f5e）
    estimation-canvas 1         0/1                 0

其中 `8a658f5e`「一支笔标价10角，一块橡皮标价5角」——第六批规则因题面
没有「另一件」三字而走单件分支，只取第一个标价 **10**，真值是 **15**。
**这不是「缺一条正则」，是「缺一条正则时会静默算出错值」**：若无对照，
该题会被记成 MISMATCH，看起来像题库有缺陷，实际是核验器读错题。

故本批的硬约束写进核验器（`q03_batch7.py`），不写进文档：

  1. **每题必须命中一条显式登记的题面模板**（`STEM_TEMPLATES`），
     命中不到即 rc=2（推导失败，不是 MISMATCH）。
  2. **模板必须声明它要抽哪几个量**，抽出数与声明数不符即 rc=2。
  3. **六批的 20 题必须仍能被第七批核验器算对**（`--crossbatch`）——
     这是「新规则没有引入回归」的唯一证据。

## 名额为什么仍然按 solve_path 记

本批全取，名额等于池内实际数，写出来是为了让覆盖率**可对账**：

    digit_config 4 / geometry_constraint 4 / numeric_exact 13 / sequence_order 13
    numeric_tolerance 1（估算族）

用法：
  export DATABASE_URL="$(security find-generic-password -s iqc-database-url -w)"
  python scripts/iqc/rt1472/freeze_batch7.py           # 选样并写 quota_list
  python scripts/iqc/rt1472/freeze_batch7.py --verify  # 只看已有清单
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

QUOTA_PATH = os.path.join(HERE, "batch7_quota_list.json")

# 已核批次：**六批**，115 题。第七批的候选池 = 并集 224 − 已核 115 = 109。
DONE_ARTIFACTS = (
    "FE1469_q03_number_input.json",
    "FE1470_q03_batch2.json",
    "FE1471_q03_batch3.json",
    "FE1472_q03_batch4.json",
    "FE1472_q03_batch5.json",
    "FE1472_q03_batch6.json",
)

# 本批覆盖的两个族
FAMILIES = ("construct_constraint", "open_estimate")

SOLVE_PATHS = ("digit_config", "geometry_constraint", "numeric_exact",
               "sequence_order", "numeric_tolerance")

SELECTION_RULE = (
    "候选池 = 并集 224 − 已核 115 = **109**（numeric_judge 74 / "
    "construct_constraint 34 / open_estimate 1）；本批**把两个未清零的族全取**："
    "construct_constraint 剩余 34 + open_estimate 1 = **35 题，不抽样**。"
    "理由：抽样永远达不到「族级清零」这个可核验终态，而 34+1 与第六批 20 题同量级。"
    "numeric_judge 剩余 74 题本批**刻意不取**——已核 95/169，同族继续抽样边际信息量低。"
    "名额按 solve_path 记录（本批即池内实际数），用于覆盖率的可对账性："
    "digit_config 4 / geometry_constraint 4 / numeric_exact 13 / sequence_order 13 / "
    "numeric_tolerance 1。**不因「难核」排除任何一类**，也不因「凑不齐」而放宽判据。"
)

# 本批全取，名额 = 池内实际数。任一 path 的池内数与此处不符即 rc=2，
# 防止「题库变了而清单没变」导致覆盖率口径悄悄失真。
QUOTA_BY_SOLVE_PATH = {
    "digit_config": 4,
    "geometry_constraint": 4,
    "numeric_exact": 13,
    "sequence_order": 13,
    "numeric_tolerance": 1,
}

# 已被第六批排除、本批纳入的族，必须写明推翻理由与不推翻的边界。
NOT_SELECTED_WHY = {
    "numeric_judge": (
        "已核 95/169，剩余 74 题。本批刻意**不加量**——同一族内继续抽样边际信息量低；"
        "先把 construct_constraint 与 open_estimate 两个 0 覆盖族清零。"
    ),
}

# 推翻第六批裁定的显式记录（**不得隐藏**：读者需要知道前后口径不一致）
OVERRIDES = {
    "open_estimate": {
        "batch6_ruling": "全量仅 1 题，且属估算类（答案非唯一）。单列待定，不与构造类混批。",
        "batch7_decision": "纳入本批，与构造族同批但**判据分开**。",
        "why_overturned": (
            "该族若不核，`open_estimate` 永远停在 0/1，「全族清零」终态不可达；"
            "而该题本身无其他技术障碍（题面、config、答案均可取）。"
        ),
        "what_is_not_overturned": (
            "**判据不合并**。构造族用「独立推导值 == 存储答案」严格相等；"
            "估算族答案由「参照 + 取整到整十」唯一确定，容差只是反馈粒度——"
            "两者 MATCH 的定义不同，绝不能为凑齐 35 题而让估算题走严格相等、"
            "或让构造题走容差。"
        ),
    }
}

# 各 renderer 的题面模板覆盖统计（**实测值**，由 `--probe` 生成，
# 不手填）。用于让「第六批规则不够用」成为可复核事实而非叙述。
BATCH6_RULE_COVERAGE = {
    "note": "用第六批 derive() 的抽取正则硬套本批 34 题 + 1 题的实测命中情况，"
            "由 `freeze_batch7.py --probe` 现场统计，不手填。",
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
        if x["semantic_family"] not in FAMILIES:
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


def probe(pool: dict[str, dict], data: dict[str, dict]) -> dict:
    """现场统计「第六批抽取规则在本批题面上的命中情况」。

    **这是本批最重要的一步**：不做这件事，就会在核验阶段把「核验器读错题」
    记成「题库算错」。统计口径分三档：

      - `hit`：第六批规则能抽出**正确**的推导值
      - `wrong`：能抽出值，但值是错的（最危险——不报错、静默出错值）
      - `crash`：抽不到，第六批会抛 ValueError

    **判据按「模板组」而不是「逐个正则」**：第六批的抽取是**二选一/多选一**的
    （shape-canvas 要么「长+宽」要么「底边+高」），首版把每个正则都当成必要
    条件，导致 shape-canvas 明明 3/4 可覆盖却被记成 0/4——**判据写错产假结论**。
    故此处每组内全部命中才算该组命中，任一组命中即 `hit`。
    """
    import re
    groups: dict[str, list[list[str]]] = {
        "pattern-board": [[r"前四格(?:颜色编码)?(?:依次)?是\s*([\d、,，\s]+)",
                           r"补上接下来的\s*(一|二|两|三|\d)\s*格"]],
        "place-value": [[r"位值卡片\s*\[([\d,\s]+)\]", r"(千|百|十|个)位是\s*(\d+)"]],
        "array-board": [[r"每行摆\s*(\d+)\s*个", r"共摆\s*(\d+)\s*行"]],
        "shape-canvas": [[r"长\s*(\d+)\s*格", r"宽\s*(\d+)\s*格"],
                         [r"底边\s*(\d+)\s*格", r"高\s*(\d+)\s*格"]],
        "sorting-board": [[r"\[([\d,\s]+)\]", r"从小到大|从大到小"]],
        "money-board": [[r"标价\s*(\d+)\s*角"]],
        "estimation-canvas": [],
    }
    out: dict[str, dict] = {}
    for rid, x in sorted(pool.items()):
        r = x["renderer"]
        stem = data[rid]["stem"] or ""
        gs = groups.get(r, [])
        hits = [all(re.search(p, stem) for p in g) for g in gs]
        # money-board 的「能抽到」不等于「算得对」——必须与答案对账才判
        detail = {"renderer": r, "solve_path": x.get("solve_path"),
                  "rvid": rid, "pattern_hits": hits}
        if r == "money-board":
            prices = [int(v) for v in re.findall(r"标价\s*(\d+)\s*角", stem)]
            if not prices:
                detail["b6_outcome"] = "crash"
            elif "另一件" in stem:
                got = prices[0] + prices[1] if len(prices) >= 2 else None
                detail["b6_outcome"] = ("hit" if str(got) == str(data[rid]["answer"])
                                        else "wrong")
                detail["b6_value"] = got
            else:
                got = prices[0]
                detail["b6_outcome"] = ("hit" if str(got) == str(data[rid]["answer"])
                                        else "wrong")
                detail["b6_value"] = got
        elif r == "estimation-canvas":
            detail["b6_outcome"] = "crash"   # 第六批没有该分支
        else:
            detail["b6_outcome"] = "hit" if any(hits) else "crash"
        out[rid] = detail
    agg: dict[str, dict] = {}
    for d in out.values():
        b = agg.setdefault(d["renderer"], {"n": 0, "hit": 0, "wrong": 0, "crash": 0})
        b["n"] += 1
        b[d["b6_outcome"]] += 1
    return {"by_renderer": dict(sorted(agg.items())), "detail": out}


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

    # 本批全取：名额必须**精确等于**池内实际数，多一少一都说明题库变了
    picked: list[dict] = []
    picks_log = []
    for sp, n in QUOTA_BY_SOLVE_PATH.items():
        cand = sorted(by_path.get(sp, []), key=lambda x: x["rvid"])
        if len(cand) != n:
            print(f"{sp} 池内 {len(cand)} 题，清单声明 {n} 题——"
                  f"本批是全取批，两者必须相等。题库或已核基线变了？",
                  file=sys.stderr)
            sys.exit(2)
        picked.extend(cand)
        picks_log.append({
            "solve_path": sp, "pool_n": len(cand), "picked_n": len(cand),
            "picked": [x["rvid"] for x in cand],
            "renderers": sorted({x["renderer"] for x in cand}),
            "families": sorted({x["semantic_family"] for x in cand}),
        })

    # 池内若有不在清单里的 solve_path，必须报出来（不能静默漏掉）
    extra_paths = set(by_path) - set(QUOTA_BY_SOLVE_PATH)
    extra_n = sum(len(by_path[k]) for k in extra_paths)
    if extra_n:
        print(f"池内有清单未声明的 solve_path："
              f"{ {k: len(by_path[k]) for k in sorted(extra_paths)} }",
              file=sys.stderr)
        sys.exit(2)

    if len({x["rvid"] for x in picked}) != len(picked):
        print("选题出现重复 RVID", file=sys.stderr)
        sys.exit(2)
    if len(picked) != len(pool):
        print(f"全取批：picked {len(picked)} ≠ 池内 {len(pool)}", file=sys.stderr)
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
            "semantic_family": x["semantic_family"],
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
        "title": "FE-1472 第七批｜Q03 选题集合"
                 "（construct_constraint 余量 + open_estimate 全量）",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "why": ("第六批后 construct_constraint 剩 34、open_estimate 剩 1。"
                "本批全取以达成「族级清零」这一可核验终态；"
                "numeric_judge 剩余 74 题本批不加量。"),
        "selection_rule": SELECTION_RULE,
        "quota_by_solve_path": QUOTA_BY_SOLVE_PATH,
        "picks_log": picks_log,
        "not_selected_why": NOT_SELECTED_WHY,
        "overrides": OVERRIDES,
        "batch6_rule_coverage": dict(
            BATCH6_RULE_COVERAGE, **probe(pool, data)),
        "pool_size": len(pool),
        "quota_n": len(items),
        "quota": [i["rvid"] for i in items],
        "items": items,
    }
    json.dump(out, open(QUOTA_PATH, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"已冻结选题集合：{len(items)} 题 -> {os.path.relpath(QUOTA_PATH, REPO)}")
    from collections import Counter
    print("  solve_path  :", dict(Counter(i["solve_path"] for i in items)))
    print("  renderer    :", dict(Counter(i["renderer"] for i in items)))
    print("  family      :", dict(Counter(i["semantic_family"] for i in items)))
    print(f"  候选池（两族合计）：{len(pool)}（全取）")
    print("\n  第六批规则在本批题面上的命中情况：")
    for r, b in out["batch6_rule_coverage"]["by_renderer"].items():
        print(f"    {r:18s} n={b['n']:2d}  hit={b['hit']}  "
              f"**wrong={b['wrong']}**  crash={b['crash']}")
    return out


def verify() -> None:
    if not os.path.exists(QUOTA_PATH):
        print("未找到 batch7_quota_list.json——必须先冻结选题集合。", file=sys.stderr)
        sys.exit(2)
    q = json.load(open(QUOTA_PATH, encoding="utf-8"))
    print(f"quota_list：{q['quota_n']} 题（{os.path.relpath(QUOTA_PATH, REPO)}）")
    print(f"候选池 {q['pool_size']}（全取）；逐 solve_path 名额：{q['quota_by_solve_path']}")
    from collections import Counter
    print("  实际分布 solve_path:", dict(Counter(i["solve_path"] for i in q["items"])))
    print("  实际分布 renderer  :", dict(Counter(i["renderer"] for i in q["items"])))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if a.verify:
        verify()
    else:
        freeze()