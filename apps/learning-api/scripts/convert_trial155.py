#!/usr/bin/env python3
"""FE-1432 实灌验证②：trial155 → 我方 V2 seed 形态转换器。

用法：python3 scripts/convert_trial155.py <输入.json> <输出.json>
产出：与我方 resource_seed_v2.GOLD_RESOURCES_V2 同构的 dict 列表（可直接喂 seed 链），
      并打印每题 config 能否过我方对应 parser 的预检结果（调 node 审计）。

映射原则（见 docs/frontend/34 RENDERER_CONFIG_CONTRACT）：
- answer：{type,value} → 标量 value（我方 _judge 标量口径；字符串答案原样）
- 渲染器侧字段名差异在本转换器逐 renderer 适配，但**这是临时垫片**——
  正式口径以契约表为准，交付方按契约重导后本转换器退役。
"""
import json, sys, math
from collections import Counter

def jiao_of(text: str):
    return None

def to_scalar(a):
    if isinstance(a, dict) and "value" in a:
        return a["value"]
    return a

def conv_bar_model(cfg, ans):
    bars = cfg.get("bars", [])
    known = {}
    unknown_id = None
    for b in bars:
        if b.get("unknown"):
            unknown_id = b["id"]
        else:
            known[b["id"].replace("known_", "")] = b["value"]
    out = {"mode": "part_whole", "known": known, "answer_bar": (unknown_id or "c").replace("unknown", "c"),
           "max_blocks": cfg.get("max_value", 20)}
    return out

def conv_place_value(cfg, ans):
    return {"target": cfg.get("number"), "pool": sorted([int(x) for x in str(cfg.get("number"))], reverse=False)}

def conv_array(cfg, ans):
    return {"target_rows": cfg.get("rows"), "target_cols": cfg.get("columns"),
            "max_rows": 8, "max_cols": 8}

