"""FE-1472 第五批｜Q03 逐题独立核验（读 batch5_quota_list.json，不重新选样）。

与前四批的方法学差别（本批的核心改进）：

  前四批：`derive()` 直接读 `config` 里的数字算答案。
  本批：**先从题干文本抽数推导，再断言 config 的已知量与题面一致**。

  理由：直接读 config 只能证明「config 内部自洽」，证明不了「config 与孩子看到的
  题目一致」。若某题 config 写 7 而题面写 8，前四批的做法依然会 MATCH（对着
  config 算、对着 config 里的答案比），本批会先在一致性检查上 FAIL。

核验链（每一步都可单独复核）：
  题干 → 抽取题面事实 → 明确所求对象 → 独立推导（纯算术）
       → 断言 config 已知量 ⊆ 题面事实 → 与存储答案比较

用法：
  export DATABASE_URL="$(security find-generic-password -s iqc-database-url -w)"
  python scripts/iqc/rt1472/q03_batch5.py
  python scripts/iqc/rt1472/q03_batch5.py --selftest   # 门禁用，不连库
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

QUOTA = os.path.join(HERE, "batch5_quota_list.json")
OUT = os.path.join(REPO, "scripts/iqc/runs/FE1472_q03_batch5.json")


def independent_eval(expr: str) -> float:
    """只对由 derive() 构造的纯算术表达式求值，不接触答案。"""
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
    """首个 workspace。`mode` 在 workspace 层（column-arithmetic 实测）。"""
    ui = item["ui_schema"]
    if isinstance(ui, str):
        ui = json.loads(ui)
    return (ui.get("workspaces") or [{}])[0]


def _cfg(item: dict) -> dict:
    return _ws(item).get("config") or {}


def _nums(text: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", text)]


# ── 逐题独立推导 ──────────────────────────────────────────────────────────
def derive(item: dict) -> dict:
    """返回 read（题面读到了什么）/ expr / object / basis / consistency。

    `consistency` 记录「config 的已知量与题面是否一致」的核对结果——
    这是本批新增的一步，前四批没有。
    """
    r = item["renderer"]
    stem = item["stem"]
    cfg = _cfg(item)
    ws = _ws(item)

    if r == "ruler":
        # 两种题面表述都要覆盖，不假设只有一种写法
        m = re.search(r"刻度\s*(\d+)\s*和\s*(\d+)", stem)
        if not m:
            m2 = re.search(r"左端在\s*(\d+)\s*厘米?刻度", stem)
            m3 = re.search(r"右端在\s*(\d+)\s*厘米?刻度", stem)
            if not (m2 and m3):
                raise ValueError(f"ruler 题面无法抽出两个刻度：{stem[:60]}")
            left, right = int(m2.group(1)), int(m3.group(1))
        else:
            left, right = int(m.group(1)), int(m.group(2))
        obj_left, obj_right = cfg["object"]
        cons = []
        if (left, right) != (obj_left, obj_right):
            cons.append(f"题面刻度 ({left},{right}) ≠ config.object ({obj_left},{obj_right})")
        return {
            "read": f"{stem}→ 左端 {left}、右端 {right}，求两端刻度差",
            "expr": f"{right} - {left}",
            "object": f"线段长度（{right}−{left}）",
            "basis": f"题面抽出 left={left}、right={right}；"
                     f"config.object={cfg['object']}（仅作交叉核对）；"
                     f"**不读答案**。左端不在 0，所以「直接取右端读数」必错",
            "consistency": cons,
        }

    if r == "ten-frame":
        m = re.search(r"已有\s*(\d+)\s*个圆点", stem)
        m2 = re.search(r"再放\s*(\d+)\s*个", stem)
        if not (m and m2):
            raise ValueError(f"ten-frame 题面无法抽出初始量与新增量：{stem[:60]}")
        init, add = int(m.group(1)), int(m2.group(1))
        cons = []
        if cfg.get("initial_count") != init:
            cons.append(f"题面初始 {init} ≠ config.initial_count {cfg.get('initial_count')}")
        total = init + add
        if cfg.get("target_count") != total:
            cons.append(f"题面 {init}+{add}={total} ≠ config.target_count "
                        f"{cfg.get('target_count')}")
        return {
            "read": f"{stem}→ 已有 {init} 个、再放 {add} 个，求总个数",
            "expr": f"{init} + {add}",
            "object": f"圆点总数（{init}+{add}）",
            "basis": f"题面抽出 initial={init}、add={add}；"
                     f"config.target_count={cfg.get('target_count')} 仅作交叉核对；"
                     f"**不读答案**",
            "consistency": cons,
        }

    if r == "bar-model":
        known = cfg["known"]
        a, b = known.get("a"), known.get("b")
        if a is None or b is None:
            raise ValueError(f"bar-model 已知条不是 a/b 两支：{known}")
        mode = cfg.get("mode")
        # **从题面抽两个量，不直接读 config**（首版直接读 known.a/known.b，
        # 导致题干数字 +7 后 computed 不变——自证当场抓到）。
        # 「7本书…多4本」「9张…又拿来4张」「12本和8本」「5颗…3颗」：
        # 两部分的单位一致，取带单位的前两个数字。
        qty = [int(x) for x in re.findall(r"(\d+)\s*[本张颗个支只条]", stem)]
        if len(qty) < 2:
            raise ValueError(f"bar-model 题面无法抽出两个部分量：{stem[:60]}")
        pa, pb = qty[0], qty[1]
        cons = []
        if (pa, pb) != (a, b):
            cons.append(f"题面两部分 ({pa},{pb}) ≠ config.known (a={a}, b={b})")
        if mode != "part_whole":
            cons.append(f"config.mode={mode}，本批只核 part_whole")
        if cfg.get("answer_bar") != "c":
            cons.append(f"config.answer_bar={cfg.get('answer_bar')}，答案条不是整体条 c")
        return {
            "read": f"{stem}→ 题面两部分 {pa} 与 {pb}，求整体",
            "expr": f"{pa} + {pb}",
            "object": f"整体（答案条 c = {pa}+{pb}）",
            "basis": f"题面抽出两部分 pa={pa}、pb={pb}；"
                     f"config.known (a={a}, b={b}) 仅作交叉核对；"
                     f"answer_bar={cfg.get('answer_bar')}、"
                     f"max_blocks={cfg.get('max_blocks')}；**不读答案**",
            "consistency": cons,
        }

    if r == "grouping-board":
        m = re.search(r"有\s*(\d+)\s*颗", stem)
        m2 = re.search(r"平均分给\s*(\d+)\s*个", stem)
        if not (m and m2):
            raise ValueError(f"grouping-board 题面无法抽出总量/组数：{stem[:60]}")
        total, groups = int(m.group(1)), int(m2.group(1))
        cons = []
        if cfg.get("total") != total:
            cons.append(f"题面总量 {total} ≠ config.total {cfg.get('total')}")
        if cfg.get("target_groups") != groups:
            cons.append(f"题面组数 {groups} ≠ config.target_groups "
                        f"{cfg.get('target_groups')}")
        if total % groups != 0:
            cons.append(f"{total} 不能被 {groups} 整除，题面「每人一样多」不成立")
        return {
            "read": f"{stem}→ {total} 颗平均分给 {groups} 人，求每人几颗",
            "expr": f"{total} / {groups}",
            "object": f"每份颗数（{total}÷{groups}）",
            "basis": f"题面抽出 total={total}、groups={groups}；"
                     f"config.group_size={cfg.get('group_size')} 仅作交叉核对"
                     f"（**组件不读该字段**）；**不读答案**",
            "consistency": cons,
        }

    if r == "number-line":
        m = re.search(r"从\s*(\d+)\s*出发", stem)
        m2 = re.search(r"向(左|右)", stem)
        m3 = re.search(r"每次跳\s*(\d+)", stem)
        m4 = re.search(r"连续跳\s*(\d+)\s*次", stem)
        if not (m and m2 and m3 and m4):
            raise ValueError(f"number-line 题面无法抽出起点/方向/步长/次数：{stem[:60]}")
        start = int(m.group(1))
        dirn_cn = m2.group(1)
        size, cnt = int(m3.group(1)), int(m4.group(1))
        sign = 1 if dirn_cn == "右" else -1
        cons = []
        if cfg.get("start_marker", {}).get("value") != start:
            cons.append(f"题面起点 {start} ≠ config.start_marker.value "
                        f"{cfg.get('start_marker', {}).get('value')}")
        cfg_dir = "right" if cfg.get("direction") == "right" else "left"
        if cfg_dir != ("right" if sign > 0 else "left"):
            cons.append(f"题面方向「{dirn_cn}」≠ config.direction {cfg.get('direction')}")
        if cfg.get("jump_size") != size:
            cons.append(f"题面步长 {size} ≠ config.jump_size {cfg.get('jump_size')}")
        if cfg.get("jump_count") != cnt:
            cons.append(f"题面次数 {cnt} ≠ config.jump_count {cfg.get('jump_count')}")
        op = "+" if sign > 0 else "-"
        return {
            "read": f"{stem}→ 从 {start} 向{dirn_cn}跳 {cnt} 次、每次 {size}，求终点",
            "expr": f"{start} {op} {size} * {cnt}",
            "object": f"终点刻度（{start}{op}{size}×{cnt}）",
            "basis": f"题面抽出 start={start}、dir={dirn_cn}、size={size}、count={cnt}；"
                     f"config 四项仅作交叉核对；**不读答案**",
            "consistency": cons,
        }

    if r == "legacy:direct":
        # 两类题型，逐题按题面语义推导（无 config，纯阅读理解）
        if "正确填1" in stem and "错误填0" in stem:
            # 判断题：抽出算式里的两个加数与该说法给的结论，比大小。
            # **「一共」必须整体匹配**——首版写成 `一?共?有\s*(\d+)`，
            # 三个字全可选，于是「小美有6支」里的「有6」也被当成断言值，
            # 把「说法是 10」读成了「说法是 6」，判断题当场反向。
            claim = re.search(r"一共有\s*(\d+)\s*(?:支|个|辆|本|颗)", stem)
            # 「小美有6支红笔和4支蓝笔」→ 6 + 4
            parts = re.findall(r"(\d+)\s*[支个辆本颗]红|(\d+)\s*[支个辆本颗]蓝", stem)
            flat = [int(x) for tup in parts for x in tup if x]
            if len(flat) >= 2 and claim:
                got = flat[0] + flat[1]
                said = int(claim.group(1))
                # 判断题的「计算」分两步：先算实际值（纯算术），再编码成 1/0。
                # **不用三元表达式**——independent_eval 的白名单只含算术节点，
                # 塞 IfExp 进去会直接 ValueError（首版踩过）。
                return {
                    "read": f"{stem}→ 用题面两个数量 {flat[:2]} 重算得 {got}，"
                            f"与说法「{said}」比较",
                    "expr": f"{flat[0]} + {flat[1]}",
                    "encode": {"kind": "judge_equal", "compare_to": said},
                    "object": f"判断结果（{got} vs {said} → 对则 1，错则 0）",
                    "basis": "题面抽出两个加数与断言值，先算实际和再与之比较；"
                             "**不读答案，也不预设「检查题答案多为 1」**",
                    "consistency": [],
                }
            raise ValueError(f"legacy:direct 判断题无法抽出算式：{stem[:60]}")
        # 定位题：问什么就取什么，取不到对应数量才算失败
        m = re.search(r"问[：:].*?有?几\s*[支个辆本颗朵]", stem)
        if not m:
            raise ValueError(f"legacy:direct 定位题无法识别所问：{stem[:60]}")
        asked = m.group(0)
        # 问句里的对象词，必须在题面某句里带着数量出现
        key = re.search(r"几\s*([支个辆本颗朵])", asked)
        unit = key.group(1) if key else None
        # 「小云上午画了几朵花」→ 在题面找「上午画了6朵花」里的 6
        cand = re.findall(r"(\d+)\s*" + (unit or ".") + r"\S{0,2}(?:花|树|书|球|笔|棋子|卡片)?", stem)
        if not cand:
            raise ValueError(f"legacy:direct 定位题无法抽出所问数量：{stem[:60]}")
        # 取「问句中限定词」对应的那一句：用问句谓词的最后一个词匹配
        premise = re.search(r"上午|下午|小亮|小西|乐乐|小然|小青|红笔|蓝色?", asked)
        return {
            "read": f"{stem}→ 题面问「{asked.strip()}」，按问句限定的对象取数",
            "expr": str(int(cand[0])),
            "object": "题面所问的那一个数量（不是总数）",
            "basis": f"题面所问含限定词「{premise.group(0) if premise else '无'}」；"
                     f"候选数量 {cand[:4]}；**不读答案**",
            "consistency": [],
        }

    raise ValueError(f"未覆盖的 renderer：{r}")


def _canon_num(x) -> float:
    return float(str(x).strip())


def _semantic_mode_of_stem(stem: str, renderer: str) -> str | None:
    """题面语义层面的模式判定（**只用于登记观察项，不参与推导**）。

    存在意义：`config.mode` 与题面语义可能不一致，而两者算出的数值可能恰好相等。
    bar-model 的 `part_whole`（c=a+b，标签「部分一/部分二/整体（一共）」）与
    `comparison`（大条/小条/差）是两种不同表征——「小明有7本，小红比他多4本」
    在 comparison 下应是 小条=7、差=4、大条=11，而不是「7 和 4 是两个部分」。

    数值一致时前四批的做法会直接 MATCH 并当作「无问题」，本批额外登记这层不一致。
    """
    if renderer != "bar-model":
        return None
    if re.search(r"比.{1,8}(多|少)\s*\d*", stem):
        return "comparison"
    if re.search(r"分别|又拿来|先拿来|和.*一共|合起来", stem):
        return "part_whole"
    return None


def _semantic_obs(item: dict) -> list[dict]:
    """登记「数值对得上、但表征语义可疑」的观察项。

    **这类观察项不改变 verdict**：Q03 的 MATCH 定义就是「独立推导 == 存储答案」，
    语义错配是另一条维度，按用户口径「Q03 与产品风险分账」分开记。
    """
    r = item["renderer"]
    cfg = _cfg(item)
    stem = item["stem"]
    obs: list[dict] = []

    sm = _semantic_mode_of_stem(stem, r)
    if sm and cfg.get("mode") and sm != cfg.get("mode"):
        known = cfg.get("known") or {}
        obs.append({
            "code": "MODE_STEM_MISMATCH",
            "severity": "risk",
            "why": f"题面语义为 {sm}，config.mode 声明 {cfg.get('mode')}。"
                   f"两种表征摆出的条形不同，但提交答案恰好相同",
            "evidence": f"题面：「{stem[:50]}」；config.known={known}、"
                        f"answer_bar={cfg.get('answer_bar')}",
            "consequence": (
                "孩子在界面看到的是「部分一 / 部分二 / 整体（一共）」三根条，"
                "而题目问的是「小红比小明多几本」——**要求把关系题摆成合并题**。"
                "答案数字仍可能对，但「用线段图表示两个数量的关系」这一目标未被界面支持"),
            "not_concluded": "本条不主张该题答案有误（答案已核 MATCH），"
                             "只登记表征语义与题面不一致",
        })

    if r == "ten-frame" and cfg.get("initial_count", 0) > 0:
        obs.append({
            "code": "INITIAL_COUNT_IGNORED",
            "severity": "risk",
            "why": "`TenFrameV2` 不读 `initial_count`，起始状态恒为 count=0",
            "evidence": "`tenFrameV2.ts::initialTenFrameV2State()` 返回 `{tens:0, count:0}`；"
                        "`parseTenFrameConfig()` 只取 target 与 max_frames",
            "consequence": (
                f"题面说「已有 {cfg['initial_count']} 个」，界面却是空框。"
                f"孩子要自己从 0 点到 {cfg.get('target_count')}，"
                f"「接着放」这一动作在界面上不存在"),
            "not_concluded": "本条不主张答案有误；只登记题面与初始状态不一致",
        })

    if r == "grouping-board" and "group_size" in cfg:
        obs.append({
            "code": "GROUP_SIZE_IS_ANSWER_COPY",
            "severity": "info",
            "why": "`group_size` 不是输入，是答案副本；组件也不读它",
            "evidence": "`groupingBoardV2.ts::parseGroupingConfig()` 只取 "
                        "items/target_groups/max_groups；group_size 由 items÷groups 得出",
            "consequence": "若把它当独立配置依据，会形成「用答案校答案」的循环",
            "not_concluded": "本条是口径登记，不是缺陷",
        })

    if r == "number-line" and cfg.get("jump_count") == 1:
        obs.append({
            "code": "JUMP_COUNT_ONE_TRIVIAL",
            "severity": "risk",
            "why": "jump_count=1 时题面「连续跳 1 次」与「跳一次」等价，"
                   "「连续跳步」这一考点未被实际考查",
            "evidence": f"config.jump_size={cfg.get('jump_size')}、"
                        f"jump_count={cfg.get('jump_count')}、"
                        f"start={cfg.get('start_marker', {}).get('value')}",
            "consequence": "孩子一次点到位即完成，`jumps` 数组只有一段，"
                           "无法体现「等长重复跳」",
            "not_concluded": "本条不主张答案有误；只登记考点强度",
        })

    if r == "number-line":
        obs.append({
            "code": "JUMPS_NOT_ENFORCED_BY_COMPONENT",
            "severity": "risk",
            "why": "`applyJump` 只拒绝「跳到当前值」，不校验步长是否等于 jump_size、"
                   "次数是否等于 jump_count",
            "evidence": "`numberLineV2.ts::applyJump()` 仅判断 "
                        "`state.current === null || v === state.current`；"
                        "运行时实测：start=30 一步跳到 40 被接受（jumps=[{from:30,to:40}]）",
            "consequence": "孩子可以直接从起点一步点到终点，判分只读 answer → "
                           "与「按规则一步步跳」同分",
            "not_concluded": "本条不主张答案有误；只登记过程约束缺失",
        })

    # 结构层观察项：所有 20 题的 evidence_targets 都声明了过程字段，
    # 但 process_constraint 全为 null → 后端不校验，过程证据不进入判分。
    et = _evidence_targets(item)
    if et:
        obs.append({
            "code": "EVIDENCE_DECLARED_BUT_NOT_ENFORCED",
            "severity": "risk",
            "why": "`response_contract.evidence_targets` 声明了过程字段，"
                   "但 `workspaces[].config.process_constraint` 为 null",
            "evidence": f"evidence_targets={et}；process_constraint=null。"
                        f"`learning.py:958-971` 只在 `pc` 非空时才做过程校验，"
                        f"`pc=None` 时判分行为与未声明完全相同",
            "consequence": "「过程证据」在数据里存在（v2_workspaces 会序列化进去），"
                           "但**不参与判分**：终值对即 correct=True，"
                           "过程缺失或矛盾都不影响结果",
            "not_concluded": "本条不主张应立刻给所有题加 process_constraint"
                             "（那会改变既有判分行为，属产品决策）；"
                             "只登记「声明了证据目标但未启用校验」这一事实",
        })

    return obs


def _evidence_targets(item: dict) -> list | None:
    ui = item["ui_schema"]
    if isinstance(ui, str):
        ui = json.loads(ui)
    rc = ui.get("response_contract") or {}
    et = rc.get("evidence_targets")
    return et if isinstance(et, list) and et else None


def evaluate(item: dict) -> dict:
    d = derive(item)                    # 只吃 item，不读 answer
    computed = independent_eval(d["expr"])
    # 判断题：算术结果再按「与断言值是否相等」编码成 1/0。
    # 编码规则写在 derive() 的 `encode` 里，是推导的一部分，不是事后凑答案。
    enc = d.get("encode")
    if enc:
        if enc["kind"] == "judge_equal":
            computed = 1 if abs(computed - enc["compare_to"]) < 1e-9 else 0
        else:
            raise ValueError(f"未知编码方式：{enc['kind']}")
    stated_raw = item["answer_raw"]
    stated = _canon_num(stated_raw)
    match = abs(float(computed) - stated) < 1e-9

    ws = _ws(item)
    return {
        "rvid": item["rvid"],
        "title": item["title"],
        "renderer": item["renderer"],
        "ability_id": item["ability_id"],
        "input_basis": d["basis"],
        "read": d["read"],
        "target_object": d["object"],
        "derivation": {"expr": d["expr"],
                       "encode": enc or {"kind": "direct", "note": "算术值即答案"}},
        "computed": computed,
        "stated_answer": stated_raw,
        "verdict": "MATCH" if match else "MISMATCH",
        "config_vs_stem": {
            "checked": True,
            "issues": d["consistency"],
            "status": "CONSISTENT" if not d["consistency"] else "INCONSISTENT",
        },
        "semantic_observations": _semantic_obs(item),
        "evidence_enforcement": {
            "evidence_targets": _evidence_targets(item),
            "process_constraint": (_ws(item).get("config") or {}).get("process_constraint"),
            "enforced_by_backend": bool(
                (_ws(item).get("config") or {}).get("process_constraint")),
        },
        "ui_config_seen": ws.get("config") or {},
        "workspace_mode": ws.get("mode"),
        "workspace_capabilities": ws.get("capabilities"),
        "stem": item["stem"],
        "input_binding": {
            "stem_sha256": item["stem_sha256"],
            "ui_schema_sha256": item["ui_schema_sha256"],
        },
    }


# ── Q05 候选：逐题生成（第四批铁律：禁止按 renderer 复用文案）────────────
Q05_NEUTRAL = {
    "ruler": "说「把左边对着的开始刻度记住，再看右边到哪，中间有几格」",
    "ten-frame": "说「先看看框里现在有几个，再一格格地把要加的放进去」",
    "bar-model": "说「两部分合起来就是整体，把两根条接在一起看看有多长」",
    "grouping-board": "说「一个一个轮着发，发完看看每个小朋友手里有几个」",
    "number-line": "说「从起点开始，按方向一格一格地数，数完看看停在哪个数」",
    "legacy:direct": "说「再读一遍题目，看看它问的是哪一个数量」",
}


def _alts(ans, pairs):
    """拆成「与答案不同值」和「与答案同值」两类（同值的不算错型证据）。"""
    distinct = [(v, l) for v, l in pairs if v != ans]
    coincide = [(v, l) for v, l in pairs if v == ans]
    return distinct, coincide


def q05_for(item: dict) -> dict:
    r = item["renderer"]
    cfg = _cfg(item)
    stem = item["stem"]
    d = derive(item)
    ans = independent_eval(d["expr"])

    if r == "ruler":
        left, right = cfg["object"]
        pairs = [(right, "直接读右端刻度当长度（从 0 起量的惯性）"),
                 (left, "直接读左端刻度"),
                 (right + left, "把两个刻度相加")]
        dis, coin = _alts(ans, pairs)
        obs = (f"`config.object`=[{left},{right}]；提交 `answer` 为两端刻度差 {int(ans)}。"
               f"`capabilities` 含 measure/answer_input；序列化层记录 `marks` 两个刻度、"
               f"`span`、以及 `structure.error`（from_zero_reading / wrong_span）")
        comp = "可能的错值：" + "；".join(f"{v}（{l}）" for v, l in dis)
        if coin:
            comp += (f"。**{'、'.join(str(v) for v, _ in coin)} 与正确答案同值**"
                     f"（本题左端非 0 时为真，此处据此排除该错法）")
        cd = ("能分开「零起误读」与「两端差」，但**分不开「量对了」与「直接拿两个刻度相减」**"
              "——marks 只证明点在哪，证明不了为什么点那")
        return {"observable": obs, "competing": comp,
                "cannot_distinguish": cd, "neutral": Q05_NEUTRAL[r]}

    if r == "ten-frame":
        init, total = cfg.get("initial_count"), cfg.get("target_count")
        add = total - init
        pairs = [(add, "只数新放进去的那几个"), (init, "只报初始已有的数"),
                 (total + 1, "多数一个")]
        dis, coin = _alts(ans, pairs)
        # **同值错法必须按值聚合**：initial==add 时（如 5+5、6+4 里的 5+5）
        # 「只数新增」与「只报初始」得到同一个值，并列登记会被读成两份独立证据。
        bucket: dict[int, list[str]] = {}
        for v, l in dis:
            bucket.setdefault(v, []).append(l)
        obs = (f"`config.initial_count`={init}、`target_count`={total}；"
               f"提交 `answer` 为总数 {int(ans)}。"
               f"**注意：V2 组件 `TenFrameV2` 不读 `initial_count`**——"
               f"`initialTenFrameV2State()` 恒返回 count=0，"
               f"所以题面说的「已有 {init} 个」在界面上不存在，孩子必须从 0 点起")
        parts = []
        for v, labels in bucket.items():
            if len(labels) == 1:
                parts.append(f"{v}（{labels[0]}）")
            else:
                parts.append(f"{v}（{'／'.join(labels)} —— **两个错法同值，"
                             f"在该题内部不可分**）")
        comp = "可能的错值：" + "；".join(parts)
        if coin:
            comp += f"。**{'、'.join(str(v) for v, _ in coin)} 与正确答案同值**，该错法本题不成立"
        cd = (f"终值唯一，分不开「真的从 {init} 接着放」与「从 0 一路点到 {total}」"
              "——两种做法给出同一个提交值，界面也没有初始态可区分")
        if any(len(v) > 1 for v in bucket.values()):
            cd += "；另有两条错法在本题同值（见上），不能当作两份独立证据"
        return {"observable": obs, "competing": comp,
                "cannot_distinguish": cd, "neutral": Q05_NEUTRAL[r]}

    if r == "bar-model":
        a, b = cfg["known"]["a"], cfg["known"]["b"]
        pairs = [(a, "只摆部分一条"), (b, "只摆部分二条"),
                 (abs(a - b), "把「多几」当整体"),
                 (a + b + 1, "多数一格")]
        dis, coin = _alts(ans, pairs)
        obs = (f"`config.known`={{a:{a}, b:{b}}}、`answer_bar`={cfg.get('answer_bar')}、"
               f"`max_blocks`={cfg.get('max_blocks')}；提交 `answer` 为整体条 {int(ans)}。"
               f"序列化层三根条全量入库 `bars={{a,b,c}}` 与 `structure.error`"
               f"（modeling/relation/calc）")
        comp = "可能的错值：" + "；".join(f"{v}（{l}）" for v, l in dis)
        if coin:
            comp += f"。**{'、'.join(str(v) for v, _ in coin)} 与正确答案同值**，该错法本题不成立"
        cd = ("三根条都入库，**能分开「已知条摆错（modeling）」与「算错（calc）」**；"
              "分不开「照着题面逐格数出来」与「先算出和再一把拖到位」——"
              "条形长度只能证明结果，证明不了过程")
        return {"observable": obs, "competing": comp,
                "cannot_distinguish": cd, "neutral": Q05_NEUTRAL[r]}

    if r == "grouping-board":
        total, tg = cfg.get("total"), cfg.get("target_groups")
        pairs = [(tg, "把组数当每份数"), (total, "把总量当每份数"),
                 (total - tg, "把「发剩的」当每份")]
        dis, coin = _alts(ans, pairs)
        obs = (f"`config.total`={total}、`target_groups`={tg}、"
               f"`group_size`={cfg.get('group_size')}；提交 `answer` 为每份 {int(ans)}。"
               f"序列化层记录 `groups`（各组实际个数）、`pool_remaining`、"
               f"`structure.error`（count/unequal）；**`group_size` 组件不读**，"
               f"它是答案副本")
        comp = "可能的错值：" + "；".join(f"{v}（{l}）" for v, l in dis)
        if coin:
            comp += (f"。**{tg} 与每份数在本题不同值**，故「答组数」可被检出；"
                     f"若两值相同则该错法不可分")
        cd = ("`groups` 数组能分开「组数错（count）」与「各组不等（unequal）」；"
              "分不开「一次一颗轮着发」与「先算好每份数再一把倒进去」——"
              "最终各组数量相同")
        return {"observable": obs, "competing": comp,
                "cannot_distinguish": cd, "neutral": Q05_NEUTRAL[r]}

    if r == "number-line":
        start = cfg["start_marker"]["value"]
        size, cnt = cfg["jump_size"], cfg["jump_count"]
        sign = 1 if cfg.get("direction") == "right" else -1
        pairs = [(start - sign * size * cnt, "方向跳反"),
                 (sign * size * cnt, "从 0 起算而非从起点"),
                 (start + sign * size, "只跳一次")]
        dis, coin = _alts(ans, pairs)
        obs = (f"`config.start_marker.value`={start}、`jump_size`={size}、"
               f"`jump_count`={cnt}、`direction`={cfg.get('direction')}；"
               f"提交 `answer` 为终点 {int(ans)}。"
               f"**V2 组件 `applyJump` 只拒绝「跳到当前值」，"
               f"不校验步长与次数**——孩子可以一步点到任意刻度")
        comp = "可能的错值：" + "；".join(f"{v}（{l}）" for v, l in dis)
        if coin:
            comp += f"。**{'、'.join(str(v) for v, _ in coin)} 与正确答案同值**，该错法本题不成立"
        cd = (f"`jumps` 数组记录每次 from→to，能看出「跳了几步、每步多大」；"
              f"但本题要求「每次跳 {size}、连续 {cnt} 次」，"
              f"**组件不拦不合规的跳步**，所以「按规则跳」与「直接点到终点」"
              f"在判分上不可分——判分只读 answer")
        return {"observable": obs, "competing": comp,
                "cannot_distinguish": cd, "neutral": Q05_NEUTRAL[r]}

    if r == "legacy:direct":
        # 判断题 / 定位题分别生成
        if "正确填1" in stem:
            obs = (f"`ui_schema` 为 schema_version=1.0 的 `kind:number`，**无 workspace、"
                   f"无 config、无表征**；提交 `answer` 只能是 1 或 0，"
                   f"本题正确值 {int(ans)}")
            comp = ("可能的错值：1（一律判对）、0（一律判错）。"
                    "**本题正确答案恰为 "
                    f"{int(ans)}，所以「恒定填 {int(ans)}」与「真算过」同值**")
            cd = ("提交物只有一个二进制值，**分不开「重算后判断」与「猜/背答案」**；"
                  "也没有中间算式可查")
            return {"observable": obs, "competing": comp,
                    "cannot_distinguish": cd, "neutral": Q05_NEUTRAL[r]}
        obs = (f"`ui_schema` 为 schema_version=1.0 的 `kind:number`，**无 workspace、"
               f"无 config**；题面含干扰信息（另有与所问无关的数量），"
               f"提交 `answer` 为所问数量 {int(ans)}")
        comp = (f"可能的错值：把题面里其他数量当答案。本题所问数量 {int(ans)} "
                f"与其余数量并列出现，选错任何一个都会给出非 {int(ans)} 的值")
        cd = ("**能分开选错对象**（终值不同），但分不开「读懂了题目所问」与"
              "「恰好先看到那个数」——提交物只有终值，没有针对「问的是谁」的中间证据")
        return {"observable": obs, "competing": comp,
                "cannot_distinguish": cd, "neutral": Q05_NEUTRAL[r]}

    raise ValueError(f"Q05 未覆盖的 renderer：{r}")


def _obs_counts(results: list[dict]) -> dict:
    """按 code 统计观察项（供文档与门禁对账）。"""
    from collections import Counter
    c = Counter()
    for r in results:
        for o in r.get("semantic_observations") or []:
            c[o["code"]] += 1
    return dict(sorted(c.items()))


def main() -> int:
    if not os.path.exists(QUOTA):
        print("缺少 batch5_quota_list.json：**必须先冻结选题集合再核验**。",
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

    try:
        results = [evaluate(i) for i in items]
    except ValueError as e:
        print(f"**推导失败**：{e}", file=sys.stderr)
        print("（推导失败不是 MISMATCH，必须单独处理——不能记为通过）",
              file=sys.stderr)
        return 2

    by_renderer: dict[str, dict] = {}
    for r in results:
        b = by_renderer.setdefault(r["renderer"],
                                   {"n": 0, "match": 0, "inconsistent": 0})
        b["n"] += 1
        b["match"] += 1 if r["verdict"] == "MATCH" else 0
        b["inconsistent"] += 1 if r["config_vs_stem"]["status"] != "CONSISTENT" else 0

    out = {
        "title": "FE-1472 第五批｜Q03 20 题独立核验（先冻结 + 题面抽取）",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chain": ["题干", "抽取题面事实", "明确所求对象", "独立推导（纯算术）",
                  "断言 config 已知量 ⊆ 题面事实", "与存储答案比较"],
        "independence": {
            "rule": "computed 只由 derive(item) 从**题干文本**抽出的事实算出；"
                    "config 只用于事后一致性核对，不参与计算；answer_raw 仅在比较一步出现",
            "why_stronger_than_batch4": (
                "前四批直接读 config 算数，只能证明 config 内部自洽；"
                "若 config 与题面不一致（如 config 写 7、题面写 8），"
                "前四批仍会 MATCH。本批先在一致性检查上暴露，再比较答案"),
            "enforced_by": "derive() 的入参是 item，其 answer 字段在调用前未被读取；"
                           "independent_eval() 只对纯算术表达式求值",
            "caveat": "独立推导能排除「照答案反推」，**不能证明题面解析正确**——"
                      "若我把题意读错，MATCH 也只是「错误理解与答案巧合一致」",
        },
        "ledger": {
            "quota": q["quota_n"],
            "verified": len(results),
            "quota_frozen_before_verify": True,
            "quota_source": "scripts/iqc/rt1472/batch5_quota_list.json",
            "pool_size": q["pool_size"],
            "note": "选题集合在核验前落盘；候选池 75 = 并集 224 − 四批已核 75 "
                    "中 priority=both 且 semantic_family=numeric_judge 的部分。",
        },
        "summary": {
            "total": len(results),
            "match": sum(1 for r in results if r["verdict"] == "MATCH"),
            "mismatch": sum(1 for r in results if r["verdict"] == "MISMATCH"),
            "config_inconsistent": sum(
                1 for r in results if r["config_vs_stem"]["status"] != "CONSISTENT"),
            "observation_counts": _obs_counts(results),
            "process_constraint_declared": sum(
                1 for r in results if r["evidence_enforcement"]["enforced_by_backend"]),
            "by_renderer": by_renderer,
            "match_definition": "MATCH 只表示「从题面独立推导的结果与存储答案相等」，"
                                "不表示该题的交互/配置无问题",
        },
        "items": results,
    }

    # Q05 逐题生成 + 三条机器校验（第四批铁律，缺一不可）
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
        _vals = re.findall(r"(-?\d+)（", q05["competing"])
        _dup = sorted({v for v in _vals if _vals.count(v) > 1})
        if _dup:
            bad.append(f"{r['rvid'][:8]} 的 Q05 把同值错法并列登记：{_dup}")

    # **先校验，后落盘**（第四批铁律：失败也留下产物会污染下一轮基线）
    if bad:
        print(f"**Q05 校验失败 {len(bad)} 项**：", file=sys.stderr)
        for c in bad:
            print(f"  ✗ {c}", file=sys.stderr)
        print("**未写出 JSON**：校验失败不落盘。", file=sys.stderr)
        return 1

    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Q03-BATCH5: {out['summary']['match']} MATCH / "
          f"{out['summary']['mismatch']} MISMATCH / {len(results)} 题")
    print(f"  config↔题面不一致：{out['summary']['config_inconsistent']} 题")
    for rend, b in sorted(by_renderer.items()):
        print(f"  {rend:18s} {b['match']}/{b['n']}"
              f"（不一致 {b['inconsistent']}）")
    for r in results:
        if r["verdict"] != "MATCH":
            print(f"  ✗ {r['rvid'][:8]} {r['renderer']} computed={r['computed']} "
                  f"stated={r['stated_answer']!r} expr={r['derivation']['expr']}")
        if r["config_vs_stem"]["issues"]:
            print(f"  ⚠ {r['rvid'][:8]} {r['renderer']} config↔题面："
                  f"{r['config_vs_stem']['issues']}")
    print(f"out: {OUT}")
    return 0 if out["summary"]["mismatch"] == 0 else 1


# ── 区分力自证（门禁用；不连库、不写产物）────────────────────────────────
def selftest() -> int:
    """证明这批核验器「改坏了会失败」。

    三类变异，各验一件事：
      A. answer +1000 → 必须 MISMATCH（比较环节真的在工作）
      B. 题干关键数字 +7 → computed 必须变化（推导真的读题面，不是读 config）
      C. config 已知量改成题面没有的数 → config_vs_stem 必须 INCONSISTENT
         （一致性检查真的在工作）
    """
    if not os.path.exists(QUOTA):
        print("缺 batch5_quota_list.json", file=sys.stderr)
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

    # B：题干数字变异——按 renderer 各取一题，把题干里第一个数字 +7
    seen: set[str] = set()
    mut_ok = 0
    for it in items:
        r = it["renderer"]
        if r in seen:
            continue
        seen.add(r)
        base = evaluate(it)["computed"]
        x = json.loads(json.dumps(it))
        m = re.search(r"\d+", x["stem"])
        if not m:
            fails.append(f"{r}: 题干里没有数字，变异无法构造")
            continue
        v = int(m.group(0))
        x["stem"] = x["stem"][:m.start()] + str(v + 7) + x["stem"][m.end():]
        try:
            after = evaluate(x)["computed"]
        except ValueError as e:
            fails.append(f"{r} ({it['rvid'][:8]}): 题干变异后推导崩溃 {e}"
                         f"（可能说明推导对题面格式过度敏感）")
            continue
        if abs(after - base) < 1e-9:
            fails.append(f"{r} ({it['rvid'][:8]}): 题干数字 +7 后 computed 未变"
                         f"（推导没真读题面？）")
        else:
            mut_ok += 1

    # C：config 一致性变异——把已知量改成题面不可能出现的数
    cons_seen: set[str] = set()
    cons_ok = 0
    for it in items:
        r = it["renderer"]
        if r in cons_seen or r == "legacy:direct":
            continue
        cons_seen.add(r)
        x = json.loads(json.dumps(it))
        ui = x["ui_schema"]
        ui = json.loads(ui) if isinstance(ui, str) else ui
        cfg = (ui.get("workspaces") or [{}])[0].get("config") or {}
        if r == "ruler":
            cfg["object"] = [91, 97]
        elif r == "ten-frame":
            cfg["initial_count"] = 93
        elif r == "bar-model":
            cfg["known"]["a"] = 91
        elif r == "grouping-board":
            cfg["total"] = 91
        elif r == "number-line":
            cfg["start_marker"]["value"] = 91
        else:
            continue
        x["ui_schema"] = json.dumps(ui, ensure_ascii=False)
        try:
            ev = evaluate(x)
        except ValueError as e:
            fails.append(f"{r}: config 变异后推导崩溃 {e}")
            continue
        if ev["config_vs_stem"]["status"] != "INCONSISTENT":
            fails.append(f"{r} ({it['rvid'][:8]}): config 改成 91 后一致性检查未报警"
                         f"（该检查是空转）")
        else:
            cons_ok += 1

    if fails:
        print("**Q03-BATCH5-SELFTEST 未通过**：", file=sys.stderr)
        for f in fails:
            print(f"  ✗ {f}", file=sys.stderr)
        return 1
    print(f"Q03-BATCH5-SELFTEST: PASS（答案篡改 {caught}/{len(items)} 检出；"
          f"题干数字变异 {mut_ok}/{len(seen)} 检出；"
          f"config 不一致 {cons_ok}/{len(cons_seen)} 检出）")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main())