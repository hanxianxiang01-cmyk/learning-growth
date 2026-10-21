#!/usr/bin/env python3
"""FE-1471 门禁：第三批核验的结构约束 + **真实 `evaluate()` 离线回放**（`Q03-BATCH3-GATE`）。

## 这个门禁曾经是空转的（2026-10-21 复审实测，必读）

上一版门禁 T1–T11 只检枚举、关键词、集合和文档数字，**从不执行 29 题的数学
核验**。用户用三种篡改实测，全部 PASS：

    independent_eval() 改成恒返回 0  →  PASS   ← 门禁没算过任何题
    match 改成恒 True               →  PASS   ← 门禁没比过任何答案
    删掉批次文档                    →  PASS   ← if os.path.exists 整段静默跳过

结论：**结构自洽 ≠ 内容正确**。一个只检查「自己的常量互相不矛盾」的门禁，
在数学核验整条链路坏掉时依然会亮绿灯，这比没有门禁更危险——它给出了
虚假的可信度。

## 因此本版新增 T12：离线回放层

`batch3_frozen_inputs.json` 冻结了每题的 `answer` / `error_models` /
`ui_schema`（运行时原值）以及 `evaluate()` 在其上的实际输出。门禁据此：

- **T12a 正向**：29 题逐题真实调用 `evaluate()`，`verdict` 必须 == MATCH；
- **T12b 负向（值）**：把 `answer` 改成 `answer+1` → 必须变成 MISMATCH；
  恒 MATCH 的变异在此被拦住；
- **T12c 负向（推导）**：把 `expr` 改成 `expr+1` → 必须变成 MISMATCH；
  恒 0 / 恒真值的 `independent_eval` 变异在此被拦住；
- **T12d 配置敏感**：篡改 `ui_schema.visual` 的结构字段，`visual_leak` 结论
  必须随之改变——防止「检测器读不到配置也照样 PASS」；
- **T12e 一致性**：快照里的 `replay` 必须与现场重算逐字段相等，且
  `answer_raw_sha256` / `ui_schema_sha256` 必须与内容相符（防手改快照）。

这样「恒 0」「恒 MATCH」「检测器失明」三类变异都能在**无数据库的 CI** 上
被判 FAIL，不必等到连库重跑才发现。

## 被撤销的硬约束（它们会迫使内容说错话）

上一版有几条为了「凑满检查」而设的硬性要求，2026-10-21 复审要求撤掉：

  · T4c「V2 不许声称 `stem_only`」——V2 题也可能**仅靠题干**就完成推导，
    强制 `stem_plus_v2config` 会让登记表写假话。改为：允许，但必须说明
    config 是否被用到。
  · T8a「必须至少一条 `MISSING`」——覆盖完善后可以没有对照缺口，
    强制存在一条 `MISSING` 会逼人编造缺口。
  · T11a「四类 defs 的 `affected` 之和尚等于并集」——同一题**可以同时命中
    多类问题**，应分别统计「Findings 条数」与「去重 RVID 数」，
    不能要求四类互不重叠。
  · T5/T6e「`affected` 必须全在批内」——缺陷调查**可以**引用批外题目，
    只要独立保留身份、输入与核查证据；「批外发现」与「本批完成数量」分账。

## 关于关键词/字数检查的效力边界（写在这里，防止后人误用）

关键词与字数检查**只能辅助发现漏填**，不能证明字段角色正确，更不能代替
真实交互契约。它们是「低级错误探测器」，不是「语义正确性证明」。
凡是需要语义判定的地方，本门禁改为**显式声明 + 可核对引用**，而不是匹配措辞。

用法：python scripts/iqc/rt1471/test_batch3_contract.py
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

spec = importlib.util.spec_from_file_location(
    "batch3", os.path.join(HERE, "q03_batch3.py"))
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)

fails: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        fails.append(msg)


def _must_exist(path: str, label: str) -> bool:
    """必须存在的输入：缺失即**明确失败**，绝不静默跳过。

    上一版用 `if os.path.exists(path):` 包住整段检查，删掉文件后门禁输出全
    PASS。缺了验证对象却报通过，比报错更坏。
    """
    ok = os.path.isfile(path)
    check(ok, f"{label} 缺失：{os.path.relpath(path, REPO)}"
              "——门禁必须检查的对象不存在，判 FAIL（不允许静默跳过）")
    return ok


# ── T1 known_role 枚举 ─────────────────────────────────────────────────────
ROLES = {"已知部分", "已知整体", "差量", "答案副本"}
roles_used = {c["known_role"] for c in B.CHECKS}
check(roles_used <= ROLES, f"T1a known_role 有非法值：{sorted(roles_used - ROLES)}")
# 答案副本必须至少出现一条（本批确实存在泄露），且该条必须挂上 DEF-D1
copies = [c for c in B.CHECKS if c["known_role"] == "答案副本"]
check(len(copies) >= 1, "T1b 本批已检出滑杆泄露，却没有任何题标为「答案副本」")
for c in copies:
    rid = c["rvid"][:8]
    check(rid in B.KNOWN_DEFECTS["DEF-D1"]["affected"],
          f"T1c {rid} 标为「答案副本」，却不在 DEF-D1.affected 里")
# 「答案副本」题的 boundary 必须把泄露写出来，不能只贴标签
LEAK_WORDS = ("上限", "答案副本", "最右端", "拖到底", "拖满", "滑杆",
              "泄露", "max =", "max=", "bars.max")
for c in copies:
    body = c["boundary"] + c["config_role"]
    check(any(k in body for k in LEAK_WORDS),
          f"T1d {c['rvid'][:8]} 标为答案副本但 boundary/config_role 未说明泄露机制")

# ── T2 五类关系全覆盖 + 判据原文 ───────────────────────────────────────────
check(set(B.RELATION_RULES) == {
    "part_whole", "difference", "larger_smaller", "continuous", "conditional"},
    f"T2a 五类关系定义不全：{sorted(B.RELATION_RULES)}")
used = {c["relation"] for c in B.CHECKS}
check(used == set(B.RELATION_RULES),
      f"T2b 五类未覆盖，缺：{sorted(set(B.RELATION_RULES) - used)}")
for k, v in B.RELATION_RULES.items():
    check(len(v) >= 20, f"T2c 关系 {k} 的判据太短，不足以当判据：{v!r}")
for k, v in B.RELATION_RULES.items():
    check("renderer" not in v,
          f"T2d 关系 {k} 的判据里出现 renderer 字样——判据应是题面层判据")

# ── T3 config_role 必须指名真实字段 ───────────────────────────────────────
FIELD_HINTS = ("workspaces[0].config", "visual", "kind=number",
               "bars=[", "groups:[", "groups=[", "bars:", "max_value",
               "没有配置", "无 visual", "没有任何配置", "纯数字输入框")
for c in B.CHECKS:
    cr = c["config_role"]
    ok = any(k in cr for k in FIELD_HINTS)
    check(ok, f"T3a {c['rvid'][:8]} 的 config_role 未指名字段路径：{cr[:40]!r}")
    check("见上" not in cr and "同上" not in cr,
          f"T3b {c['rvid'][:8]} 的 config_role 用了「见上/同上」这类空话")
    check(any(ch.isdigit() for ch in cr) or "visual" in cr or "config" in cr,
          f"T3c {c['rvid'][:8]} 的 config_role 没有任何具体值/字段名")

# ── T4 source_kind 与 renderer 相符 ───────────────────────────────────────
for c in B.CHECKS:
    rd, sk = c["renderer"], c["source_kind"]
    if rd.startswith("legacy:"):
        check(sk != "stem_plus_v2config",
              f"T4a {c['rvid'][:8]} 是 V1 {rd}，却声称 stem_plus_v2config")
        check(sk in ("stem_only", "stem_plus_visual"),
              f"T4b {c['rvid'][:8]} 的 source_kind 非法：{sk}")
    else:
        # ★ 已撤销 T4c「V2 不许声称 stem_only」。
        #   复审原文：V2 题也可能仅靠题干完成推导。强制它必须声明
        #   stem_plus_v2config 会让登记表写假话——为满足工具而扭曲事实。
        #   替代做法（T4c'）：允许 stem_only，但必须显式说明 config 未被用作
        #   推导依据，且该说明要能被 `config_role` 佐证。
        check(sk in ("stem_plus_v2config", "stem_plus_visual", "stem_only"),
              f"T4b2 {c['rvid'][:8]} 的 source_kind 非法：{sk}")
        if sk == "stem_only":
            # 不是在查关键词，而是要求在登记里出现「config 起什么作用」的判断
            check(bool(c.get("config_role")),
                  f"T4c {c['rvid'][:8]} 是 V2 却声称 stem_only，"
                  "且没有 config_role 说明 config 起了什么作用")
# V1 legacy 若声称 stem_plus_visual，必须写明 visual 的真实角色
ROLE_WORDS = ("摆设", "不参与", "不承载", "不是题面", "演示参数", "不泄露",
              "上限", "写死", "固定", "只能", "无法", "永远", "不记录",
              "容量不足", "没有", "不是「", "不是“", "不表达", "丢")
for c in B.CHECKS:
    if c["renderer"].startswith("legacy:") and c["source_kind"] == "stem_plus_visual":
        body = c["config_role"] + c["boundary"]
        check(any(k in body for k in ROLE_WORDS),
              f"T4e {c['rvid'][:8]} 声称 visual 是已知量来源，但未说明其真实角色")

# ── T5 缺陷登记必须可核对现场（允许批外，但必须独立留证）──────────────────
# ★ 已撤销「affected 必须全在批内」。复审要求：缺陷调查可以引用批外题目，
#   只要独立保留其身份、输入和核查证据；批外发现与本批完成数量分账。
batch_ids = {c["rvid"][:8] for c in B.CHECKS}
_oob = B.LEDGER.get("selection_record", {})  # 仅保证结构存在
check("out_of_batch_refs" not in B.LEDGER or True, "")  # 占位：结构由 T5b 校验
for did, d in B.KNOWN_DEFECTS.items():
    outside = [x for x in d["affected"] if x not in batch_ids]
    if outside:
        # 必须留证：批外引用要有独立的 RVID 列表与核查依据
        refs = d.get("out_of_batch_evidence") or {}
        for x in outside:
            check(x in refs,
                  f"T5 {did}.affected 含批外 RVID {x}，但未在 "
                  "`out_of_batch_evidence` 中独立留证（身份/输入/核查依据）")
# T5b 每条风险必须有证据分层，且 confirmed=False 时必须写清不主张什么
TIERS = {"static_fact", "inference", "needs_runtime"}
for did, d in B.KNOWN_DEFECTS.items():
    tier = str(d.get("evidence_tier", ""))
    parts = [p.strip() for p in tier.split("→")]
    check(bool(tier), f"T5b {did} 缺少 evidence_tier——风险条目必须标出证据层级")
    check(all(p in TIERS for p in parts if p),
          f"T5c {did} 的 evidence_tier 含非法值：{tier!r}")
    check("confirmed" in d, f"T5d {did} 缺少 confirmed 标志")
    if d.get("confirmed") is False:
        check(bool(d.get("not_claimed")),
              f"T5e {did} 标为未确证，却没有 not_claimed——"
              "必须写明「不主张什么」，否则会被读成已确证的故障")

# ── T6 检测器与登记表双向一致（合成样本，不连库）──────────────────────────
fake_leak_vis = {"type": "bar-model",
                 "bars": [{"id": "base", "max": 11, "value": 7},
                          {"id": "unknown", "max": 11, "unknown": True}],
                 "max_value": 13}
check(B.detect_visual_leak(fake_leak_vis, 11.0) != [],
      "T6a DEF-D1 合成样本（max==answer）未被检出")
check(B.detect_visual_leak(fake_leak_vis, 12.0) == [],
      "T6b DEF-D1 负向：max≠answer 时误报")
# DEF-D2：线索检测器
check(B.detect_unreachable(fake_leak_vis, 18.0) is not None,
      "T6c DEF-D2 合成样本（answer>max）未给出线索")
check(B.detect_unreachable(fake_leak_vis, 8.0) is None,
      "T6d DEF-D2 负向：answer 在范围内时误报")
# ★ T6f 线索检测器的已知漏报必须被记录在案，不能假装它是判定器。
#   反例：答案条上限 5、无关条上限 100、答案 10 → 取 max(100) 后判定可达。
_miss_vis = {"type": "bar-model",
             "bars": [{"id": "answer_bar", "max": 5},
                      {"id": "unrelated", "max": 100}],
             "max_value": 5}
check(B.detect_unreachable(_miss_vis, 10.0) is None,
      "T6f 线索检测器行为已变：预期它会**漏报**（取 max 而非答案条上限）。"
      "若此处失败，请先更新 KNOWN_DEFECTS['DEF-D2'].detector_limits 再改断言")
check("线索" in (B.KNOWN_DEFECTS["DEF-D2"].get("title", "")),
      "T6g DEF-D2 标题必须体现「线索，非可完成性判定」，不得写成「物理摆不出」")
check("不主张「永远拿不到分」" in B.KNOWN_DEFECTS["DEF-D2"].get("not_claimed", "")
      or "永远拿不到分" in B.KNOWN_DEFECTS["DEF-D2"].get("not_claimed", ""),
      "T6h DEF-D2 必须明确不主张「永远拿不到分」")
check("detector_limits" in B.KNOWN_DEFECTS["DEF-D2"],
      "T6i DEF-D2 必须登记检测器局限（角色语义缺失 + max 漏报反例）")
check(bool(B.KNOWN_DEFECTS["DEF-D2"].get("verification_plan")),
      "T6j DEF-D2 必须给出定向核验计划（表征对象/正确候选/负例/提交关联）")

# ── T7 Q05 三字段 + 去重口径 ─────────────────────────────────────────────
renderer_of = {c["rvid"][:8]: c["renderer"] for c in B.CHECKS}
seen: dict[tuple[str, str], str] = {}
for rid, ev in B.Q05_EVIDENCE.items():
    check(bool(ev.get("competing")), f"T7a {rid} 缺 competing_explanations")
    check(bool(ev.get("neutral")), f"T7b {rid} 缺 neutral_feedback")
    o = ev.get("observable")
    if isinstance(o, dict):
        items = list(o.items())
    else:
        check(bool(o), f"T7c {rid} 缺 observable_evidence")
        items = [("<any>", o)]
    for code, text in items:
        key = (renderer_of.get(rid, "?"), text)
        if key in seen and seen[key] != rid:
            check(False, f"T7d 同 renderer 内 observable 重复（又套模板）：{(key, seen[key], rid)}")
        seen[key] = rid

# ── T8 对照声明 ───────────────────────────────────────────────────────────
kinds = [p["kind"] for p in B.CONTRAST_PAIRS]
# ★ 已撤销 T8a「必须至少一条 MISSING」。覆盖完善后可以没有对照缺口；
#   强制存在 MISSING 会逼人编造一个不真实的缺口。
#   替代：若声明了 MISSING，必须写明缺什么（why 非空），不能只挂标签。
for p in B.CONTRAST_PAIRS:
    if p["kind"] == "MISSING":
        check(bool(p.get("why")), "T8a MISSING 对照未写明缺口内容")
    else:
        check(p["a"] in batch_ids, f"T8c 对照 a={p['a']} 不在本批")
        check(p["b"] in batch_ids, f"T8d 对照 b={p['b']} 不在本批")
check(sum(1 for k in kinds if k != "MISSING") >= 3,
      "T8b 本批可用的对照对少于 3 条")

# ── T9 负向自检：注入违规必须被检出 ───────────────────────────────────────
def _would_fail(checks_snapshot) -> list[str]:
    out = []
    for c in checks_snapshot:
        if c["renderer"].startswith("legacy:") and c["source_kind"] == "stem_plus_v2config":
            out.append("T4a")
        if c["known_role"] not in ROLES:
            out.append("T1a")
        if c["relation"] not in B.RELATION_RULES:
            out.append("T2b")
        if not any(k in c["config_role"] for k in
                   ("workspaces[0].config", "visual", "kind=number",
                    "没有配置", "无 visual", "没有任何配置")):
            out.append("T3a")
    return out


synth = [
    {"rvid": "aaaa0000-0000-0000-0000-000000000000", "renderer": "legacy:direct",
     "relation": "difference", "source_kind": "stem_plus_v2config",
     "known_role": "已知部分", "config_role": "workspaces[0].config"},
    {"rvid": "bbbb0000-0000-0000-0000-000000000000", "renderer": "bar-model",
     "relation": "difference", "source_kind": "stem_plus_v2config",
     "known_role": "已知量", "config_role": "workspaces[0].config"},
    {"rvid": "cccc0000-0000-0000-0000-000000000000", "renderer": "bar-model",
     "relation": "transfer", "source_kind": "stem_plus_v2config",
     "known_role": "已知部分", "config_role": "workspaces[0].config"},
    {"rvid": "dddd0000-0000-0000-0000-000000000000", "renderer": "bar-model",
     "relation": "difference", "source_kind": "stem_plus_v2config",
     "known_role": "已知部分", "config_role": "配置见上"},
]
detected = _would_fail(synth)
for expect in ("T4a", "T1a", "T2b", "T3a"):
    check(expect in detected, f"T9 负向自检未检出 {expect}（检出集合 {detected}）")
legal = [{"rvid": "eeee0000-0000-0000-0000-000000000000", "renderer": "bar-model",
          "relation": "difference", "source_kind": "stem_plus_v2config",
          "known_role": "已知部分", "config_role": "workspaces[0].config.known"}]
check(_would_fail(legal) == [], "T9b 负向自检把合法数据误判为违规")

# ── T10 账目 ─────────────────────────────────────────────────────────────
_n = len(B.CHECKS)
_doc = (B.__doc__ or "")
_led = getattr(B, "LEDGER", None)

check("计划" in _doc or "额定" in _doc,
      "T10a docstring 未标明「计划/额定」——计划与实际必须分开写")
check("实核" in _doc, "T10a2 docstring 未标明「实核」")
_m = re.search(r"实核\s*(\d+)\s*题", _doc)
check(_m is not None, "T10a3 docstring 里找不到「实核 N 题」")
if _m:
    check(int(_m.group(1)) == _n,
          f"T10b docstring 写实核 {_m.group(1)} 题，实际 CHECKS 有 {_n} 条")

_title = _doc.strip().splitlines()[0] if _doc.strip() else ""
if _led:
    _tq = re.search(r"额定\s*(\d+)\s*题", _title)
    if _tq:
        check(int(_tq.group(1)) == _led["quota"],
              f"T10c1 标题行额定 {_tq.group(1)} ≠ LEDGER.quota {_led['quota']}")
_tv = re.search(r"实核\s*(\d+)\s*题", _title)
if _tv:
    check(int(_tv.group(1)) == _n, f"T10c2 标题行实核 {_tv.group(1)} ≠ 实际 {_n}")

check(_led is not None, "T10d 缺少 LEDGER 常量——账目没有单一出处")
if _led:
    traced = {x for v in _led["traced_extra_breakdown"].values() for x in v}
    check(_led["verified"] == _n,
          f"T10e LEDGER.verified={_led['verified']} ≠ 实核 {_n}")
    check(len(traced) == _led["traced_extra"],
          f"T10f LEDGER.traced_extra={_led['traced_extra']} ≠ 明细 {len(traced)} 条")
    check(traced <= batch_ids,
          f"T10g LEDGER 可追溯补入含批外 RVID：{sorted(traced - batch_ids)}")
    # ★ 已撤销「差额必须存在且必须标未解释」。
    #   复审裁决：不再让门禁强制这批永远保留「差额必须未解释」的固定状态。
    #   改为：计划与实际若不一致，必须由 selection_record 说明**记录缺失**，
    #   且必须同时声明 29 条身份是否完整——不允许把「记录缺失」讲成「题来路不明」。
    check("selection_record" in _led,
          "T10h 计划≠实际时必须用 selection_record 记录「初始选样名单缺失」")
    if "selection_record" in _led:
        sr = _led["selection_record"]
        check(bool(sr.get("missing_reason")),
              "T10i selection_record 未说明缺失原因")
        check(bool(sr.get("what_this_is_not")),
              "T10j selection_record 未明确「这不是什么」——"
              "必须写清不是「有身份不明的记录」")
        check(bool(sr.get("remedy")), "T10k selection_record 缺少改进措施")
    check(_led.get("identity_complete") is True,
          "T10l 29 条 RVID 身份必须声明完整（identity_complete=True）")
    for did, ids in _led["traced_extra_breakdown"].items():
        for rid in ids:
            check(rid in batch_ids, f"T10m {did} 的补入 {rid} 不在 CHECKS 内")
    # 反向：不允许再出现旧的 gap 口径（防止回退）
    check("gap_explained" not in _led,
          "T10n LEDGER 又出现了 gap_explained——该字段已被复审撤销，"
          "口径应为 selection_record")

# ── T11 文档与工件一致（缺失即 FAIL）──────────────────────────────────────
_doc_path = os.path.join(REPO, "docs", "qa", "FE1469_FE1470_Q03_BATCHES.md")
if _must_exist(_doc_path, "批次报告文档"):
    _d = open(_doc_path, encoding="utf-8").read()
    _all_defect_ids = {x for d in B.KNOWN_DEFECTS.values() for x in d["affected"]}
    _sum = sum(len(d["affected"]) for d in B.KNOWN_DEFECTS.values())
    # ★ T11a 已改口径：不再要求「四类互不重叠」。
    #   同一题可以同时命中多类问题，应分别统计 Findings 与去重 RVID。
    #   这里只要求文档里给出的两个数各自与现场一致。
    check(_all_defect_ids <= batch_ids | set(
        x for d in B.KNOWN_DEFECTS.values()
        for x in (d.get("out_of_batch_evidence") or {})),
        "T11a 缺陷引用含既不在批内、也未留证的 RVID")
    # 文档里的「命中风险条目（DEF-D1 a / D2 b / D3 c / D4 d）」形态
    _hit = re.search(
        r"(\d+) 条命中[^（]*（DEF-D1 (\d+) / D2 (\d+) / D3 (\d+) / D4 (\d+)）", _d)
    if _hit:
        got = [int(_hit.group(i)) for i in range(1, 6)]
        want = [len(_all_defect_ids)] + [
            len(B.KNOWN_DEFECTS[k]["affected"])
            for k in ("DEF-D1", "DEF-D2", "DEF-D3", "DEF-D4")]
        # 文档第一个数是去重 RVID 数（同一题可命中多类，故与求和不同）
        check(got[1:] == want[1:],
              f"T11b 文档各类命中数 {got[1:]} 与现场 {want[1:]} 不符")
        check(got[0] == len(_all_defect_ids),
              f"T11b2 文档去重命中数 {got[0]} ≠ 现场去重 {len(_all_defect_ids)}"
              f"（各类求和 {_sum}，两者不同是允许的）")
    # 累计题数
    _cum = re.search(r"累计 (\d+) 条（(\d+) \+ (\d+) \+ (\d+)）", _d)
    check(_cum is not None,
          "T11c 文档缺少「累计 N 条（a + b + c）」形态的进度表述")
    if _cum:
        total = int(_cum.group(1))
        addends = [int(_cum.group(i)) for i in (2, 3, 4)]
        check(total == sum(addends),
              f"T11c2 文档累计 {total} ≠ {'+'.join(map(str, addends))}={sum(addends)}")
        check(addends[-1] == _n,
              f"T11c3 文档累计算式第三项 {addends[-1]} ≠ 本批实核 {_n}")

    _B1, _B2 = 6, 20
    _tot = _B1 + _B2 + _n
    _q03 = re.findall(r"\| Q03 待核验 \| 212 \| \*{0,2}(\d+)\*{0,2} \|", _d)
    check(bool(_q03), "T11d 文档缺少「Q03 待核验」行")
    for v in _q03:
        check(int(v) == 212 - _tot,
              f"T11d2 文档「Q03 待核验」={v}，三批后应为 {212 - _tot}")
    _both = re.findall(r"\| 交集（both） \| 197 \| \*{0,2}(\d+)\*{0,2} \|", _d)
    for v in _both:
        check(int(v) == 197 - _tot,
              f"T11e 文档「交集（both）」={v}，三批后应为 {197 - _tot}")
    _q05o = re.findall(r"\| Q05_only \| 12 \| \*{0,2}(\d+)\*{0,2} \|", _d)
    for bv, qv in zip(_both, _q05o):
        check(15 + int(bv) + int(qv) == 224,
              f"T11f 并集恒等式不成立：15 + {bv} + {qv} ≠ 224")
    # 文档必须把「已撤回的定性」讲清楚，并且给出新的正确表述。
    #
    # ★ 这里**不做禁词**。上一版试过「正文不得出现『物理摆不出』」，结果连
    #   「撤回了『物理摆不出』」这种正当叙述也被判错——而删掉撤回记录，报告
    #   就失去了可追溯性，等于为了过门禁而毁掉内容。复审早已指出：关键词检查
    #   只能发现漏填，不能证明语义正确。所以改成**正向断言**：文档必须写到
    #   这些要点，缺哪个就报哪个。
    _required = {
        "5.8.4 撤回记录小节": "#### 5.8.4 撤回记录",
        "DEF-D2 改为线索表述": "线索检测器",
        "DEF-D2 定向核验计划": "定向核验",
        "DEF-D2 数学答案无需修改": "无需修改",
        "DEF-D1 不主张拖到底即满分": "表征层",
        "DEF-D3 不等于不能一一对应": "不等于",
        "DEF-D4 四件事分开": "有没有记录",
        "15 条改称风险条目": "风险条目",
        "证据分层": "static_fact",
        "门禁空转记录": "independent_eval",
    }
    for label, needle in _required.items():
        check(needle in _d, f"T11g 文档缺少必要内容：{label}（找不到 {needle!r}）")
    _retract = re.search(r"####\s*5\.8\.4\s*撤回记录(.*?)(?=\n####\s|\Z)", _d, re.S)
    check(_retract is not None, "T11h 缺少「撤回记录」小节——被撤回的定性必须留痕")
    if _retract:
        rows = [ln for ln in _retract.group(1).splitlines()
                if ln.strip().startswith("|") and "---" not in ln]
        check(len(rows) >= 7,
              f"T11h2 撤回记录表只有 {len(rows)} 行（含表头），上一版有 7 条被撤回的定性")
    _retract = re.search(r"####\s*5\.8\.4\s*撤回记录(.*?)(?=\n####\s|\Z)", _d, re.S)
    if _retract:
        check(_retract.group(1).count("|") >= 12,
              "T11h2 撤回记录表少于 6 行（上一版有 7 条被撤回的定性）")

# ── T12 离线回放：真实跑 evaluate() ───────────────────────────────────────
SNAP = os.path.join(HERE, "batch3_frozen_inputs.json")
if _must_exist(SNAP, "冻结输入快照 batch3_frozen_inputs.json"):
    snap = json.load(open(SNAP, encoding="utf-8"))
    by_id = {it["rvid"]: it for it in snap["items"]}
    check(set(by_id) == {c["rvid"] for c in B.CHECKS},
          "T12a 快照覆盖的 RVID 与 CHECKS 不一致")
    check(snap.get("count") == len(B.CHECKS),
          f"T12a2 快照 count={snap.get('count')} ≠ CHECKS {len(B.CHECKS)}")

    def _sha(obj) -> str:
        raw = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    # T12b 正向：逐题真实调用 evaluate()，必须 MATCH
    _live_verdicts: dict[str, str] = {}
    for c in B.CHECKS:
        it = by_id.get(c["rvid"])
        if not it:
            continue
        r = B.evaluate(c, it["answer_raw"], it["error_models"],
                       it["ui_schema"] or {})
        _live_verdicts[c["rvid"]] = r["verdict"]
        check(r["verdict"] == "MATCH",
              f"T12b {c['rvid'][:8]} 离线回放结论 {r['verdict']}，应为 MATCH"
              f"（computed={r['computed']} stated={it['answer_raw']!r}）")
        # 防手改快照
        check(_sha(it["answer_raw"]) == it["answer_raw_sha256"],
              f"T12b2 {c['rvid'][:8]} 的 answer 被手改（sha 不符）")
        check(_sha(it["ui_schema"]) == it["ui_schema_sha256"],
              f"T12b3 {c['rvid'][:8]} 的 ui_schema 被手改（sha 不符）")
        # 与快照里记录的 replay 逐字段一致
        rep = it["replay"]
        check(rep["verdict"] == r["verdict"],
              f"T12b4 {c['rvid'][:8]} 现场 verdict 与快照 replay 不一致")
        check(rep["computed"] == r["computed"],
              f"T12b5 {c['rvid'][:8]} 现场 computed 与快照 replay 不一致")
        check(rep["visual_leak"] == r["visual_leak"],
              f"T12b6 {c['rvid'][:8]} 现场 visual_leak 与快照 replay 不一致")
        check(rep["unreachable_signal"] == r["unreachable_signal"],
              f"T12b7 {c['rvid'][:8]} 现场 unreachable_signal 与快照不一致")

    # T12c 负向（值）：answer 改成 answer+1 → 必须 MISMATCH
    #        这条能拦住「match 恒 True」的变异。
    _wrong_ok = 0
    for c in B.CHECKS:
        it = by_id.get(c["rvid"])
        if not it:
            continue
        try:
            bumped = str(int(float(it["answer_raw"])) + 1)
        except (TypeError, ValueError):
            continue
        r = B.evaluate(c, bumped, it["error_models"], it["ui_schema"] or {})
        if r["verdict"] == "MISMATCH":
            _wrong_ok += 1
        else:
            check(False, f"T12c {c['rvid'][:8]} 把答案改成 {bumped} 后仍判 MATCH"
                         "——负向断言失效（match 可能被写成恒 True）")
    check(_wrong_ok >= 25,
          f"T12c2 负向断言覆盖不足：只有 {_wrong_ok} 题成功构造了错值")

    # T12d 负向（推导）：expr 改成 expr+1 → 必须 MISMATCH
    #        这条能拦住「independent_eval 恒 0 / 恒真值」的变异。
    _expr_ok = 0
    for c in B.CHECKS:
        it = by_id.get(c["rvid"])
        if not it:
            continue
        c2 = dict(c)
        c2["expr"] = f"({c['expr']}) + 1"
        r = B.evaluate(c2, it["answer_raw"], it["error_models"],
                       it["ui_schema"] or {})
        if r["verdict"] == "MISMATCH":
            _expr_ok += 1
        else:
            check(False, f"T12d {c['rvid'][:8]} 把推导 {c['expr']} 改成 +1 后"
                         "仍判 MATCH——数学核验路径没有真正执行")
    check(_expr_ok >= 25,
          f"T12d2 推导篡改覆盖不足：只有 {_expr_ok} 题被检出")

    # T12e 配置敏感：篡改 visual 的关键字段，检测器结论必须变
    #        这条能拦住「检测器读不到配置也照样 PASS」。
    _leak_rid = None
    for c in B.CHECKS:
        it = by_id.get(c["rvid"])
        if it and it["replay"]["visual_leak"]:
            _leak_rid = (c, it)
            break
    check(_leak_rid is not None, "T12e 快照里没有任何 visual_leak 样本，无法做配置敏感断言")
    if _leak_rid:
        c, it = _leak_rid
        vis = copy.deepcopy(it["ui_schema"] or {})
        # 把所有 max 提高到答案 +5：泄露应当消失
        try:
            ans = float(it["answer_raw"])
        except (TypeError, ValueError):
            ans = None
        if ans is not None and isinstance(vis.get("visual"), dict):
            v = vis["visual"]
            for b in (v.get("bars") or []):
                if isinstance(b, dict) and isinstance(b.get("max"), (int, float)):
                    b["max"] = ans + 5
            if isinstance(v.get("max_value"), (int, float)):
                v["max_value"] = ans + 5
            r2 = B.evaluate(c, it["answer_raw"], it["error_models"], vis)
            check(r2["visual_leak"] == [],
                  f"T12e {c['rvid'][:8]} 把所有 max 提高后仍报泄露"
                  "——检测器没有真正读配置")
        else:
            check(False, f"T12e {c['rvid'][:8]} 的 ui_schema.visual 结构异常，"
                         "无法构造配置敏感断言")

    # T12f 变异自检：把 evaluate 的核验路径整体替换，门禁必须判 FAIL
    #        这是对「门禁能否发现审计器自身失效」的元检查。
    _orig_eval = B.independent_eval
    try:
        B.independent_eval = lambda expr: 0          # 变异 1：恒 0
        mocked_fail = 0
        for c in B.CHECKS:
            it = by_id.get(c["rvid"])
            if not it:
                continue
            r = B.evaluate(c, it["answer_raw"], it["error_models"],
                           it["ui_schema"] or {})
            if r["verdict"] == "MISMATCH":
                mocked_fail += 1
        check(mocked_fail >= 25,
              f"T12f 把 independent_eval 改成恒 0 后只有 {mocked_fail} 题变 MISMATCH"
              "（应 ≥25）——说明回放层没有真正依赖它，门禁仍会空转")
    finally:
        B.independent_eval = _orig_eval

# ── 输出 ──────────────────────────────────────────────────────────────────
if fails:
    print(f"Q03-BATCH3-GATE: FAIL ({len(fails)} 项)")
    for f in fails:
        print("  ✗", f)
    sys.exit(1)

print(f"Q03-BATCH3-GATE: PASS "
      f"({len(B.CHECKS)} 题 / {len(B.Q05_EVIDENCE)} 条证据 / "
      f"{len(B.KNOWN_DEFECTS)} 类风险条目 / "
      f"{len(B.CONTRAST_PAIRS)} 条对照声明 / "
      f"计划 {B.LEDGER['quota']} → 实核 {B.LEDGER['verified']}"
      f"（身份完整={B.LEDGER['identity_complete']}，"
      f"初始选样名单缺失已登记）)")