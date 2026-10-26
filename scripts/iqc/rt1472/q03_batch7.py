"""FE-1472 第七批｜Q03 逐题独立核验（读 batch7_quota_list.json）。

## 本批覆盖 35 题 = construct_constraint 余量 34 + open_estimate 全量 1

第六批核了 construct_constraint 20/54。本批把余下 34 题与估算族唯一 1 题
一次取全，使两个族可以写成**族级清零**（54/54、1/1）——抽样永远达不到这个终态。

## 与第六批最大的方法学差别：**题面模板必须显式登记**

第六批 `q03_batch6.py` 的 `derive()` 用「边写边补正则」的方式，只覆盖了
第六批 20 题实际出现的写法。本批 35 题是同一族的另外一批题，题面写法
明显更多样。`freeze_batch7.py --probe` 用第六批规则硬套本批 35 题，实测：

    renderer            n   可直接覆盖   算错   抽不到
    array-board         7      7          0      0
    estimation-canvas   1      0          0      1
    money-board         6      4        **1**    1
    pattern-board       6      3          0      3
    place-value         4      2          0      2
    shape-canvas        4      3          0      1
    sorting-board       7      6          0      1

两条结论，都必须落到代码而不是文档里：

1. **`money-board` 有 1 题会被静默算错**（`8a658f5e`：「一支笔标价10角，
   一块橡皮标价5角」，第六批因题面无「另一件」三字而只取第一个标价 → 10，
   真值 15）。这类错误的可怕之处在于**不报错**：核验器会输出 MISMATCH，
   看起来像题库算错，实际是核验器读错题。故本批改用**显式的题面模板表**
   `STEM_TEMPLATES`，每模板声明「要抽哪几个量」，抽出数与声明数不符即 rc=2。

2. **抽不到必须 rc=2，不能 rc=1**。rc=1 的含义是「核验失败（结论不成立）」；
   「核验器读不懂题」是工件/环境问题，与 `_check_layout()` 返 2 同款。

## 估算题为什么与构造族同批但判据分开

`open_estimate` 那题（`cd7f008d`）第六批的裁定是「单列待定，不与构造类混批」，
本批推翻了它，但**只推翻「同批」，不推翻「判据分开」**。事实基础（源码+数据实测）：

  - 前端 `estimationCanvasV2.ts:114`：`PASS` 判据是 `e === config.expected`，
    **严格相等**；`tolerance` 只在 `:119` 算 `close`（诊断粒度），不参与判分。
  - 后端 `learning.py:1118`：`float(expected) == float(user_answer)`，也是严格相等。
    （估算题与其他题在判分上是**同一套**口径，因此 verdict 可比。）
  - 但**推导不可复算**：题面只给「这一摞是 10 本」「比这一摞多得多」，
    `config.actual=38` 与 `expected=40` **都不在题面里**。孩子看不到 38，
    无法从题面唯一确定 40。

故本批对估算题**不给 MATCH**，而给 `UNVERIFIABLE_FROM_STEM` 这一独立类别：

  - 它**不是** MISMATCH（不能据此说答案错）；
  - 也**不是** MATCH（不能据 config 自证 config，那是循环论证）；
  - 本批核到的东西是**可核的**：`expected == round(actual/10)*10`（源码规则）、
    `0 <= expected <= max`（滑条可达）、`reference < actual`（「多得多」的
    语义下限）、`tolerance` 不影响判分。这些逐条登记，供人工终审。

**绝不为凑齐 35/35 而把估算题记成 MATCH**——那是用放宽判据换覆盖率。

## 链（每步可单独复核）

  题干 → 命中登记模板 → 抽取题面事实 → 明确所求对象 → 独立推导/构造（纯算术）
       → 断言 config 已知量 ⊆ 题面事实 → 题面可完成性 → 与存储答案比较

用法：
  export DATABASE_URL="$(security find-generic-password -s iqc-database-url -w)"
  python scripts/iqc/rt1472/q03_batch7.py              # 连库核验，写产物
  python scripts/iqc/rt1472/q03_batch7.py --selftest    # 门禁用，不连库
  python scripts/iqc/rt1472/q03_batch7.py --crossbatch  # 验证第六批 20 题仍算对
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


def _check_layout() -> int:
    """确认脚本位于仓库内，否则以 2 退出（0=正常继续）。

    与 `check_independence.py` / `q03_batch6.py` 同款修法：`assert` 触发时进程
    以 **1** 结束，与「1 = 核验失败」撞码。直接解压交付件（扁平目录）跑会得到
    rc=1，看起来像结论不成立，其实只是布局不对。
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

QUOTA = os.path.join(HERE, "batch7_quota_list.json")
OUT = os.path.join(REPO, "scripts/iqc/runs/FE1472_q03_batch7.json")

CN_NUM = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6,
          "七": 7, "八": 8, "九": 9, "十": 10}
PLACE_WEIGHT = {"千": 1000, "百": 100, "十": 10, "个": 1}

# 后端过程校验支持的 mode（源码事实：process_validate.py:199-204）。
# **不凭记忆**——若源码改了，这里必须跟着改，否则「无校验器」的判断会失真。
BACKEND_MODES = ("pattern_extension", "payment_change",
                 "shape_drawing", "place_value_build")


class StemError(ValueError):
    """题面读不懂 → 调用方必须 rc=2（工件/规则问题，不是核验失败）。"""


