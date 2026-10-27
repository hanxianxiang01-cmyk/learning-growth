"""FE-1472 第六批｜Q03 construct_constraint 族逐题独立核验（读 batch6_quota_list.json）。

## 与前五批的三处方法学差别

前五批核的都是 `numeric_judge`（95 题全部该族）。本批**首次开
`construct_constraint` 整族**（54 题，此前 0 题完成），因此出现三件前五批
不存在的事：

1. **答案不是「算出来的一个数」，而是「构造结果被编码成的一个数」**
   - sorting-board：排好序后拼成多位数（[4,9,1,6] 升序 → 1469）
   - place-value：按位名拼数（十位5、个位8 → 58）
   - pattern-board：空格 token 顺序拼接（补 4、2 → 42）
   - shape-canvas：面积 = 边长之积
   编码常量（位权 10/100/1000）会被「表达式数字 ⊆ 题干数字」判据判为
   题干外数字——那是**编码规则**，不是抄 config。故本批把这类数字单独
   登记进 `encoding_constants`，不混入「不独立」的指控。

2. **题面可完成性成为独立判据**（本批新增维度）
   `shape-canvas` 的组件 `parseShapeCanvasConfig` 只读 `grid/target_area/
   target_shape`，且 `applyAddPoint` 把点约束在 `0..grid-1`——**grid 是钉位数
   不是格数**，可画的最大边长是 `grid-1`。题面写「5×5 方格纸」时孩子看到的
   是 4×4 格。若题面要求「长 5 格」，该矩形在板上根本画不出来。
   本批对每题穷举钉位、判定「题面所要求的形状是否真的画得出」。

3. **过程约束从「声明了但没启用」变成「部分启用」**
   第五批 20 题 `process_constraint` 全为 null（观察项 EVIDENCE_DECLARED_
   BUT_NOT_ENFORCED）。本批实测 **17/20 带 process_constraint**——不带 pc 的
   3 题是 array-board 1 题 + sorting-board 2 题，这 17 题后端
   `process_validate.py` 会真校验。
   **全族口径是 37/54，不是「54 题全部带」**（上一轮笔记曾如此误记，本批实地
   统计更正，见 `_family_process_coverage()`）；缺口 17 题全部落在
   array-board（8/8 全无）与 sorting-board（9/9 全无），而后端 RULES 只有
   pattern_extension / payment_change / shape_drawing / place_value_build 四个
   mode，没有这两类的校验器——属**过程校验能力缺口**，不是题目漏配。
   且「已启用」不等于「过程正确就能被发现」：`_rule_shape` 只重算面积与直角，
   **不读 base/height**，所以画一个同样面积的斜正方形仍判 valid。此边界本批
   显式登记。

核验链（每步可单独复核）：
  题干 → 抽取题面事实 → 明确所求对象 → 独立推导/构造（纯算术）
       → 断言 config 已知量 ⊆ 题面事实 → 题面可完成性 → 与存储答案比较

用法：
  export DATABASE_URL="$(security find-generic-password -s iqc-database-url -w)"
  python scripts/iqc/rt1472/q03_batch6.py
  python scripts/iqc/rt1472/q03_batch6.py --selftest   # 门禁用，不连库
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
from contextlib import redirect_stdout
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


def _check_layout() -> int:
    """确认脚本位于仓库内，否则以 2 退出（0=正常继续）。

    与 `check_independence.py` 同款修法：`assert` 触发时进程以 **1** 结束，
    与「1 = 核验失败」撞码。直接解压交付件（扁平目录）跑会得到 rc=1，
    看起来像结论不成立，其实只是布局不对。
    """
    if not os.path.isdir(os.path.join(REPO, "scripts", "iqc")):
        print(f"REPO 层级算错：{REPO}（其下没有 scripts/iqc/）", file=sys.stderr)
        print(f"  本脚本预期位于 <repo>/scripts/iqc/rt1472/，当前实际在：{HERE}",
              file=sys.stderr)
        print("  退出码 2 = 环境/布局问题，**不是核验失败**。", file=sys.stderr)
        return 2
    return 0


_L = _check_layout()
if _L:
    sys.exit(_L)

QUOTA = os.path.join(HERE, "batch6_quota_list.json")
OUT = os.path.join(REPO, "scripts/iqc/runs/FE1472_q03_batch6.json")

# 中文数字（题面里的空格数写作「两格」）
CN_NUM = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5}
# 位名的权重
PLACE_WEIGHT = {"千": 1000, "百": 100, "十": 10, "个": 1}


def independent_eval(expr: str) -> float:
    """只对由 derive() 构造的纯算术表达式求值，不接触答案。

    白名单**不含 IfExp**——判断题/分支题不得用三元表达式把判断塞进 expr，
    判断必须写在 `encode` 里（第五批踩过：塞 IfExp 直接 ValueError）。
    """
    import ast
    tree = ast.parse(expr, mode="eval")
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Add,
               ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd, ast.Mod,
               ast.FloorDiv, ast.Pow, ast.Load)
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            raise ValueError(f"表达式含不允许的节点：{type(node).__name__}")
    return eval(expr, {"__builtins__": {}}, {})   # noqa: S307 - 已白名单校验


def _ws(item: dict) -> dict:
    ui = item["ui_schema"]
    if isinstance(ui, str):
        ui = json.loads(ui)
    return (ui.get("workspaces") or [{}])[0]


def _cfg(item: dict) -> dict:
    return _ws(item).get("config") or {}


def _nums(text: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", text)]


def _cn_or_digit(tok: str) -> int | None:
    if tok.isdigit():
        return int(tok)
    return CN_NUM.get(tok)


def _concat_expr(tokens: list[int]) -> str:
    """把一串一位数按顺序拼成整数：位权展开（编码规则，不是答案）。

    `[4,9,1,6]` → `4*1000 + 9*100 + 1*10 + 6`。位权（1000/100/10）是
    **编码常量**，会出现在 `encoding_constants` 里，不据此判「不独立」。
    """
    n = len(tokens)
    parts = []
    for i, t in enumerate(tokens):
        w = 10 ** (n - 1 - i)
        parts.append(f"{t} * {w}" if w > 1 else f"{t} * 1")
    return " + ".join(parts)


def _encoding_constants(expr: str, stem: str) -> list[dict]:
    """列出 expr 里不出现在题干中的数字，供人工分诊（不是判决）。

    与 `check_independence.py` 的口径一致：这条判据只能出线索。
    本批的编码常量（位权）与「抄 config」在数字层面无法区分，
    必须靠 `purpose` 字段逐条写明。

    **必须排除 `* 1`**：个位权重为 1 时表达式写 `d * 1`，那个 `1` 是
    「不乘位权」的句式产物，不是信息量。不排除会让 7 道题各报一条
    `UNCLASSIFIED`，把真实待分诊项淹没（首版实测踩到）。
    """
    stem_nums = set(_nums(stem))
    out = []
    for n in sorted({x for x in _nums(expr)}):
        if n in stem_nums:
            continue
        if n == 1:
            # 个位权重 1（或单件题 `a * 1` 的恒等乘）——句式产物，非数据
            out.append({"value": 1,
                        "purpose": "个位位权=1（`d * 1` 即不乘位权，句式产物）"})
            continue
        if n in (10, 100, 1000):
            out.append({"value": n, "purpose": "进位权（十进制位值编码规则）"})
            continue
        out.append({"value": n, "purpose": "UNCLASSIFIED"})
    return out


# ── 题面可完成性（本批新增维度）──────────────────────────────────────────
def geometry_feasibility(stem: str, cfg: dict, base: int, height: int) -> dict:
    """判定「题面要求的那个长方形，在组件板上是否画得出来」。

    两件事必须分开，混在一起会把题面缺陷记成组件缺陷：

      A. `stem_grid`：题面自称的方格纸尺寸（「5×5方格纸」→ 5）。
         按常理 5×5 方格纸有 6×6 个格点，能画长 5 格的矩形——**题面自洽**。
      B. `component_span`：组件实际能画的跨度 = `grid - 1`。
         `parseShapeCanvasConfig` 只读 grid，`applyAddPoint` 用
         `0 <= x < grid` 约束钉位，`ShapeCanvasV2.tsx:140` 的
         `span = (grid - 1) * CELL` 证实渲染跨度只有 grid-1 格。

    因此 `base <= stem_grid` 但 `base > grid - 1` 时，题面自洽、板上做不到。
    """
    m = re.search(r"(\d+)\s*[×xX]\s*(\d+)\s*方格纸", stem)
    stem_grid = int(m.group(1)) if m else None
    grid = cfg.get("grid")
    area = cfg.get("target_area")
    out = {
        "stem_grid_declared": stem_grid,
        "component_grid": grid,
        "component_span": (grid - 1) if isinstance(grid, int) else None,
        "required_base": base, "required_height": height,
        "stem_self_consistent": (stem_grid is not None and base <= stem_grid
                                 and height <= stem_grid),
        "fits_component_board": (isinstance(grid, int)
                                 and base <= grid - 1 and height <= grid - 1),
        "area_reachable_on_component": None,
        "area_reachable_without_side_constraint": None,
    }
    if isinstance(grid, int) and isinstance(area, int):
        out["area_reachable_on_component"] = any(
            a * b == area for a in range(1, grid) for b in range(1, grid))
    if stem_grid:
        out["area_reachable_without_side_constraint"] = any(
            a * b == area for a in range(1, stem_grid + 1)
            for b in range(1, stem_grid + 1))
    out["verdict"] = ("FEASIBLE" if (out["stem_self_consistent"]
                                     and out["fits_component_board"])
                      else "INFEASIBLE_ON_COMPONENT")
    return out


# ── 逐题独立推导（六类 renderer / 四类 solve_path）───────────────────────
def derive(item: dict) -> dict:
    r = item["renderer"]
    stem = item["stem"]
    cfg = _cfg(item)
    cons: list[str] = []
    extra: dict = {}

    # ── money-board（numeric_exact）────────────────────────────────────
    if r == "money-board":
        # 两种题面写法必须分开处理，不能一律当「两件相加」：
        #   A 两件：「一件文具标价20角，另一件标价15角」→ 20+15
        #   B 单件：「一本练习本标价35角」→ 题面直接给总价
        prices = [int(x) for x in re.findall(r"标价\s*(\d+)\s*角", stem)]
        if "另一件" in stem:
            if len(prices) < 2:
                raise ValueError(f"money-board 两件题抽不到两个标价：{stem[:60]}")
            a, b = prices[0], prices[1]
            expr = f"{a} + {b}"
            read = f"{stem}→ 两件标价 {a} 角与 {b} 角，求总价"
            obj = f"总价（{a}+{b} 角）"
            kind = "two_items_sum"
        else:
            if not prices:
                raise ValueError(f"money-board 单件题抽不到标价：{stem[:60]}")
            a = prices[0]
            expr = f"{a} * 1"
            read = f"{stem}→ 题面已给单件总价 {a} 角，无需再运算"
            obj = f"总价（题面直给 {a} 角）"
            kind = "single_item_direct"
        if cfg.get("price") != independent_eval(expr):
            cons.append(f"config.price={cfg.get('price')} ≠ 推导 "
                        f"{int(independent_eval(expr))}")
        target = cfg.get("target") or {}
        if target.get("total") not in (None, independent_eval(expr)):
            cons.append(f"config.target.total={target.get('total')} ≠ 推导")
        extra["money_variant"] = kind
        return {"read": read, "expr": expr, "object": obj,
                "basis": (f"题面抽出标价 {prices[:2]}（{kind}）；"
                          f"config.price={cfg.get('price')}、"
                          f"target.total={target.get('total')} 仅作交叉核对；"
                          f"**不读答案**"),
                "consistency": cons, "extra": extra}

    # ── place-value（digit_config）──────────────────────────────────────
    if r == "place-value":
        # 题面两处信息：卡片池「位值卡片[5, 8]」+ 位名指派「十位是5，个位是8」
        mp = re.search(r"位值卡片\s*\[([\d,\s]+)\]", stem)
        pool_read = [int(x) for x in re.findall(r"\d+", mp.group(1))] if mp else []
        assigns = re.findall(r"(千|百|十|个)位是\s*(\d+)", stem)
        if not assigns:
            raise ValueError(f"place-value 抽不到位名指派：{stem[:60]}")
        # 每个数字放进 it 声明的位；缺位位补 0 不行——必须每位都有声明
        by_place: dict[str, int] = {p: int(d) for p, d in assigns}
        declared_places = [p for p, _ in assigns]
        # 权重从题面位数推，不读 config.target
        n_digits = len(declared_places)
        ordered = ["千", "百", "十", "个"][-n_digits:]
        if sorted(declared_places) != sorted(ordered):
            cons.append(f"题面声明的位 {declared_places} 与 {n_digits} 位数的位序不符")
        digits = [by_place.get(p) for p in ordered]
        if any(d is None for d in digits):
            raise ValueError(f"place-value 有位没给数字：{assigns}")
        # expr 用位名权重展开（编码规则），不用 5*10+8 之外的任何东西
        parts = []
        for p, d in zip(ordered, digits):
            w = PLACE_WEIGHT[p]
            parts.append(f"{d} * {w}" if w > 1 else f"{d} * 1")
        expr = " + ".join(parts)
        if cfg.get("target") is not None and cfg["target"] != independent_eval(expr):
            cons.append(f"config.target={cfg.get('target')} ≠ 位名拼数 "
                        f"{int(independent_eval(expr))}")
        # 卡片池 multiset 必须等于拼出来的数字的各位（否则「只能错在位」不成立）
        if pool_read:
            if sorted(pool_read) != sorted(digits):
                cons.append(f"题面卡片池 {sorted(pool_read)} ≠ 目标各位 "
                            f"{sorted(digits)}")
            if cfg.get("pool") is not None and sorted(cfg["pool"]) != sorted(pool_read):
                cons.append(f"config.pool={cfg.get('pool')} ≠ 题面卡片池 {pool_read}")
        extra["place_assignment"] = dict(zip(ordered, digits))
        extra["digit_count"] = n_digits
        return {"read": f"{stem}→ 卡片池 {pool_read}，位名指派 "
                        f"{dict(zip(declared_places, [int(d) for _, d in assigns]))}",
                "expr": expr,
                "object": f"按位拼出的数（{'/'.join(f'{p}{d}' for p, d in zip(ordered, digits))}）",
                "basis": (f"题面抽出卡片池 {pool_read} 与位名指派；"
                          f"位权 {'/'.join(str(PLACE_WEIGHT[p]) for p in ordered)} "
                          f"是十进制编码规则（encoding constant），不是 config 数据；"
                          f"config.target={cfg.get('target')} 仅作交叉核对；**不读答案**"),
                "consistency": cons, "extra": extra}

    # ── array-board（numeric_exact）────────────────────────────────────
    if r == "array-board":
        m = re.search(r"每行摆\s*(\d+)\s*个", stem)
        m2 = re.search(r"共摆\s*(\d+)\s*行", stem)
        if not (m and m2):
            raise ValueError(f"array-board 抽不到每行个数/行数：{stem[:60]}")
        cols, rows = int(m.group(1)), int(m2.group(1))
        expr = f"{cols} * {rows}"
        if cfg.get("target_cols") is not None and cfg["target_cols"] != cols:
            cons.append(f"config.target_cols={cfg['target_cols']} ≠ 题面每行 {cols}")
        if cfg.get("target_rows") is not None and cfg["target_rows"] != rows:
            cons.append(f"config.target_rows={cfg['target_rows']} ≠ 题面 {rows} 行")
        for k in ("max_cols", "max_rows"):
            if cfg.get(k) is not None and cfg[k] < max(cols, rows):
                cons.append(f"config.{k}={cfg[k]} 小于题面要求的 {max(cols, rows)}")
        return {"read": f"{stem}→ 每行 {cols} 个、共 {rows} 行，求总数",
                "expr": expr, "object": f"棋子总数（{cols}×{rows}）",
                "basis": (f"题面抽出每行 cols={cols}、rows={rows}；"
                          f"config.target_cols/rows={cfg.get('target_cols')}/"
                          f"{cfg.get('target_rows')} 仅作交叉核对；**不读答案**"),
                "consistency": cons, "extra": {"cols": cols, "rows": rows}}

    # ── shape-canvas（geometry_constraint）─────────────────────────────
    if r == "shape-canvas":
        # 两种写法：「底边2格、高3格」/「长5格、宽2格」
        m = re.search(r"底边\s*(\d+)\s*格", stem)
        m2 = re.search(r"高\s*(\d+)\s*格", stem)
        if m and m2:
            base, height = int(m.group(1)), int(m2.group(1))
            form = "base_height"
        else:
            m3 = re.search(r"长\s*(\d+)\s*格", stem)
            m4 = re.search(r"宽\s*(\d+)\s*格", stem)
            if not (m3 and m4):
                raise ValueError(f"shape-canvas 抽不到两条边长：{stem[:60]}")
            base, height = int(m3.group(1)), int(m4.group(1))
            form = "length_width"
        expr = f"{base} * {height}"
        if cfg.get("target_area") is not None and cfg["target_area"] != independent_eval(expr):
            cons.append(f"config.target_area={cfg.get('target_area')} ≠ "
                        f"{base}×{height}={int(independent_eval(expr))}")
        # **base/height 是否被组件读取**——用源码事实核对，不假设
        if cfg.get("base") is not None and cfg["base"] != base:
            cons.append(f"config.base={cfg['base']} ≠ 题面 {base}")
        if cfg.get("height") is not None and cfg["height"] != height:
            cons.append(f"config.height={cfg['height']} ≠ 题面 {height}")
        feas = geometry_feasibility(stem, cfg, base, height)
        if cfg.get("target_shape") != "rectangle":
            cons.append(f"config.target_shape={cfg.get('target_shape')}，本批只核长方形")
        return {"read": f"{stem}→ {form}：{base} 格 × {height} 格，求面积",
                "expr": expr, "object": f"面积（{base}×{height} 平方格）",
                "basis": (f"题面抽出 {form} base={base}、height={height}；"
                          f"**config.base/height 组件不读**（`parseShapeCanvasConfig` "
                          f"只取 grid/target_area/target_shape），故这两字段仅作"
                          f"题面↔config 交叉核对；面积由题面两数相乘得出；**不读答案**"),
                "consistency": cons, "extra": {"feasibility": feas,
                                               "dimension_form": form}}

    # ── sorting-board（sequence_order）─────────────────────────────────
    if r == "sorting-board":
        m = re.search(r"\[([\d,\s]+)\]", stem)
        if not m:
            raise ValueError(f"sorting-board 抽不到数字卡序列：{stem[:60]}")
        cards = [int(x) for x in re.findall(r"\d+", m.group(1))]
        if "从小到大" in stem:
            direction = "asc"
        elif "从大到小" in stem:
            direction = "desc"
        else:
            raise ValueError(f"sorting-board 抽不到排序方向：{stem[:60]}")
        ordered = sorted(cards, reverse=(direction == "desc"))
        expr = _concat_expr(ordered)
        # config 交叉核对：卡片值集合 + 方向 + 初始序 ≠ 正解序
        cfg_vals = sorted(x["value"] for x in (cfg.get("items") or []))
        if cfg_vals and cfg_vals != sorted(cards):
            cons.append(f"config.items 的值 {cfg_vals} ≠ 题面卡片 {sorted(cards)}")
        if cfg.get("direction") not in (None, direction):
            cons.append(f"config.direction={cfg.get('direction')} ≠ 题面 {direction}")
        if cfg.get("initial_order") and cfg.get("items"):
            by_val = {x["value"]: x["id"] for x in cfg["items"]}
            # 题面卡片值与 config.items 不一致时，不能 KeyError 崩掉——
            # 那会让「config↔题面不一致」这条判据只在**两者一致时**才跑得动，
            # 等于把该判据做成空转。改为登记 INCONSISTENT 并跳过该子检查。
            missing_vals = [v for v in ordered if v not in by_val]
            if missing_vals:
                cons.append(f"题面卡片值 {missing_vals} 在 config.items "
                            f"{sorted(by_val)} 中不存在（无法核对初始序）")
            else:
                target_ids = [by_val[v] for v in ordered]
                if cfg["initial_order"] == target_ids:
                    cons.append("config.initial_order 已等于正解序（题已做完）")
        return {"read": f"{stem}→ 数字卡 {cards}，按「{'从小到大' if direction == 'asc' else '从大到小'}」排",
                "expr": expr,
                "object": f"排序后拼接的数（{'→'.join(map(str, ordered))}）",
                "basis": (f"题面抽出卡片 {cards} 与方向 {direction}；排序是题面要求，"
                          f"位权展开是编码规则（encoding constant）；"
                          f"config.items 仅作集合交叉核对；**不读答案**"),
                "consistency": cons,
                "extra": {"ordered": ordered, "direction": direction}}

    # ── pattern-board（sequence_order 或 numeric_exact 判断题）──────────
    if r == "pattern-board":
        m = re.search(r"前四格(?:颜色编码)?(?:依次)?是\s*([\d、,，\s]+)", stem)
        if not m:
            raise ValueError(f"pattern-board 抽不到可见序列：{stem[:60]}")
        visible = [int(x) for x in re.findall(r"\d+", m.group(1))]
        # 空格数有三种写法，必须都覆盖（第四批教训：不能只认一种题面格式）：
        #   A 「再按顺序补上接下来的两格」（常规续接题）
        #   B 「就把后两格写成"3、3"」（判断题变体，本题踩到）
        #   C 「在规律板的两个空格里改填」（判断题变体的第二处表述）
        # 只匹配「后X格」「X个空格」——**不能抓「前四格」里的「四格」**。
        blanks = None
        for pat in (r"补上接下来的\s*(一|二|两|三|\d)\s*格",
                    r"后\s*(一|二|两|三|\d)\s*格",
                    r"(一|二|两|三|\d)\s*个空格"):
            mb = re.search(pat, stem)
            if mb:
                blanks = _cn_or_digit(mb.group(1))
                if blanks is not None:
                    break
        if blanks is None:
            raise ValueError(f"pattern-board 抽不到空格数：{stem[:60]}")
        # 独立推周期：最小 p>=2 使 visible 以 p 展开（p=1 全同不算规律）
        period = None
        for p in range(2, min(3, len(visible) - 1) + 1):
            if all(visible[i] == visible[i % p] for i in range(len(visible))):
                period = p
                break
        if period is None:
            raise ValueError(f"pattern-board 可见段无 2..3 周期：{visible}")
        expected = [visible[(len(visible) + i) % period] for i in range(blanks)]
        expr = _concat_expr(expected)

        # 判断题变体：「乐乐…写成"3、3"，并说"我接对了"」——先判断再决定填谁
        enc = None
        claimed = None
        mc = re.search(r"写成\s*[“\"]([^”\"]+)[”\"]", stem)
        if mc:
            claimed = [int(x) for x in re.findall(r"\d+", mc.group(1))]
            # 判断：他填的两格是否都符合交替规律
            agree = (claimed == expected)
            # 他说「我接对了」——需核对；若 claimed 与 expected 不同则需改填
            enc = {"kind": "judge_then_fill",
                   "claimed": claimed, "expected": expected,
                   "claim_correct": agree,
                   "note": ("他填对了，照他的提交" if agree
                            else "他填错了，须改填正确编码")}
            # 数据绑定：答案应等于「他填的（若对）或正确的（若错）」
            chosen = claimed if agree else expected
            if chosen != expected:
                # 理论上不会发生：若 claimed==expected 则 chosen==expected
                raise ValueError("判断题分支逻辑自相矛盾")
        if cfg.get("visible") is not None and list(cfg["visible"]) != visible:
            cons.append(f"config.visible={cfg.get('visible')} ≠ 题面 {visible}")
        if cfg.get("blanks") is not None and cfg["blanks"] != blanks:
            cons.append(f"config.blanks={cfg['blanks']} ≠ 题面 {blanks} 格")
        pal = cfg.get("palette")
        if pal is not None and not set(visible).issubset(set(pal)):
            cons.append(f"config.palette={pal} 不含题面可见 token {sorted(set(visible))}")
        extra["period"] = period
        extra["expected_tokens"] = expected
        extra["variant"] = "judge_claimed" if claimed else "plain_extend"
        read = (f"{stem}→ 可见 {visible}，周期 {period}，缺 {blanks} 格 → "
                f"应补 {expected}")
        if claimed:
            read += f"；乐乐写成 {claimed}（{'对' if claimed == expected else '错'}）"
        return {"read": read, "expr": expr,
                "object": f"空格编码拼接（{'→'.join(map(str, expected))}）",
                "basis": (f"题面抽出 visible={visible}、blanks={blanks}；"
                          f"周期 {period} 由题面「两次重复」独立推得，"
                          f"不读 config.palette；空格拼接的位权是编码规则；"
                          f"config.visible/blanks/palette 仅作交叉核对；**不读答案**"),
                "encode": enc, "consistency": cons, "extra": extra}

    raise ValueError(f"未覆盖的 renderer：{r}")


def _canon_num(x) -> float:
    return float(str(x).strip())


def evaluate(item: dict) -> dict:
    d = derive(item)
    computed = independent_eval(d["expr"])
    # 判断题分支：把「判断 → 填哪一格」的规则显式写出来，而不是把判断塞进 expr
    enc = d.get("encode")
    if enc:
        if enc["kind"] == "judge_then_fill":
            # 分支结果就是「选中的那串编码」的位权值；此处 computed 已是
            # expected 的编码值，故只需确认分支方向与预期一致
            if enc["claim_correct"] and enc["claimed"] != enc["expected"]:
                raise ValueError("claim_correct=True 但 claimed≠expected")
        else:
            raise ValueError(f"未知编码方式：{enc['kind']}")
    stated_raw = item["answer_raw"]
    stated = _canon_num(stated_raw)
    match = abs(float(computed) - stated) < 1e-9

    cfg = _cfg(item)
    feas = (d.get("extra") or {}).get("feasibility")
    ws = _ws(item)
    return {
        "rvid": item["rvid"],
        "title": item["title"],
        "renderer": item["renderer"],
        "solve_path": item.get("solve_path"),
        "ability_id": item["ability_id"],
        "priority": item.get("priority"),
        "input_basis": d["basis"],
        "read": d["read"],
        "target_object": d["object"],
        "derivation": {
            "expr": d["expr"],
            "encode": enc or {"kind": "direct", "note": "算术值即答案（构造结果的编码）"},
            "encoding_constants": _encoding_constants(d["expr"], item["stem"]),
            "extra": d.get("extra") or {},
        },
        "computed": computed,
        "stated_answer": stated_raw,
        "verdict": "MATCH" if match else "MISMATCH",
        "config_vs_stem": {
            "checked": True,
            "issues": d["consistency"],
            "status": "CONSISTENT" if not d["consistency"] else "INCONSISTENT",
        },
        "feasibility": feas,
        "semantic_observations": _semantic_obs(item, feas),
        "evidence_enforcement": {
            "evidence_targets": _evidence_targets(item),
            "process_constraint": cfg.get("process_constraint"),
            "enforced_by_backend": bool(cfg.get("process_constraint")),
        },
        "ui_config_seen": cfg,
        "workspace_mode": ws.get("mode"),
        "workspace_capabilities": ws.get("capabilities"),
        "stem": item["stem"],
        "input_binding": {
            "stem_sha256": item["stem_sha256"],
            "ui_schema_sha256": item["ui_schema_sha256"],
        },
    }


def _evidence_targets(item: dict) -> list | None:
    ui = item["ui_schema"]
    if isinstance(ui, str):
        ui = json.loads(ui)
    et = (ui.get("response_contract") or {}).get("evidence_targets")
    return et if isinstance(et, list) and et else None


def _semantic_obs(item: dict, feas: dict | None) -> list[dict]:
    """登记「答案对得上、但题面或组件有其性质疑」的观察项。

    **这类观察项不改变 verdict**：Q03 的 MATCH 定义就是「独立推导 == 存储答案」，
    可完成性与过程约束效力是另外两条维度，按用户口径分账登记。
    """
    r = item["renderer"]
    cfg = _cfg(item)
    stem = item["stem"]
    obs: list[dict] = []

    # 1) 题面可完成性（本批新增，shape-canvas 专用）
    if feas and feas["verdict"] != "FEASIBLE":
        obs.append({
            "code": "INFEASIBLE_ON_COMPONENT",
            "severity": "risk",
            "why": ("题面要求的边长超出组件板可画跨度。组件 grid 是**钉位数**不是格数："
                    f"grid={feas['component_grid']} → 渲染跨度 {feas['component_span']} 格"
                    f"（`ShapeCanvasV2.tsx:140` span=(grid-1)*CELL，"
                    f"`applyAddPoint` 约束 0<=x<grid），"
                    f"而题面要求长 {feas['required_base']} 格 × 宽 {feas['required_height']} 格"),
            "evidence": (f"题面自称「{feas['stem_grid_declared']}×"
                         f"{feas['stem_grid_declared']} 方格纸」（题面自洽："
                         f"{feas['required_base']} <= {feas['stem_grid_declared']}）；"
                         f"组件 component_grid={feas['component_grid']}、"
                         f"component_span={feas['component_span']} → "
                         f"fits_component_board={feas['fits_component_board']}"),
            "consequence": (f"孩子在板上画不出题面要求的 {feas['required_base']}×"
                            f"{feas['required_height']} 长方形。但面积 "
                            f"{cfg.get('target_area')} 在板上仍可达——穷举 5×5 钉位后，"
                            f"存在**倾斜正方形**（顶点 (0,1)(1,4)(4,3)(3,0)，"
                            f"边长 √10、四个直角、面积恰为 "
                            f"{cfg.get('target_area')}）能通过 `evaluateShapeCanvas`，"
                            f"于是「画不出正解」与「画错形状却判对」同时成立"),
            "not_concluded": ("本条不主张该题答案有误（独立推导与存储答案一致，已 MATCH），"
                              "只登记「题面所要求之图形在组件上不可构造」；"
                              "修法涉及改 grid 语义或改题目尺寸，属产品决策"),
            "scope_check": (f"全量 published shape-canvas 共 9 题，"
                            f"逐题穷举后**仅此题**不可达（其余 8 题 fits=True）——"
                            f"是单题缺陷，不是 renderer 系统性问题"),
        })

    # 2) 题面「方格纸」与组件「钉位数」的通用偏差（本题可完成时也成立）
    if r == "shape-canvas" and feas and feas["verdict"] == "FEASIBLE":
        if (feas["stem_grid_declared"] is not None
                and feas["component_span"] is not None
                and feas["stem_grid_declared"] != feas["component_span"]):
            obs.append({
                "code": "GRID_SEMANTICS_OFF_BY_ONE",
                "severity": "info",
                "why": ("题面「5×5 方格纸」与组件「5 个钉位」是两个概念："
                        "后者只能画 4 格跨度。本题尺寸未越界故可完成，"
                        "但题面描述与界面呈现相差一档"),
                "evidence": (f"stem_grid_declared={feas['stem_grid_declared']}、"
                             f"component_span={feas['component_span']}"),
                "consequence": ("孩子按「5×5 方格纸」理解，会去找 5 格长边，"
                                "而板上最长只有 4 格——本题只需 "
                                f"{feas['required_base']}×{feas['required_height']} 尚不受影响，"
                                "但这种表述差异会让边界尺寸题（如 5 格）直接失效"),
                "not_concluded": "本条是口径登记，不主张本题有缺陷",
            })

    # 3) 过程约束已启用，但对几何题抓不到「形状错但面积对」
    if r == "shape-canvas":
        pc = cfg.get("process_constraint") or {}
        obs.append({
            "code": "PROCESS_CONSTRAINT_BLIND_TO_SHAPE",
            "severity": "risk",
            "why": (f"`process_constraint.mode={pc.get('mode')}` 已声明，后端会校验；"
                    "但 `_rule_shape` 只重算**面积**与**直角数**，"
                    "**不读 config.base / config.height**"),
            "evidence": ("`process_validate.py:154-168`："
                         "`_rule_shape` 取 vertices 算 shoelace 面积与 right_angles，"
                         "面积 == target_area 且直角 == 4 即 valid；"
                         "base/height 在整个函数内未被引用"),
            "consequence": ("斜正方形（面积相同、四个直角）过程校验也判 valid。"
                            "即：启用 process_constraint **不能**弥补上面那条"
                            "「画错形状却判对」——两道防线在同一处失效"),
            "not_concluded": ("本条不主张过程校验写错了（它按冻结契约只验面积/直角），"
                              "只登记「该契约无法表达边长约束」这一能力边界"),
        })

    # 4) 过程约束已启用（本批与第五批的关键对照）
    pc = cfg.get("process_constraint") or {}
    if pc.get("mode"):
        obs.append({
            "code": "PROCESS_CONSTRAINT_ENABLED",
            "severity": "info",
            "why": (f"`process_constraint.mode={pc['mode']}` 已声明且 `params` "
                    f"{'非空' if pc.get('params') else '为空'}；后端 `process_validate` "
                    f"会真校验（第五批同位置 20 题全为 null）"),
            "evidence": (f"config.process_constraint={json.dumps(pc, ensure_ascii=False)}；"
                         f"`process_validate.py` RULES 含该 mode"),
            "consequence": ("过程证据进入判分链，这是本族与 numeric_judge 批的结构性差异。"
                            "但「已启用」不等于「能判所有错法」——见同题其他观察项"),
            "not_concluded": "本条不主张该题过程校验充分，只登记其已启用",
        })

    # 5) place-value：卡片池 multiset 锁死 → 错误只剩「位置」维度
    if r == "place-value":
        obs.append({
            "code": "ERROR_SPACE_RESTRICTED_TO_POSITION",
            "severity": "info",
            "why": ("`parsePlaceValueConfig` 强制 pool 与 target 的各位数字 multiset 相等，"
                    "于是孩子**不可能**填出数字错、只能是位置错"),
            "evidence": (f"config.pool={cfg.get('pool')}、target={cfg.get('target')}；"
                         "`placeValueV2.ts` 用 `sorted(pool)!==sorted(expected)` 直接拒配"),
            "consequence": ("诊断靶唯一（place_confusion），好处是判定干净；"
                            "代价是「拿错卡片」这一类错因在本 renderer 下不可观测"),
            "not_concluded": "本条是能力边界登记，不是缺陷",
        })

    # 6) sorting-board：干扰维度（字号）与数值序故意错开
    if r == "sorting-board":
        vals = [x["value"] for x in (cfg.get("items") or [])]
        ranks = [x["visual_rank"] for x in (cfg.get("items") or [])]
        if vals and ranks:
            by_val = [x["id"] for x in sorted(cfg["items"], key=lambda x: x["value"])]
            by_vis = [x["id"] for x in sorted(cfg["items"],
                                              key=lambda x: -x["visual_rank"])]
            obs.append({
                "code": "DISTRACTOR_DIMENSION_PRESENT",
                "severity": "info",
                "why": ("卡片字号档位（visual_rank）与数值序故意不一致，"
                        "用于区分「按数值排」与「按看起来大小排」"),
                "evidence": f"数值序={by_val}；视觉序={by_vis}；两者不同",
                "consequence": ("「按字大排」会给出与正解不同的拼接值，可被终值检出；"
                                "但**分不开**「真的比较了数值」与「只是没看字号」"),
                "not_concluded": "本条是设计意图登记，不是缺陷",
            })

    # 6b) array-board / sorting-board：后端根本没有对应过程校验器
    #
    # 这条与上面第 4 条「PROCESS_CONSTRAINT_ENABLED」互斥出现，二者不能同时成立——
    # 所以必须放在 `if not pc.get("mode")` 分支里，否则同一题会既说「已启用」
    # 又说「没有校验器」，自相矛盾。
    if r in ("array-board", "sorting-board") and not (cfg.get("process_constraint") or {}).get("mode"):
        mode_gap = {"array-board": "array_build", "sorting-board": "order_sort"}[r]
        obs.append({
            "code": "NO_PROCESS_VALIDATOR_FOR_RENDERER",
            "severity": "risk",
            "why": (f"`config.process_constraint` 为 null，且后端 `process_validate.py` "
                    f"的 RULES **没有 {r} 的校验器**（只有 pattern_extension / "
                    f"payment_change / shape_drawing / place_value_build 四个 mode）"),
            "evidence": ("`process_validate.py:199-204` RULES 字典逐项列出四个 mode，"
                         f"无 {r} 项；`learning.py` 在 pc=None 时不做过程校验，"
                         "判分行为与未声明完全相同"),
            "consequence": (f"本题属 construct_constraint 族，考点是「{mode_gap}」这一"
                            f"构造过程，但**过程证据不进入判分**：终值对即 correct=True。"
                            f"即使人为补上 process_constraint，mode 也不在 RULES 里，"
                            f"会落 `unknown_mode` → unverifiable，等于没校验"),
            "not_concluded": ("本条不主张应该立刻为这两个 renderer 写校验器"
                              "（属产品决策），也不主张本题答案有误（已 MATCH）；"
                              "只登记「该求解形态缺过程校验能力」这一事实"),
            "scope": ("全族 54 题中 17 题无 pc，缺口**全部**在这两个 renderer："
                      "array-board 8/8、sorting-board 9/9；"
                      "其余四类 renderer 均 100% 覆盖"),
        })

    # 7) pattern-board：相位靶与惯性靶是否真的可区分
    if r == "pattern-board":
        visible = cfg.get("visible") or []
        blanks = cfg.get("blanks") or 0
        period = (derive(item).get("extra") or {}).get("period")
        if visible and period:
            expected = [visible[(len(visible) + i) % period] for i in range(blanks)]
            shifted = [visible[(len(visible) + i + 1) % period] for i in range(blanks)]
            inertia = [visible[-1]] * blanks
            obs.append({
                "code": "PATTERN_DISTRACTOR_TARGETS",
                "severity": "info",
                "why": "相位靶（整体后移一位）与惯性靶（全填末颗）是否与正解互异，决定分诊是否成立",
                "evidence": (f"expected={expected}、phase_shift={shifted}、"
                             f"rule_ignored={inertia}"),
                "consequence": ("三者互异 → 两种错法都能被 `evaluatePattern` 单独识别；"
                                if len({tuple(expected), tuple(shifted), tuple(inertia)}) == 3
                                else "存在重合 → 该错法在本题不可单独识别；"),
                "not_concluded": "本条只核对分诊靶位是否互异，不主张题目有缺陷",
            })

    return obs


# ── Q05 候选：逐题生成（第四批铁律，禁止按 renderer 复用文案）────────────
Q05_NEUTRAL = {
    "money-board": "说「先看清两样东西各多少钱，再把它们合起来」",
    "place-value": "说「先找到十位在哪一格，再看个位该放哪个数字」",
    "array-board": "说「一行有几个，一共有几行，想一想行和行之间是怎么重复的」",
    "shape-canvas": "说「先数一数底边有几格，再数高有几格，长方形里面一共盖住多少格」",
    "sorting-board": "说「先找出最小的那个数，再在剩下的里面找最小的」",
    "pattern-board": "说「看看前面几个数是一组一组重复的，一组里面是什么顺序」",
}


def _alts(ans, pairs):
    """拆成「与答案不同值」和「与答案同值」两类（同值的不算错型证据）。"""
    distinct = [(v, l) for v, l in pairs if v != ans]
    coincide = [(v, l) for v, l in pairs if v == ans]
    return distinct, coincide


def _bucket_text(pairs) -> str:
    """同值错法必须按值聚合，否则会被读成两份独立证据（第五批铁律）。"""
    bucket: dict[int, list[str]] = {}
    for v, l in pairs:
        bucket.setdefault(int(v), []).append(l)
    parts = []
    for v, labels in bucket.items():
        if len(labels) == 1:
            parts.append(f"{v}（{labels[0]}）")
        else:
            parts.append(f"{v}（{'／'.join(labels)} —— **两个错法同值，在该题内部不可分**）")
    return "；".join(parts)


def q05_for(item: dict) -> dict:
    """逐题生成 Q05 候选。**每题的文案由该题的具体数字拼出来**，不套模板。"""
    r = item["renderer"]
    cfg = _cfg(item)
    stem = item["stem"]
    d = derive(item)
    ans = int(independent_eval(d["expr"]))
    ex = d.get("extra") or {}

    if r == "money-board":
        prices = [int(x) for x in re.findall(r"标价\s*(\d+)\s*角", stem)]
        if ex.get("money_variant") == "two_items_sum":
            a, b = prices[0], prices[1]
            pairs = [(a, f"只算第一件 {a} 角"), (b, f"只算第二件 {b} 角"),
                     (abs(a - b), "把两件的差当总价")]
            dis, coin = _alts(ans, pairs)
            obs = (f"`config.price`={cfg.get('price')}、"
                   f"`denominations`={cfg.get('denominations')}；"
                   f"提交 `answer` 为付出总角数 {ans}。序列化层记 "
                   f"`counts`（面额→枚数）与 `selection_history`；"
                   f"过程约束 `payment_change` 会核 `sum(sel)==price`")
            comp = "可能的错值：" + _bucket_text(dis)
            if coin:
                comp += (f"。**{'、'.join(str(v) for v, _ in coin)} 与正确答案同值**，"
                         f"该错法本题不成立")
            cd = (f"本题两件是 {a} 角与 {b} 角，求 {ans} 角。"
                  "`counts` 能分开「少算了某一件」与「换算错」；"
                  "但**分不开「先相加再凑币」与「边凑边加」**——"
                  "终态 counts 相同")
            return {"observable": obs, "competing": comp,
                    "cannot_distinguish": cd, "neutral": Q05_NEUTRAL[r]}
        a = prices[0] if prices else cfg.get("price")
        pairs = [(a // 10, "只算元位、漏掉角位"), (a % 10, "只算角位"),
                 (a + 10, "多算一元")]
        dis, coin = _alts(ans, pairs)
        obs = (f"`config.price`={cfg.get('price')}（单件，题面直给 {a} 角）、"
               f"`denominations`={cfg.get('denominations')}；提交 `answer` 为 {ans}。"
               f"本题**不含加法**——只有凑币，没有两数合并")
        comp = "可能的错值：" + _bucket_text(dis)
        if coin:
            comp += f"。**{'、'.join(str(v) for v, _ in coin)} 与正确答案同值**"
        cd = ("单件直给价，分不开「看懂面额」与「试凑到对」——"
              "凑币过程本身即答案，没有中间表征可查")
        return {"observable": obs, "competing": comp,
                "cannot_distinguish": cd, "neutral": Q05_NEUTRAL[r]}

    if r == "place-value":
        pa = ex.get("place_assignment") or {}
        nd = ex.get("digit_count") or len(pa)
        pairs = []
        # 逆序摆放：把每一位放到对称位置
        rev = ["".join(str(pa[p]) for p in reversed(list(pa)))]
        pairs.append((int(rev[0]), "整体逆序摆放（每个数字都放到了对称的位上）"))
        # 单点错位：把最高位与最低位交换
        if nd >= 2:
            items = list(pa.items())
            swapped = dict(items)
            swapped[items[0][0]], swapped[items[-1][0]] = items[-1][1], items[0][1]
            val = sum(int(swapped[p]) * PLACE_WEIGHT[p] for p in swapped)
            pairs.append((val, f"最高位（{items[0][0]}）与最低位（{items[-1][0]}）互换"))
        # 漏位：最低位当 0 处理
        dropped = 0
        for p, v in pa.items():
            if PLACE_WEIGHT[p] != 1:
                dropped += v * PLACE_WEIGHT[p]
        pairs.append((dropped, "漏掉最低位（个位没放）"))
        dis, coin = _alts(ans, pairs)
        obs = (f"`config.pool`={cfg.get('pool')}、`target`={cfg.get('target')}；"
               f"题面位名指派 {pa}；提交 `answer` 为框拼出的数 {ans}。"
               f"序列化层记 `slots`（各框）与 `pool`（余牌），"
               f"结构判定 EMPTY/PASS/place_confusion；"
               f"过程约束 `place_value_build` 会按位重算")
        comp = "可能的错值：" + _bucket_text(dis)
        if coin:
            comp += (f"。**{'、'.join(str(v) for v, _ in coin)} 与正确答案同值**"
                     f"（本题位值对称，该错法不可分）")
        cd = ("`slots` 数组能分开「哪个位放错」，这是本 renderer 的强项；"
              "但**分不开「知道自己放在十位」与「只是把牌塞进了空格」**——"
              "框的语义由界面给出，提交物只记位置不记理解")
        return {"observable": obs, "competing": comp,
                "cannot_distinguish": cd, "neutral": Q05_NEUTRAL[r]}

    if r == "array-board":
        cols, rows = ex.get("cols"), ex.get("rows")
        pairs = [(cols, f"把每行个数 {cols} 当总数"), (rows, f"把行数 {rows} 当总数"),
                 (cols + rows, "把行数与列数相加")]
        dis, coin = _alts(ans, pairs)
        obs = (f"`config.target_cols`={cfg.get('target_cols')}、"
               f"`target_rows`={cfg.get('target_rows')}、"
               f"`max_cols/max_rows`={cfg.get('max_cols')}/{cfg.get('max_rows')}；"
               f"提交 `answer` 为积 {ans}。无 process_constraint——"
               f"本族内 array-board 属少数未声明过程约束的 renderer")
        comp = "可能的错值：" + _bucket_text(dis)
        if coin:
            comp += f"。**{'、'.join(str(v) for v, _ in coin)} 与正确答案同值**"
        cd = (f"本题 {cols}×{rows}，行与列数量"
              f"{'相同' if cols == rows else '不同'}。"
              "若相同，摆成转置（行列互换）乘积不变，`structure.error=transpose` "
              "可留痕；若不同，转置会变成另一个积，可被终值检出。"
              "**共同盲区**：分不开「按行列数出来」与「背乘法表」")
        return {"observable": obs, "competing": comp,
                "cannot_distinguish": cd, "neutral": Q05_NEUTRAL[r]}

    if r == "shape-canvas":
        feas = ex.get("feasibility") or {}
        base, h = feas.get("required_base"), feas.get("required_height")
        pairs = [(base + h, "把两条边长相加当面积"), (base * h + base, "多数一条边"),
                 (base * h - 1, "数格时漏一格")]
        dis, coin = _alts(ans, pairs)
        extra = ""
        if feas.get("verdict") == "INFEASIBLE_ON_COMPONENT":
            extra = (f" **注意：本题题面要求 {base}×{h}，而组件 grid="
                     f"{feas.get('component_grid')} 只能画到跨度 "
                     f"{feas.get('component_span')} 格——"
                     f"该长方形在板上画不出来**；面积 {ans} 却可由倾斜正方形"
                     f"（顶点 (0,1)(1,4)(4,3)(3,0)）凑出并通过判分。")
        obs = (f"`config.target_area`={cfg.get('target_area')}、"
               f"`grid`={cfg.get('grid')}；题面 {base}×{h}；提交 `answer` 为面积 {ans}。"
               f"序列化层记 `vertices`（顶点序）与几何属性；"
               f"过程约束 `shape_drawing` 会重算面积与直角数。{extra}")
        comp = "可能的错值：" + _bucket_text(dis)
        if coin:
            comp += f"。**{'、'.join(str(v) for v, _ in coin)} 与正确答案同值**"
        cd = ("`vertices` 能分开「顶点数错」「非直角」「尺寸错」三态；"
              "**但分不开「按边数格子」与「画个面积相同的斜正方形」**——"
              "`_rule_shape` 只验面积与直角数，不读 base/height")
        return {"observable": obs, "competing": comp,
                "cannot_distinguish": cd, "neutral": Q05_NEUTRAL[r]}

    if r == "sorting-board":
        ordered = ex.get("ordered") or []
        cards = [x["value"] for x in (cfg.get("items") or [])]
        rev = list(reversed(ordered))
        pairs = [(int("".join(map(str, rev))), "整串降序（方向反了）"),
                 (int("".join(map(str, cards))), "照初始顺序原样提交（没排）")]
        dis, coin = _alts(ans, pairs)
        obs = (f"`config.items`={[(x['value'], x['visual_rank']) for x in (cfg.get('items') or [])]}"
               f"（值为数值、rank 为字号档）；题面初始序 {cards}；"
               f"提交 `answer` 为排序后拼接 {ans}。序列化层记 `order` 与 `swaps`。"
               f"**本 renderer 无 process_constraint**")
        comp = "可能的错值：" + _bucket_text(dis)
        if coin:
            comp += f"。**{'、'.join(str(v) for v, _ in coin)} 与正确答案同值**"
        cd = (f"本题 {len(cards)} 张卡，`swaps` 记录每次交换。能分开「降序」"
              f"（reversed）与「按字号排」（dimension_confusion）两个靶；"
              "**但分不开「真比较了数值」与「恰好按出现顺序蒙对」**——"
              "后者会给出初始序拼接值，仅当初始序≠正解时才可排除")
        return {"observable": obs, "competing": comp,
                "cannot_distinguish": cd, "neutral": Q05_NEUTRAL[r]}

    if r == "pattern-board":
        period = ex.get("period")
        exp = ex.get("expected_tokens") or []
        visible = [int(x) for x in re.findall(r"\d+",
                   re.search(r"前四格(?:颜色编码)?(?:依次)?是\s*([\d、,，\s]+)",
                             stem).group(1))]
        inertia = [visible[-1]] * len(exp)
        shifted = [visible[(len(visible) + i + 1) % period] for i in range(len(exp))]
        pairs = [(int("".join(map(str, inertia))), "无脑延续末颗（惯性靶 rule_ignored）"),
                 (int("".join(map(str, shifted))), "周期读对但相位后移一位（phase_shift）")]
        dis, coin = _alts(ans, pairs)
        obs = (f"`config.visible`={visible}、`blanks`={cfg.get('blanks')}、"
               f"`palette`={cfg.get('palette')}；周期由题面推出为 {period}；"
               f"提交 `answer` 为空格编码拼接 {ans}。序列化层记 `beads`、`attempt_history`、"
               f"`pattern_text`；过程约束 `pattern_extension` 会按 visible+period 重算")
        comp = "可能的错值：" + _bucket_text(dis)
        if coin:
            comp += (f"。**{'、'.join(str(v) for v, _ in coin)} 与正确答案同值**"
                     f"（本题该错法与正解重合，不可分）")
        cd = ("`attempt_history` 记每次 [slot, from, to]，能分开相位错与惯性错；"
              "**但分不开「推出周期 2」与「看到 3、1 就接着写 3、1」**——"
              "本题可见段本身就是两个完整周期，规律强度不足")
        return {"observable": obs, "competing": comp,
                "cannot_distinguish": cd, "neutral": Q05_NEUTRAL[r]}

    raise ValueError(f"Q05 未覆盖的 renderer：{r}")


def _obs_counts(results: list[dict]) -> dict:
    from collections import Counter
    c = Counter()
    for r in results:
        for o in r.get("semantic_observations") or []:
            c[o["code"]] += 1
    return dict(sorted(c.items()))


def _family_process_coverage(conn) -> dict:
    """实地统计 construct_constraint **全族 54 题**的 process_constraint 覆盖。

    为什么要在这里算，而不是沿用上一轮的笔记：
      上一轮的记录写的是「54 题全部带 process_constraint」，本批实核 20 题
      只有 17 题带，两者矛盾。实地一查，真值是 **37/54**，缺口精确落在
      `array-board`（8/8 全无）与 `sorting-board`（9/9 全无）两个 renderer。

    而且这不是「题目漏配」而是**后端能力缺口**：`process_validate.py` 的
    RULES 只有四个 mode（pattern_extension / payment_change / shape_drawing /
    place_value_build），根本没有 array / sorting 的校验器——这两个 renderer
    就算写了 process_constraint 也会落到 `unknown_mode` → unverifiable。
    """
    union = os.path.join(REPO, "scripts/iqc/runs/FE1468_worklist_union.json")
    u = json.load(open(union, encoding="utf-8"))
    cc = [x for x in u["items"] if x["semantic_family"] == "construct_constraint"]
    ids = [x["rvid"] for x in cc]
    rows = conn.execute(
        "select resource_version_id::text, ui_schema from resource_version "
        "where resource_version_id = any(%s::uuid[])", (ids,)).fetchall()
    cfg_by_id = {}
    for rid, ui in rows:
        if isinstance(ui, str):
            ui = json.loads(ui)
        ws = (ui.get("workspaces") or [{}])[0]
        cfg_by_id[rid] = ws.get("config") or {}

    by_rend: dict[str, dict] = {}
    without: list[dict] = []
    withpc = 0
    for x in cc:
        cfg = cfg_by_id.get(x["rvid"], {})
        pc = cfg.get("process_constraint")
        has = isinstance(pc, dict) and bool(pc.get("mode"))
        r = x["renderer"]
        b = by_rend.setdefault(r, {"n": 0, "with_pc": 0})
        b["n"] += 1
        if has:
            withpc += 1
            b["with_pc"] += 1
        else:
            without.append({"rvid": x["rvid"], "renderer": r})
    # 后端 RULES 支持的 mode（源码事实，不凭记忆）
    backend_modes = ["pattern_extension", "payment_change",
                     "shape_drawing", "place_value_build"]
    gap_renderers = sorted({w["renderer"] for w in without})
    return {
        "family_total": len(cc),
        "with_process_constraint": withpc,
        "without_process_constraint": len(without),
        "by_renderer": dict(sorted(by_rend.items())),
        "renderers_without_any_pc": gap_renderers,
        "backend_supported_modes": backend_modes,
        "why_the_gap": ("不带 pc 的题**全部**落在 "
                        + " / ".join(gap_renderers)
                        + " 两个 renderer；而后端 `process_validate.py` 的 RULES 只有 "
                        + " / ".join(backend_modes)
                        + " 四个 mode，没有 array / sorting 的校验器。"
                          "故这不是「题目漏配」，是**该两类求解形态没有过程校验能力**——"
                          "即使补上 process_constraint 也会落 unknown_mode → unverifiable。"),
        "correction": ("更正上一轮笔记的错误口径：曾记为「54 题全部带 "
                       "process_constraint」，实地统计为 37/54。"
                       "本批 20 题实核 17/20 与该缺口一致（差额 3 题 = "
                       "1 题 array-board + 2 题 sorting-board）。"),
    }


def main() -> int:
    if not os.path.exists(QUOTA):
        print("缺少 batch6_quota_list.json：**必须先冻结选题集合再核验**。",
              file=sys.stderr)
        return 2
    q = json.load(open(QUOTA, encoding="utf-8"))
    items = q["items"]

    import psycopg
    db = os.environ.get("DATABASE_URL")
    if not db:
        print("缺少 DATABASE_URL（只读账号即可）", file=sys.stderr)
        return 2
    ids = [i["rvid"] for i in items]
    # 连接放在 with 里跑完两个用途：①本批 20 题的答案/题干 ②全族 54 题的
    # process_constraint 覆盖。**只读，零 DML**（with-connect 退出会自动
    # commit，但本脚本没有任何写语句路径——项目铁律：DRY 工具必须「零 DML
    # 路径」而非「执行后 rollback」）。
    with psycopg.connect(db) as conn:
        rows = conn.execute(
            "select resource_version_id::text, content->>'answer', "
            "content->>'stem', ui_schema::text "
            "from resource_version where resource_version_id = any(%s::uuid[])",
            (ids,)).fetchall()
        live = {r[0]: {"answer": r[1], "stem": r[2], "ui": r[3]} for r in rows}
        missing = [i for i in ids if i not in live]
        if missing:
            print(f"清单里有 {len(missing)} 题库里取不到：{missing}", file=sys.stderr)
            return 2
        drift = [i["rvid"] for i in items
                 if str(live[i["rvid"]]["answer"]) != str(i["answer_raw"])]
        if drift:
            print(f"**答案漂移** {len(drift)} 题（清单与库不一致）：{drift}",
                  file=sys.stderr)
            return 2
        coverage = _family_process_coverage(conn)

    try:
        results = [evaluate(i) for i in items]
    except ValueError as e:
        print(f"**推导失败**：{e}", file=sys.stderr)
        print("（推导失败不是 MISMATCH，必须单独处理——不能记为通过）",
              file=sys.stderr)
        return 2

    by_renderer: dict[str, dict] = {}
    by_solve: dict[str, dict] = {}
    for r in results:
        b = by_renderer.setdefault(r["renderer"],
                                   {"n": 0, "match": 0, "inconsistent": 0,
                                    "infeasible": 0})
        b["n"] += 1
        b["match"] += 1 if r["verdict"] == "MATCH" else 0
        b["inconsistent"] += 1 if r["config_vs_stem"]["status"] != "CONSISTENT" else 0
        b["infeasible"] += 1 if (r.get("feasibility") or {}).get(
            "verdict") == "INFEASIBLE_ON_COMPONENT" else 0
        s = by_solve.setdefault(r["solve_path"] or "UNKNOWN",
                                {"n": 0, "match": 0})
        s["n"] += 1
        s["match"] += 1 if r["verdict"] == "MATCH" else 0

    out = {
        "title": "FE-1472 第六批｜Q03 construct_constraint 族 20 题独立核验",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chain": ["题干", "抽取题面事实", "明确所求对象",
                  "独立推导/构造（纯算术）", "断言 config 已知量 ⊆ 题面事实",
                  "题面可完成性（新增维度）", "与存储答案比较"],
        "family_scope": {
            "semantic_family": "construct_constraint",
            "why_this_batch": "前五批 95 题的 semantic_family 全部是 numeric_judge；"
                              "construct_constraint 54 题此前 0 题完成。"
                              "本批首次开族，名额按 solve_path 分配。",
            "total_in_family": 54,
            "verified_here": len(results),
            "quota_by_solve_path": q.get("quota_by_solve_path"),
            "pool_size": q.get("pool_size"),
            "process_constraint_coverage": coverage,
        },
        "independence": {
            "rule": "computed 只由 derive(item) 从**题干文本**抽出的事实算出；"
                    "config 只用于事后一致性核对，不参与计算；answer_raw 仅在比较一步出现",
            "new_in_this_batch": (
                "construct_constraint 族的答案是「构造结果的编码」（排序拼接/按位拼数/"
                "空格拼接/面积），故 expr 中会出现位权 10/100/1000——那是编码规则常量。"
                "本批把它单列进 derivation.encoding_constants 并写明 purpose，"
                "不据此指控「推导不独立」。"),
            "enforced_by": "derive() 只吃 item，其 answer 字段在 evaluate() 的比较步才被读取；"
                           "independent_eval() 只对纯算术表达式求值",
            "caveat": "独立推导能排除「照答案反推」，**不能证明题面解析正确**——"
                      "若我把题意读错，MATCH 也只是「错误理解与答案巧合一致」",
        },
        "feasibility_dimension": {
            "why": "本族含 geometry_constraint（shape-canvas 9 题），"
                   "存在「答案算得出、但界面画不出」的可能，故单列一条维度。",
            "method": "从题面抽 grid 与两条边长，用组件源码事实"
                      "（applyAddPoint 约束 0<=x<grid、span=(grid-1)*CELL）判断可行性；"
                      "并对每个 target_area 穷举钉位组合验证面积是否可达。",
            "infeasible_count": sum(
                1 for r in results
                if (r.get("feasibility") or {}).get("verdict") == "INFEASIBLE_ON_COMPONENT"),
        },
        "summary": {
            "total": len(results),
            "match": sum(1 for r in results if r["verdict"] == "MATCH"),
            "mismatch": sum(1 for r in results if r["verdict"] == "MISMATCH"),
            "config_inconsistent": sum(
                1 for r in results if r["config_vs_stem"]["status"] != "CONSISTENT"),
            "infeasible_on_component": sum(
                1 for r in results
                if (r.get("feasibility") or {}).get("verdict") == "INFEASIBLE_ON_COMPONENT"),
            "observation_counts": _obs_counts(results),
            "process_constraint_declared": sum(
                1 for r in results if r["evidence_enforcement"]["enforced_by_backend"]),
            "by_renderer": by_renderer,
            "by_solve_path": by_solve,
            "match_definition": "MATCH 只表示「从题面独立推导/构造的结果与存储答案相等」，"
                                "不表示该题的交互、可完成性或教学质量已验收",
        },
        "items": results,
    }

    # Q05 逐题生成 + 三条机器校验（第四批铁律）
    all_ids = [r["rvid"] for r in out["items"]]
    bad: list[str] = []
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
        blob = json.dumps(r["q05_candidates"], ensure_ascii=False)
        for other in all_ids:
            if other != r["rvid"] and other[:8] in blob:
                bad.append(f"{r['rvid'][:8]} 的 Q05 引用了他题 {other[:8]}")
        for fixed in ("应为 660/270", "答 300（应为"):
            if fixed in blob:
                bad.append(f"{r['rvid'][:8]} 的 Q05 含跨题固定答案串：{fixed}")
        _vals = re.findall(r"(\d+)（", q05["competing"])
        _dup = sorted({v for v in _vals if _vals.count(v) > 1})
        # 同值错法必须是「并列注明不可分」的唯一一档，不能出现两次独立条目
        if _dup and "在该题内部不可分" not in q05["competing"]:
            bad.append(f"{r['rvid'][:8]} 的 Q05 把同值错法并列登记：{_dup}")

    # **先校验，后落盘**（第四批铁律：失败也留下产物会污染下一轮基线）
    if bad:
        print(f"**Q05 校验失败 {len(bad)} 项**：", file=sys.stderr)
        for c in bad:
            print(f"  ✗ {c}", file=sys.stderr)
        print("**未写出 JSON**：校验失败不落盘。", file=sys.stderr)
        return 1

    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    s = out["summary"]
    print(f"Q03-BATCH6: {s['match']} MATCH / {s['mismatch']} MISMATCH / {s['total']} 题"
          f"（construct_constraint 族）")
    print(f"  config↔题面不一致：{s['config_inconsistent']} 题")
    print(f"  题面在组件上不可完成：{s['infeasible_on_component']} 题")
    print(f"  process_constraint 已声明（本批）："
          f"{s['process_constraint_declared']}/{s['total']} 题")
    cov = out["family_scope"]["process_constraint_coverage"]
    print(f"  process_constraint 已声明（全族 54）："
          f"{cov['with_process_constraint']}/{cov['family_total']} 题；"
          f"缺口全在 {'/'.join(cov['renderers_without_any_pc'])}")
    for rend, b in sorted(by_renderer.items()):
        print(f"  {rend:16s} {b['match']}/{b['n']}"
              f"（不一致 {b['inconsistent']}，不可完成 {b['infeasible']}）")
    for sp, b in sorted(by_solve.items()):
        print(f"  [{sp:20s}] {b['match']}/{b['n']}")
    for r in results:
        if r["verdict"] != "MATCH":
            print(f"  ✗ {r['rvid'][:8]} {r['renderer']} computed={r['computed']} "
                  f"stated={r['stated_answer']!r} expr={r['derivation']['expr']}")
        if r["config_vs_stem"]["issues"]:
            print(f"  ⚠ {r['rvid'][:8]} {r['renderer']} config↔题面："
                  f"{r['config_vs_stem']['issues']}")
        if (r.get("feasibility") or {}).get("verdict") == "INFEASIBLE_ON_COMPONENT":
            f = r["feasibility"]
            print(f"  ⚠ {r['rvid'][:8]} {r['renderer']} **不可完成**："
                  f"题面 {f['required_base']}×{f['required_height']}，"
                  f"组件跨度 {f['component_span']}（grid={f['component_grid']}）")
    print(f"out: {OUT}")
    return 0 if out["summary"]["mismatch"] == 0 else 1


# ── 区分力自证（门禁用；不连库、不写产物）────────────────────────────────
def selftest() -> int:
    """证明这批核验器「改坏了会失败」。

    四类变异，各验一件事：
      A. answer +1000 → 必须 MISMATCH（比较环节真的在工作）
      B. 题干关键数字变异 → computed 必须变化（推导真的读题面）
      C. config 已知量改成题面没有的数 → config_vs_stem 必须 INCONSISTENT
      D. 把题面边长改成超出板面 → feasibility 必须 INFEASIBLE
         （**本批新增维度的有效性证明**；不测这条就等于该维度空转）
    """
    if not os.path.exists(QUOTA):
        print("缺 batch6_quota_list.json", file=sys.stderr)
        return 2
    items = json.load(open(QUOTA, encoding="utf-8"))["items"]
    fails: list[str] = []

    # A：答案篡改
    caught = 0
    for it in items:
        x = json.loads(json.dumps(it))
        x["answer_raw"] = str(int(float(x["answer_raw"])) + 1000)
        if evaluate(x)["verdict"] == "MISMATCH":
            caught += 1
    if caught != len(items):
        fails.append(f"答案篡改只检出 {caught}/{len(items)}")

    # B：题干数字变异——**逐位逐个数字试**，不是盲目改第一个数字。
    #
    # 首版按「取题干第一个数字 +7」构造，三类题全部报「computed 未变」。
    # 复查后确认**是变异构造错了，不是判据失效**：
    #   place-value  「位值卡片[5, 8]」→ 首个数字在卡片池里，而推导用的是
    #                 位名指派「十位是5」，改 pool 不影响按位拼数；
    #   shape-canvas 「5×5方格纸」→ 首个数字是纸张尺寸，不是边长；
    #   sorting-board「桌上有4张数字卡」→ 首个数字是卡数量，不是卡片值。
    # 修法不是放宽判据，而是让变异真的改到「参与推导的那个数」：
    # 对每个数字位逐个 +7，只要**至少一处**能让 computed 变化或推导崩溃，
    # 就证明推导确实在读题面。全部数字位都改不动 → 才是真的没读题面。
    seen: set[str] = set()
    mut_ok = 0
    for it in items:
        sp = it.get("solve_path") or "?"
        if sp in seen:
            continue
        seen.add(sp)
        base = evaluate(it)["computed"]
        stem = it["stem"]
        positions = [(mm.start(), mm.end(), int(mm.group(0)))
                     for mm in re.finditer(r"\d+", stem)]
        if not positions:
            fails.append(f"{sp}: 题干无数字，变异无法构造")
            continue
        reactive = 0
        crashes = 0
        for st, en, v in positions:
            x = json.loads(json.dumps(it))
            x["stem"] = stem[:st] + str(v + 7) + stem[en:]
            try:
                after = evaluate(x)["computed"]
            except ValueError:
                # 推导对题面格式敏感而崩溃，也算「读到了题面」
                crashes += 1
                reactive += 1
                continue
            if abs(after - base) > 1e-9:
                reactive += 1
        if reactive == 0:
            fails.append(f"{sp} ({it['rvid'][:8]}): 题干 {len(positions)} 个数字位"
                         f"逐个 +7 后 computed 全未变（推导没真读题面？）")
        else:
            mut_ok += 1
            if crashes:
                print(f"  · {sp} ({it['rvid'][:8]}) 变异中有 {crashes} 处触发"
                      f"推导崩溃（说明解析对题面格式敏感，建议记录）",
                      file=sys.stderr)

    # C：config 一致性变异
    cons_seen: set[str] = set()
    cons_ok = 0
    for it in items:
        r = it["renderer"]
        if r in cons_seen:
            continue
        cons_seen.add(r)
        x = json.loads(json.dumps(it))
        ui = x["ui_schema"]
        ui = json.loads(ui) if isinstance(ui, str) else ui
        cfg = (ui.get("workspaces") or [{}])[0].get("config") or {}
        if r == "money-board":
            cfg["price"] = 91
        elif r == "place-value":
            cfg["target"] = 91
        elif r == "array-board":
            cfg["target_cols"] = 9
        elif r == "shape-canvas":
            cfg["target_area"] = 91
        elif r == "sorting-board":
            cfg["direction"] = "desc"
        elif r == "pattern-board":
            cfg["blanks"] = 3
        else:
            continue
        x["ui_schema"] = json.dumps(ui, ensure_ascii=False)
        try:
            ev = evaluate(x)
        except ValueError as e:
            fails.append(f"{r}: config 变异后推导崩溃 {e}")
            continue
        if ev["config_vs_stem"]["status"] != "INCONSISTENT":
            fails.append(f"{r} ({it['rvid'][:8]}): config 改成 91/异常值后"
                         f"一致性检查未报警（该检查是空转）")
        else:
            cons_ok += 1

    # D：可完成性维度有效性——必须用真实存在的题构造真实越界
    feas_ok = 0
    geo = [it for it in items if it["renderer"] == "shape-canvas"]
    if not geo:
        fails.append("本批无 shape-canvas 题，可完成性维度无法自证")
    for it in geo[:1]:
        x = json.loads(json.dumps(it))
        x["stem"] = re.sub(r"(长|底边)\s*\d+\s*格", r"\g<1>9 格", x["stem"])
        try:
            ev = evaluate(x)
        except ValueError as e:
            fails.append(f"shape-canvas 边长变异后推导崩溃 {e}")
            continue
        f = ev.get("feasibility") or {}
        if f.get("verdict") != "INFEASIBLE_ON_COMPONENT":
            fails.append(f"shape-canvas ({it['rvid'][:8]}): 题面边长改成 9 格后 "
                         f"feasibility 未判 INFEASIBLE（该维度是空转）")
        else:
            feas_ok += 1

    # D2：反向对照——合法题必须判 FEASIBLE（防「一律 INFEASIBLE」的假通过）
    #
    # 注意：这里**不能要求 5/5 全过**。实测 5 题里恰有 1 题
    # （8b41e648，V14-P0-102「长5格、宽2格」/ grid=5）是真不可完成——
    # 把它要求成 FEASIBLE 就等于逼检测器对真实缺陷说假话（项目硬规则：
    # 门禁不得逼内容说错话）。故此处只断言「至少一题 FEASIBLE」+
    # 「不可完成的那题必须精确点名」，后者才是真正有区分力的对照。
    feas_legit = 0
    infeasible_ids: list[str] = []
    for it in geo:
        f = (evaluate(it).get("feasibility") or {})
        if f.get("verdict") == "FEASIBLE":
            feas_legit += 1
        else:
            infeasible_ids.append(it["rvid"][:8])
    if geo and feas_legit == 0:
        fails.append("所有 shape-canvas 题都判 INFEASIBLE——可完成性判据可能恒真")
    if infeasible_ids != ["8b41e648"]:
        fails.append(f"不可完成集合与人工核对结果不符：实测 {infeasible_ids}，"
                     f"应为 ['8b41e648']（V14-P0-102 长5格宽2格 / grid=5 跨度4）")

    if fails:
        print("**Q03-BATCH6-SELFTEST 未通过**：", file=sys.stderr)
        for f in fails:
            print(f"  ✗ {f}", file=sys.stderr)
        return 1
    print(f"Q03-BATCH6-SELFTEST: PASS（答案篡改 {caught}/{len(items)} 检出；"
          f"题干数字变异 {mut_ok}/{len(seen)} 检出；"
          f"config 不一致 {cons_ok}/{len(cons_seen)} 检出；"
          f"可完成性变异 {feas_ok} 检出、合法 {feas_legit}/{len(geo)} 通过）")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main())