"""FE-1472｜DEF-D2 三题定向契约核验（把「线索」升级为有据定性，或撤回）。

背景：Q03 第三批把这三题登记为 DEF-D2（未知条语义歧义）——
`max_value`（17/14/13）小于「最终合计」（18/21/19），一度被读成
「界面物理上摆不到正确答案，任务不可完成」。第三批复审要求撤回该定性，
改按线索处理，并做定向核验。

本脚本只回答四个可核对的事实，**不做"任务不可完成"的结论**：
  F1 未知条的滑条可达范围是多少？（读 BarModel.tsx 实际实现，不猜）
  F2 「另一个人的数量」是否落在可达范围内？
  F3 提交物里有哪些字段？答案字段与表征字段是分开的吗？
  F4 判分是否读取表征？判分只看什么？

证据来源：
  - 运行时配置：resource_version.ui_schema（本题实际值）
  - 渲染实现：apps/child-web/src/components/manipulatives/BarModel.tsx
  - 提交就绪：apps/child-web/src/features/task-renderer/TaskRenderer.tsx
              isTaskResponseReady()
  - 后端判分：apps/learning-api/app/services/learning.py（expected/_judge）

产出：scripts/iqc/runs/FE1472_d2_directed.json（只读库，零 DML）

用法：
  export DATABASE_URL="$(security find-generic-password -s iqc-database-url -w)"
  python scripts/iqc/rt1472/d2_directed_check.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
assert os.path.isdir(os.path.join(REPO, "scripts", "iqc")), f"REPO 层级算错：{REPO}"
OUT = os.path.join(REPO, "scripts/iqc/runs/FE1472_d2_directed.json")

# 冻结本批三题（第三批 DEF-D2 的 affected 集合）
TARGETS = ["421ede36", "6e5395f0", "8981fbcc"]


def load_cases() -> list[dict]:
    import psycopg
    db = os.environ.get("DATABASE_URL")
    if not db:
        raise SystemExit("缺少 DATABASE_URL（只读账号即可）")
    with psycopg.connect(db) as conn:          # 只读，零 DML
        rows = conn.execute(
            "select resource_version_id::text, version_no, content, ui_schema, "
            "       review_status, published_at "
            "from resource_version "
            "where left(resource_version_id::text, 8) = any(%s)",
            (TARGETS,)).fetchall()
    out = []
    for rvid, vno, content, ui, status, pub in rows:
        if isinstance(content, str):
            content = json.loads(content)
        if isinstance(ui, str):
            ui = json.loads(ui)
        out.append({"rvid": rvid, "version_no": vno, "content": content,
                    "ui_schema": ui, "review_status": status,
                    "published_at": str(pub) if pub else None})
    out.sort(key=lambda x: TARGETS.index(x["rvid"][:8]))
    return out


def analyse(case: dict) -> dict:
    ui = case["ui_schema"]
    vis = ui.get("visual") or {}
    bars = vis.get("bars") or []
    stem = case["content"].get("stem") or ui.get("prompt") or ""
    answer = case["content"].get("answer")

    base_bar = next((b for b in bars if not b.get("unknown")), None)
    unk_bar = next((b for b in bars if b.get("unknown")), None)
    assert base_bar and unk_bar, "本题没有“已知/未知”两根条，不属于本核验对象"

    base_v = base_bar.get("value")
    # 题面里「比…多/少 N」的差量
    diff = _parse_diff(stem)
    other = base_v + diff if diff is not None else None
    total = float(answer) if answer is not None else None

    # F1：未知条滑条的实际可达范围。
    # BarModel.tsx 第 44-66 行：
    #   const barMax = source?.max ?? max;
    #   <input type="range" min={min} max={Math.max(min + 1, barMax)} />
    # → 每根条的可达上限是**它自己的 bar.max**，不是 max_value。
    unk_min = unk_bar.get("min", 0)
    unk_max = unk_bar.get("max")
    reachable = (unk_min, unk_max)

    f1 = {
        "unknown_bar_range": reachable,
        "max_value_is_scale_only": True,
        "source": "BarModel.tsx:44-66（barMax=source.max；max_value 仅用于宽度比例）",
        "note": "max_value 只参与条宽百分比计算，不限制滑条；滑条上限取该条自己的 max",
    }
    f2 = {
        "base_value": base_v,
        "diff_parsed": diff,
        "other_person": other,
        "other_within_range": (other is not None and unk_max is not None
                               and unk_min <= other <= unk_max),
        "total_answer": total,
        "total_within_range": (total is not None and unk_max is not None
                               and total <= unk_max),
    }
    # F3：提交物字段（来自 response_schema 与后端判分两处交叉）
    f3 = {
        "response_schema": ui.get("response_schema"),
        "submitted_fields": ["answer", "interaction_events"],
        "answer_is_scalar": (ui.get("response_schema") or {}).get("answer_type") == "number",
        "bar_values_enter_answer": False,
        "source": "TaskRenderer.tsx isTaskResponseReady(): 只校验 answer 非空 + "
                  "(representation_required 时) representation 存在；"
                  "answer 与 representation 是两个独立字段",
    }
    f4 = {
        "judge_reads": ["content.answer", "response.answer"],
        "judge_ignores": ["representation", "visual.bars", "interaction_events"],
        "source": "learning.py:926-937（expected=content.answer；"
                  "user_answer=response.answer；correct=_judge 两值比较）",
        "evidence": "除 FE-1455 的 jump_constraint 对**数轴题**额外校验轨迹外，"
                    "没有其他过程校验分支",
    }

    # 结论只到"事实层"：正确候选可完成、半成品被判错——是否等于"任务不可完成"
    half_ok_answer = (total is not None and other is not None
                      and total != other)
    return {
        "rvid": case["rvid"],
        "version_no": case["version_no"],
        "review_status": case["review_status"],
        "published_at": case["published_at"],
        "stem": stem,
        "answer": answer,
        "f1_reachability": f1,
        "f2_role_hypothesis": f2,
        "f3_submission": f3,
        "f4_judging": f4,
        "facts": {
            "unknown_bar_can_reach_other_person": f2["other_within_range"],
            "unknown_bar_cannot_reach_total": not f2["total_within_range"],
            "answer_field_determines_score_alone": True,
            "half_done_representation_still_fails": half_ok_answer,
        },
        "not_concluded": "本条**不**主张任务不可完成：未知条能否表达合计不是完成性的必要条件——"
                         "判分只看数字框。也不主张未知条的角色已被确证；"
                         "「另一个人的数量」是当前证据下最相容的假设。",
    }


def _parse_diff(stem: str) -> int | None:
    import re
    # 「小雨比小青少4张」/「小红比小明多3本」
    m = re.search(r"比[^，。]*?(多|少)\s*(\d+)", stem)
    if not m:
        return None
    n = int(m.group(2))
    return n if m.group(1) == "多" else -n


def main() -> int:
    cases = load_cases()
    if len(cases) != len(TARGETS):
        print(f"预期 {len(TARGETS)} 题，实取 {len(cases)} 题："
              f"{[c['rvid'][:8] for c in cases]}", file=sys.stderr)
        return 2
    items = [analyse(c) for c in cases]

    # 汇总断言：三题必须全部满足"另一个人的数量可达" + "合计不可达" + "半成品被判错"
    fails = []
    for it in items:
        f = it["facts"]
        if not f["unknown_bar_can_reach_other_person"]:
            fails.append(f"{it['rvid'][:8]} 另一个人的数量超出未知条可达范围")
        if not f["unknown_bar_cannot_reach_total"]:
            fails.append(f"{it['rvid'][:8]} 合计竟然可达——需要重看 max 配置")
        if not f["half_done_representation_still_fails"]:
            fails.append(f"{it['rvid'][:8]} 半成品与正确答案同值，无法区分")

    out = {
        "title": "FE-1472｜DEF-D2 三题定向契约核验（未知条角色与完成性）",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "targets": TARGETS,
        "summary": {
            "n": len(items),
            "fails": len(fails),
            "verdict": ("每题的未知条都能表达「另一个人的数量」，"
                        "但都表达不了「两人合计」；而判分只读数字框，"
                        "因此**不构成『任务不可完成』**——只构成"
                        "「该表征无法承载合计」这一表征层事实"),
        },
        "items": items,
    }
    if fails:
        print("**定向核验未通过**：", file=sys.stderr)
        for x in fails:
            print(f"  ✗ {x}", file=sys.stderr)
        print("未写出 JSON。", file=sys.stderr)
        return 1

    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"D2-DIRECTED: {len(items)} 题全部通过事实断言")
    for it in items:
        f = it["facts"]
        print(f"  {it['rvid'][:8]} 未知条可达[0,{it['f1_reachability']['unknown_bar_range'][1]}] "
              f"另一人={it['f2_role_hypothesis']['other_person']}"
              f"{'✓' if f['unknown_bar_can_reach_other_person'] else '✗'} "
              f"合计={it['f2_role_hypothesis']['total_answer']}"
              f"{'不可达' if f['unknown_bar_cannot_reach_total'] else '可达!'} "
              f"| 判分只读 answer")
    print(f"out: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())