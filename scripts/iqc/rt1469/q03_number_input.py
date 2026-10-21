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
    },
    {
        "rvid": "103b0e3f-4287-469c-96ec-6a173e84a4f5",
        "read": "47 = 4个十 + ?个一 → 个位数字即所问",
        "expression": "47 - 4 * 10",
        "boundary": "问的是『几个一』即个位数，不是剩余数值 7 之外的任何除法结果",
    },
    {
        "rvid": "19081b90-e789-4275-a60a-79815a80bc73",
        "read": "65里有几个十 → 十位数字（向下取整）",
        "expression": "(65 - 65 % 10) // 10",
        "boundary": "问『几个整十』而非『能凑成几组十还有余』；余数 5 不计入",
    },
    {
        "rvid": "b7261e66-12fa-4c09-a070-5708b1d8da9d",
        "read": "24张，每6张一组，正好分完 → 等分组数",
        "expression": "24 // 6",
        "boundary": "题面声明『正好分完』，故无需处理余数；若有余数应问『几组余几张』",
    },
    {
        "rvid": "e0d22830-7ce7-4581-b1cd-db9ba2f3a8c5",
        "read": "原有7只，飞走2只 → 求剩余（减法而非加法）",
        "expression": "7 - 2",
        "boundary": "『飞走』= 减少；若题面为『又飞来』则为加法。strategy 错因对应此反向",
    },
    {
        "rvid": "ffa54e00-0701-470e-9624-3d62a80a8832",
        "read": "38比42少几 → 大数减小数",
        "expression": "42 - 38",
        "boundary": "『A比B少几』= B − A；若误作 A − B 得负数，是 reversed 类错误",
    },
]


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

    results = []
    for c in CASES:
        # 第一步：独立求解（只用 derivation，不碰 DB）
        computed = eval(c["expression"], {"__builtins__": {}}, {})  # noqa: S307 常量算式

        # 第二步：取比较对象（此处才允许读 answer）
        import psycopg
        with psycopg.connect(db) as conn:
            row = conn.execute(
                "select content->>'answer', content->>'stem', "
                "error_models from resource_version "
                "where resource_version_id = %s::uuid", (c["rvid"],)).fetchone()
        if not row:
            results.append({**c, "computed": computed, "verdict": "RVID_NOT_FOUND"})
            continue
        stated_raw, stem, ems = row
        try:
            stated = float(stated_raw)
        except (TypeError, ValueError):
            stated = None
        match = stated is not None and abs(float(computed) - stated) < 1e-9

        results.append({
            "rvid": c["rvid"],
            "stem": stem,
            "read": c["read"],
            "expression": c["expression"],
            "computed": computed,
            "stated_answer": stated_raw,
            "verdict": "MATCH" if match else "MISMATCH",
            "boundary": c["boundary"],
            "q05_error_models": ems,
            "q05_note": ("code == pattern 同质占位，无法区分具体错法"
                         if ems and all(e.get("code") == e.get("pattern") for e in ems)
                         else "code ≠ pattern，仍需核验可观察性"),
        })

    out = {
        "title": "FE-1469｜Q03 独立核验首批（number-input 6 题）",
        "chain": "题干 → 独立求解 → 与已存答案比较 → 留存推导与适用边界",
        "discipline": [
            "预期答案只由 expression 算出，不读 DB answer",
            "DB answer 仅作比较对象，不参与生成预期",
            "只读运行：不写库、不调会写学习记录的接口",
            "q05_note 仅标候选信号，不判定错因是否有区分力",
        ],
        "summary": {
            "total": len(results),
            "match": sum(1 for r in results if r["verdict"] == "MATCH"),
            "mismatch": sum(1 for r in results if r["verdict"] == "MISMATCH"),
            "not_found": sum(1 for r in results if r["verdict"] == "RVID_NOT_FOUND"),
        },
        "items": results,
    }
    os.makedirs(os.path.join(REPO, "scripts/iqc/runs"), exist_ok=True)
    path = os.path.join(REPO, "scripts/iqc/runs/FE1469_q03_number_input.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    for r in results:
        print(f"{r['verdict']:8s} {r['expression']:18s} = {r['computed']:<5} "
              f"stated={r.get('stated_answer')!r:6} {r['rvid'][:8]}")
    print("\n", json.dumps(out["summary"], ensure_ascii=False))
    print("out:", path)
    return 0 if out["summary"]["mismatch"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())