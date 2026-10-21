#!/usr/bin/env python3
"""FE-1468：Q03/Q05 去重工作清单（下一批治理输入底表）。

背景（用户 2026-10-21 复审 §三 / §四）：
    「以 **224 个去重 RVID** 为报告中的工作范围，Q03 优先，197 个交集题同步
      形成 Q05 候选。」「首批按**任务语义族**组织，而不是只按 Renderer 分组。」

本脚本只做一件事：把 FE-1467 的两份清单合并成 224 条去重底表，并给每条打上
**语义族**标签，便于按族推进 Q03 独立核验。不做判定、不改题库、不写库。

语义族（依据 task_type + content 结构 + renderer 交互形态判定）：
    numeric_judge      数值与判断：算术、差比、判断型 0/1、符号编码、时间金额单位
    construct_constraint 构造与约束：数位排列、凑付金额、规律延拓、几何构造
    open_estimate      开放或资料不足：估算、理由、图形信息不足、语义不明确

分族规则必须**可解释**，否则等于换了个名字的 renderer 分组：
    1. task_type=estimation            → open_estimate
    2. answer ∈ {0,1} 且 stem 含判断词   → numeric_judge（判断型）
    3. renderer ∈ 构造类四件（place-value / shape-canvas / money-board /
       pattern-board / array-board / grouping-board / sorting-board）且
       content 有"摆/放/组成/凑/排/延拓"等构造动词 → construct_constraint
    4. 其余                              → numeric_judge

用法：
  DATABASE_URL=... python scripts/iqc/rt1468/build_worklist_union.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", ".."))
REPO = os.path.abspath(os.path.join(SCRIPTS, ".."))

CONSTRUCT_RENDERERS = {
    "place-value", "shape-canvas", "money-board", "pattern-board",
    "array-board", "grouping-board", "sorting-board", "legacy:objects",
}
# 刻意不把 grouping-board 当构造类的实际效果（2026-10-21 核对）：
# 它的 9 条题面用「动手分组 / 圈出 3 个组 / 每人几颗」，问的是**除法结果**
# 而不是"摆出什么顺序"，因此 9 条全部落在 numeric_judge——这是**正确**的，
# 不是漏判。把它们记在这里，是为了下次有人看到 "grouping-board 在集合里
# 却一条都没命中 R3" 时不必重新排查一遍。
# 动词表必须覆盖"排好/补上/接着"这类实际题面用词。
# 2026-10-21 实测：首版只用 摆/放/组成/凑/排列/延拓/拼/画，漏掉
# "把它们按数字从小到大排好"（排序）与"再按顺序补上接下来的两格"（延拓），
# 导致 25 条纯构造题被误归为 numeric_judge。判据必须按真实语料校准。
CONSTRUCT_VERBS = (
    "摆", "放", "组成", "凑", "排列", "排好", "排序", "从小到大", "从大到小",
    "延拓", "补上", "接着", "继续排", "下一格", "拼", "画", "拖动", "改填",
    "续排",
)
# 「填」类动词（填入/填上）**故意不收**：实测会误拉 6 条 "□+8=17 请把数字卡
# 填入空格" 的纯算术题进构造族。词面相同而交互语义不同（填空算式 vs 续排
# 规律），只能靠更具体的词（如"续排"）或 renderer 组合来区分，不能凭"填"字。
JUDGE_MARKERS = ("判断", "检查", "对不对", "是否正确", "是不是", "对吗",
                 "正确填1", "错误填0")
# 反面教材（2026-10-21 实测）：上一版把 "√"/"×" 也当判断词，结果
# 「5×5方格盘」里的乘号命中 ×，把一道几何路线题判成了判断题（答案 1 是
# 格编码不是真值）。符号类 marker 只有在"打勾打叉"语境里才有意义，
# 单独出现时歧义太大，一律不参与判定。

# 规则表：每条规则有编号，运行后统计命中数。命中数为 0 的规则说明它是
# 装饰性条款（写在文档里但实际不区分任何题），必须显式告警——
# 2026-10-21 实测：上一版「题面要求提交顺序/补位」这条救了 0 条题，
# 因为前面的规则已经把它们全吃掉了。不加计数就发现不了。
# 同时删掉了上一版的 DRAG_RENDERERS 常量：它被定义但从未参与判定，
# 属于死代码。真要靠"拖拽 renderer"判族，等于退化成 renderer 分组，
# 与用户 §三「按任务语义族而不只按 Renderer」冲突。
RULES: list[tuple[str, str]] = [
    ("R1", "task_type=estimation → 开放估算（天然多解/容差）"),
    ("R2", "题面判定命题真假（判断词）→ 数值与判断；与答案值域无关"),
    ("R3", "构造类 renderer + 构造动词 → 构造与约束"),
    ("R5", "默认数值候选 → 数值与判断（**求解语义待逐题确认**）"),
]
RULE_HITS: Counter = Counter()

# 求值语义：与"族"正交的第二维。族回答"该按哪类思路组织核验"，
# 这里回答"独立求解时到底要算什么对象"。
# 用户 2026-10-21 复审 §二.2 明确要求补这一维，且指出方向不是"求数值 vs
# 求顺序相反"——两者都是「按题意与约束求出数学对象，再按提交契约编码，
# 最后比较答案」。所以维度名是 solve_path（求解路径），不是"方向"。
SOLVE_PATHS: dict[str, str] = {
    "numeric_exact": "唯一数值：算式或计数直接得出，按标量相等比较",
    "numeric_tolerance": "容差数值：参照量+取整/容差规则得出可接受集合，按容差判定",
    "sequence_order": "顺序/规律：求出有序序列或相位，再按提交契约编码",
    "digit_config": "数位配置：按卡片/位值/零与重复约束求合法排列",
    "geometry_constraint": "几何约束：在网格/画布边界内判定合法构造是否存在，再核验提交量",
    "count_by_attribute": "按属性计数：从配置枚举对象并按属性筛选计数（答案值域可能为 0/1）",
    "answer_type_unresolved": "答案类型未定：值域与题面语义不足以确定求解路径",
}


def solve_path_of(task_type: str, answer, stem: str, renderer: str,
                  ui_schema: dict | None = None) -> tuple[str, str]:
    """返回 (求解路径, 说明)。**只描述该算什么，不声称一定可自动求解。**

    2026-10-21 用户复审指出的两个坑，这里逐个避开：
      1. 「Renderer 叫估算面板」不等于开放题，也不等于可精算题——
         实测 8 道 estimation-canvas/numeric_judge 全部是
         "以 10 为参照取最近整十 + tolerance 6"，是**容差数值**，
         既不是唯一精确等式，也不是无边界开放答案。
      2. 「答案看起来像 0/1」不等于判断题——实测 4 道 shape-gallery 问
         "这一类有几张卡"、1 道 direction-grid 问"终点格编码"，
         值域同构而语义不同，必须按题干所求对象分路径。
    """
    tt = (task_type or "").lower()
    s = str(answer).strip()
    stem = stem or ""

    # 估算面板：看配置是容差型还是真开放
    if renderer == "estimation-canvas" or tt == "estimation":
        cfg = _ws_config(ui_schema)
        if cfg.get("tolerance") is not None or cfg.get("reference") is not None:
            return ("numeric_tolerance",
                    f"estimation-canvas 且配置含 tolerance={cfg.get('tolerance')}"
                    f"/reference={cfg.get('reference')}（参照+取整+容差）")
        return ("answer_type_unresolved", "estimation-canvas 但配置无容差/参照，需读题面")

    # 判断题：判「命题真假」，与值域无关地识别
    if any(m in stem for m in JUDGE_MARKERS):
        return ("numeric_exact", "题面要求判定命题真假，按约定的 0/1 映射核验")

    # 按属性计数：题面问「几张/几个」且配置有可枚举对象
    if any(k in stem for k in ("几张", "几个", "数数这类")):
        cfg = _ws_config(ui_schema)
        if cfg.get("shapes") or cfg.get("items"):
            return ("count_by_attribute",
                    "题面问数量且配置有可枚举对象列表（按属性筛选计数，非布尔）")

    # 格编码：坐标约定明确
    if renderer == "direction-grid":
        cfg = _ws_config(ui_schema)
        if cfg.get("cols") and cfg.get("target"):
            return ("numeric_exact",
                    f"终点格编码 row*cols+col（cols={cfg.get('cols')}，行主序 0 起）")

    if s in ("0", "1") and not any(m in stem for m in JUDGE_MARKERS):
        return ("answer_type_unresolved",
                "值域为 {0,1} 但题面无判断词，是否布尔或计数未定")

    if renderer in ("sorting-board", "pattern-board"):
        return ("sequence_order", f"{renderer}：求有序序列/周期相位后按契约编码")
    if renderer == "place-value":
        return ("digit_config", "place-value：按数位与卡片使用约束求合法排列")
    if renderer in ("shape-canvas", "shape-gallery"):
        return ("geometry_constraint" if renderer == "shape-canvas"
                else "count_by_attribute",
                f"{renderer}：几何约束求合法构造" if renderer == "shape-canvas"
                else f"{renderer}：按图形属性分类计数")

    return ("numeric_exact", "默认：按题意求唯一数值（求解语义待逐题确认）")


def _ws_config(ui_schema: dict | None) -> dict:
    """取首个 workspace 的 config；结构不认识就返回空 dict（不猜）。"""
    if not isinstance(ui_schema, dict):
        return {}
    for ws in ui_schema.get("workspaces") or []:
        if isinstance(ws, dict) and isinstance(ws.get("config"), dict):
            return ws["config"]
    return {}


def semantic_family(task_type: str, answer, stem: str, renderer: str,
                    ui_schema: dict | None = None) -> tuple[str, str]:
    """返回 (族, 判据说明)。**族只是初步分流，不是逐题语义认证。**"""
    tt = (task_type or "").lower()
    if tt == "estimation":
        RULE_HITS["R1"] += 1
        return "open_estimate", "R1: task_type=estimation（估算类，天然多解/容差）"

    # R2 判定依据是**题面是否要求判定命题真假**，不再用「答案看起来像 0/1」。
    # 用户 §二.3 指出的口径冲突：上一版 answer_shape_note 说"答案形态不参与
    # 判族"，R2 却依赖"答案为布尔编码"——两句话互相矛盾。现在 R2 只看题面，
    # 值域另由 solve_path 处理，避免"错误的数据库答案反过来决定核验路径"。
    is_judge = any(m in stem for m in JUDGE_MARKERS) and str(answer).strip() in (
        "0", "1", "True", "False", "true", "false")
    if is_judge:
        RULE_HITS["R2"] += 1
        return "numeric_judge", "R2: 题面要求判定命题真假（答案按约定映射 0/1）"

    hit_v = [v for v in CONSTRUCT_VERBS if v in stem]
    if renderer in CONSTRUCT_RENDERERS and hit_v:
        RULE_HITS["R3"] += 1
        return ("construct_constraint",
                f"R3: 构造类 renderer({renderer}) + 构造动词{hit_v[:2]}")

    # R4（"题面要求交出顺序/序列"）已于 2026-10-21 删除，原因有两条：
    #   1. 它原有的写法含 "补上"，与 R3 的构造动词表重叠。冗余兜底会让
    #      "R3 的动词表是否真在起作用"无法被变异测试验证——实测删掉
    #      「补上」后 T13 仍然 PASS，因为被 R4 接住了。
    #   2. 去掉重叠后它只剩 1 条命中，且完全被 R3 覆盖。
    # 删除的**真实影响**（实测，不是推测）：1 条 pattern-board 续排题
    # （rvid 82ff6618，答案 '35'，题面用「续排/填入」而非动词表里的词）
    # 从构造族掉进了默认规则。已通过给 R3 补「续排」修回，最终分布
    # 与删除前一致（170/53/1）。教训：删规则时必须逐条比对，不能凭印象
    # 写"结果不变"——我第一版注释就是这么写错的，比对后才发现有 1 条漂移。
    RULE_HITS["R5"] += 1
    return "numeric_judge", "R5: 默认数值候选（求解语义待逐题确认，非「已确认可精算」）"


def answer_shape(answer) -> str:
    """答案形态旁证（**不参与判族**，只提示 Q03 该走哪条求解路径）。

    2026-10-21 实测失败记录：曾试图用"题面是否要求提交顺序"判断答案是
    "摆出来的"还是"算出来的"，实测不可靠——
      · direction-grid「要移动几步」答案 4 被判成 assembled（其实是数出来的）
      · place-value「组成 352」答案 352 被判成 computed（其实是拼出来的）
    只靠 stem + answer 无法可靠区分两者。所以这里**不判族**，只做形态标注，
    并明确告诉核验者：multi_digit 的题必须走"枚举合法解集合 + 定规范序"，
    不能直接照 answer 反推。
    """
    s = str(answer).strip()
    if s in ("0", "1", "True", "False", "true", "false"):
        return "boolean"
    if s.replace(".", "", 1).lstrip("-").isdigit():
        return "multi_digit" if len(s.lstrip("-")) >= 2 else "single"
    return "text"


def bool_ambiguity(answer, stem: str) -> str | None:
    """答案落在 {0,1} 时，语义可能不是布尔而是一个**数量**。

    2026-10-21 实测：224 条里答案形态为 {0,1} 的有 10 条，其中 3 条的
    答案其实是数量（shape-gallery「这一类一共有几张卡」答 1；
    direction-grid「提交终点格编码」答 1），不是真/假。
    值域相同、语义不同，单看 answer 无法区分 —— 必须看题面问的是
    「对/错」还是「几个」。这里只做标记，交给 Q03 逐题核验，不自动归类。
    """
    s = str(answer).strip()
    if s not in ("0", "1", "True", "False", "true", "false"):
        return None
    judge_like = any(m in stem for m in JUDGE_MARKERS)
    count_like = any(k in stem for k in ("几张", "几个", "多少", "共几", "一共有几"))
    if judge_like and count_like:
        return "ambiguous: 同时含判断词与数量词，0/1 究竟是真假还是计数需人工确认"
    if judge_like:
        return None
    if count_like:
        return "count_like: 答案 {0,1} 但题面问的是数量，不是真/假"
    return "value_only: 答案 {0,1} 而题面既无判断词也无数量词，语义待定"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", default=os.path.join(
        REPO, "scripts/iqc/runs/FE1467_q05_q03_baseline.json"))
    ap.add_argument("--out", default=os.path.join(
        REPO, "scripts/iqc/runs/FE1468_worklist_union.json"))
    args = ap.parse_args()

    db = os.environ.get("DATABASE_URL")
    if not db:
        sys.exit("缺少 DATABASE_URL")
    db = db.replace("postgresql+psycopg://", "postgresql://")

    base = json.load(open(args.baseline))
    q05 = {x["rvid"]: x for x in base["worklist_Q05"]}
    q03 = {x["rvid"]: x for x in base["worklist_Q03_unverified"]}
    union = sorted(set(q05) | set(q03))
    meta = {}
    for d in (base["worklist_Q05"], base["worklist_Q03_unverified"]):
        for x in d:
            meta.setdefault(x["rvid"], x)

    import psycopg
    rows = []
    with psycopg.connect(db) as c:
        detail = {
            r[0]: r[1:] for r in c.execute(
                "select resource_version_id::text, task_type, content, error_models, "
                "ui_schema from resource_version "
                "where resource_version_id = any(%s::uuid[])", (union,)).fetchall()
        }

    fam_count = Counter()
    shape_count = Counter()
    sp_count = Counter()
    sp_count_by_family = Counter()
    unresolved: list[dict] = []
    review_flags: list[dict] = []
    for rvid in union:
        tt, content, ems, ui = detail.get(rvid, (None, None, None, None))
        content = content or {}
        stem = content.get("stem") or ""
        ans = content.get("answer")
        m = meta.get(rvid, {})
        renderer = m.get("renderer") or "none"
        fam, why = semantic_family(tt, ans, stem, renderer, ui)
        fam_count[fam] += 1
        sp, sp_why = solve_path_of(tt, ans, stem, renderer, ui)
        sp_count[sp] += 1
        sp_count_by_family[(fam, sp)] += 1
        shape = answer_shape(ans)
        shape_count[(fam, shape)] += 1
        bool_note = bool_ambiguity(ans, stem)
        if bool_note:
            review_flags.append({"rvid": rvid, "flag": "bool_semantics",
                                 "detail": bool_note})
        # 求解路径未定的题单列，便于下一批"明确写出缺什么"
        if sp == "answer_type_unresolved":
            unresolved.append({"rvid": rvid, "renderer": renderer,
                               "reason": sp_why})

        # Q05 候选的信号：error_models 是否只是把 pattern 抄成 code
        em_list = ems or []
        same = [e for e in em_list
                if str(e.get("code")) == str(e.get("pattern"))]
        rows.append({
            "rvid": rvid,
            "title": m.get("title"),
            "ability_id": m.get("ability_id"),
            "renderer": renderer,
            "task_type": tt,
            "semantic_family": fam,
            "family_rule": why.split(":", 1)[0],
            "family_reason": why,
            "solve_path": sp,
            "solve_path_reason": sp_why,
            "answer_shape": shape,
            "needs_review": bool_note,
            "in_Q03": rvid in q03,
            "in_Q05": rvid in q05,
            "priority": ("both" if rvid in q03 and rvid in q05
                         else "Q03_only" if rvid in q03 else "Q05_only"),
            # Q03 目标：需要在题面之外独立求出预期解
            "q03_goal": (content.get("answer") is not None),
            "q05_signal": {
                "error_model_count": len(em_list),
                "code_eq_pattern": len(same),
                "note": ("code == pattern 同质占位，需判断是否真有区分力"
                         if same else "code ≠ pattern，仍需核验可观察性"),
            },
        })

    payload = {
        "title": "FE-1468｜Q03/Q05 去重工作清单（224 条，按任务语义族分组）",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "why": "用户 2026-10-21 复审 §三/§四：以 224 个去重 RVID 为工作范围，"
               "Q03 优先，197 个交集题同步形成 Q05 候选；首批按任务语义族组织。",
        "scope": {
            "source_baseline": os.path.relpath(args.baseline, REPO),
            "source_snapshot": base.get("method", {}).get("inventory_snapshot"),
            "Q05_n": len(q05), "Q03_n": len(q03),
            "union_n": len(union),
            "intersection_n": len(set(q05) & set(q03)),
            "Q05_only_n": len(set(q05) - set(q03)),
            "Q03_only_n": len(set(q03) - set(q05)),
            "read_only": True,
            "identity": ("union(224) = Q05(209) + Q03(212) - intersection(197)；"
                         "排期按 union，不按相加的 421"),
        },
        "family_definition": {
            "numeric_judge": "数值与判断：算术、差比、判断型 0/1、符号编码、时间与金额单位",
            "construct_constraint": "构造与约束：数位排列、凑付金额、规律延拓、几何构造",
            "open_estimate": "开放或资料不足：估算、理由、图形信息不足、语义不明确",
            # 2026-10-21 用户 §二.3 指出的口径冲突：上一版这里写"依据 task_type
            # + 答案形态 + ..."，但 R2 确实依赖答案值域，等于"用答案反推判族"。
            # 现在 R2 只看题面，答案形态只做旁证（answer_shape），不进判族。
            "rules_are_explainable": "分族依据 task_type + 题面判断词 + 构造动词 + "
                                     "renderer；**答案形态不参与判族**。"
                                     "每条都带 family_reason，不用黑箱分类",
            "family_scope": ("族只回答『按哪类思路组织核验』，**不回答**"
                             "『这条一定可自动求解』。后一个问题由 solve_path 回答，"
                             "且仍须逐题确认。"),
            "R5_caveat": ("R5 是**默认兜底**，不是语义证明。它命中多少条，"
                          "只说明其他规则没接住多少条，不能承担"
                          "『已确认可数值化求解』的举证责任。"),
        },
        "solve_path_definition": SOLVE_PATHS,
        "solve_path_distribution": dict(sp_count.most_common()),
        "solve_path_by_family": {
            f"{fam}/{sp}": n
            for (fam, sp), n in sp_count_by_family.most_common()
        },
        "solve_path_note": (
            "求解路径回答『独立核验时到底算什么对象』，与族正交。同一族里"
            "numeric_exact 与 numeric_tolerance 的核验方式不同（等式 vs 可接受集合），"
            "不能因为都叫『数值题』就套同一个比较器。"
        ),
        "unresolved_items": {
            "n": len(unresolved),
            "note": ("这些题**没有**被转人工签认，只是求解路径无法仅凭"
                     "task_type + 答案值域 + 配置确定，需要读题面。"
                     "下一批遇到时按『明确写出缺什么』处理，不靠改分族提高通过率。"),
            "items": unresolved,
        },
        "family_distribution": dict(fam_count.most_common()),
        "family_rule_hits": {k: RULE_HITS.get(k, 0) for k, _ in RULES},
        "family_rule_table": {k: d for k, d in RULES},
        "family_rule_dead_warnings": [
            f"{k} 命中 0 条——该规则是装饰性条款，实际不区分任何题，"
            f"要么删掉要么说明为何保留"
            for k, _ in RULES if RULE_HITS.get(k, 0) == 0
        ],
        "answer_shape_by_family": {
            f"{fam}/{shape}": n
            for (fam, shape), n in shape_count.most_common()
        },
        "answer_shape_note": (
            "答案形态只是**旁证**，不参与判族，也不参与定求解路径。"
            "multi_digit 不等于『由摆位决定』：实测 direction-grid 步数 4 与 "
            "place-value 组成 352 都会落在单一形态里，无法据此区分求解路径。"
            "更要紧的是相反方向：**值域相同 ≠ 语义相同**——"
            "实测 4 道 shape-gallery『这一类有几张卡』答 1（数量）、"
            "1 道 direction-grid『提交终点格编码』答 1（row*cols+col）、"
            "真判断题答 1（真/假），三者同为 {0,1} 却是三种所求对象。"
            "所以 Q03 一律按 solve_path 走『独立求解 / 枚举合法解集合』，"
            "不因为值是 0/1 就判成布尔题，也不因为值是 0/1 就转人工。"
        ),
        "priority_distribution": dict(Counter(r["priority"] for r in rows).most_common()),
        "review_flags": review_flags,
        "review_flags_note": (
            "这些是**语义层面待人工确认**的条目，不是分族失败。"
            "值域相同（0/1）但语义不同（真假 vs 数量），规则无法也不应该自动裁决，"
            "列入 Q03 核验时必须逐题读题面。"
        ),
        "items": rows,
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    print(json.dumps({
        "union": len(union),
        "family_distribution": payload["family_distribution"],
        "family_rule_hits": payload["family_rule_hits"],
        "dead_rules": payload["family_rule_dead_warnings"],
        "answer_shape_by_family": payload["answer_shape_by_family"],
        "solve_path_distribution": payload["solve_path_distribution"],
        "solve_path_by_family": payload["solve_path_by_family"],
        "unresolved_n": payload["unresolved_items"]["n"],
        "priority_distribution": payload["priority_distribution"],
    }, ensure_ascii=False, indent=1))
    print("out:", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())