def independent_eval(expr: str) -> float:
    """只对由 derive() 构造的纯算术表达式求值，不接触答案。

    白名单**不含 IfExp**——分支题不得用三元表达式把判断塞进 expr，
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


def _canon_sha256(obj) -> str:
    """canonical JSON sha256——**必须与 `freeze_batch7.py::_sha()` 逐字同款**。

    冻结侧在 `freeze_batch7.py:163-166` 定义，这里不能"看起来差不多"：
    - 同为 `sort_keys=True`、`separators=(",", ":")`、`ensure_ascii=False`；
    - 同为**解析后的对象**入参（dict），不是 DB 的 `::text` 排版。

    换掉任一参数都会让全部 35 题的哈希对不上，而现象看起来像"题库全被改了"。
    今日实踩：对 `ui_schema::text` 算哈希 → 35/35 误报漂移。
    """
    import hashlib
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _cfg(item: dict) -> dict:
    return _ws(item).get("config") or {}


def _nums(text: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", text or "")]


def _one(pattern: str, text: str, what: str, grp: int = 1) -> str:
    """取一个**唯一**匹配；取不到或取到多个都抛 StemError。

    「取到多个」也抛，是因为题面模板化程度很高，多匹配通常意味着模板选错
    （例：money-board 的「标价10角…标价5角」被单件模板匹配到两次）。
    """
    ms = re.findall(pattern, text)
    if not ms:
        raise StemError(f"抽不到{what}：pattern={pattern!r} stem={text[:70]!r}")
    if len(ms) > 1:
        raise StemError(f"{what} 抽到 {len(ms)} 个（模板可能选错）：{ms} "
                        f"stem={text[:70]!r}")
    return ms[0]


def _concat_expr(tokens: list[int]) -> str:
    """把一串一位数按顺序拼成整数：位权展开（编码规则，不是答案）。"""
    n = len(tokens)
    parts = []
    for i, t in enumerate(tokens):
        w = 10 ** (n - 1 - i)
        parts.append(f"{t} * {w}" if w > 1 else f"{t} * 1")
    return " + ".join(parts)


def _encoding_constants(expr: str, stem: str) -> list[dict]:
    """列出 expr 里不出现在题干中的数字，供人工分诊（不是判决）。

    必须排除 `* 1`：个位权重为 1 时表达式写 `d * 1`，那个 `1` 是
    「不乘位权」的句式产物，不是信息量。不排除会把真实待分诊项淹没。
    """
    stem_nums = set(_nums(stem))
    out = []
    for n in sorted({x for x in _nums(expr)}):
        if n in stem_nums:
            continue
        if n == 1:
            out.append({"value": 1,
                        "purpose": "个位位权=1（`d * 1` 即不乘位权，句式产物）"})
            continue
        if n in (10, 100, 1000):
            out.append({"value": n, "purpose": "进位权（十进制位值编码规则）"})
            continue
        out.append({"value": n, "purpose": "UNCLASSIFIED"})
    return out


# ── 题面模板登记表 ──────────────────────────────────────────────────────
# 每个模板声明：名称、必需抽取的量、判据说明。**命中多个模板 = 模板歧义 = rc=2**，
# 因为歧义意味着「同一句题面能被两种规则读成两个值」，静默选一个就是在赌。
#
# 设计原则：模板只描述**题面给了什么**，不描述答案长什么样。
STEM_TEMPLATES: list[dict] = [
    # ── money-board 四型（第六批只有两种，本批实测出现四种）──────────────
    {
        "id": "money_two_items_sum",
        "renderer": "money-board",
        "requires": ["prices"],
        "why": "「一件…标价A角，另一件标价B角」→ 求和。**不能靠「另一件」三字**"
               "判定：8a658f5e 写的是「一支笔标价10角，一块橡皮标价5角」，"
               "第六批规则因缺这三字而只取首个标价，静默算出 10（真值 15）。",
    },
    {
        "id": "money_single_direct",
        "renderer": "money-board",
        "requires": ["price"],
        "why": "「一本练习本标价A角」→ 题面直给总价，无需运算",
    },
    {
        "id": "money_yuan_jiao",
        "renderer": "money-board",
        "requires": ["yuan", "jiao"],
        "why": "「一本练习本 3 元 5 角」→ 元角换算（1 元=10 角），"
               "第六批只认「标价N角」，此题抽不到而崩溃。"
               "换算常量 10 是**单位制常量**，不是 config 数据。",
    },
    # ── place-value 三型 ─────────────────────────────────────────────────
    {
        "id": "pv_cards_plus_assignment",
        "renderer": "place-value",
        "requires": ["pool", "assigns"],
        "why": "「位值卡片[6, 3]…按十位是6，个位是3」——卡片池 + 位名指派齐全",
    },
    {
        "id": "pv_goal_direct",
        "renderer": "place-value",
        "requires": ["digits", "places", "target"],
        "why": "「数字卡 3、5、2…放回百、十、个的框里，组成 352」——"
               "**题面直接给了目标数**。此时答案不是「推导」出来的，"
               "而是题面给定；核验点转为「卡片池能否拼出该数」+「位序是否相符」。"
               "此时 verdict 记为 STEM_GIVEN_ANSWER，不是 MATCH（见 evaluate）。",
    },
    {
        "id": "pv_constraint_only",
        "renderer": "place-value",
        "requires": ["digits", "places", "constraints"],
        "why": "「三张数字卡 3、0、5…①百位框放3；②个位框的数比十位框的数大」"
               "——题面**不给目标数**，只给两条约束，需要用约束唯一确定排列。"
               "本模板独立求解（穷举满足约束的排列），是真推导。",
    },
    # ── array-board 一型 ────────────────────────────────────────────────
    {
        "id": "array_rows_cols",
        "renderer": "array-board",
        "requires": ["cols", "rows"],
        "why": "「每行摆N个棋子，共摆M行」→ N×M",
    },
    # ── shape-canvas 三型 ────────────────────────────────────────────────
    {
        "id": "shape_base_height",
        "renderer": "shape-canvas",
        "requires": ["base", "height"],
        "why": "「底边A格、高B格」",
    },
    {
        "id": "shape_length_width",
        "renderer": "shape-canvas",
        "requires": ["base", "height"],
        "why": "「长A格、宽B格」",
    },
    {
        "id": "shape_area_only",
        "renderer": "shape-canvas",
        "requires": ["area"],
        "why": "「围出一个长方形，要正好盖住 A 个格子（面积=A）。…答案填它的面积」"
               "——题面**只给面积**，不给边长，答案是题面给定值；"
               "核验点转为「该面积在板上是否可达」+「是否存在整数边长分解」，"
               "verdict 记 STEM_GIVEN_ANSWER。",
    },
    # ── sorting-board 二型 ──────────────────────────────────────────────
    {
        "id": "sort_bracket_list",
        "renderer": "sorting-board",
        "requires": ["cards", "direction"],
        "why": "「当前从左到右依次是[6, 2, 8, 4]」——方括号列表",
    },
    {
        "id": "sort_inline_list",
        "renderer": "sorting-board",
        "requires": ["cards", "direction"],
        "why": "「排得乱七八糟：7、1、4、2（卡片上的字有大有小…）」"
               "——**无方括号**的顿号列表，第六批只认方括号而抽不到。",
    },
    # ── pattern-board 四型 ───────────────────────────────────────────────
    {
        "id": "pattern_named_codes",
        "renderer": "pattern-board",
        "requires": ["visible", "blanks", "code_map"],
        "why": "题面可见段是**颜色名**，需先按题面给的颜色→编码映射转成数字。"
               "覆盖两种写法：①「黄、蓝、黄、蓝……」；"
               "②「红、黄、黄，红、黄，黄……已经闪了这样两轮」"
               "（**逗号分轮**——不能把逗号当序列结束，否则只抽到一轮加半个周期，"
               "周期判不出来）。第六批只认数字序列，这两种都抽不到。",
    },
    {
        "id": "pattern_visible_digits",
        "renderer": "pattern-board",
        "requires": ["visible", "blanks"],
        "why": "「前四格依次是 4、1、4、1…补上接下来的两格」——数字序列直给",
    },
    {
        "id": "pattern_claim_judge",
        "renderer": "pattern-board",
        "requires": ["visible", "blanks", "claimed"],
        "why": "「小贝…说：接下来的两格都应填5、5。请先核对…若有错误填正确的，"
               "若正确就保留」——判断题变体；需独立判断 claimed 是否符合周期，"
               "**不能预设他错**（第六批 e6bc5139 他确实错了，本批 82ff6618 也错，"
               "但规则仍需真的判断）。",
    },
    # ── estimation-canvas ───────────────────────────────────────────────
    {
        "id": "estimation_reference_round_ten",
        "renderer": "estimation-canvas",
        "requires": ["reference"],
        "why": "「这一摞是 10 本…比这一摞多得多…（答案估到最接近的整十）」"
               "——**题面只有参照量与定性比较，没有实际数量**，"
               "故答案不可从题面独立推出，见 ESTIMATION 分支处理。",
    },
]


def _match_template(item: dict) -> tuple[dict, dict]:
    """按 renderer 过滤后逐个模板试抽取，**必须恰好命中一个**。

    返回 (template, facts)。命中 0 个或 >1 个都抛 StemError——歧义不是
    「选一个更像的」，而是「规则不足，需要人工补模板」。
    """
    r = item["renderer"]
    cands = [t for t in STEM_TEMPLATES if t["renderer"] == r]
    if not cands:
        raise StemError(f"renderer 无登记模板：{r}")
    hits = []
    errs = []
    for t in cands:
        try:
            facts = _EXTRACTORS[t["id"]](item["stem"])
        except StemError as e:
            errs.append(f"{t['id']}: {e}")
            continue
        hits.append((t, facts))
    if not hits:
        raise StemError(f"{r} 无任何模板命中；试过：\n  " + "\n  ".join(errs))
    if len(hits) > 1:
        raise StemError(f"{r} 命中 {len(hits)} 个模板（歧义）："
                        f"{[t['id'] for t, _ in hits]}")
    return hits[0]


# ── 各模板的抽取器（**只读题面**，不碰 config / answer）──────────────────
def _ex_money_two_items(stem: str) -> dict:
    # 「标价A角…标价B角」：两处标价缺一不可。**不依赖「另一件」措辞**。
    prices = [int(x) for x in re.findall(r"标价\s*(\d+)\s*角", stem)]
    if len(prices) != 2:
        raise StemError(f"two_items 需恰好 2 个标价，实得 {prices}")
    return {"prices": prices}


def _ex_money_single(stem: str) -> dict:
    prices = [int(x) for x in re.findall(r"标价\s*(\d+)\s*角", stem)]
    if len(prices) != 1:
        raise StemError(f"single 需恰好 1 个标价，实得 {prices}")
    return {"price": prices[0]}


def _ex_money_yuan_jiao(stem: str) -> dict:
    m = re.search(r"(\d+)\s*元\s*(\d+)\s*角", stem)
    if not m:
        raise StemError("抽不到「N元M角」")
    # 题面若出现两次「N元M角」（题干+要求各一次），必须一致，否则歧义
    all_pairs = re.findall(r"(\d+)\s*元\s*(\d+)\s*角",
                           re.sub(r"钱包里有.*?四种钱", "", stem))
    yuan, jiao = int(m.group(1)), int(m.group(2))
    if all_pairs and any((int(a), int(b)) != (yuan, jiao) for a, b in all_pairs):
        raise StemError(f"题面出现多个不同的「N元M角」：{all_pairs}")
    return {"yuan": yuan, "jiao": jiao}


def _ex_pv_cards_assignment(stem: str) -> dict:
    mp = re.search(r"位值卡片\s*\[([\d,\s]+)\]", stem)
    if not mp:
        raise StemError("抽不到「位值卡片[...]」")
    assigns = re.findall(r"(千|百|十|个)位是\s*(\d+)", stem)
    if not assigns:
        raise StemError("抽不到位名指派")
    return {"pool": [int(x) for x in re.findall(r"\d+", mp.group(1))],
            "assigns": [(p, int(d)) for p, d in assigns]}


def _ex_pv_goal_direct(stem: str) -> dict:
    # 「数字卡 3、5、2 走丢了。把它们放回百、十、个的框里，组成 352」
    md = re.search(r"数字卡\s*([\d、,，\s]+?)\s*走丢", stem)
    if not md:
        raise StemError("抽不到「数字卡 … 走丢了」")
    # **先抓整段位名列表，再从中取位名**：首版用
    # `(千|百|十|个)、?(?=(?:千|百|十|个))` 前瞻式匹配，要求位名后面
    # 还跟着另一个位名，于是「百、十、个」的最后那个「个」被吃掉——
    # 抽出 ['百','十'] 而目标 352 是三位数，被误报成
    # 「题面位名数 2 ≠ 目标位数 3」的**内容不一致**。
    # 判据写错产假结论，这是本批第三次踩到同类。
    mseg = re.search(r"放回\s*((?:(?:千|百|十|个)[、,，]?){2,})的?框", stem)
    if not mseg:
        raise StemError("抽不到位名序列")
    places = re.findall(r"(千|百|十|个)", mseg.group(1))
    mt = re.search(r"组成\s*(\d+)", stem)
    if not mt:
        raise StemError("抽不到「组成 N」")
    if len(places) != len(str(mt.group(1))):
        raise StemError(f"题面位名数 {len(places)} ≠ 目标位数 {len(mt.group(1))}"
                        f"（位名抽取可能仍有遗漏）")
    return {"digits": [int(x) for x in re.findall(r"\d+", md.group(1))],
            "places": places, "target": int(mt.group(1))}


def _ex_pv_constraint(stem: str) -> dict:
    md = re.search(r"数字卡\s*([\d、,，\s]+?)\s*要放进", stem)
    if not md:
        raise StemError("抽不到「数字卡 … 要放进」")
    mplaces = re.search(r"放进((?:千|百|十|个)、?(?:千|百|十|个)?、?(?:千|百|十|个)?)的?三?个?框",
                        stem)
    if not mplaces:
        raise StemError("抽不到位名序列")
    places = re.findall(r"(千|百|十|个)", mplaces.group(1))
    cons = []
    for m in re.finditer(r"(千|百|十|个)位框(?:里)?放\s*(\d+)", stem):
        cons.append({"kind": "fixed", "place": m.group(1), "digit": int(m.group(2))})
    if re.search(r"个位框的数比十位框的数大", stem):
        cons.append({"kind": "gt", "left": "个", "right": "十"})
    if not cons:
        raise StemError("抽不到任何约束")
    return {"digits": [int(x) for x in re.findall(r"\d+", md.group(1))],
            "places": places, "constraints": cons}


def _ex_array(stem: str) -> dict:
    cols = _one(r"每行摆\s*(\d+)\s*个", stem, "每行个数")
    rows = _one(r"共摆\s*(\d+)\s*行", stem, "行数")
    return {"cols": int(cols), "rows": int(rows)}


def _ex_shape_base_height(stem: str) -> dict:
    return {"base": int(_one(r"底边\s*(\d+)\s*格", stem, "底边")),
            "height": int(_one(r"高\s*(\d+)\s*格", stem, "高"))}


def _ex_shape_length_width(stem: str) -> dict:
    return {"base": int(_one(r"长\s*(\d+)\s*格", stem, "长")),
            "height": int(_one(r"宽\s*(\d+)\s*格", stem, "宽"))}


def _ex_shape_area_only(stem: str) -> dict:
    m = re.search(r"盖住\s*(\d+)\s*个格子", stem) or re.search(r"面积\s*=\s*(\d+)", stem)
    if not m:
        raise StemError("抽不到面积")
    if "面积填" not in stem and "答案填它的面积" not in stem:
        raise StemError("题面未明示「答案填面积」——不能假定所求对象")
    return {"area": int(m.group(1))}


def _ex_sort_bracket(stem: str) -> dict:
    mb = re.search(r"依次是\s*\[([\d,\s]+)\]", stem)
    if not mb:
        raise StemError("抽不到「依次是[...]」")
    return {"cards": [int(x) for x in re.findall(r"\d+", mb.group(1))],
            "direction": _dir(stem),
            "raw": mb.group(1)}


def _ex_sort_inline(stem: str) -> dict:
    # 「排得乱七八糟：7、1、4、2（卡片上的字…）」——冒号后到括号前的顿号列表
    mi = re.search(r"[：:]\s*([\d、,，]+)\s*(?:（|\()", stem)
    if not mi:
        raise StemError("抽不到冒号后的顿号数列")
    val = [int(x) for x in re.findall(r"\d+", mi.group(1))]
    if len(val) < 2:
        raise StemError(f"内联数列不足 2 个：{val}")
    return {"cards": val, "direction": _dir(stem), "raw": mi.group(1)}


def _dir(stem: str) -> str:
    if "从小到大" in stem:
        return "asc"
    if "从大到小" in stem:
        return "desc"
    raise StemError("抽不到排序方向")


def _code_map(stem: str) -> dict:
    """「黄=1，蓝=2」/「红=1、黄=2」→ {颜色名: 编码}。"""
    pairs = re.findall(r"([\u4e00-\u9fa5])\s*=\s*(\d+)", stem)
    if not pairs:
        raise StemError("抽不到颜色→编码映射")
    return {name: int(code) for name, code in pairs}


def _ex_pattern_named(stem: str) -> dict:
    """抽颜色可见段。两种写法都要覆盖，且**不能把逗号当序列终点**。

    A. 「**黄、蓝、黄、蓝**……后面还缺 2 颗珠子」
    B. 「红、黄、黄，红、黄，黄……已经闪了这样两轮」
       ——这里 `，` 是「轮」的分隔符，不是序列结束。若按 `，` 截断，
       只能拿到 `[红,黄,黄]`，虽然碰巧周期仍是 3（p=3 需 n>=6 才判得出，
       得到的是 [红,黄,黄] 直接被判「无周期」）→ 崩溃。
       故必须把逗号也当作分隔符，取到「……」之前为止。

    实现：先定位「……」作为终止锚点，取其前的整段，再抽出全部中文颜色字，
    只保留在题面颜色→编码映射表里出现过的字（过滤「已」「看」「这」等）。
    """
    if "……" in stem or "..." in stem:
        idx = min([i for i in (stem.find("……"), stem.find("...")) if i >= 0])
        head = stem[:idx]
    else:
        # 无省略号时退回到冒号后的颜色序列
        m0 = re.search(r"[：:]\s*(.+)$", stem)
        if not m0:
            raise StemError("找不到可见段起点")
        head = m0.group(1)
    # 只取最后一个「：/，」之后到结尾的颜色串（去掉前面叙述句）
    seg = re.split(r"[：:]", head)[-1]
    cmap = _code_map(stem)
    # 按出现顺序抽出映射表里有的单字颜色名
    names = [ch for ch in seg if ch in cmap]
    if len(names) < 4:
        raise StemError(f"可用颜色序列过短：{names}（映射 {cmap}）")
    blanks = _blanks(stem)
    return {"visible_names": names, "code_map": cmap, "blanks": blanks}


def _ex_pattern_digits(stem: str) -> dict:
    m = re.search(r"前四格(?:颜色编码)?(?:依次)?是\s*([\d、,，\s]+)", stem)
    if not m:
        raise StemError("抽不到「前四格…是 X、Y、Z、W」")
    return {"visible": [int(x) for x in re.findall(r"\d+", m.group(1))],
            "blanks": _blanks(stem)}


def _ex_pattern_claim(stem: str) -> dict:
    # 「小贝观察颜色编码3、5、3、5后说："接下来的两格都应填5、5。"」
    m = re.search(r"颜色编码\s*([\d、,，\s]+?)\s*后说", stem)
    if not m:
        raise StemError("抽不到「颜色编码 X 后说」")
    visible = [int(x) for x in re.findall(r"\d+", m.group(1))]
    mc = re.search(r"[“\"]([^”\"]+)[”\"]", stem)
    if not mc:
        raise StemError("抽不到被试的说法")
    claimed = [int(x) for x in re.findall(r"\d+", mc.group(1))]
    if not claimed:
        raise StemError(f"被试说法里无数字：{mc.group(1)!r}")
    return {"visible": visible, "blanks": _blanks(stem), "claimed": claimed}


def _blanks(stem: str) -> int:
    """空格数（颗/格/个/无 CSV 量词多种写法都要认）。

    实测踩到三种措辞，缺一种就有一题崩溃：
      「后面还缺 2 颗珠子」（颗）
      「补上接下来的两格」（格）
      「接下来两个该闪什么」（**两个，无量词「格」**——首版漏了这一型，
        2f2e8491 直接抽不到空格数）
    """
    for pat in (r"还缺\s*(\d+)\s*颗", r"补上接下来的\s*(一|二|两|三|\d)\s*格",
                r"后\s*(一|二|两|三|\d)\s*格", r"接下来的\s*(一|二|两|三|\d)\s*格",
                r"接下来\s*(一|二|两|三|\d)\s*个",
                r"(一|二|两|三|\d)\s*个空格", r"填入.*?(\d+)\s*格"):
        m = re.search(pat, stem)
        if m:
            tok = m.group(1)
            n = int(tok) if tok.isdigit() else CN_NUM.get(tok)
            if n:
                return n
    raise StemError("抽不到空格数")


def _ex_estimation(stem: str) -> dict:
    # 「这一摞是 10 本」——参照量
    m = re.search(r"这一摞是\s*(\d+)\s*本", stem)
    if not m:
        raise StemError("抽不到参照量「这一摞是 N 本」")
    if "多得多" not in stem:
        raise StemError("抽不到「比这一摞多得多」这一比较关系")
    if "最接近的整十" not in stem:
        raise StemError("抽不到「估到最接近的整十」这一取整要求")
    return {"reference": int(m.group(1)),
            "qualitative": "多得多", "round_to": 10}


_EXTRACTORS = {
    "money_two_items_sum": _ex_money_two_items,
    "money_single_direct": _ex_money_single,
    "money_yuan_jiao": _ex_money_yuan_jiao,
    "pv_cards_plus_assignment": _ex_pv_cards_assignment,
    "pv_goal_direct": _ex_pv_goal_direct,
    "pv_constraint_only": _ex_pv_constraint,
    "array_rows_cols": _ex_array,
    "shape_base_height": _ex_shape_base_height,
    "shape_length_width": _ex_shape_length_width,
    "shape_area_only": _ex_shape_area_only,
    "sort_bracket_list": _ex_sort_bracket,
    "sort_inline_list": _ex_sort_inline,
    "pattern_named_codes": _ex_pattern_named,
    "pattern_named_codes_two_rounds": _ex_pattern_named,
    "pattern_visible_digits": _ex_pattern_digits,
    "pattern_claim_judge": _ex_pattern_claim,
    "estimation_reference_round_ten": _ex_estimation,
}


# ── 题面可完成性（shape-canvas 专用）────────────────────────────────────
def geometry_feasibility(stem: str, cfg: dict, base: int | None,
                         height: int | None, area: int | None) -> dict:
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
    out = {
        "stem_grid_declared": stem_grid,
        "component_grid": grid,
        "component_span": (grid - 1) if isinstance(grid, int) else None,
        "required_base": base, "required_height": height,
        "required_area": area,
        "stem_self_consistent": None,
        "fits_component_board": None,
        "area_reachable_on_component": None,
        "area_integer_sides": None,
    }
    if isinstance(grid, int):
        out["area_reachable_on_component"] = (
            any(a * b == area for a in range(1, grid) for b in range(1, grid))
            if area is not None else None)
    if area is not None:
        out["area_integer_sides"] = any(
            a * b == area
            for a in range(1, area + 1)
            for b in range(1, area + 1))
    if base is not None and height is not None:
        out["stem_self_consistent"] = (
            stem_grid is not None and base <= stem_grid and height <= stem_grid)
        out["fits_component_board"] = (
            isinstance(grid, int) and base <= grid - 1 and height <= grid - 1)
        out["verdict"] = ("FEASIBLE" if (out["stem_self_consistent"]
                                         and out["fits_component_board"])
                          else "INFEASIBLE_ON_COMPONENT")
    else:
        # 只给面积的题：无法用边长判，改判「面积是否可由整套边长在板上达成」
        out["verdict"] = ("FEASIBLE_AREA_ONLY"
                          if out["area_reachable_on_component"]
                          else "INFEASIBLE_ON_COMPONENT")
    return out


# ── 逐题独立推导 ────────────────────────────────────────────────────────
def derive(item: dict) -> dict:
    """只吃 item（题干 + ui_schema 只用于**事后**交叉核对）。

    返回 dict，含：
      expr       —— 可被 independent_eval 求值的纯算术表达式
      basis      —— 输入来源声明（题面给了什么 / config 给了什么 / 哪些只能来自 config）
      verdict_hint —— `MATCH` 候选 或 `STEM_GIVEN_ANSWER`（答案由题面直接给定）
      consistency —— config ↔ 题面不一致项（**不影响 verdict**，单独一列）
    """
    tpl, f = _match_template(item)
    cfg = _cfg(item)
    stem = item["stem"]
    tid = tpl["id"]
    cons: list[str] = []
    extra: dict = {"template": tid}

    # ── money-board ────────────────────────────────────────────────────
    if tid == "money_two_items_sum":
        a, b = f["prices"]
        expr = f"{a} + {b}"
        total = a + b
        if cfg.get("price") is not None and cfg["price"] != total:
            cons.append(f"config.price={cfg['price']} ≠ {a}+{b}={total}")
        t = cfg.get("target") or {}
        if t.get("total") not in (None, total):
            cons.append(f"config.target.total={t.get('total')} ≠ {total}")
        return {"read": f"{stem}→ 两件标价 {a} 角与 {b} 角，求总价",
                "expr": expr, "object": f"总价（{a}+{b} 角）",
                "basis": (f"题面抽出两个标价 {a}/{b}；"
                          f"config.price={cfg.get('price')}、target.total="
                          f"{t.get('total')} 仅作交叉核对；**不读答案**"),
                "consistency": cons, "extra": extra, "verdict_hint": "MATCH"}

    if tid == "money_single_direct":
        a = f["price"]
        expr = f"{a} * 1"
        if cfg.get("price") is not None and cfg["price"] != a:
            cons.append(f"config.price={cfg['price']} ≠ 题面 {a}")
        t = cfg.get("target") or {}
        if t.get("total") not in (None, a):
            cons.append(f"config.target.total={t.get('total')} ≠ {a}")
        return {"read": f"{stem}→ 题面直给单件总价 {a} 角",
                "expr": expr, "object": f"总价（题面直给 {a} 角）",
                "basis": (f"题面抽出单件标价 {a}；**本题不含加法**，只有凑币；"
                          f"config 仅作交叉核对；**不读答案**"),
                "consistency": cons, "extra": extra, "verdict_hint": "MATCH"}

    if tid == "money_yuan_jiao":
        yuan, jiao = f["yuan"], f["jiao"]
        expr = f"{yuan} * 10 + {jiao}"
        total = yuan * 10 + jiao
        if cfg.get("price") is not None and cfg["price"] != total:
            cons.append(f"config.price={cfg['price']} ≠ {yuan}元{jiao}角={total}角")
        t = cfg.get("target") or {}
        if t.get("total") not in (None, total):
            cons.append(f"config.target.total={t.get('total')} ≠ {total}")
        extra["unit_constant"] = {"value": 10, "purpose": "1 元 = 10 角（单位制常量）"}
        return {"read": f"{stem}→ {yuan} 元 {jiao} 角，换算成角",
                "expr": expr, "object": f"总价（{yuan}元{jiao}角 = {total} 角）",
                "basis": (f"题面抽出 {yuan} 元 {jiao} 角；换算常量 10 是**单位制常量**"
                          f"（题面亦明示「1 元=10 角」）；"
                          f"config.price={cfg.get('price')} 仅作交叉核对；**不读答案**"),
                "consistency": cons, "extra": extra, "verdict_hint": "MATCH"}

    # ── place-value ────────────────────────────────────────────────────
    if tid == "pv_cards_plus_assignment":
        pool, assigns = f["pool"], f["assigns"]
        by_place = dict(assigns)
        declared = [p for p, _ in assigns]
        n = len(declared)
        ordered = ["千", "百", "十", "个"][-n:]
        if sorted(declared) != sorted(ordered):
            cons.append(f"题面声明的位 {declared} 与 {n} 位数的位序不符")
        digits = [by_place.get(p) for p in ordered]
        if any(d is None for d in digits):
            raise StemError(f"有位没给数字：{assigns}")
        parts = []
        for p, d in zip(ordered, digits):
            w = PLACE_WEIGHT[p]
            parts.append(f"{d} * {w}" if w > 1 else f"{d} * 1")
        expr = " + ".join(parts)
        val = int(independent_eval(expr))
        if cfg.get("target") is not None and cfg["target"] != val:
            cons.append(f"config.target={cfg['target']} ≠ 位名拼数 {val}")
        if cfg.get("pool") is not None and sorted(cfg["pool"]) != sorted(pool):
            cons.append(f"config.pool={cfg['pool']} ≠ 题面卡片池 {pool}")
        if sorted(pool) != sorted(digits):
            cons.append(f"题面卡片池 {sorted(pool)} ≠ 目标各位 {sorted(digits)}")
        extra["place_assignment"] = dict(zip(ordered, digits))
        extra["digit_count"] = n
        return {"read": f"{stem}→ 卡片池 {pool}，位名指派 {by_place}",
                "expr": expr, "object": f"按位拼出的数（{val}）",
                "basis": (f"题面抽出卡片池 {pool} 与位名指派 {by_place}；"
                          f"位权是十进制编码规则（encoding constant）；"
                          f"config.target/pool 仅作交叉核对；**不读答案**"),
                "consistency": cons, "extra": extra, "verdict_hint": "MATCH"}

    if tid == "pv_goal_direct":
        digits, places, target = f["digits"], f["places"], f["target"]
        # 题面直接给了目标数 → 答案不是推导出来的。核验点变为：
        #   ① 卡片池能否拼出该数（multiset 相等）
        #   ② 位序声明是否与位数相符
        # 这两条是真判断，但**都不是**「独立推导出答案」，故 verdict 另立一类。
        n = len(str(target))
        if len(places) != n:
            cons.append(f"题面位名数 {len(places)} ≠ 目标位数 {n}")
        tgt_digits = [int(c) for c in str(target)]
        if sorted(digits) != sorted(tgt_digits):
            cons.append(f"题面卡片池 {sorted(digits)} ≠ 目标各位 "
                        f"{sorted(tgt_digits)}（拼不出该数）")
        ordered = ["千", "百", "十", "个"][-n:] if n <= 4 else places
        if sorted(places) != sorted(ordered[:n]):
            cons.append(f"题面位序 {places} 与 {n} 位数的标准位序 {ordered[:n]} 不符")
        if cfg.get("target") is not None and cfg["target"] != target:
            cons.append(f"config.target={cfg['target']} ≠ 题面给定 {target}")
        if cfg.get("pool") is not None and sorted(cfg["pool"]) != sorted(digits):
            cons.append(f"config.pool={cfg['pool']} ≠ 题面卡片池 {digits}")
        # expr 用题面给定数本身（恒等），使 downstream 一致
        expr = f"{target} * 1"
        extra["stem_given"] = target
        return {"read": f"{stem}→ 题面已给定目标数 {target}，卡片池 {digits}，位序 {places}",
                "expr": expr, "object": f"题面给定数（{target}）",
                "basis": (f"**题面直接给出目标数 {target}**，不存在「从题面推导出答案」"
                          f"这一步；本题的核验点转为「卡片池能否拼出该数」"
                          f"与「位序声明是否相符」两项**可独立判定**的事实。"
                          f"故 verdict 记 STEM_GIVEN_ANSWER 而非 MATCH——"
                          f"MATCH 的定义是「独立推导值 == 存储答案」，"
                          f"本题不满足「独立推导」前提。"),
                "consistency": cons, "extra": extra,
                "verdict_hint": "STEM_GIVEN_ANSWER"}

    if tid == "pv_constraint_only":
        digits, places, constraints = (f["digits"], f["places"],
                                       f["constraints"])
        n = len(places)
        std = ["千", "百", "十", "个"][-n:]
        if sorted(places) != sorted(std):
            cons.append(f"题面位序 {places} 与 {n} 位标准位序 {std} 不符")
        # 穷举所有排列，保留满足全部约束者
        import itertools
        sols = []
        for perm in set(itertools.permutations(digits)):
            if sorted(perm) != sorted(digits):
                continue
            assignment = dict(zip(std, perm))
            ok = True
            for c in constraints:
                if c["kind"] == "fixed":
                    if assignment.get(c["place"]) != c["digit"]:
                        ok = False
                        break
                elif c["kind"] == "gt":
                    if not (assignment.get(c["left"]) is not None
                            and assignment.get(c["right"]) is not None
                            and assignment[c["left"]] > assignment[c["right"]]):
                        ok = False
                        break
                else:
                    raise StemError(f"未知约束类型：{c}")
            if ok:
                sols.append(assignment)
        if not sols:
            raise StemError(f"约束无解（题面不可解）：digits={digits} "
                            f"constraints={constraints}")
        if len(sols) > 1:
            # 多解 → 题面不足以唯一确定，答案不唯一 = 不能记 MATCH
            extra["constraint_solutions"] = [
                {p: s[p] for p in std} for s in sols]
            expr = f"{target_of(sols[0], std)} * 1"
            return {"read": (f"{stem}→ 卡片池 {digits}，约束 {constraints}，"
                             f"满足约束的排列有 {len(sols)} 个"),
                    "expr": expr, "object": "满足约束的排列（**不唯一**）",
                    "basis": (f"穷举 {len(digits)} 个数字的全部排列后，"
                              f"满足题面约束的有 {len(sols)} 个 → "
                              f"题面**不足以唯一确定答案**"),
                    "consistency": cons, "extra": extra,
                    "verdict_hint": "STEM_UNDERDETERMINED"}
        sol = sols[0]
        val = target_of(sol, std)
        parts = []
        for p in std:
            w = PLACE_WEIGHT[p]
            d = sol[p]
            parts.append(f"{d} * {w}" if w > 1 else f"{d} * 1")
        expr = " + ".join(parts)
        if cfg.get("target") is not None and cfg["target"] != val:
            cons.append(f"config.target={cfg['target']} ≠ 约束唯一解 {val}")
        if cfg.get("pool") is not None and sorted(cfg["pool"]) != sorted(digits):
            cons.append(f"config.pool={cfg['pool']} ≠ 题面卡片池 {digits}")
        extra["constraint_solution"] = {p: sol[p] for p in std}
        return {"read": (f"{stem}→ 卡片池 {digits}，约束 {constraints} → "
                         f"唯一解 {sol}"),
                "expr": expr, "object": f"满足约束的唯一排列（{val}）",
                "basis": (f"题面抽出卡片池 {digits} 与约束 {constraints}；"
                          f"**穷举全部排列**后仅一个满足约束 → 答案是约束的唯一解，"
                          f"不是题面给定；位权是编码常量；"
                          f"config 仅作交叉核对；**不读答案**"),
                "consistency": cons, "extra": extra, "verdict_hint": "MATCH"}

    # ── array-board ────────────────────────────────────────────────────
    if tid == "array_rows_cols":
        cols, rows = f["cols"], f["rows"]
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
                "basis": (f"题面抽出 cols={cols}、rows={rows}；"
                          f"config.target_cols/rows 仅作交叉核对；**不读答案**"),
                "consistency": cons, "extra": extra, "verdict_hint": "MATCH"}

    # ── shape-canvas ───────────────────────────────────────────────────
    if tid in ("shape_base_height", "shape_length_width"):
        base, height = f["base"], f["height"]
        expr = f"{base} * {height}"
        area = base * height
        if cfg.get("target_area") is not None and cfg["target_area"] != area:
            cons.append(f"config.target_area={cfg['target_area']} ≠ "
                        f"{base}×{height}={area}")
        if cfg.get("base") is not None and cfg["base"] != base:
            cons.append(f"config.base={cfg['base']} ≠ 题面 {base}")
        if cfg.get("height") is not None and cfg["height"] != height:
            cons.append(f"config.height={cfg['height']} ≠ 题面 {height}")
        if cfg.get("target_shape") != "rectangle":
            cons.append(f"config.target_shape={cfg.get('target_shape')}，"
                        f"本批只核长方形")
        feas = geometry_feasibility(stem, cfg, base, height, area)
        extra["feasibility"] = feas
        return {"read": f"{stem}→ {tid}：{base} 格 × {height} 格，求面积",
                "expr": expr, "object": f"面积（{base}×{height} 平方格）",
                "basis": (f"题面抽出 base={base}、height={height}；"
                          f"**config.base/height 组件不读**"
                          f"（`parseShapeCanvasConfig` 只取 grid/target_area/target_shape），"
                          f"故这两字段仅作题面↔config 交叉核对；"
                          f"面积由题面两数相乘得出；**不读答案**"),
                "consistency": cons, "extra": extra, "verdict_hint": "MATCH"}

    if tid == "shape_area_only":
        area = f["area"]
        expr = f"{area} * 1"
        if cfg.get("target_area") is not None and cfg["target_area"] != area:
            cons.append(f"config.target_area={cfg['target_area']} ≠ 题面 {area}")
        feas = geometry_feasibility(stem, cfg, None, None, area)
        extra["feasibility"] = feas
        # 该面积是否有整数边长分解（题面要求「长方形」且边落格线 → 必须是整数边长）
        if not feas.get("area_integer_sides"):
            cons.append(f"面积 {area} 无整数边长分解，画不成格线长方形")
        return {"read": f"{stem}→ 题面给定面积 {area}，求在板上画出该面积长方形",
                "expr": expr, "object": f"题面给定面积（{area} 平方格）",
                "basis": (f"**题面只给面积 {area}，不给边长**，答案是题面给定值；"
                          f"本题核验点转为「该面积在板上是否可达」"
                          f"（穷举 grid 内边长组合）与「是否有整数边长分解」。"
                          f"verdict 记 STEM_GIVEN_ANSWER。"),
                "consistency": cons, "extra": extra,
                "verdict_hint": "STEM_GIVEN_ANSWER"}

    # ── sorting-board ──────────────────────────────────────────────────
    if tid in ("sort_bracket_list", "sort_inline_list"):
        cards, direction = f["cards"], f["direction"]
        ordered = sorted(cards, reverse=(direction == "desc"))
        expr = _concat_expr(ordered)
        cfg_items = cfg.get("items") or []
        cfg_vals = sorted(x["value"] for x in cfg_items)
        if cfg_vals and cfg_vals != sorted(cards):
            cons.append(f"config.items 的值 {cfg_vals} ≠ 题面卡片 {sorted(cards)}")
        if cfg.get("direction") not in (None, direction):
            cons.append(f"config.direction={cfg.get('direction')} ≠ 题面 {direction}")
        # 初始序若已等于正解序，则「没排」也能给对值 → 该题失去区分力
        by_val = {x["value"]: x["id"] for x in cfg_items}
        if cfg.get("initial_order") and cfg_items:
            missing = [v for v in ordered if v not in by_val]
            if missing:
                cons.append(f"题面卡片值 {missing} 在 config.items "
                            f"{sorted(by_val)} 中不存在（无法核对初始序）")
            else:
                target_ids = [by_val[v] for v in ordered]
                if cfg["initial_order"] == target_ids:
                    cons.append("config.initial_order 已等于正解序（题已做完）")
                extra["initial_order_differs"] = (cfg["initial_order"] != target_ids)
        extra["ordered"] = ordered
        extra["direction"] = direction
        return {"read": (f"{stem}→ 数字卡 {cards}，按「"
                         f"{'从小到大' if direction == 'asc' else '从大到小'}」排"),
                "expr": expr,
                "object": f"排序后拼接的数（{'→'.join(map(str, ordered))}）",
                "basis": (f"题面抽出卡片 {cards} 与方向 {direction}；排序是题面要求；"
                          f"位权展开是编码规则（encoding constant）；"
                          f"config.items 仅作集合交叉核对；**不读答案**"),
                "consistency": cons, "extra": extra, "verdict_hint": "MATCH"}

    # ── pattern-board ──────────────────────────────────────────────────
    if tid in ("pattern_named_codes", "pattern_named_codes_two_rounds"):
        names, cmap, blanks = f["visible_names"], f["code_map"], f["blanks"]
        visible = [cmap[n] for n in names]
        period = _period(visible)
        expected = [visible[(len(visible) + i) % period] for i in range(blanks)]
        expr = _concat_expr(expected)
        if cfg.get("blanks") is not None and cfg["blanks"] != blanks:
            cons.append(f"config.blanks={cfg['blanks']} ≠ 题面 {blanks}")
        if cfg.get("visible") is not None and list(cfg["visible"]) != visible:
            cons.append(f"config.visible={cfg.get('visible')} ≠ 题面映射后 {visible}")
        extra["period"] = period
        extra["expected_tokens"] = expected
        extra["visible_after_code_map"] = visible
        extra["code_map"] = cmap
        return {"read": (f"{stem}→ 颜色段 {names}，按题面映射 {cmap} 转为 {visible}，"
                         f"周期 {period}，缺 {blanks} 格 → 应补 {expected}"),
                "expr": expr,
                "object": f"空格编码拼接（{'→'.join(map(str, expected))}）",
                "basis": (f"题面抽出颜色序列 {names} 与题面给定的颜色→编码映射 {cmap}；"
                          f"**映射来自题面，不是 config**；周期 {period} 由序列本身推出；"
                          f"config.visible/blanks 仅作交叉核对；**不读答案**"),
                "consistency": cons, "extra": extra, "verdict_hint": "MATCH"}

    if tid == "pattern_visible_digits":
        visible, blanks = f["visible"], f["blanks"]
        period = _period(visible)
        expected = [visible[(len(visible) + i) % period] for i in range(blanks)]
        expr = _concat_expr(expected)
        if cfg.get("visible") is not None and list(cfg["visible"]) != visible:
            cons.append(f"config.visible={cfg.get('visible')} ≠ 题面 {visible}")
        if cfg.get("blanks") is not None and cfg["blanks"] != blanks:
            cons.append(f"config.blanks={cfg['blanks']} ≠ 题面 {blanks}")
        pal = cfg.get("palette")
        if pal is not None and not set(visible).issubset(set(pal)):
            cons.append(f"config.palette={pal} 不含题面 token {sorted(set(visible))}")
        extra["period"] = period
        extra["expected_tokens"] = expected
        return {"read": (f"{stem}→ 可见 {visible}，周期 {period}，"
                         f"缺 {blanks} 格 → 应补 {expected}"),
                "expr": expr,
                "object": f"空格编码拼接（{'→'.join(map(str, expected))}）",
                "basis": (f"题面抽出 visible={visible}、blanks={blanks}；"
                          f"周期 {period} 由题面「两次重复」独立推得，"
                          f"不读 config.palette；位权是编码规则；"
                          f"config 仅作交叉核对；**不读答案**"),
                "consistency": cons, "extra": extra, "verdict_hint": "MATCH"}

    if tid == "pattern_claim_judge":
        visible, blanks, claimed = f["visible"], f["blanks"], f["claimed"]
        period = _period(visible)
        expected = [visible[(len(visible) + i) % period] for i in range(blanks)]
        # 独立判断被试是否正确；**不预设他错**
        claim_correct = (claimed == expected)
        chosen = claimed if claim_correct else expected
        expr = _concat_expr(chosen)
        if len(claimed) != blanks:
            cons.append(f"被试填了 {len(claimed)} 格，题面要求 {blanks} 格")
        # config 交叉核对：三道都要核，缺一道该分支就会在变异测试里空转。
        # 首版只核了 blanks 与 palette，**漏了 visible**，于是「改 blanks」
        # 在本分支被 visible 检查之外的路径吸收——自证测试（C 类）实测报出。
        if cfg.get("visible") is not None and list(cfg["visible"]) != visible:
            cons.append(f"config.visible={cfg.get('visible')} ≠ 题面 {visible}")
        if cfg.get("blanks") is not None and cfg["blanks"] != blanks:
            cons.append(f"config.blanks={cfg['blanks']} ≠ 题面 {blanks}")
        pal = cfg.get("palette")
        if pal is not None and not set(visible).issubset(set(pal)):
            cons.append(f"config.palette={pal} 不含题面 token {sorted(set(visible))}")
        extra["period"] = period
        extra["expected_tokens"] = expected
        extra["claimed_tokens"] = claimed
        extra["claim_correct"] = claim_correct
        extra["chosen"] = chosen
        return {"read": (f"{stem}→ 可见 {visible}，周期 {period}，应补 {expected}；"
                         f"被试填 {claimed}（{'对' if claim_correct else '错'}）"
                         f"→ 提交 {'保留他的' if claim_correct else '改填正确值'}"),
                "expr": expr,
                "object": (f"最终提交的编码（{'→'.join(map(str, chosen))}）"),
                "basis": (f"题面抽出 visible={visible}、blanks={blanks}、"
                          f"被试说法 {claimed}；先独立判 claimed==expected，"
                          f"再决定「保留」还是「改填」；"
                          f"**判断写进 encode 而非 expr**；**不读答案**"),
                "consistency": cons, "extra": extra, "verdict_hint": "MATCH",
                "encode": {"kind": "judge_then_fill", "claimed": claimed,
                           "expected": expected, "claim_correct": claim_correct}}

    # ── estimation-canvas ──────────────────────────────────────────────
    if tid == "estimation_reference_round_ten":
        ref = f["reference"]
        actual, expected = cfg.get("actual"), cfg.get("expected")
        mx = cfg.get("max")
        # 源码规则核对（estimationCanvasV2.ts:62）
        rule_ok = (isinstance(actual, int) and isinstance(expected, int)
                   and _round_ten(actual) == expected)
        if not rule_ok:
            cons.append(f"config.expected={expected} ≠ round({actual}/10)*10="
                        f"{_round_ten(actual) if isinstance(actual, int) else 'N/A'}"
                        f"（违反 estimationCanvasV2.ts:62 的自洽约束）")
        if isinstance(expected, int) and isinstance(mx, int) and not (0 <= expected <= mx):
            cons.append(f"config.expected={expected} 超出滑条可达范围 0..{mx}")
        if isinstance(expected, int) and expected % 10 != 0:
            cons.append(f"config.expected={expected} 不是整十（题面要求「估到最接近的整十」）")
        if isinstance(actual, int) and isinstance(ref, int) and actual <= ref:
            cons.append(f"config.actual={actual} ≤ reference={ref}，"
                        f"与题面「多得多」矛盾")
        tol = cfg.get("tolerance")
        extra["tolerance_role"] = (
            "tolerance 只在 evaluateEstimation:119 算 close（诊断粒度），"
            "**不参与 PASS**；PASS 判据是 :114 的 e === expected（严格相等），"
            "后端 learning.py:1118 同为 float 严格相等。故本题**不可**按容差判 MATCH。")
        extra["stem_cannot_derive"] = (
            "题面只有 reference（10 本）与定性比较（多得多），"
            f"config.actual={actual} 与 expected={expected} **均不在题面**；"
            "孩子看不到 actual，无法从题面唯一确定 expected。")
        # expr 用「题面可得的唯一算术事实」：参照量本身（恒等），
        # 不构造 expected——那会是把 config 抄进推导
        expr = f"{ref} * 1"
        return {"read": (f"{stem}→ 题面仅给参照量 {ref} 本与「多得多」；"
                         f"未给实际数量"),
                "expr": expr, "object": "参照量（题面唯一可得的数量事实）",
                "basis": (f"题面可抽出的数量只有 reference={ref}；"
                          f"config.actual={actual}、expected={expected} "
                          f"**都不在题面**。故**无法从题面独立推出答案**——"
                          f"若用 config 算 expected 再与 config 比，是循环论证。"
                          f"本题只核「config 是否自洽」（源码规则、可达性、整十、"
                          f"参照关系），答案本身记 UNVERIFIABLE_FROM_STEM。"),
                "consistency": cons, "extra": extra,
                "verdict_hint": "UNVERIFIABLE_FROM_STEM"}

    raise StemError(f"模板 {tid} 未实现推导分支")


def _round_ten(x: int) -> int:
    """复现 JS `Math.round(x/10)*10`：**.5 向 +∞ 取整**。

    不能用 Python 内置 round（银行家舍入）：round(0.5)=0 而 Math.round(0.5)=1。
    本批 actual=38 不受影响，但规则必须写对，否则边界题会算错。
    """
    return int((x + 5) // 10) * 10


def _period(visible: list[int]) -> int:
    """最小周期 p（2 <= p <= len//2，且至少出现两次）。"""
    n = len(visible)
    for p in range(2, n // 2 + 1):
        if all(visible[i] == visible[i % p] for i in range(n)):
            return p
    raise StemError(f"可见段无周期（>=2 且重复完整）：{visible}")


def target_of(assignment: dict, places: list[str]) -> int:
    return sum(int(assignment[p]) * PLACE_WEIGHT[p] for p in places)


# ── 语义观察项 ──────────────────────────────────────────────────────────
def _evidence_targets(item: dict) -> list | None:
    ui = item["ui_schema"]
    if isinstance(ui, str):
        ui = json.loads(ui)
    et = (ui.get("response_contract") or {}).get("evidence_targets")
    return et if isinstance(et, list) and et else None


def _semantic_obs(item: dict, d: dict, feas: dict | None) -> list[dict]:
    """登记「答案对得上、但题面或组件有其性质疑」的观察项。

    **这类观察项不改变 verdict**：Q03 的 MATCH 定义就是「独立推导 == 存储答案」，
    可完成性与过程约束效力是另外两条维度，按用户口径分账登记。
    """
    r = item["renderer"]
    cfg = _cfg(item)
    stem = item["stem"]
    ex = d.get("extra") or {}
    tid = ex.get("template")
    obs: list[dict] = []

    # 1) 题面可完成性（shape-canvas）
    if feas and feas.get("verdict") == "INFEASIBLE_ON_COMPONENT":
        obs.append({
            "code": "INFEASIBLE_ON_COMPONENT",
            "severity": "risk",
            "why": ("题面要求的边长超出组件板可画跨度。组件 grid 是**钉位数**不是"
                    f"格数：grid={feas['component_grid']} → 渲染跨度 "
                    f"{feas['component_span']} 格（`ShapeCanvasV2.tsx:140` "
                    f"span=(grid-1)*CELL，`applyAddPoint` 约束 0<=x<grid），"
                    f"而题面要求长 {feas['required_base']} 格 × "
                    f"宽 {feas['required_height']} 格"),
            "evidence": (f"题面自称「{feas['stem_grid_declared']}×"
                         f"{feas['stem_grid_declared']} 方格纸」；"
                         f"component_grid={feas['component_grid']}、"
                         f"component_span={feas['component_span']} → "
                         f"fits_component_board={feas['fits_component_board']}"),
            "consequence": "孩子在板上画不出题面要求的长方形",
            "not_concluded": "本条不主张该题答案有误，只登记「题面所要求之图形"
                             "在组件上不可构造」",
        })

    # 2) 方格纸语义偏差（可完成时也成立）
    if (r == "shape-canvas" and feas
            and feas.get("stem_grid_declared") is not None
            and feas.get("component_span") is not None
            and feas["stem_grid_declared"] != feas["component_span"]):
        obs.append({
            "code": "GRID_SEMANTICS_OFF_BY_ONE",
            "severity": "info",
            "why": ("题面「N×N 方格纸」与组件「N 个钉位」是两个概念："
                    "后者只能画 N-1 格跨度"),
            "evidence": (f"stem_grid_declared={feas['stem_grid_declared']}、"
                         f"component_span={feas['component_span']}"),
            "consequence": ("题面描述与界面呈现相差一档，边界尺寸题会直接失效"),
            "not_concluded": "本条是口径登记，不主张本题有缺陷",
        })

    # 3) 过程约束
    pc = cfg.get("process_constraint") or {}
    mode = pc.get("mode")
    if mode and mode in BACKEND_MODES:
        obs.append({
            "code": "PROCESS_CONSTRAINT_ENABLED",
            "severity": "info",
            "why": (f"`process_constraint.mode={mode}` 已声明且后端 "
                    f"`process_validate.py` RULES 含该 mode"),
            "evidence": f"config.process_constraint={json.dumps(pc, ensure_ascii=False)}",
            "consequence": "过程证据进入判分链",
            "not_concluded": "本条只登记其已启用，不主张校验充分",
        })
    elif not mode and r in ("array-board", "sorting-board"):
        obs.append({
            "code": "NO_PROCESS_VALIDATOR_FOR_RENDERER",
            "severity": "risk",
            "why": (f"`config.process_constraint` 为 null，且后端 RULES "
                    f"**没有 {r} 的校验器**（只有 {' / '.join(BACKEND_MODES)}）"),
            "evidence": ("`process_validate.py:199-204` RULES 逐项列出四个 mode，"
                         f"无 {r} 项"),
            "consequence": ("本题属 construct_constraint 族，考点是构造过程，"
                            "但**过程证据不进入判分**：终值对即 correct=True"),
            "not_concluded": "本条不主张应立即补校验器（属产品决策），"
                             "也不主张本题答案有误",
        })
    elif mode and mode not in BACKEND_MODES:
        obs.append({
            "code": "PROCESS_CONSTRAINT_MODE_UNSUPPORTED",
            "severity": "risk",
            "why": f"`process_constraint.mode={mode}` 不在后端 RULES 中",
            "evidence": f"RULES 仅含 {' / '.join(BACKEND_MODES)}",
            "consequence": "会落 unknown_mode → unverifiable，等于没校验",
            "not_concluded": "本条不主张题目有误",
        })

    # 4) shape-canvas 的过程校验读不到边长
    if r == "shape-canvas" and mode == "shape_drawing":
        obs.append({
            "code": "PROCESS_CONSTRAINT_BLIND_TO_SHAPE",
            "severity": "risk",
            "why": ("`_rule_shape` 只重算**面积**与**直角数**，"
                    "**不读 config.base / config.height**"),
            "evidence": ("`process_validate.py:154-168`：取 vertices 算 shoelace 面积"
                         "与 right_angles，面积 == target_area 且直角 == 4 即 valid；"
                         "base/height 全程未被引用"),
            "consequence": ("斜正方形（面积相同、四个直角）过程校验也判 valid。"
                            "启用 process_constraint **不能**弥补「画错形状却判对」"),
            "not_concluded": "本条不主张过程校验写错了，只登记该契约的能力边界",
        })

    # 5) place-value：卡片池锁死 → 错误只剩位置维度
    if r == "place-value":
        obs.append({
            "code": "ERROR_SPACE_RESTRICTED_TO_POSITION",
            "severity": "info",
            "why": ("`parsePlaceValueConfig` 强制 pool 与 target 的各位数字 multiset 相等，"
                    "于是孩子**不可能**填出数字错、只能是位置错"),
            "evidence": f"config.pool={cfg.get('pool')}、target={cfg.get('target')}",
            "consequence": "诊断靶唯一（place_confusion），代价是「拿错卡片」不可观测",
            "not_concluded": "本条是能力边界登记，不是缺陷",
        })

    # 6) place-value 题面直接给目标数 → 考点被架空
    if tid == "pv_goal_direct":
        obs.append({
            "code": "STEM_GIVES_TARGET_NUMBER",
            "severity": "risk",
            "why": ("题面写「组成 {0}」，**把答案直接写在题干里**；"
                    "孩子只需照抄数字摆牌，无需自行确定数位组合").format(
                        ex.get("stem_given")),
            "evidence": f"stem 含「组成 {ex.get('stem_given')}」，"
                        f"config.target={cfg.get('target')} 与之相同",
            "consequence": ("digit_config 的考点本是「按位名组装数字」，"
                            "但目标数已给，考点退化为「照抄」；"
                            "且终值判分对「照抄」与「真的理解位值」不可区分"),
            "not_concluded": ("本条不主张答案有误（卡片池确实能拼出该数），"
                              "只登记「题面泄露答案」这一教学质量问题"),
        })

    # 7) sorting-board 干扰维度
    if r == "sorting-board":
        items = cfg.get("items") or []
        vals = [x["value"] for x in items]
        ranks = [x["visual_rank"] for x in items]
        if vals and ranks:
            by_val = [x["id"] for x in sorted(items, key=lambda x: x["value"])]
            by_vis = [x["id"] for x in sorted(items, key=lambda x: -x["visual_rank"])]
            # **区分「真干扰设计」与「只是按位置编号」**：
            # 本批 7 题里只有 6cf420db 的 visual_rank 与数值序**构造性错开**
            # （vals=[7,1,4,2] ranks=[2,4,1,3]）；其余 6 题 ranks=[1,2,3,4]
            # 就是按初始摆放位置递增编号——它们之所以「数值序≠视觉序」，
            # 只是因为初始序本身被打乱了，**不是字号干扰设计**。
            # 首版判据只看 `by_val != by_vis`，把这 6 题也算成有干扰，
            # 高估了干扰设计的覆盖（假结论）。
            sequential_ranks = (sorted(ranks) == list(range(1, len(ranks) + 1))
                                and ranks == sorted(ranks))
            designed = (not sequential_ranks) and (by_val != by_vis)
            obs.append({
                "code": ("DISTRACTOR_DIMENSION_PRESENT" if designed
                         else "DISTRACTOR_DIMENSION_COLLAPSES_WITH_INITIAL"),
                "severity": "info" if designed else "risk",
                "why": ("卡片字号档位（visual_rank）与数值序**构造性**错开"
                        if designed else
                        "visual_rank 按初始摆放位置递增编号（%s），"
                        "于是**视觉序 == 初始序**。源码守卫 "
                        "`sortingBoardV2.ts:72` 只拒绝「视觉序 == 数值正序」与"
                        "「视觉序 == 数值降序」，**不拒绝「视觉序 == 初始序」**，"
                        "故这类配置能通过校验。" % ranks),
                "evidence": (f"数值序={by_val}；视觉序={by_vis}；ranks={ranks}；"
                             f"初始序={cfg.get('initial_order')}；"
                             f"sequential_ranks={sequential_ranks}"),
                "consequence": ("「按字大排」会给出与正解不同的值，可被终值检出"
                                if designed else
                                "此时「按字号从大到小排」与「完全不动」得到**同一个"
                                "提交物**（都等于初始序），而初始序≠正解序，"
                                "所以两者都会被判错、且**无法互相区分**。"
                                "若题面还写着「卡片上的字有大有小，那是画的，"
                                "别上当」，该提示就与实际配置不符——"
                                "字号维度在这个配置下不构成对抗靶。"),
                "not_concluded": ("本条不主张答案有误（已 MATCH），"
                                  "也不主张应改题；只登记「该配置下字号维度"
                                  "与初始序折叠、诊断不可分」这一事实"),
            })

    # 8) pattern-board 干扰靶
    if r == "pattern-board":
        per = ex.get("period")
        exp_t = ex.get("expected_tokens") or []
        vis = ex.get("visible_after_code_map") or ex.get("visible") or []
        if per and exp_t and vis:
            inertia = [vis[-1]] * len(exp_t)
            shifted = [vis[(len(vis) + i + 1) % per] for i in range(len(exp_t))]
            obs.append({
                "code": "PATTERN_DISTRACTOR_TARGETS",
                "severity": "info",
                "why": "相位靶（整体后移一位）与惯性靶（全填末颗）是否与正解互异",
                "evidence": f"expected={exp_t}、phase_shift={shifted}、"
                            f"rule_ignored={inertia}",
                "consequence": ("三者互异 → 两种错法都能被单独识别；"
                                if len({tuple(exp_t), tuple(shifted), tuple(inertia)}) == 3
                                else "存在重合 → 该错法在本题不可单独识别；"),
                "not_concluded": "本条只核对分诊靶位是否互异，不主张题目有缺陷",
            })

    # 9) estimation：答案不可从题面推导
    if r == "estimation-canvas":
        obs.append({
            "code": "ANSWER_NOT_DERIVABLE_FROM_STEM",
            "severity": "risk",
            "why": (f"题面只给参照量 {ex.get('reference_hint', '')}"
                    "与定性比较，**未给实际数量**；"
                    f"而 config.actual={cfg.get('actual')} 只在 UI 配置里"),
            "evidence": (ex.get("stem_cannot_derive") or ""),
            "consequence": ("孩子无法从题面唯一确定 expected；"
                            "「估到最接近的整十」在缺少 actual 时是**不可判定要求**。"
                            "故本批记 UNVERIFIABLE_FROM_STEM，不记 MATCH。"),
            "not_concluded": ("本条不主张该题答案错（expected 与 actual 在源码规则下"
                              "自洽），也不主张估算题不该存在；"
                              "只登记「答案无法从题面独立推出」这一事实"),
        })
        obs.append({
            "code": "TOLERANCE_DOES_NOT_JUDGE",
            "severity": "info",
            "why": ("`tolerance` 易被误读为「±6 都对」。源码事实："
                    "PASS 判据是 `e === expected`（:114 严格相等），"
                    "tolerance 只在 :119 算 diagnosis 用的 `close`"),
            "evidence": ex.get("tolerance_role") or "",
            "consequence": ("若按容差判 MATCH，会把 34..46 全记成「对」，"
                            "与后端实际判分（只有 40 对）不符"),
            "not_concluded": "本条是判据澄清，不是缺陷",
        })

    return obs


# ── evaluate ────────────────────────────────────────────────────────────
def _canon_num(x) -> float:
    return float(str(x).strip())


def evaluate(item: dict) -> dict:
    d = derive(item)
    computed = independent_eval(d["expr"])
    enc = d.get("encode")
    if enc:
        if enc["kind"] == "judge_then_fill":
            if enc["claim_correct"] and enc["claimed"] != enc["expected"]:
                raise ValueError("claim_correct=True 但 claimed≠expected")
        else:
            raise ValueError(f"未知编码方式：{enc['kind']}")

    stated_raw = item["answer_raw"]
    stated = _canon_num(stated_raw)
    eq = abs(float(computed) - stated) < 1e-9

    hint = d["verdict_hint"]
    if hint == "MATCH":
        verdict = "MATCH" if eq else "MISMATCH"
    elif hint == "STEM_GIVEN_ANSWER":
        # 题面已给答案：只能核「题面给定值 == 存储答案」，
        # 这**不是**独立推导，故不记 MATCH，单独一类。
        verdict = ("STEM_GIVEN_ANSWER_AGREES" if eq
                   else "STEM_GIVEN_ANSWER_DISAGREES")
    elif hint == "STEM_UNDERDETERMINED":
        verdict = "STEM_UNDERDETERMINED"
    elif hint == "UNVERIFIABLE_FROM_STEM":
        verdict = "UNVERIFIABLE_FROM_STEM"
    else:
        raise ValueError(f"未知 verdict_hint：{hint}")

    cfg = _cfg(item)
    feas = (d.get("extra") or {}).get("feasibility")
    ws = _ws(item)
    ex = d.get("extra") or {}
    if "reference" in ex:
        pass
    return {
        "rvid": item["rvid"],
        "title": item["title"],
        "renderer": item["renderer"],
        "semantic_family": item.get("semantic_family"),
        "solve_path": item.get("solve_path"),
        "ability_id": item["ability_id"],
        "priority": item.get("priority"),
        "stem_template": ex.get("template"),
        "input_basis": d["basis"],
        "read": d["read"],
        "target_object": d["object"],
        "derivation": {
            "expr": d["expr"],
            "encode": enc or {"kind": "direct",
                              "note": "算术值即答案（构造结果的编码）"},
            "encoding_constants": _encoding_constants(d["expr"], item["stem"]),
            "extra": ex,
        },
        "computed": computed,
        "stated_answer": stated_raw,
        "verdict": verdict,
        "verdict_note": _VERDICT_NOTES.get(verdict),
        "config_vs_stem": {
            "checked": True,
            "issues": d["consistency"],
            "status": "CONSISTENT" if not d["consistency"] else "INCONSISTENT",
        },
        "feasibility": feas,
        "semantic_observations": _semantic_obs(item, d, feas),
        "evidence_enforcement": {
            "evidence_targets": _evidence_targets(item),
            "process_constraint": cfg.get("process_constraint"),
            "enforced_by_backend": bool((cfg.get("process_constraint") or {})
                                        .get("mode")) and
                                   (cfg.get("process_constraint") or {}).get("mode")
                                   in BACKEND_MODES,
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


_VERDICT_NOTES = {
    "MATCH": "独立推导/构造值 == 存储答案。这是唯一可以读作「答案被独立复算确认」的状态。",
    "MISMATCH": "独立推导值 ≠ 存储答案。必须人工裁决是题库错还是核验器读错题。",
    "STEM_GIVEN_ANSWER_AGREES": (
        "题面**直接给出了答案数值**，故不存在「独立推导出答案」这一步。"
        "本条只表示「题面给定值 == 存储答案」，**不能**读作「答案被独立复算确认」。"
    ),
    "STEM_GIVEN_ANSWER_DISAGREES": (
        "题面给定值与存储答案不一致——这是**高优先级疑点**，"
        "通常意味着题面与数据不同步。"
    ),
    "STEM_UNDERDETERMINED": (
        "题面约束有多个解，不足以唯一确定答案。"
        "不能记 MATCH（无唯一解可比），也不能记 MISMATCH（答案未必错）。"
    ),
    "UNVERIFIABLE_FROM_STEM": (
        "答案所需信息不在题面（只存在于 config），无法从题面独立复算。"
        "用 config 算 config 是循环论证，故本批明确记为不可核，"
        "**不并入 MATCH 覆盖率**。"
    ),
}


def _obs_counts(results: list[dict]) -> dict:
    from collections import Counter
    c = Counter()
    for r in results:
        for o in r.get("semantic_observations") or []:
            c[o["code"]] += 1
    return dict(sorted(c.items()))


def _family_coverage(conn) -> dict:
    """实地统计两族全量的 process_constraint 覆盖与核验进度。"""
    union = os.path.join(REPO, "scripts/iqc/runs/FE1468_worklist_union.json")
    u = json.load(open(union, encoding="utf-8"))
    out = {}
    for fam in ("construct_constraint", "open_estimate"):
        members = [x for x in u["items"] if x["semantic_family"] == fam]
        ids = [x["rvid"] for x in members]
        rows = conn.execute(
            "select resource_version_id::text, ui_schema from resource_version "
            "where resource_version_id = any(%s::uuid[])", (ids,)).fetchall()
        withpc = 0
        by_rend: dict[str, dict] = {}
        for rid, ui in rows:
            if isinstance(ui, str):
                ui = json.loads(ui)
            ws = (ui.get("workspaces") or [{}])[0]
            cfg = ws.get("config") or {}
            pc = cfg.get("process_constraint") or {}
            mode = pc.get("mode")
            has = bool(mode)
            x = next(m for m in members if m["rvid"] == rid)
            b = by_rend.setdefault(x["renderer"], {"n": 0, "with_pc": 0})
            b["n"] += 1
            if has:
                withpc += 1
                b["with_pc"] += 1
        out[fam] = {
            "family_total": len(members),
            "with_process_constraint": withpc,
            "without_process_constraint": len(members) - withpc,
            "by_renderer": dict(sorted(by_rend.items())),
            "backend_supported_modes": list(BACKEND_MODES),
            "modes_in_this_family": sorted({
                ((json.loads(ui) if isinstance(ui, str) else ui)
                 .get("workspaces") or [{}])[0].get("config", {})
                .get("process_constraint", {}).get("mode")
                for _, ui in rows
                if ((json.loads(ui) if isinstance(ui, str) else ui)
                    .get("workspaces") or [{}])[0].get("config", {})
                .get("process_constraint")}),
        }
    return out


def main() -> int:
    if not os.path.exists(QUOTA):
        print("缺少 batch7_quota_list.json：**必须先冻结选题集合再核验**。",
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
    # 只读，零 DML 路径（项目铁律：DRY 工具必须「零 DML 路径」而非
    # 「执行后 rollback」——psycopg3 with-connect 退出会自动 commit）
    #
    # **`ui_schema` 不能写成 `ui_schema::text`**：冻结侧 `freeze_batch7.py`
    # 的 `_sha()` 吃的是 jsonb 被 psycopg 解析后的 dict，做 canonical JSON
    # 再 sha256。若这里取 `::text` 拿到的是 Postgres 自己的排版字符串，
    # 与冻结侧不同源 → **35/35 全部误报 UI 漂移**（今日实踩）。
    # 哈希不变量：两边必须是同一个函数吃同一种类型。
    with psycopg.connect(db) as conn:
        rows = conn.execute(
            "select resource_version_id::text, content->>'answer', "
            "content->>'stem', ui_schema "
            "from resource_version where resource_version_id = any(%s::uuid[])",
            (ids,)).fetchall()
        live = {r[0]: {"answer": r[1], "stem": r[2], "ui": r[3]} for r in rows}
        missing = [i for i in ids if i not in live]
        if missing:
            print(f"清单里有 {len(missing)} 题库里取不到：{missing}", file=sys.stderr)
            return 2
        # 三列都要核，不只答案。只核答案的话，若题面或 UI 契约在冻结后
        # 被改过，核验仍会用**旧题面**去推导、再用**旧答案**去比，全链自洽
        # 却与线上题不同——那种「账实相符」是假的。
        d_ans = [i["rvid"] for i in items
                 if str(live[i["rvid"]]["answer"]) != str(i["answer_raw"])]
        d_stem = [i["rvid"] for i in items
                  if _canon_sha256(live[i["rvid"]]["stem"]) != i["stem_sha256"]]
        d_ui = [i["rvid"] for i in items
                if _canon_sha256(live[i["rvid"]]["ui"]) != i["ui_schema_sha256"]]
        if d_ans or d_stem or d_ui:
            print("**输入漂移**——冻结清单与当前库不是同一版，核验结论对线上无效：",
                  file=sys.stderr)
            for label, xs in (("答案", d_ans), ("题干", d_stem), ("UI契约", d_ui)):
                if xs:
                    print(f"  {label}漂移 {len(xs)} 题：{[x[:8] for x in xs]}",
                          file=sys.stderr)
            print("（这是**工件过期**，须重新 freeze；退出码 2，不是核验失败）",
                  file=sys.stderr)
            return 2
        coverage = _family_coverage(conn)

    try:
        results = [evaluate(i) for i in items]
    except StemError as e:
        print(f"**题面模板未覆盖（StemError）**：{e}", file=sys.stderr)
        print("（这是**核验器读不懂题**，不是题库有错——必须补模板，"
              "不得记为 MISMATCH）", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"**推导失败**：{e}", file=sys.stderr)
        print("（推导失败不是 MISMATCH，必须单独处理——不能记为通过）",
              file=sys.stderr)
        return 2
    except Exception as e:      # noqa: BLE001
        # **未捕获异常必须 rc=2，不能让它以 rc=1 掉出去**。
        # Python 未捕获异常默认退出码就是 1，与「1 = 核验失败」撞码：
        # 一次 NameError 会被读成「35 题里有答案算错了」。这类 bug 本批
        # 真踩到过一次（`area_integer_sides` 少写一层循环），当时 rc=1，
        # 现象与「核验不通过」完全一致。
        import traceback
        print(f"**核验器自身异常**：{type(e).__name__}: {e}", file=sys.stderr)
        traceback.print_exc()
        print("（这是**工具 bug**，不是核验结论——退出码 2 与布局/工件问题同类，"
              "**不得读作 MISMATCH**）", file=sys.stderr)
        return 2

    by_renderer: dict[str, dict] = {}
    by_solve: dict[str, dict] = {}
    for r in results:
        b = by_renderer.setdefault(r["renderer"],
                                   {"n": 0, "match": 0, "non_match": 0,
                                    "inconsistent": 0, "infeasible": 0})
        b["n"] += 1
        b["match"] += 1 if r["verdict"] == "MATCH" else 0
        b["non_match"] += 1 if r["verdict"] != "MATCH" else 0
        b["inconsistent"] += 1 if r["config_vs_stem"]["status"] != "CONSISTENT" else 0
        b["infeasible"] += 1 if (r.get("feasibility") or {}).get(
            "verdict") == "INFEASIBLE_ON_COMPONENT" else 0
        s = by_solve.setdefault(r["solve_path"] or "UNKNOWN",
                                {"n": 0, "match": 0})
        s["n"] += 1
        s["match"] += 1 if r["verdict"] == "MATCH" else 0

    from collections import Counter
    vc = Counter(r["verdict"] for r in results)
    tc = Counter(r["stem_template"] for r in results)

    out = {
        "title": "FE-1472 第七批｜Q03 两族清零核验"
                 "（construct_constraint 余 34 + open_estimate 全 1 = 35 题）",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chain": ["题干", "命中登记模板", "抽取题面事实", "明确所求对象",
                  "独立推导/构造（纯算术）", "断言 config 已知量 ⊆ 题面事实",
                  "题面可完成性", "与存储答案比较"],
        "scope": {
            "why_this_batch": ("第六批后 construct_constraint 余 34、open_estimate 余 1；"
                               "本批全取，使两族可写成族级清零（54/54、1/1）。"),
            "families": ["construct_constraint", "open_estimate"],
            "quota_by_solve_path": q.get("quota_by_solve_path"),
            "pool_size": q.get("pool_size"),
            "overrides": q.get("overrides"),
            "family_coverage": coverage,
        },
        "template_discipline": {
            "why": ("第六批用「边写边补正则」，只覆盖了那 20 题的写法。"
                    "本批 35 题是同族另一批题，实测第六批规则会 **静默算错 1 题**"
                    "（8a658f5e：无「另一件」三字 → 只取首个标价 10，真值 15）、"
                    "**抽不到 9 题**。故本批改为显式模板表，每题必须恰好命中一个模板。"),
            "templates_used": dict(tc),
            "rule": ("命中 0 个或 >1 个模板 → rc=2（规则不足，需人工补模板），"
                     "**不得记为 MISMATCH**；rc=1 只用于「结论不成立」。"),
            "batch6_probe": q.get("batch6_rule_coverage", {}).get("by_renderer"),
        },
        "independence": {
            "rule": "computed 只由 derive(item) 从**题干文本**抽出的事实算出；"
                    "config 只用于事后一致性核对，不参与计算；answer_raw 仅在比较一步出现",
            "enforced_by": "derive() 只吃 item；independent_eval() 只对纯算术表达式求值",
            "caveat": "独立推导能排除「照答案反推」，**不能证明题面解析正确**——"
                      "若把题意读错，MATCH 也只是「错误理解与答案巧合一致」。"
                      "本批用 `--crossbatch` 验证第六批 20 题仍算对，用于部分缓解此项。",
            "new_in_this_batch": (
                "① 题面模板显式登记，抽不到即 rc=2；"
                "② 新增 4 类非 MATCH verdict，把「不能核」与「核过对不上」分开："
                "STEM_GIVEN_ANSWER_*（题面已给答案）、STEM_UNDERDETERMINED（约束多解）、"
                "UNVERIFIABLE_FROM_STEM（答案不在题面）。"),
        },
        "verdict_definition": _VERDICT_NOTES,
        "summary": {
            "total": len(results),
            "verdict_counts": dict(vc),
            "match": vc.get("MATCH", 0),
            "mismatch": vc.get("MISMATCH", 0),
            "not_match_total": sum(v for k, v in vc.items() if k != "MATCH"),
            "config_inconsistent": sum(
                1 for r in results if r["config_vs_stem"]["status"] != "CONSISTENT"),
            "infeasible_on_component": sum(
                1 for r in results
                if (r.get("feasibility") or {}).get("verdict")
                == "INFEASIBLE_ON_COMPONENT"),
            "observation_counts": _obs_counts(results),
            "process_constraint_effective": sum(
                1 for r in results if r["evidence_enforcement"]["enforced_by_backend"]),
            "by_renderer": by_renderer,
            "by_solve_path": by_solve,
            "match_definition": (
                "MATCH 只表示「从题面独立推导/构造的结果与存储答案相等」，"
                "不表示该题的交互、可完成性或教学质量已验收。"
                "**非 MATCH 不等于答案错**——见 verdict_definition。"),
        },
        "items": results,
    }

    # **先校验，后落盘**（第四批铁律：失败也留下产物会污染下一轮基线）
    bad = _self_check(results, out)
    if bad:
        print(f"**产物自检失败 {len(bad)} 项**：", file=sys.stderr)
        for c in bad:
            print(f"  ✗ {c}", file=sys.stderr)
        print("**未写出 JSON**：校验失败不落盘。", file=sys.stderr)
        return 1

    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    s = out["summary"]
    print(f"Q03-BATCH7: {s['match']} MATCH / {s['mismatch']} MISMATCH / "
          f"{s['not_match_total']} 非 MATCH，共 {s['total']} 题")
    print(f"  verdict 分布：{s['verdict_counts']}")
    print(f"  config↔题面不一致：{s['config_inconsistent']} 题")
    print(f"  题面在组件上不可完成：{s['infeasible_on_component']} 题")
    for rend, b in sorted(by_renderer.items()):
        print(f"  {rend:20s} {b['match']}/{b['n']} MATCH"
              f"（非MATCH {b['non_match']}，不一致 {b['inconsistent']}）")
    for sp, b in sorted(by_solve.items()):
        print(f"  [{sp:20s}] {b['match']}/{b['n']}")
    for r in results:
        if r["verdict"] != "MATCH":
            print(f"  · {r['rvid'][:8]} {r['renderer']:18s} {r['verdict']}")
    print(f"out: {OUT}")
    # 只有真 MISMATCH（推导值对不上答案）才 rc=1；其余非 MATCH 是分层结论，不算失败
    return 0 if s["mismatch"] == 0 else 1


def _self_check(results: list[dict], out: dict) -> list[str]:
    """产物自检：防止「看起来跑通了」的假成功。"""
    bad: list[str] = []
    if len(results) != out["summary"]["total"]:
        bad.append(f"results {len(results)} ≠ summary.total {out['summary']['total']}")
    ids = [r["rvid"] for r in results]
    if len(set(ids)) != len(ids):
        bad.append("results 有重复 rvid")
    # 每题必须有模板、有 visible 答案、有 verdict_note
    for r in results:
        if not r.get("stem_template"):
            bad.append(f"{r['rvid'][:8]} 无 stem_template")
        if not r.get("read"):
            bad.append(f"{r['rvid'][:8]} 无 read")
        if r["verdict"] not in _VERDICT_NOTES:
            bad.append(f"{r['rvid'][:8]} verdict 无定义：{r['verdict']}")
        # 判断题/编码类：expr 不得为空
        if not (r["derivation"].get("expr") or "").strip():
            bad.append(f"{r['rvid'][:8]} derivation.expr 为空")
    # 汇总数必须与逐题重算一致（**不只信自己算的计数器**）
    from collections import Counter
    recalc = Counter(r["verdict"] for r in results)
    if dict(recalc) != out["summary"]["verdict_counts"]:
        bad.append(f"verdict_counts 与逐题重算不符："
                   f"{out['summary']['verdict_counts']} vs {dict(recalc)}")
    if out["summary"]["match"] != recalc.get("MATCH", 0):
        bad.append("summary.match 与逐题重算不符")
    return bad


# ── 跨批次回归：第六批 20 题必须仍算对 ──────────────────────────────────
def crossbatch() -> int:
    """证明「第七批的新模板没有引入回归」。

    第六批 20 题全部是 MATCH。用第七批的 derive() 重算它们，必须仍全部
    MATCH——否则说明新规则把老题算错了。这是**反向对照**：只测新题不够，
    因为「新规则只会算新题」与「新规则破坏了老题」都表现为「新题全对」。
    """
    p = os.path.join(HERE, "batch6_quota_list.json")
    if not os.path.exists(p):
        print("缺 batch6_quota_list.json", file=sys.stderr)
        return 2
    items = json.load(open(p, encoding="utf-8"))["items"]
    fails: list[str] = []
    for it in items:
        try:
            r = evaluate(it)
        except (StemError, ValueError) as e:
            fails.append(f"{it['rvid'][:8]} {it['renderer']}: 第七批规则算不出（{e}）")
            continue
        if r["verdict"] != "MATCH":
            fails.append(f"{it['rvid'][:8]} {it['renderer']}: 第六批为 MATCH，"
                         f"第七批规则得 {r['verdict']}（computed={r['computed']} "
                         f"stated={r['stated_answer']!r}）")
    if fails:
        print(f"**跨批次回归失败 {len(fails)}/{len(items)}**：", file=sys.stderr)
        for f in fails:
            print(f"  ✗ {f}", file=sys.stderr)
        print("说明第七批模板改动破坏了已核结论，**不能**视为「只加了新规则」。",
              file=sys.stderr)
        return 1
    print(f"CROSSBATCH: PASS（第六批 {len(items)}/{len(items)} 题在第七批规则下仍 MATCH）")
    return 0


# ── 区分力自证（门禁用；不连库、不写产物）──────────────────────────────
def selftest() -> int:
    """证明这批核验器「改坏了会失败」。

    五类变异，各验一件事：
      A. answer +1000 → MATCH 类的题必须变 MISMATCH（比较环节真的在工作）
      B. 题干关键数字变异 → computed 必须变化（推导真的读题面）
      C. config 已知量改成题面没有的数 → config_vs_stem 必须 INCONSISTENT
      D. 题面边长改成超出板面 → feasibility 必须 INFEASIBLE
      E. **模板判据本身**：把题面改成不命中任何模板 → 必须 StemError（rc=2 路径）
         （不测这条，「模板登记」就是装饰品）
      F. **估算题必须仍是 UNVERIFIABLE_FROM_STEM**：若有人把它改成 MATCH，
         说明判据被放宽了
    """
    if not os.path.exists(QUOTA):
        print("缺 batch7_quota_list.json", file=sys.stderr)
        return 2
    items = json.load(open(QUOTA, encoding="utf-8"))["items"]
    fails: list[str] = []

    # A：答案篡改 —— 只对 MATCH 类题做（其他类的 verdict 本来就不由 eq 决定）
    match_items = [it for it in items
                   if evaluate(it)["verdict"] == "MATCH"]
    caught = 0
    for it in match_items:
        x = json.loads(json.dumps(it))
        x["answer_raw"] = str(int(float(x["answer_raw"])) + 1000)
        if evaluate(x)["verdict"] == "MISMATCH":
            caught += 1
    if caught != len(match_items):
        fails.append(f"答案篡改只检出 {caught}/{len(match_items)}")

    # B：题干数字变异——逐位逐个数字试（第六批教训：不能盲目改第一个数字）
    #
    # **key 必须取 evaluate() 结果里的 stem_template，不能用 it.get(...)**：
    # `items` 来自 quota_list，**没有** stem_template 字段，首版写成
    # `it.get("stem_template")` 会全部回落到 solve_path，于是只测了 5 个
    # solve_path 却打印「5/5 模板」——**判据写错产假结论**（本批第二次踩到）。
    seen: set[str] = set()
    mut_ok = 0
    for it in items:
        key = evaluate(it)["stem_template"]
        if key in seen:
            continue
        seen.add(key)
        base = evaluate(it)["computed"]
        stem = it["stem"]
        positions = [(m.start(), m.end(), int(m.group(0)))
                     for m in re.finditer(r"\d+", stem)]
        if not positions:
            fails.append(f"{key}: 题干无数字，变异无法构造")
            continue
        reactive = 0
        crashes = 0
        for st, en, v in positions:
            x = json.loads(json.dumps(it))
            x["stem"] = stem[:st] + str(v + 7) + stem[en:]
            try:
                after = evaluate(x)["computed"]
            except (StemError, ValueError):
                # 推导对题面格式敏感而崩溃，也算「读到了题面」
                crashes += 1
                reactive += 1
                continue
            if abs(after - base) > 1e-9:
                reactive += 1
        if reactive == 0:
            fails.append(f"{key} ({it['rvid'][:8]}): 题干 {len(positions)} 个数字位"
                         f"逐个 +7 后 computed 全未变（推导没真读题面？）")
        else:
            mut_ok += 1

    # C：config 一致性变异
    cons_by_tpl: dict[str, dict] = {}
    for it in items:
        t = evaluate(it)["stem_template"]
        cons_by_tpl.setdefault(t, it)
    cons_ok = 0
    mutators = {
        "money_two_items_sum": ("price", 91),
        "money_single_direct": ("price", 91),
        "money_yuan_jiao": ("price", 91),
        "pv_cards_plus_assignment": ("target", 91),
        "pv_goal_direct": ("target", 91),
        "pv_constraint_only": ("target", 91),
        "array_rows_cols": ("target_cols", 9),
        "shape_base_height": ("target_area", 91),
        "shape_length_width": ("target_area", 91),
        "shape_area_only": ("target_area", 91),
        "sort_bracket_list": ("direction", "desc"),
        "sort_inline_list": ("direction", "desc"),
        "pattern_named_codes": ("blanks", 3),
        "pattern_named_codes_two_rounds": ("blanks", 3),
        "pattern_visible_digits": ("blanks", 3),
        "pattern_claim_judge": ("blanks", 3),
        "estimation_reference_round_ten": ("expected", 91),
    }
    for t, it in cons_by_tpl.items():
        if t not in mutators:
            fails.append(f"{t}: 无 config 变异方案（该判据未自证）")
            continue
        key, val = mutators[t]
        x = json.loads(json.dumps(it))
        ui = x["ui_schema"]
        ui = json.loads(ui) if isinstance(ui, str) else ui
        cfg = (ui.get("workspaces") or [{}])[0].setdefault("config", {})
        cfg[key] = val
        x["ui_schema"] = json.dumps(ui, ensure_ascii=False)
        try:
            ev = evaluate(x)
        except (StemError, ValueError) as e:
            fails.append(f"{t}: config 变异后推导崩溃 {e}")
            continue
        if ev["config_vs_stem"]["status"] != "INCONSISTENT":
            fails.append(f"{t} ({it['rvid'][:8]}): config 改成 {key}=91/异常值后"
                         f"一致性检查未报警（该检查是空转）")
        else:
            cons_ok += 1

    # D：可完成性维度有效性 + 反向对照（合法题必须判 FEASIBLE）
    geo = [it for it in items if it["renderer"] == "shape-canvas"]
    feas_ok = 0
    if not geo:
        fails.append("本批无 shape-canvas 题，可完成性维度无法自证")
    side_geo = [it for it in geo
                if evaluate(it)["stem_template"] != "shape_area_only"]
    for it in side_geo[:1]:
        x = json.loads(json.dumps(it))
        x["stem"] = re.sub(r"(长|底边)\s*\d+\s*格", r"\g<1>9 格", x["stem"])
        try:
            ev = evaluate(x)
        except (StemError, ValueError) as e:
            fails.append(f"shape-canvas 边长变异后推导崩溃 {e}")
            continue
        f = ev.get("feasibility") or {}
        if f.get("verdict") != "INFEASIBLE_ON_COMPONENT":
            fails.append(f"shape-canvas ({it['rvid'][:8]}): 边长改成 9 格后 "
                         f"feasibility 未判 INFEASIBLE（该维度是空转）")
        else:
            feas_ok += 1

    # D2：反向对照——合法题必须至少有一题 FEASIBLE（防「一律 INFEASIBLE」假通过）。
    # **不能要求全部 FEASIBLE**：8b41e648 在第六批已确认真不可完成，
    # 且本批可能新增同类。故只断言「至少一题 FEASIBLE」+「不可完成集合非空时逐题点名」。
    feas_legit = 0
    infeasible_ids: list[str] = []
    for it in side_geo:
        f = (evaluate(it).get("feasibility") or {})
        if f.get("verdict") == "FEASIBLE":
            feas_legit += 1
        else:
            infeasible_ids.append(it["rvid"][:8])
    if side_geo and feas_legit == 0:
        fails.append("所有带边长的 shape-canvas 题都判 INFEASIBLE——判据可能恒真")

    # E：模板判据本身有效性——题面改成不命中任何模板必须 StemError
    for t, it in cons_by_tpl.items():
        x = json.loads(json.dumps(it))
        x["stem"] = "这是一段与模板无关的文字，没有任何可抽取的量。"
        try:
            evaluate(x)
            fails.append(f"{t}: 题面换成无关文字后仍算出结果"
                         f"（模板判据未生效/是空转）")
        except (StemError, ValueError):
            pass

    # F：估算题不得被抬成 MATCH
    est = [it for it in items if it["renderer"] == "estimation-canvas"]
    for it in est:
        v = evaluate(it)["verdict"]
        if v != "UNVERIFIABLE_FROM_STEM":
            fails.append(f"estimation ({it['rvid'][:8]}): verdict={v}，"
                         f"应为 UNVERIFIABLE_FROM_STEM（答案不可从题面推导）")

    # G：**输入绑定判据自证**（本批新增三列漂移检查后补）
    #
    # `_canon_sha256()` 与 `freeze_batch7.py::_sha()` 是**两份独立实现**，
    # 只要有一份被改（哪怕只是 separators 换成默认带空格），对库比对就会
    # **全部 35 题误报漂移**——现象看起来像"题库全被改过"，而真正错的是核验器。
    # 今日实踩过一次同款（对 `ui_schema::text` 算哈希 → 35/35 误报）。
    # 故这里做**两种方法交叉确认**：
    #   ① 两函数在同一批真实对象上逐题给同一结果；
    #   ② 冻结清单里存的 sha 必须等于用清单自身 stem/ui_schema 重算的值
    #      （防"清单哈希是编的"，那种清单永远自洽）。
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location(
        "_fb7", os.path.join(HERE, "freeze_batch7.py"))
    bind_ok = 0
    if _spec is None:
        fails.append("无法加载 freeze_batch7.py——输入绑定判据无法交叉确认")
    else:
        _fb7 = _ilu.module_from_spec(_spec)
        try:
            _spec.loader.exec_module(_fb7)
        except SystemExit:
            # freeze_batch7 顶层若因缺 DATABASE_URL 退出，不阻断本条自证
            _fb7 = None
        if _fb7 is not None and hasattr(_fb7, "_sha"):
            for it in items:
                same_fn = (_canon_sha256(it["stem"]) == _fb7._sha(it["stem"])
                           and _canon_sha256(it["ui_schema"])
                           == _fb7._sha(it["ui_schema"]))
                # 清单自洽：存的 sha 必须能由清单内容重算出来
                self_ok = (_canon_sha256(it["stem"]) == it["stem_sha256"]
                           and _canon_sha256(it["ui_schema"])
                           == it["ui_schema_sha256"])
                if not same_fn:
                    fails.append(f"{it['rvid'][:8]}: 核验侧与冻结侧哈希函数不一致"
                                 f"——对库比对会全部误报漂移")
                elif not self_ok:
                    fails.append(f"{it['rvid'][:8]}: 清单里的 sha256 与清单内容"
                                 f"重算不符（哈希是编的）")
                else:
                    bind_ok += 1
            # 反向对照：改一个字符必须换哈希（否则该判据对内容不敏感）
            probe = json.loads(json.dumps(items[0]["stem"]))
            if _canon_sha256(probe) == _canon_sha256(probe + "。"):
                fails.append("哈希对内容不敏感——加一个字符后 sha 未变")
        elif _fb7 is not None:
            fails.append("freeze_batch7 里找不到 _sha()——冻结侧函数被改名，"
                         "两侧不再同源")

    if fails:
        print("**Q03-BATCH7-SELFTEST 未通过**：", file=sys.stderr)
        for f in fails:
            print(f"  ✗ {f}", file=sys.stderr)
        return 1
    print(f"Q03-BATCH7-SELFTEST: PASS（答案篡改 {caught}/{len(match_items)}；"
          f"题干数字变异 {mut_ok}/{len(seen)} 模板；"
          f"config 不一致 {cons_ok}/{len(cons_by_tpl)} 模板；"
          f"可完成性变异 {feas_ok} 检出、合法 {feas_legit}/{len(side_geo)} 通过；"
          f"模板失效 {len(cons_by_tpl)}/{len(cons_by_tpl)} 检出；"
          f"估算题 {len(est)} 题保持不可核；"
          f"输入绑定 {bind_ok}/{len(items)} 同源且清单自洽）")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if "--crossbatch" in sys.argv:
        sys.exit(crossbatch())
    sys.exit(main())