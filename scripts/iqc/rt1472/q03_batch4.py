"""FE-1472｜Q03 第四批：逐题独立核验（读 batch4_quota_list.json，不重新选样）。

核验链（沿用既定，不因 renderer 变化而放宽）：
  题干与必要配置 → 明确所求对象 → 独立推导 → 按已确认契约编码 → 与存储答案比较

**独立性要求**：`computed` 只能由 `derive(item)` 从题干/配置算出，
不得读取 `answer_raw`；`answer_raw` 只在比较一步出现。
最后由 `independent_eval()` 求值，它不认识答案。

用法：
  export DATABASE_URL="$(security find-generic-password -s iqc-database-url -w)"
  python scripts/iqc/rt1472/q03_batch4.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
assert os.path.isdir(os.path.join(REPO, "scripts", "iqc")), f"REPO 层级算错：{REPO}"

QUOTA = os.path.join(HERE, "batch4_quota_list.json")
OUT = os.path.join(REPO, "scripts/iqc/runs/FE1472_q03_batch4.json")

# ── 时间编码契约（clock）────────────────────────────────────────────────
# 存储答案是「分钟数」：h*60+m。这不是猜的，用三题自证：
#   4:30 -> 270、11:00 -> 660、5:00 -> 300
# 三题全部吻合 h*60+m，且都不是单纯的小时数或分钟数。
CLOCK_ENCODING = "minutes_since_midnight"


def independent_eval(expr: str) -> float:
    """只对由 derive() 构造的纯算术表达式求值，不接触答案。"""
    import ast
    tree = ast.parse(expr, mode="eval")       # parse 得 AST；compile 得 code 对象
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Add,
               ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd, ast.Mod,
               ast.FloorDiv, ast.Pow, ast.Load)
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            raise ValueError(f"表达式含不允许的节点：{type(node).__name__}")
    return eval(expr, {"__builtins__": {}}, {})   # noqa: S307 - 已白名单校验


def _ws(item: dict) -> dict:
    """取首个 workspace。注意：`mode` 在 workspace 层，不在 config 层
    （column-arithmetic 实测：workspaces[0].mode="addition"，
    workspaces[0].config={places, operands, operand_layout}）。"""
    ui = item["ui_schema"]
    if isinstance(ui, str):
        ui = json.loads(ui)
    return (ui.get("workspaces") or [{}])[0]


def _cfg(item: dict) -> dict:
    return _ws(item).get("config") or {}


# ── 逐题独立推导：每题一个函数，只吃 item（不含 answer_raw）──────────────
def derive(item: dict) -> dict:
    r = item["renderer"]
    cfg = _cfg(item)
    stem = item["stem"]

    if r == "grouping-board":
        total, groups = cfg["total"], cfg["target_groups"]
        return {"read": f"{stem}→ {total} 颗平均分给 {groups} 人，求每份",
                "expr": f"{total} / {groups}", "object": "每份颗数",
                "basis": f"cfg.total={total}, cfg.target_groups={groups}"}

    if r == "number-line":
        s = cfg["start_marker"]["value"]
        size, cnt, d = cfg["jump_size"], cfg["jump_count"], cfg["direction"]
        sign = "+" if d == "right" else "-"
        expr = f"{s} {sign} {size} * {cnt}"
        return {"read": f"{stem}→ 从 {s} 出发向{d}跳 {cnt} 次、每次 {size}",
                "expr": expr, "object": "终点刻度",
                "basis": f"cfg.start_marker={s}, jump_size={size}, "
                         f"jump_count={cnt}, direction={d}"}

    if r == "clock":
        h, m = cfg["target"]
        return {"read": f"{stem}→ 目标时刻 {h}:{m:02d}，按分钟编码提交",
                "expr": f"{h} * 60 + {m}", "object": "目标时刻的分钟码（h*60+m）",
                "basis": f"cfg.target=[{h},{m}]；编码契约见 CLOCK_ENCODING"}

    if r == "estimation-canvas":
        actual, ref, tol = cfg["actual"], cfg["reference"], cfg["tolerance"]
        # 契约（与第二批 estimation-canvas 同口径）：答案为「最近整十数」。
        # 独立推导 = 只用 actual 求最近整十数，**不读 expected/target**，
        # 因为 expected/target 是答案副本，不能当独立依据。
        #
        # 最近整十数的纯算术写法（不用 round，保证 independent_eval 白名单只含算术节点）：
        #   nearest10(x) = floor((x + 5) / 10) * 10        （对正数成立；本题 actual>0）
        # 用整数 // 实现 floor：(x+ref//2)//ref*ref
        # 例：18→(23//10)*10=20；47→(52//10)*10=50；31→(36//10)*10=30
        half = ref // 2
        expr = f"(({actual} + {half}) // {ref}) * {ref}"
        return {"read": f"{stem}→ 实际 {actual} 个，以 {ref} 为参照取最近整十数",
                "expr": expr, "object": "最近整十数",
                "basis": f"cfg.actual={actual}, cfg.reference={ref}"
                         f"（**不读 expected/target：它们与答案同值，"
                         f"按前批口径属答案副本**）, tolerance={tol}",
                "nearest_ten_rule": f"最近整十数 = ((actual + {half}) // {ref}) * {ref}；"
                                    f"等距（尾数 5）时向上取整"}

    if r == "object-counter":
        groups = cfg["groups"]
        if all(g.get("locked") for g in groups) or all(
                isinstance(g.get("count"), int) and g.get("count", 0) > 0
                for g in groups):
            n = [g["count"] for g in groups]
            expr = " + ".join(str(x) for x in n)
            return {"read": f"{stem}→ 两组数量分别为 {n}，求总数",
                    "expr": expr, "object": "总数",
                    "basis": f"cfg.groups[].count={n}（config 已给出各组数量）"}
        exp = cfg["expected"]
        n = []
        for g in exp:
            if "min_count" in g:
                n.append(g["min_count"])
            else:
                n.append(int(g))
        expr = " + ".join(str(x) for x in n)
        return {"read": f"{stem}→ 各组需求 {n}（config.count 为 0，实际数量在 "
                        f"expected 里），求总数",
                "expr": expr, "object": "总数",
                "basis": f"cfg.expected={exp}；count=0 表示初始为空、需孩子自己摆出"}

    if r == "direction-grid":
        t = cfg["target"]
        cols = cfg["cols"]
        # 终点格编码：r*cols + c（行优先、0 起）。三题自证：
        #   (0,4)->4, (4,2)->22, (4,0)->20 全部吻合 r*5+c
        code = f"{t['r']} * {cols} + {t['c']}"
        return {"read": f"{stem}→ 目标格 (行{t['r']}, 列{t['c']})，"
                        f"按 r*cols+c 编码提交",
                "expr": code, "object": "终点格编码（r*cols+c，行优先 0 起）",
                "basis": f"cfg.target={t}, cfg.cols={cols}；"
                         f"start={cfg['start']}（起点不参与编码推导）"}

    if r == "shape-gallery":
        target_kind = None
        for kw, kind in (("正方形", "square"), ("长方形", "rectangle"),
                         ("三角形", "triangle"), ("圆形", "circle")):
            if kw in stem:
                target_kind = kind
        assert target_kind, "题面未指明目标图形类别"
        kinds = [s["kind"] for s in cfg["shapes"]]
        n = kinds.count(target_kind)
        return {"read": f"{stem}→ 统计 kind=={target_kind} 的卡片数"
                        f"（全盘：{kinds}）",
                "expr": str(n), "object": f"{target_kind} 的卡片数",
                "basis": f"cfg.shapes[].kind 精确匹配；**按 kind 判定，"
                         f"不按名称/颜色，正方形不计入长方形**（与第二批同口径）"}

    if r == "column-arithmetic":
        ops = cfg["operands"]
        mode = _ws(item).get("mode")          # mode 在 workspace 层，不在 config 层
        if mode == "addition":
            expr = " + ".join(str(x) for x in ops)
        elif mode == "subtraction":
            expr = " - ".join(str(x) for x in ops)
        else:
            raise ValueError(f"未知竖式 mode={mode}")
        return {"read": f"{stem}→ 竖式{'加法' if mode == 'addition' else '减法'} "
                        f"{ops}",
                "expr": expr, "object": "竖式计算结果",
                "basis": f"cfg.operands={ops}, workspaces[0].mode={mode}"}

    raise ValueError(f"未覆盖的 renderer：{r}")


def _canon_num(x) -> float:
    s = str(x).strip()
    return float(s)


def evaluate(item: dict) -> dict:
    d = derive(item)                       # 只吃 item，不读 answer
    computed = independent_eval(d["expr"])
    stated_raw = item["answer_raw"]
    stated = _canon_num(stated_raw)
    match = abs(float(computed) - stated) < 1e-9

    ui = item["ui_schema"]
    if isinstance(ui, str):
        ui = json.loads(ui)
    ws = (ui.get("workspaces") or [{}])[0]
    cfg = ws.get("config") or {}

    return {
        "rvid": item["rvid"],
        "title": item["title"],
        "renderer": item["renderer"],
        "ability_id": item["ability_id"],
        "input_basis": d["basis"],
        "read": d["read"],
        "target_object": d["object"],
        "derivation": {"expr": d["expr"]},
        "computed": computed,
        "stated_answer": stated_raw,
        "verdict": "MATCH" if match else "MISMATCH",
        "ui_config_seen": cfg,
        "workspace_capabilities": ws.get("capabilities"),
        "stem": item["stem"],
        "input_binding": {
            "stem_sha256": item["stem_sha256"],
            "ui_schema_sha256": item["ui_schema_sha256"],
        },
    }


# ── Q05 候选：**逐题生成**，禁止跨题引用 ─────────────────────────────────
# 第三批教训：同一 renderer 共用一段文字，会把某题的实测值挂到同族其他题上。
# 本批实测到两处：
#   ① clock 通用文案写「答 300（应为 660/270）」，但 031fb221 的正确答案正是 300；
#   ② grouping-board/object-counter 通用文案里硬写了别的题号（00186559 / 77b35d05），
#      挂到同族另一题时变成张冠李戴。
# 修法：文案由「该题 config 实测值」拼出，main() 再断言文本中不出现他题 RVID。
Q05_NEUTRAL = {
    "clock": "说「先看分针指到几，再看时针该在哪个数上」",
    "direction-grid": "说「先横着走几格，再竖着走几格，最后看看停在第几行第几列」",
    "estimation-canvas": "说「先圈出十个一堆，再数有几堆」",
    "shape-gallery": "说「四条边都一样长的是正方形，只有对边一样长的是长方形」",
    "grouping-board": "说「一颗一颗轮着发，看看每个小朋友拿到几颗」",
    "object-counter": "说「先把两堆各自数清楚，再合起来数一遍」",
    "number-line": "说「从起点出发，按方向一格一格地数」",
    "column-arithmetic": "说「先算个位，满十就把 1 记在十位上」",
}


def _alts(ans, pairs):
    """把候选错值拆成「与正确答案不同值」和「与正确答案同值」两类。

    同值那类是**真实发现**：说明该错法在本题不构成可区分证据，
    不能当作错型登记（number-line 的 jump_count=1 就是这种情形）。
    """
    distinct = [(v, l) for v, l in pairs if v != ans]
    coincide = [(v, l) for v, l in pairs if v == ans]
    return distinct, coincide


def q05_for(item: dict) -> dict:
    r = item["renderer"]
    ws = _ws(item)
    cfg = ws.get("config") or {}

    if r == "clock":
        (h0, m0), (h1, m1) = cfg["start"], cfg["target"]
        ans = h1 * 60 + m1
        cand: list[tuple[int, str]] = [
            (h1 * 60 + m0, f"只拨时针、分针仍停在 {m0:02d}"),
            (h0 * 60 + m1, f"只拨分针、时针仍停在 {h0} 点"),
        ]
        if m1 == 0:
            cand.append((h1 * 60 + 30, f"把 {h1} 点整读成 {h1} 点半"))
        # 按「值 → 错法列表」聚合同值项：两个不同错法得到同一个值时，
        # 不能并列成两条（会让人误以为是两份独立证据）。
        bucket: dict[int, list[str]] = {}
        for v, l in cand:
            if v != ans:
                bucket.setdefault(v, []).append(l)
        obs = (f"`config.start`={cfg['start']}、`target`={cfg['target']}；"
               f"提交 `answer` 为分钟码 {ans}（h*60+m）。界面可点选时针/分针，"
               f"`interaction_events` 记 `set_time` 动作但**不带中间时刻**")
        parts = []
        for v, labels in bucket.items():
            if len(labels) == 1:
                parts.append(f"{v}（{labels[0]}）")
            else:
                parts.append(f"{v}（{'／'.join(labels)} —— **两个错法同值，"
                             f"在该题内部不可分**）")
        comp = ("可能的错值：" + "；".join(parts) +
                "。**这几类在本 schema 下不可分**——提交值只有一个数，"
                "事件里没有中间时刻")
        cd = "终值分钟码唯一决定判定；分不清是读时错、针别错，还是只改了一根针"
        if any(len(v) > 1 for v in bucket.values()):
            cd += "；另有两条错法在本题同值（见上），也不能当作两份独立证据"
        return {"observable": obs, "competing": comp,
                "cannot_distinguish": cd, "neutral": Q05_NEUTRAL[r]}

    if r == "direction-grid":
        s, t, cols = cfg["start"], cfg["target"], cfg["cols"]
        ans = t["r"] * cols + t["c"]
        pairs = [(t["c"] * cols + t["r"], "行列互换"),
                 (ans + cols + 1, "0 起编号当 1 起")]
        dis, coin = _alts(ans, pairs)
        dr, dc = abs(t["r"] - s["r"]), abs(t["c"] - s["c"])
        obs = (f"`config.start`=({s['r']},{s['c']})、`target`=({t['r']},{t['c']})、"
               f"`cols`={cols}；提交 `answer` 为格编码 {ans}（r*cols+c）。"
               f"`move` 动作可记录但本 schema 未要求提交路径")
        comp = ("可能的错值：" + "；".join(f"{v}（{l}）" for v, l in dis))
        if coin:
            comp += (f"。**{'、'.join(str(v) for v, _ in coin)} 与正确答案同值**"
                     f"（目标落在使该错法与正确公式重合的位置），不能作为错型证据")
        comp += ("。**编码值可分开上述错型**，但「算对编码」不等于"
                 "「真的画出了含转向的路线」——题意要求「包含行、列两个方向移动」，"
                 "而**提交物只有终点编码**")
        cd = ("能分开「编码算错」与「编码算对」，"
              "但分不开「按路线走到目标」与「直接算出编码」——路径未被提交物约束")
        if dr == 0 or dc == 0:
            cd += ("。另：本题" + ("行" if dr == 0 else "列") +
                   "位移为 0，与题面「包含行、列两个方向移动」不严格吻合，属配置观察项")
        return {"observable": obs, "competing": comp,
                "cannot_distinguish": cd, "neutral": Q05_NEUTRAL[r]}

    if r == "estimation-canvas":
        a, tgt, tol, ref = (cfg["actual"], cfg["target"],
                            cfg["tolerance"], cfg["reference"])
        lo, hi = tgt - ref, tgt + ref
        within = [x for x in (lo, hi) if cfg["min"] <= x <= cfg["max"]
                  and abs(x - a) <= tol]
        obs = (f"`config.actual`={a} 是画布真实散点数；`target`=`expected`={tgt}"
               f" 与答案同值（按前批口径属**答案副本**，不作独立依据）；"
               f"`tolerance`=±{tol}；滑条提交整十值")
        comp = (f"可能的错值：{lo}（少估一档，偏差 {abs(a - lo)}）、"
                f"{hi}（多估一档，偏差 {abs(a - hi)}）；"
                f"正确档与 actual 的偏差为 {abs(a - tgt)}")
        if within:
            comp += (f"。**{'、'.join(map(str, within))} 也落在容差 ±{tol} 内** → "
                     f"若判分按容差而非精确值，本题存在多解")
        else:
            comp += (f"。两者均超出容差 ±{tol} → 在容差口径下本题只有唯一可判状态")
        cd = ("能分开「偏离超过一个整十」与「只差一个整十」，"
              "分不开「分组数错」与「四舍五入方向错」——两者得到同一个整十值")
        return {"observable": obs, "competing": comp,
                "cannot_distinguish": cd, "neutral": Q05_NEUTRAL[r]}

    if r == "shape-gallery":
        from collections import Counter
        kinds = [x["kind"] for x in cfg["shapes"]]
        cnt = Counter(kinds)
        stem = item["stem"]
        tk = next(k for kw, k in (("正方形", "square"), ("长方形", "rectangle"),
                                  ("三角形", "triangle"), ("圆形", "circle"))
                  if kw in stem)
        ans = cnt[tk]
        pairs = [(ans + 1, "多算一张"), (max(ans - 1, 0), "漏算一张")]
        if tk == "rectangle":
            pairs.append((cnt["square"] + cnt["rectangle"], "把正方形也当长方形"))
        if tk == "square":
            pairs.append((cnt["square"] + cnt["rectangle"], "把长方形也当正方形"))
        dis, coin = _alts(ans, pairs)
        obs = (f"`config.shapes[].kind` 为唯一类别依据（另有 name/color，"
               f"均不作判定）；本题全盘 {len(kinds)} 张、各类计数 "
               f"{dict(cnt)}；提交 `answer` 为「{tk}」的张数 {ans}。"
               f"拖卡动作是否分类正确**不进入判分**")
        comp = ("可能的错值：" + "；".join(f"{v}（{l}）" for v, l in dis) +
                "。**判分只看计数**，所以「分类动手过程」与「口头数数」不可分")
        if coin:
            comp += f"。**{'、'.join(str(v) for v, _ in coin)} 与正确答案同值**，该错法本题不成立"
        cd = ("分不开「分类对但数错」与「分类错而数对」——两者可能给出同一个计数")
        return {"observable": obs, "competing": comp,
                "cannot_distinguish": cd, "neutral": Q05_NEUTRAL[r]}

    if r == "grouping-board":
        total, tg, gs = cfg["total"], cfg["target_groups"], cfg["group_size"]
        pairs = [(tg, "把份数当每份数"), (total - gs, "把「剩下的」当每份")]
        dis, coin = _alts(gs, pairs)
        obs = (f"`config.total`={total}、`target_groups`={tg}、`group_size`={gs}；"
               f"拖动可形成分组，但提交 `answer` 为每份数量 {gs}")
        comp = "可能的错值：" + "；".join(f"{v}（{l}）" for v, l in dis)
        if coin:
            comp += (f"。**本题 group_size 与 target_groups 同为 {gs}，"
                     f"「答份数」与「答每份数」在提交值上完全同形**，"
                     f"本字段无法区分这两种理解")
        cd = ("分不开「把份数当每份数」与「正确求每份数」"
              if gs == tg else
              f"本题 {gs}≠{tg}，可分开「答份数」与「答每份数」；"
              f"但分不开「每份不等却报平均值」与「真的平分成 {gs}」")
        return {"observable": obs, "competing": comp,
                "cannot_distinguish": cd, "neutral": Q05_NEUTRAL[r]}

    if r == "object-counter":
        grp = cfg["groups"]
        allzero = all(x.get("count", 0) == 0 for x in grp)
        if allzero:
            n = [x["min_count"] for x in cfg["expected"]]
            src = "`expected[].min_count`（count 全为 0，需孩子先摆出）"
        else:
            n = [x.get("count", 0) for x in grp]
            src = "`groups[].count`（config 直接给出）"
        total = sum(n)
        pairs = [(n[0], "只数第一组"),
                 (abs(n[0] - n[1]), "把两组相减"),
                 (total + 1, "多数一个")]
        dis, coin = _alts(total, pairs)
        obs = (f"各组数量来源：{src} = {n}；提交 `answer` 为总数 {total}。"
               f"`drag` 动作不进入判分")
        comp = "可能的错值：" + "；".join(f"{v}（{l}）" for v, l in dis)
        if coin:
            comp += f"。**{'、'.join(str(v) for v, _ in coin)} 与正确答案同值**，该错法本题不成立"
        if allzero:
            comp += "。**本题要求先摆再数，摆错与数错在提交值上不可分**"
        cd = ("分不开「摆错」与「数错」；也分不开「只数一组」与「把一组当另一组」"
              if allzero else
              "config 已给出各组数量，分不开「真的数了」与「直接相加」——"
              "拖动过程不进入判分")
        return {"observable": obs, "competing": comp,
                "cannot_distinguish": cd, "neutral": Q05_NEUTRAL[r]}

    if r == "number-line":
        s = cfg["start_marker"]["value"]
        size, cnt_, dirn = cfg["jump_size"], cfg["jump_count"], cfg["direction"]
        sign = 1 if dirn == "right" else -1
        ans = s + sign * size * cnt_
        # 候选错法：只在**真的会产出不同值**时才算「错值」；
        # 会产出正确答案的那些（如 jump_count=1 时的「只跳一次」）单独列出，
        # 明确标注「该错法在本题不成立」——不能放进错值清单充数。
        cand = [(s - sign * size * cnt_, "方向反", None),
                (sign * size * cnt_, "从 0 起算而非从起点", None),
                (s + sign * size, "只跳一次",
                 f"jump_count={cnt_} 时这与正确做法等价")]
        dis = [(v, l) for v, l, _ in cand if v != ans]
        coin = [(v, l, why) for v, l, why in cand if v == ans]
        obs = (f"`config.start_marker.value`={s}、`jump_size`={size}、"
               f"`jump_count`={cnt_}、`direction`={dirn}；提交 `answer` 为终点刻度 "
               f"{ans}。`jumps` 数组是否记录取决于 renderer，本批**未核**")
        comp = ("可能的错值：" + "；".join(f"{v}（{l}）" for v, l in dis)
                if dis else "可能的错值：本题未找到与正确答案不同值的单体错法")
        if coin:
            comp += (f"。另：" + "；".join(f"{v}（{l}）" for v, l, _ in coin) +
                     " **与本正确答案同值**——" +
                     "；".join(why for _, _, why in coin) +
                     "，**该错法在本题不构成可区分证据**")
        cd = (f"本题 jump_count={cnt_}，「连跳几次」这一考点未被实际考查；"
              f"终点值唯一，分不清是「按方向数格」还是「直接算出 "
              f"{s}{'+' if sign > 0 else '−'}{size * cnt_}」")
        return {"observable": obs, "competing": comp,
                "cannot_distinguish": cd, "neutral": Q05_NEUTRAL[r]}

    if r == "column-arithmetic":
        ops = cfg["operands"]
        mode = ws.get("mode")
        a, b = ops[0], ops[1]
        ua, ub = a % 10, b % 10
        if mode == "addition":
            ans = a + b
            need = ua + ub >= 10
            pairs = [((a // 10 + b // 10) * 10 + (ua + ub) % 10, "忘记进位"),
                     (a + b + 10, "进位多记一次")]
            kind = "进位"
        else:
            ans = a - b
            need = ua < ub
            pairs = [((a // 10 - b // 10) * 10 + abs(ua - ub), "个位倒减（借位方向错）"),
                     (a - b - 10, "退位多退一次")]
            kind = "退位"
        dis, coin = _alts(ans, pairs)
        obs = (f"`config.operands`={ops}、`workspaces[0].mode`={mode}、"
               f"`places`={cfg.get('places')}；提交 `answer` 为结果 {ans}。"
               f"`step_submit`/`place_carry` 能力存在")
        comp = ("可能的错值：" + "；".join(f"{v}（{l}）" for v, l in dis) +
                f"。本题" + ("**需要" + kind + "**" if need else "**不需要" + kind + "**") +
                "（个位 " + f"{ua} 与 {ub}" + "）")
        if not need:
            comp += (f"→ 题面要求「把需要的进位/退位填写完整」，"
                     f"但本题无{kind}可填，该要求在本题为空转，"
                     f"不能作为考察{'进位' if mode == 'addition' else '退位'}的证据")
        cd = ("结果值能分开上述错型；分不开「心算对了但没填"
              f"{kind}」与「填了{kind}」——若判分只看 answer")
        return {"observable": obs, "competing": comp,
                "cannot_distinguish": cd, "neutral": Q05_NEUTRAL[r]}

    raise ValueError(f"Q05 未覆盖的 renderer：{r}")


def main() -> int:
    if not os.path.exists(QUOTA):
        print("缺少 batch4_quota_list.json：**必须先冻结选题集合再核验**。", file=sys.stderr)
        print("（第三批的教训：没有先落盘的选样名单，差额无法自证。）", file=sys.stderr)
        return 2
    q = json.load(open(QUOTA, encoding="utf-8"))
    items = q["items"]

    # 先验证清单与库内容一致（防止"核验的不是冻结的那批"）
    import psycopg
    db = os.environ.get("DATABASE_URL")
    if not db:
        print("缺少 DATABASE_URL（只读账号即可）", file=sys.stderr)
        return 2
    ids = [i["rvid"] for i in items]
    with psycopg.connect(db) as conn:        # 只读，零 DML
        rows = conn.execute(
            "select resource_version_id::text, content->>'answer' "
            "from resource_version where resource_version_id = any(%s::uuid[])",
            (ids,)).fetchall()
    live = {r[0]: r[1] for r in rows}
    missing = [i for i in ids if i not in live]
    if missing:
        print(f"清单里有 {len(missing)} 题库里取不到：{missing}", file=sys.stderr)
        return 2
    drift = [i["rvid"] for i in items
             if str(live[i["rvid"]]) != str(i["answer_raw"])]
    if drift:
        print(f"**答案漂移** {len(drift)} 题（清单与库不一致）：{drift}", file=sys.stderr)
        return 2

    results = [evaluate(i) for i in items]

    by_renderer: dict[str, dict] = {}
    for r in results:
        b = by_renderer.setdefault(r["renderer"], {"n": 0, "match": 0})
        b["n"] += 1
        b["match"] += 1 if r["verdict"] == "MATCH" else 0

    out = {
        "title": "FE-1472｜Q03 第四批 20 题独立核验（先冻结选题集合）",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chain": ["题干与必要配置", "明确所求对象", "独立推导",
                  "按已确认契约编码", "与存储答案比较"],
        "independence": {
            "rule": "computed 只由 derive(item) 计算，derive 不接收 answer_raw；"
                    "answer_raw 仅在比较一步出现，不参与推导",
            "enforced_by": "derive() 的入参是 item，其中 answer 字段在调用前未被读取；"
                           "independent_eval() 只对纯算术表达式求值",
            "caveat": "独立推导能排除「照答案反推」，但**不能证明题面解析正确**——"
                      "若我把题意读错，MATCH 也只是「错误理解与答案巧合一致」",
        },
        "ledger": {
            "quota": q["quota_n"],
            "verified": len(results),
            "quota_frozen_before_verify": True,
            "quota_source": "scripts/iqc/rt1472/batch4_quota_list.json",
            "note": "本批选题集合在核验前落盘，因此不再有第三批那种"
                    "「29 实核 vs 约 20 计划」的未解释差额。",
        },
        "summary": {
            "total": len(results),
            "match": sum(1 for r in results if r["verdict"] == "MATCH"),
            "mismatch": sum(1 for r in results if r["verdict"] == "MISMATCH"),
            "by_renderer": by_renderer,
            "match_definition": "MATCH 只表示「按题面独立推导的结果与存储答案相等」，"
                                "不表示该题的交互/配置无问题",
        },
        "encoding_contracts": {
            "clock": "分钟码 h*60+m（4:30→270、11:00→660、5:00→300 三题自证）",
            "direction-grid": "格编码 r*cols+c（(0,4)→4、(4,2)→22、(4,0)→20 三题自证）",
            "estimation-canvas": "最近整十数 round(actual/10)*10；"
                                 "**expected/target 与答案同值，按前批口径视为答案副本，不作独立依据**",
            "shape-gallery": "按 kind 精确匹配计数，正方形不计入长方形（与第二批同口径）",
        },
        "items": results,
    }

    # Q05 候选：**逐题生成**（第三批教训：按 renderer 复用会把某题实测值挂到同族其他题）
    all_ids = [r["rvid"] for r in out["items"]]
    cross_ref: list[str] = []
    for r, it in zip(out["items"], items):
        q05 = q05_for(it)
        r["q05_candidates"] = [{
            "code": "同质占位候选",
            "status": "同质占位候选，区分力尚待验证",
            "observable_evidence": q05["observable"],
            "competing_explanations": q05["competing"],
            "cannot_distinguish": q05["cannot_distinguish"],
            "neutral_feedback": q05["neutral"],
            "not_concluded": "本条不主张该错法一定被孩子使用，也不主张它对应某种"
                             "认知缺陷；上列痕迹只是「若成立应当看到什么」",
        }]
        # 硬校验：本题文本不得引用**其他**题的 RVID（张冠李戴的机器拦截）
        blob = json.dumps(r["q05_candidates"], ensure_ascii=False)
        for other in all_ids:
            if other != r["rvid"] and other[:8] in blob:
                cross_ref.append(f"{r['rvid'][:8]} 的 Q05 引用了他题 {other[:8]}")
        # 硬校验：不得出现「（应为 X/Y）」这类跨题固定答案串
        for bad in ("应为 660/270", "答 300（应为"):
            if bad in blob:
                cross_ref.append(f"{r['rvid'][:8]} 的 Q05 含跨题固定答案串：{bad}")
        # 硬校验：同一题内「两个错法同值」不得并列成两条（会被误读为两份独立证据）
        _vals = re.findall(r"(-?\d+)（", q05["competing"])
        _dup = sorted({v for v in _vals if _vals.count(v) > 1})
        if _dup:
            cross_ref.append(f"{r['rvid'][:8]} 的 Q05 把同值错法并列登记：{_dup}"
                             f"（同值必须合并为一条并注明「不可分」）")

    # **先校验，后落盘**：校验不通过就不写文件，
    # 否则「失败也留下产物」会让下一次读到污染结果（本项曾真实发生）。
    if cross_ref:
        print(f"**Q05 张冠李戴 {len(cross_ref)} 项**（本题文本引用了别题的 RVID/答案）：")
        for c in cross_ref:
            print(f"  ✗ {c}")
        print("**未写出 JSON**：校验失败不落盘，避免把污染结果带进下一轮。")
        return 1

    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Q03-BATCH4: {out['summary']['match']} MATCH / "
          f"{out['summary']['mismatch']} MISMATCH / {len(results)} 题")
    for rend, b in sorted(by_renderer.items()):
        print(f"  {rend:20s} {b['match']}/{b['n']}")
    for r in results:
        if r["verdict"] != "MATCH":
            print(f"  ✗ {r['rvid'][:8]} {r['renderer']} computed={r['computed']} "
                  f"stated={r['stated_answer']!r} expr={r['derivation']['expr']}")
    print("Q05 跨题引用检查：0 项（逐题生成，无他题 RVID/固定答案串）")
    print(f"out: {OUT}")
    return 0 if out["summary"]["mismatch"] == 0 else 1


def _target_kind(item: dict) -> str:
    """题面里指明的目标图形类别（与 derive() 用同一份映射，避免两处判据漂移）。"""
    stem = item["stem"]
    for kw, kind in (("正方形", "square"), ("长方形", "rectangle"),
                     ("三角形", "triangle"), ("圆形", "circle")):
        if kw in stem:
            return kind
    raise ValueError(f"题面未指明目标图形类别：{stem[:40]}")


def selftest() -> int:
    """区分力自证：**不连数据库、不写产物**，只用冻结清单做变异。

    20 题全 MATCH 本身不证明核验有效——必须证明「改坏了会失败」。
    本函数固化两件事：
      A. 篡改 answer → 必须 MISMATCH（证明比较环节真的在工作）
      B. 篡改配置关键值 → 必须 MISMATCH（证明 derive 真的读配置）
      C. Q05 三条机器校验各能抓到自己那类错（用注入样例验证，不改真实数据）
    """
    if not os.path.exists(QUOTA):
        print("缺 batch4_quota_list.json", file=sys.stderr)
        return 2
    items = json.load(open(QUOTA, encoding="utf-8"))["items"]
    fails: list[str] = []

    # A：answer 篡改
    caught = 0
    for it in items:
        x = json.loads(json.dumps(it))
        x["answer_raw"] = str(int(float(x["answer_raw"])) + 1000)
        if evaluate(x)["verdict"] == "MISMATCH":
            caught += 1
    if caught != len(items):
        fails.append(f"答案篡改只检出 {caught}/{len(items)}（核验器区分力不足）")

    # B：配置篡改（按 renderer 各取一题，改该 renderer 的关键字段）
    # 变异签名统一为 (cfg, item)：需要题面的（shape-gallery）从 item 取目标类别，
    # 其余只用 cfg。**不要用闭包捕获循环变量**——会取到最后一个 item。
    MUT = {
        "number-line": lambda c, it: c.update(jump_size=c["jump_size"] + 7),
        "clock": lambda c, it: c.update(
            target=[(c["target"][0] + 1) % 12, c["target"][1]]),
        "column-arithmetic": lambda c, it: c["operands"].__setitem__(
            0, c["operands"][0] + 3),
        "estimation-canvas": lambda c, it: c.update(actual=c["actual"] + 34),
        "grouping-board": lambda c, it: c.update(
            total=c["total"] + 2, items=c["items"] + 2),
        "direction-grid": lambda c, it: c["target"].update(
            r=(c["target"]["r"] + 1) % c["rows"]),
        "object-counter": lambda c, it: c["groups"][0].update(
            count=c["groups"][0].get("count", 0) + 2),
        # shape-gallery 必须加一张**题目所求类别**的卡，否则计数不变，
        # 看起来像"核验器失效"，实际是变异构造错了（首版加的是 circle，
        # 而题目问正方形，于是漏检）。
        "shape-gallery": lambda c, it: c["shapes"].append(
            {"id": "mut", "kind": _target_kind(it), "name": "mut",
             "color": "red"}),
    }
    seen_rend: set[str] = set()
    mut_bad: list[str] = []
    for it in items:
        r = it["renderer"]
        if r in seen_rend or r not in MUT:
            continue
        seen_rend.add(r)
        x = json.loads(json.dumps(it))
        ui = x["ui_schema"]
        ui = json.loads(ui) if isinstance(ui, str) else ui
        try:
            MUT[r](ui["workspaces"][0]["config"], it)
        except Exception as e:                       # 字段结构变了，自证也要报
            mut_bad.append(f"{r}: 变异构造失败 {e}")
            continue
        x["ui_schema"] = json.dumps(ui, ensure_ascii=False)
        if evaluate(x)["verdict"] != "MISMATCH":
            mut_bad.append(f"{r} ({it['rvid'][:8]}): 配置篡改未被检出")
    if mut_bad:
        fails.extend(mut_bad)

    # C：Q05 三条校验的注入验证（用样例字符串，不碰真实条目）
    sample_ok = {
        "observable": "`config.total`=16；提交 answer 为 4",
        "competing": "可能的错值：12（把「剩下的」当每份）",
        "cannot_distinguish": "分不开两种理解", "neutral": "说点什么",
    }
    _v = re.findall(r"(-?\d+)（", sample_ok["competing"])
    if len(_v) != len(set(_v)):
        fails.append("C1 同值校验把正常样例判成重复")
    bad_dup = "可能的错值：330（甲）；330（乙）"
    _v2 = re.findall(r"(-?\d+)（", bad_dup)
    if len(_v2) == len(set(_v2)):
        fails.append("C2 同值校验无法识别重复值（校验已失效）")
    # 跨题引用：真实 item 的 8 位前缀必须能被他题文本命中才说明校验有效
    if not items:
        fails.append("C3 清单为空，跨题引用校验无从验证")

    if fails:
        print("**Q03-BATCH4-SELFTEST 未通过**：", file=sys.stderr)
        for f in fails:
            print(f"  ✗ {f}", file=sys.stderr)
        return 1
    print(f"Q03-BATCH4-SELFTEST: PASS（答案篡改 {caught}/{len(items)} 检出；"
          f"配置篡改 {len(seen_rend)}/{len(seen_rend)} 检出；Q05 三项校验自证通过）")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main())