#!/usr/bin/env python3
"""FE-1469：Q03 独立核验（number-input 首批 6 题）。

用户 2026-10-21 复审 §三 规定的核验链：
    **题干与必要配置 → 独立求解／合法解集合 → 与现有答案比较 → 留存推导与适用边界**
且明确：「数据库 `answer` 可以作为比较对象，不能反过来参与生成预期答案」。

本脚本的纪律（对应上面这句）：
    1. 预期答案**只**由 `derivation` 里的算式算出，不读 DB 的 answer；
    2. DB 的 answer 只在最后一步作为**比较对象**出现，且只在断言处读取；
    3. 推导留痕：每条记 expression / computed / stated / 适用边界；
    4. 不判「题好不好」，只判「答案是否等于独立求解结果」；
    5. 只读：本脚本不写库、不调任何会写学习记录的接口。

用法：
  DATABASE_URL=... python scripts/iqc/rt1469/q03_number_input.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# HERE = <repo>/scripts/iqc/rt1469 → 退三级才是仓库根。
# 2026-10-21：本文件首版只退两级（得到 scripts），产物落到 scripts/scripts/，
# 与 test_baseline_provenance.py 上一轮踩的是同一个坑。PATH_DEPTH 常量把
# 层级写死在一处，避免每个路径各算一遍。
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

assert os.path.isdir(os.path.join(REPO, "scripts", "iqc")), \
    f"REPO 层级算错：{REPO} 下没有 scripts/iqc"

# 手工登记的推导。**先解题、后对答案**——顺序不能反。
# 每条都写清：从题干哪句话得到什么关系、适用边界是什么。
CASES: list[dict] = [
    {
        "rvid": "066c5362-762c-4a52-995b-db7d55747a12",
        "read": "4排椅子，每排6把 → 行×列",
        "expression": "4 * 6",
        "boundary": "每排数量相同（题面无缺排），故为规则阵列；若排数不等需逐排累加",
        "q05_hypothesis": "把「4排×6把」当作「4+6」直接相加 → 10",
    },
    {
        "rvid": "103b0e3f-4287-469c-96ec-6a173e84a4f5",
        "read": "47 = 4个十 + ?个一 → 个位数字即所问",
        "expression": "47 - 4 * 10",
        "boundary": "问的是『几个一』即个位数，不是剩余数值 7 之外的任何除法结果",
        "q05_hypothesis": "把「4个十和几个一」的十位/个位互换，交 4",
    },
    {
        "rvid": "19081b90-e789-4275-a60a-79815a80bc73",
        "read": "65里有几个十 → 十位数字（向下取整）",
        "expression": "(65 - 65 % 10) // 10",
        "boundary": "问『几个整十』而非『能凑成几组十还有余』；余数 5 不计入",
        "q05_hypothesis": "把「几个十」读成「取走整十后剩几」，交 5（个位数字）",
    },
    {
        "rvid": "b7261e66-12fa-4c09-a070-5708b1d8da9d",
        "read": "24张，每6张一组，正好分完 → 等分组数",
        "expression": "24 // 6",
        "boundary": "题面声明『正好分完』，故无需处理余数；若有余数应问『几组余几张』",
        "q05_hypothesis": "除法方向反（6÷24）或把每组的张数当组数，交 6",
    },
    {
        "rvid": "e0d22830-7ce7-4581-b1cd-db9ba2f3a8c5",
        "read": "原有7只，飞走2只 → 求剩余（减法而非加法）",
        "expression": "7 - 2",
        "boundary": "『飞走』= 减少；若题面为『又飞来』则为加法。strategy 错因对应此反向",
        "q05_hypothesis": "「飞走」误作「飞来」，用加法 7+2 → 9",
    },
    {
        "rvid": "ffa54e00-0701-470e-9624-3d62a80a8832",
        "read": "38比42少几 → 大数减小数",
        "expression": "42 - 38",
        "boundary": "『A比B少几』= B − A；若误作 A − B 得负数，是 reversed 类错误",
        "q05_hypothesis": "比较方向反（38−42，得 −4）或用加法 38+42 → 80",
    },
]


def judge_binding(ref_sha: str | None, recomputed: str | None) -> bool:
    """引用哈希 vs 重算哈希是否漂移。**抽成纯函数是为了能被单独测。**

    2026-10-21：drift 判定写在主流程里的话，只有连库才能验证它对不对；
    而"这条判定本身是否有效"恰恰是最该被锁的（它决定旧结论还能不能用）。
    两个都为 None 也算漂移——没有约束原件可引，就不能声称核验的是同一份题。
    """
    return not (ref_sha and recomputed and ref_sha == recomputed)


def bind_inputs(db: str, common, rvids: list[str] | None = None) -> dict:
    """把本批结果绑定到**已有冻结原件**的哈希上，不新建台账。

    用户 2026-10-21 复审 §一.1：『只有题干/推导/答案，没有标明输入快照、
    题目审计哈希、求解器版本』。要求『引用既有冻结原件和哈希即可，
    不必重新建一套台账』——所以这里只做引用与重算比对：

      · manifest_snapshot  ← scripts/iqc/runs/inventory_manifest_r2.json 的
        snapshot_sha256（cee1afda…，与 findings_fe1460_225.jsonl 同一快照）
      · per_item.sha       ← manifest 里已登记的 audit_input_sha256（**引用**）
      · per_item.recomputed ← 现在按同一九域口径重算（**核对**，不是新台账）
      · per_item.drift     ← 引用值 ≠ 重算值 → 题目在快照后被改过，
        此时旧结论不能沿用，必须显式失败

    这么做而不是"写一份新的快照文件"，是因为台账会分叉：两份各自演进的
    哈希表最终谁也证明不了谁。
    """
    import json as _json
    manifest_path = os.path.join(REPO, "scripts/iqc/runs/inventory_manifest_r2.json")
    manifest = _json.load(open(manifest_path))
    by_id = {i["resource_version_id"]: i for i in manifest["items"]}

    items = common.load_items(db, rvids or [c["rvid"] for c in CASES])
    per_item = {}
    for rvid in (rvids or [c["rvid"] for c in CASES]):
        ref = by_id.get(rvid)
        cur = items.get(rvid)
        recomputed = common.audit_input_sha(cur) if cur else None
        ref_sha = (ref or {}).get("audit_input_sha256")
        per_item[rvid] = {
            "sha": ref_sha,
            "recomputed": recomputed,
            # 引用缺失也算 drift：没有冻结原件可引，就无法证明核验的是同一份题。
            "drift": judge_binding(ref_sha, recomputed),
            "manifest_status": (ref or {}).get("review_status"),
            "manifest_version_no": (ref or {}).get("version_no"),
        }
    return {
        "frozen_source": "scripts/iqc/runs/inventory_manifest_r2.json",
        "manifest": {
            "snapshot_sha256": manifest["snapshot_sha256"],
            "inventory_version": manifest.get("inventory_version"),
            "discovered_total": manifest.get("discovered_total"),
        },
        "same_snapshot_as": "scripts/iqc/runs/findings_fe1460_225.jsonl"
                            "（run_id FE1460-eb662b5c，snapshot cee1afda…）",
        "solver_version": {
            "script": "scripts/iqc/rt1469/q03_number_input.py",
            "expression_engine": "Python eval + 空 builtins（常量算式，无外部依赖）",
            "hash_recipe": "scripts/iqc/common.py::audit_input_sha（九域规范化，"
                           "与 scan.py 同一口径）",
            "note": "求解器本身不锁版本号——算式是手工登记的常量表达式，"
                    "改动即改动本文件，diff 可见。这比自报版本号更可查。",
        },
        "drift_rule": "引用哈希 ≠ 重算哈希 → 该题在快照后被修改，"
                      "本轮结论作废，脚本以退出码 1 失败（不静默沿用旧结论）",
        "per_item": per_item,
    }


def q05_candidates(case: dict, ems: list, homogeneous: bool) -> list[dict]:
    """本批六题起形成的 Q05 候选（用户 §三 要求：候选 + 证据要求）。

    纪律：**不把最终数值直接等同于某种认知缺陷**。
    每条候选都必须写「要成立还需要看到什么」，写成 requirement 而不是结论。
    `code == pattern` 只说明这两个字段同值，说明不了"该错法可被观测"——
    所以 homogeneous=True 时区分力一律记 pending，不记 pass/fail。
    """
    if not ems:
        return []
    out = []
    for e in ems:
        code = str(e.get("code"))
        cand = {
            "code": code,
            "stated_pattern": e.get("pattern"),
            "status": "同质占位候选，区分力尚待验证" if homogeneous
                      else "非同质，区分力尚待逐条验证",
            # 用 case 里登记的错法假设（若有）当"候选方向"，但明确标为假设。
            "hypothesis": case.get("q05_hypothesis"),
            "requirement": (
                "需补充可观测证据：该错法在作答轨迹/中间量上留下什么可区分痕迹、"
                "与同题其它错法的判定边界在哪。仅有 code==pattern 不足以证明区分力。"
            ),
            "not_concluded": "本条不主张该错法一定被孩子使用，也不主张它对应某种认知缺陷",
        }
        out.append(cand)
    return out


def main() -> int:
    db = os.environ.get("DATABASE_URL")
    if not db:
        sys.exit("缺少 DATABASE_URL（只读账号即可）")
    db = db.replace("postgresql+psycopg://", "postgresql://")

    # 依赖预检：用错解释器时不要让脚本以 ModuleNotFoundError 崩溃。
    # 2026-10-21 实测：负对照用系统 python3 跑，rc=1 却没有任何 MISMATCH 行，
    # 差点被当成"检出成功"。崩溃与"答案不等"必须用不同退出码区分，
    # 否则任何环境问题都会被读成核验结论。
    try:
        import psycopg  # noqa: F401
    except ModuleNotFoundError:
        print("ENV_ERROR: 当前解释器没有 psycopg。请用 "
              "~/.workbuddy/binaries/python/envs/learning-engine/bin/python 运行。"
              "退出码 2 表示环境错误，与核验结论无关。", file=sys.stderr)
        return 2

    sys.path.insert(0, os.path.join(REPO, "scripts", "iqc"))
    import common  # 复用 IQC 的九域审计哈希，不另造一套口径

    prov = bind_inputs(db, common)

    results = []
    for c in CASES:
        # 第一步：独立求解（只用 derivation，不碰 DB）
        computed = eval(c["expression"], {"__builtins__": {}}, {})  # noqa: S307 常量算式

        # 第二步：取比较对象（此处才允许读 answer）
        import psycopg
        with psycopg.connect(db) as conn:
            row = conn.execute(
                "select content->>'answer', content->>'stem', error_models, "
                "ui_schema from resource_version "
                "where resource_version_id = %s::uuid", (c["rvid"],)).fetchone()
        if not row:
            results.append({**c, "computed": computed, "verdict": "RVID_NOT_FOUND"})
            continue
        stated_raw, stem, ems, ui = row
        try:
            stated = float(stated_raw)
        except (TypeError, ValueError):
            stated = None
        match = stated is not None and abs(float(computed) - stated) < 1e-9

        # 本题所用的输入依据：题面 + 求解所需的必要配置（number-input 无配置依赖，
        # 但要显式记"无"，而不是留空让人猜"是不是漏了"）。
        ws_cfg = {}
        for ws in (ui or {}).get("workspaces") or []:
            if isinstance(ws, dict) and isinstance(ws.get("config"), dict):
                ws_cfg = ws["config"]
                break
        ems = ems or []
        homogeneous = bool(ems) and all(
            str(e.get("code")) == str(e.get("pattern")) for e in ems)

        results.append({
            "rvid": c["rvid"],
            "stem": stem,
            "read": c["read"],
            "expression": c["expression"],
            "computed": computed,
            "stated_answer": stated_raw,
            "verdict": "MATCH" if match else "MISMATCH",
            "boundary": c["boundary"],
            "input_binding": {
                "audit_input_sha256": prov["per_item"].get(c["rvid"], {}).get("sha"),
                "manifest_snapshot": prov["manifest"]["snapshot_sha256"],
                "drift": prov["per_item"].get(c["rvid"], {}).get("drift"),
                "ui_config_used": ws_cfg or "无（该题只依赖题面数值关系）",
            },
            "q05_error_models": ems,
            "q05_note": ("同质占位候选，区分力尚待验证"
                         if homogeneous else "code ≠ pattern，区分力仍待逐条验证"),
            "q05_candidates": q05_candidates(c, ems, homogeneous),
        })

    out = {
        "title": "FE-1469｜Q03 独立核验首批（number-input 6 题）",
        "chain": "题干 → 独立求解 → 与已存答案比较 → 留存推导与适用边界",
        "discipline": [
            "预期答案只由 expression 算出，不读 DB answer",
            "DB answer 仅作比较对象，不参与生成预期",
            "只读运行：不写库、不调会写学习记录的接口",
            "q05_note 仅标候选信号，不判定错因是否有区分力——"
            "只写『同质占位候选，区分力尚待验证』，不写『无法区分具体错法』，"
            "因为后者是结论，而本轮材料只到候选",
        ],
        "provenance": prov,
        "summary": {
            "total": len(results),
            "match": sum(1 for r in results if r["verdict"] == "MATCH"),
            "mismatch": sum(1 for r in results if r["verdict"] == "MISMATCH"),
            "not_found": sum(1 for r in results if r["verdict"] == "RVID_NOT_FOUND"),
            "drift": sum(1 for r in results if r.get("input_binding", {}).get("drift")),
        },
        "items": results,
    }
    os.makedirs(os.path.join(REPO, "scripts/iqc/runs"), exist_ok=True)
    path = os.path.join(REPO, "scripts/iqc/runs/FE1469_q03_number_input.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    for r in results:
        print(f"{r['verdict']:8s} {r['expression']:18s} = {r['computed']:<5} "
              f"stated={r.get('stated_answer')!r:6} {r['rvid'][:8]}"
              f"  sha={str(r.get('input_binding', {}).get('audit_input_sha256'))[:12]}")
    print("\n", json.dumps(out["summary"], ensure_ascii=False))
    print("out:", path)
    # 漂移也是失败：题目内容变了还沿用旧结论，等于拿旧核验冒充新题。
    return 0 if out["summary"]["mismatch"] == 0 and out["summary"]["drift"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())