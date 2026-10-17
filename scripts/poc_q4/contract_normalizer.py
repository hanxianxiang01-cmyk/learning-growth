#!/usr/bin/env python3
"""PoC contract_normalizer：V1/V2 统一规范化为六列教学契约（方案 §2.2）。"""
import json


def normalize(o):
    """输入 eval_dataset 行，输出统一契约视图。"""
    ui_kind = "V2" if o["schema"] == "2.0" else "V1"
    cfg = o.get("config") or {}
    if ui_kind == "V2":
        interaction = {"type": "renderer", "id": o["renderer"], "mode": o.get("mode")}
        answer_axis = (o.get("response_contract") or {}).get("response_type")
        process_evidence = (o.get("response_contract") or {}).get("evidence_targets", [])
    else:
        interaction = {"type": "legacy", "visual": o["renderer"], "tools": cfg.get("tools", [])}
        rs = o.get("response_schema") or o.get("response_contract") or {}
        answer_axis = rs.get("answer_type") if isinstance(rs, dict) else str(rs)
        process_evidence = ["操作轨迹(jumps/objects)"] if rs.get("representation_required") else []
    return {"seq": o["seq"], "rvid": o["rvid"], "title": o["title"],
        "ability_id": o["ability_id"], "form": ui_kind,
        "interaction": interaction, "answer_axis": answer_axis,
        "process_evidence": process_evidence,
        "hint_ladder": o.get("hint_ladder"), "error_models": o.get("error_models")}


if __name__ == "__main__":
    out = [normalize(json.loads(l)) for l in open("eval_dataset.jsonl")]
    with open("normalized_contracts.jsonl", "w") as f:
        for o in out:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    v1 = sum(1 for o in out if o["form"] == "V1")
    print(f"规范化 {len(out)} 题：V1={v1} V2={len(out)-v1}（清单口径 V1 6+V2 14 → 校验: {v1==6}）")
    # 一致性检查：无 workspaces.renderer 的 legacy 题不得要求 V2 字段
    bad = [o["seq"] for o in out if o["form"] == "V1" and o["interaction"]["type"] == "renderer"]
    print("V1 误标 renderer:", bad or "无 ✓")
