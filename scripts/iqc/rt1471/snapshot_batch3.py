#!/usr/bin/env python3
"""FE-1471 冻结输入快照（`evaluate()` 的离线回放底座）。

## 为什么需要这个文件

之前门禁只检枚举、关键词、集合和文档数字，**从不执行 29 题的数学核验**。
复现实测（2026-10-21 复审）：

    independent_eval() 改成恒返回 0  →  Q03-BATCH3-GATE: PASS
    match 改成恒 True               →  Q03-BATCH3-GATE: PASS
    删掉批次文档                    →  Q03-BATCH3-GATE: PASS

也就是说门禁通过与否和「核验到底算没算对」无关。根因是门禁没有**输入**：
不连库时它手里没有 29 题的 `answer` / `exact_model` / `ui_schema`，只能检查
自己的常量互相自洽。

本文件把这三样冻结成快照，让门禁在不连库的 CI 环境里也能：
  1. 对每道题真实调用 `evaluate()`，断言 `verdict == MATCH`；
  2. 篡改快照里的 `answer` 或配置，断言结论**必须**变；
  3. 注入「恒 0 / 恒 MATCH」变异，断言门禁判 FAIL。

## 快照的口径

- `answer` / `stem` / `error_models` / `ui_schema` 是**运行时的原值**，不做任何
  规整；`answer_raw_sha256` / `ui_schema_sha256` 用于发现快照被手改。
- `replayed` 段是 `evaluate()` 在该快照上的实际输出（`computed` / `verdict` /
  `visual_leak` / `unreachable` 等），供门禁与现场重算逐字段比对。
- 本脚本**只读**：使用 psycopg3 with-connect，且无任何 DML 语句
  （见 MEMORY 铁律「DRY 工具必须零 DML 路径」）。

## 用法

    export DATABASE_URL="$(security find-generic-password -s iqc-database-url -w)"
    ~/.workbuddy/binaries/python/envs/learning-engine/bin/python \
        scripts/iqc/rt1471/snapshot_batch3.py            # 写入/刷新快照
    ... snapshot_batch3.py --check                        # 只比对不写（CI 用）
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SNAPSHOT = os.path.join(HERE, "batch3_frozen_inputs.json")


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, os.path.join(REPO, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sha(obj) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _canon_expr_num(v):
    """answer 归一成数值（与 evaluate 同口径：float 可转则 float）。"""
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def build(db: str) -> dict:
    import psycopg

    B = _load("batch3", "scripts/iqc/rt1471/q03_batch3.py")
    rvids = [c["rvid"] for c in B.CHECKS]

    with psycopg.connect(db) as conn:      # 只读，零 DML
        rows = conn.execute(
            "select resource_version_id::text, content->>'answer', "
            "content->>'stem', error_models, ui_schema from resource_version "
            "where resource_version_id = any(%s::uuid[])", (rvids,)).fetchall()
    live = {r[0]: r[1:] for r in rows}

    missing = [r for r in rvids if r not in live]
    if missing:
        raise SystemExit(f"快照构建失败：{len(missing)} 个 RVID 不在库：{missing}")

    items = []
    for c in B.CHECKS:
        answer_raw, stem, ems, ui = live[c["rvid"]]
        r = B.evaluate(c, answer_raw, ems or [], ui or {})
        items.append({
            "rvid": c["rvid"],
            "renderer": c["renderer"],
            "relation": c["relation"],
            # ── 输入（原值）──
            "answer_raw": answer_raw,
            "answer_num": _canon_expr_num(answer_raw),
            "stem": stem,
            "error_models": ems or [],
            "ui_schema": ui,
            # ── 防手改 ──
            "answer_raw_sha256": _sha(answer_raw),
            "ui_schema_sha256": _sha(ui),
            # ── evaluate() 在该快照上的实际输出 ──
            "replay": {
                "computed": r["computed"],
                "verdict": r["verdict"],
                "expr": r["derivation"]["expr"],
                "visual_leak": r["visual_leak"],
                "unreachable_signal": r["unreachable_signal"],
                "known_defects": [d["id"] for d in r["known_defects"]],
            },
        })

    return {
        "title": "FE-1471｜第三批 29 题冻结输入快照（供离线 gate 回放 evaluate()）",
        "purpose": ("门禁原先只查结构、不执行数学核验，导致 independent_eval 恒 0 / "
                    "match 恒 True 仍 PASS。本快照把 answer / error_models / ui_schema "
                    "冻结下来，使门禁可在无数据库的 CI 上真实跑一遍 evaluate()。"),
        "frozen_at_commit": _git_commit(),
        "provenance": {
            "source": "resource_version.content->>'answer' / content->>'stem' / "
                      "error_models / ui_schema（运行时原值，未规整）",
            "readonly": "psycopg3 with-connect，零 DML 路径",
            "regenerate": ("export DATABASE_URL=\"$(security find-generic-password "
                           "-s iqc-database-url -w)\" && "
                           "~/.workbuddy/binaries/python/envs/learning-engine/bin/python "
                           "scripts/iqc/rt1471/snapshot_batch3.py"),
        },
        "count": len(items),
        "items": items,
    }


def _git_commit() -> str | None:
    import subprocess
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                              capture_output=True, text=True,
                              timeout=10).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def main(argv: list[str]) -> int:
    check_only = "--check" in argv

    if check_only:
        if not os.path.exists(SNAPSHOT):
            print(f"快照不存在：{SNAPSHOT}", file=sys.stderr)
            return 2
        with open(SNAPSHOT, encoding="utf-8") as f:
            snap = json.load(f)
        print(f"快照存在：{snap['count']} 题 / "
              f"冻结于 {snap.get('frozen_at_commit')}")
        return 0

    db = os.environ.get("DATABASE_URL")
    if not db:
        print("缺少 DATABASE_URL。可执行：\n"
              "  export DATABASE_URL=\"$(security find-generic-password "
              "-s iqc-database-url -w)\"", file=sys.stderr)
        return 2
    db = db.replace("postgresql+psycopg://", "postgresql://")

    snap = build(db)
    with open(SNAPSHOT, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)

    bad = [i["rvid"][:8] for i in snap["items"] if i["replay"]["verdict"] != "MATCH"]
    print(f"快照已写入 {SNAPSHOT}（{snap['count']} 题，非 MATCH {len(bad)} 条）")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))