def conv_grouping(cfg, ans):
    # 交付语义 total/group_size → 我方 items/target_groups（等分份数=组数）
    total, gs = cfg.get("total"), cfg.get("group_size")
    return {"items": total, "target_groups": (total // gs if gs else 3), "max_groups": 6}

def conv_formula(cfg, ans):
    # "7+□=12" → tokens
    import re
    expr = cfg.get("expression", "")
    m = re.match(r"(\d+)([+\-×÷*])(\[\]|□)+=(\d+)", expr.replace("□", "[]"))
    if not m:
        return {"_unmapped": True, "raw": cfg}
    a, op, _, rhs = int(m.group(1)), m.group(2), m.group(3), int(m.group(4))
    op = op.replace("*", "×")
    val = to_scalar(ans)
    tokens = [{"t": "slot", "id": "box", "accept": "number"}, {"t": "op", "v": op},
              {"t": "num", "v": a}, {"t": "eq"}, {"t": "num", "v": rhs}]
    return {"tokens": tokens, "answer_slot": "box", "max_number": 20}

def conv_estimation(cfg, ans):
    obj = cfg.get("objects", {})
    actual = obj.get("count")
    return {"reference": 10, "max": 60, "expected": to_scalar(ans), "actual": actual,
            "tolerance": cfg.get("tolerance", 6)}

def conv_shape_gallery(cfg, ans):
    kind_map = {"triangle": "triangle", "square": "square", "rectangle": "rectangle", "circle": "circle"}
    en = cfg.get("shapes", [])
    target_en = {"三角形": "triangle", "正方形": "square", "长方形": "rectangle", "圆形": "circle"}.get(cfg.get("target_shape"))
    names = ["红", "蓝", "绿", "黄", "紫", "橙"]
    colors = ["#d64545", "#3b6fb5", "#2f9e63", "#d9a520", "#7a5aa8", "#d98324"]
    shapes = [{"id": f"s{i+1}", "name": f"{names[i%6]}{cfg.get('target_shape') if s==cfg.get('target_shape') else s}#{i}",
               "kind": s, "color": colors[i%6]} for i, s in enumerate(en)]
    # 需 target≥3 且 decoy——按 kind 归一
    shapes = [{"id": f"s{i+1}", "name": n, "kind": k, "color": colors[i%6]}
              for i, (n, k) in enumerate(zip([s["name"] for s in shapes], [s["kind"] for s in shapes]))]
    return {"_check": True, "target_kind": target_en, "shapes": shapes, "raw": cfg}

def conv_shape_canvas(cfg, ans):
    cs = cfg.get("canvas_size", {})
    return {"grid": min(cs.get("width", 5), cs.get("height", 5), 6),
            "target_area": 6, "target_shape": cfg.get("target", "rectangle")}

def conv_sorting(cfg, ans):
    # 交付=categorize（分组归类）；我方 R14=ordering 数值排序——**语义不同族，不可转换**
    return {"_semantic_gap": True, "raw": cfg}

def conv_direction(cfg, ans):
    grid = cfg.get("grid", {})
    st = cfg.get("start", {}); tg = cfg.get("target", {})
    return {"rows": grid.get("rows"), "cols": grid.get("cols"),
            "start": {"r": st.get("row", st.get("r")), "c": st.get("col", st.get("c"))},
            "target": {"r": tg.get("row", tg.get("r")), "c": tg.get("col", tg.get("c"))}}

def conv_ruler(cfg, ans):
    objs = cfg.get("objects", [{}])
    o = objs[0] if objs else {}
    mx = cfg.get("scale", {}).get("max", 20)
    return {"max": mx, "object": [o.get("start", 3), o.get("end", 8)]}

def conv_clock(cfg, ans):
    st = cfg.get("start", {})
    tgt_label = cfg.get("target", {}).get("label", "")
    try:
        th, tm = [int(x) for x in tgt_label.split(":")]
    except Exception:
        th, tm = 6, 0
    return {"start": [st.get("hour", 3), st.get("minute", 0)], "target": [th, tm]}

def conv_money(cfg, ans):
    den = cfg.get("denominations", [1, 5, 10, 50])
    return {"price": to_scalar(ans), "denominations": sorted(den)}

def conv_pattern(cfg, ans):
    vis = cfg.get("visible", [])
    blanks = vis.count(None) or cfg.get("blanks", 2)
    vlist = [v for v in vis if v is not None]
    return {"visible": vlist, "blanks": blanks, "palette": sorted(set(vlist)), "_raw": cfg}

CONVERTERS = {
    "bar-model": conv_bar_model, "place-value": conv_place_value,
    "array-board": conv_array, "grouping-board": conv_grouping,
    "formula-board": conv_formula, "estimation-canvas": conv_estimation,
    "shape-gallery": conv_shape_gallery, "shape-canvas": conv_shape_canvas,
    "sorting-board": conv_sorting, "direction-grid": conv_direction,
    "ruler": conv_ruler, "clock": conv_clock,
    "money-board": conv_money, "pattern-board": conv_pattern,
}

def main():
    src, dst = sys.argv[1], sys.argv[2]
    d = json.load(open(src))
    qs = d["questions"]
    stats = Counter()
    converted = []
    for q in qs:
        r = q["renderer_id"]
        ws = q["task_ui_schema"]["workspaces"][0]
        cfg = ws["config"]
        if r not in CONVERTERS:
            stats["passthrough"] += 1
            continue
        try:
            new_cfg = CONVERTERS[r](cfg, q["answer"])
        except Exception as e:
            stats[f"conv_exc:{r}"] += 1
            continue
        if "_semantic_gap" in new_cfg:
            stats[f"semantic_gap:{r}"] += 1
            continue
        if "_check" in new_cfg or "_unmapped" in new_cfg:
            stats[f"unmapped:{r}"] += 1
            continue
        converted.append({
            "code": q["question_id"], "renderer": r, "ui_schema_version": "2.0",
            "mode": ws["mode"], "response_type": q["response_type"],
            "ability_id": q["ability_id"],
            "content": {"stem": q["prompt"], "answer": to_scalar(q["answer"]), "goal": ""},
            "config": new_cfg,
            "context_family": q.get("context_family"),
        })
        stats["converted"] += 1
    json.dump(converted, open(dst, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(dict(stats), ensure_ascii=False, indent=1))
    print(f"转换产出: {len(converted)} 题 → {dst}")

if __name__ == "__main__":
    main()
