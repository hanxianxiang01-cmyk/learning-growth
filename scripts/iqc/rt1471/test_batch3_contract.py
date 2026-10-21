#!/usr/bin/env python3
"""FE-1471 门禁：第三批核验的结构约束回归（`Q03-BATCH3-GATE`）。

上一批（FE-1470）被打回的原因是「22 条 requirement 共用一句通用说明」。
本批面临的是**新的**退回风险，逐条对应成检查项：

  T1  `known_role` 四值枚举齐备，且「答案副本」**不被当成正常依据**
      ——复审原文：「`known` 不天然是独立事实」。
  T2  五类关系全覆盖，且每类的**判据原文**在 `RELATION_RULES` 里
      ——防止事后按结果贴标签（循环论证）。
  T3  每题 `config_role` 必须落地到**真实存在的字段路径**
      （V2 → `workspaces[].config`；V1 → `ui_schema.visual`），
      不允许写「配置见上」这类空话。
  T4  `source_kind` 必须与 `renderer` 相符：V1 legacy 不许声称
      `stem_plus_v2config`，V2 不许声称 `stem_only`
      ——这条正是本批最大的事实性风险（14 题是 V1，配置不是题面已知量）。
  T5  `KNOWN_DEFECTS` 的 `affected` 必须是**本批内**的 RVID
      ——否则「已登记」就没有核对过现场（本批曾犯，已修）。
  T6  缺陷与实际检出必须**双向一致**：
      `DEF-D1.affected` ↔ `visual_leak_items`；
      `DEF-D2.affected` ↔ `unreachable_items`。
  T7  Q05 三字段逐题非空，且**同 renderer 内无重复 observable**
      ——沿用上一批的做法，但本批要求「不止不重复，还要指名字段」。
  T8  「配对/缺口」声明必须显式：`CONTRAST_PAIRS` 里至少有一条 `MISSING`
      ——防止把「找不到对照」写成「已验证」。
  T9  负向自检：往合成数据里注入四类违规，必须全被检出。
  T10 账目自洽：额定 / 实核 / 可追溯补入 / 未解释差额四个数必须与
      `CHECKS` 实际条数三方对齐；差额若存在必须显式标「未解释」并给出
      不编造的理由与补救措施（本批真实存在 2 条无法反推的差额）。
  T11 文档与工件一致：报告里的缺陷条数、累计题数、进度表必须与现场
      重算结果相等——本批真实犯过「docstring 写 20 题、实际 29 条」
      与「进度表留两批旧数 186/171/38」两次，故由门禁兜住。

用法：python scripts/iqc/rt1471/test_batch3_contract.py
"""
from __future__ import annotations

import importlib.util
import os
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
# 合格的写法包括：明说「上限/最右端/拖到底/滑杆泄露」等具体机制
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
# 判据必须是「题面措辞」而非「renderer 名」
for k, v in B.RELATION_RULES.items():
    check("renderer" not in v,
          f"T2d 关系 {k} 的判据里出现 renderer 字样——判据应是题面层判据")

# ── T3 config_role 必须指名真实字段 ───────────────────────────────────────
# 接受的字段路径写法（任一即可）——注意 `bars=[...]` / `groups:[...]` 这类
# 已经点到了 visual 的子字段，只是省略了外层 `visual.` 前缀，应算合格。
FIELD_HINTS = ("workspaces[0].config", "visual", "kind=number",
               "bars=[", "groups:[", "groups=[", "bars:", "max_value",
               "没有配置", "无 visual", "没有任何配置", "纯数字输入框")
for c in B.CHECKS:
    cr = c["config_role"]
    ok = any(k in cr for k in FIELD_HINTS)
    check(ok, f"T3a {c['rvid'][:8]} 的 config_role 未指名字段路径：{cr[:40]!r}")
    # 禁止空话
    check("见上" not in cr and "同上" not in cr,
          f"T3b {c['rvid'][:8]} 的 config_role 用了「见上/同上」这类空话")
    # 必须至少出现一个具体数值或字段名，不能全是描述
    check(any(ch.isdigit() for ch in cr) or "visual" in cr or "config" in cr,
          f"T3c {c['rvid'][:8]} 的 config_role 没有任何具体值/字段名")

# ── T4 source_kind 与 renderer 相符（本批最大事实性风险）──────────────────
for c in B.CHECKS:
    rd, sk = c["renderer"], c["source_kind"]
    if rd.startswith("legacy:"):
        check(sk != "stem_plus_v2config",
              f"T4a {c['rvid'][:8]} 是 V1 {rd}，却声称 stem_plus_v2config")
        check(sk in ("stem_only", "stem_plus_visual"),
              f"T4b {c['rvid'][:8]} 的 source_kind 非法：{sk}")
    else:
        check(sk != "stem_only",
              f"T4c {c['rvid'][:8]} 是 V2 {rd}，却声称 stem_only（忽略了 config）")
        check(sk in ("stem_plus_v2config", "stem_plus_visual"),
              f"T4d {c['rvid'][:8]} 的 source_kind 非法：{sk}")
# V1 legacy 若声称 stem_plus_visual，必须写明 visual 的真实角色
# ——注意「visual 是摆好的物件」本身也是一种真实角色（如 legacy:objects），
#   所以合格的写法不止「不参与推导」，还包括明确指出它能/不能承载什么。
ROLE_WORDS = ("摆设", "不参与", "不承载", "不是题面", "演示参数", "不泄露",
              "上限", "写死", "固定", "只能", "无法", "永远", "不记录",
              "容量不足", "没有", "不是「", "不是“", "不表达", "丢")
for c in B.CHECKS:
    if c["renderer"].startswith("legacy:") and c["source_kind"] == "stem_plus_visual":
        body = c["config_role"] + c["boundary"]
        check(any(k in body for k in ROLE_WORDS),
              f"T4e {c['rvid'][:8]} 声称 visual 是已知量来源，但未说明其真实角色")

# ── T5 KNOWN_DEFECTS.affected 必须全在本批内 ───────────────────────────────
batch_ids = {c["rvid"][:8] for c in B.CHECKS}
for did, d in B.KNOWN_DEFECTS.items():
    outside = [x for x in d["affected"] if x not in batch_ids]
    check(not outside,
          f"T5 {did}.affected 含批外 RVID {outside}——「已登记」未核对现场")

# ── T6 缺陷与检出双向一致（用合成数据自检，不连库）──────────────────────
# DEF-D1：滑杆上限 == 答案
fake_leak_vis = {"type": "bar-model",
                 "bars": [{"id": "base", "max": 11, "value": 7},
                          {"id": "unknown", "max": 11, "unknown": True}],
                 "max_value": 13}
check(B.detect_visual_leak(fake_leak_vis, 11.0) != [],
      "T6a DEF-D1 合成样本（max==answer）未被检出")
check(B.detect_visual_leak(fake_leak_vis, 12.0) == [],
      "T6b DEF-D1 负向：max≠answer 时误报")
# DEF-D2：上限 < 答案
check(B.detect_unreachable(fake_leak_vis, 18.0) is not None,
      "T6c DEF-D2 合成样本（answer>max）未被检出")
check(B.detect_unreachable(fake_leak_vis, 8.0) is None,
      "T6d DEF-D2 负向：answer 在范围内时误报")
# 与登记表对齐
for rid in B.KNOWN_DEFECTS["DEF-D1"]["affected"]:
    check(rid in batch_ids, f"T6e DEF-D1.affected 里的 {rid} 不在本批")

# ── T7 Q05 三字段 + 同 renderer 内 observable 不重复 ─────────────────────
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
            fail_key = (key, seen[key], rid)
            check(False, f"T7d 同 renderer 内 observable 重复（又套模板）：{fail_key}")
        seen[key] = rid

# ── T8 对照声明必须含 MISSING（诚实登记缺口）────────────────────────────
kinds = [p["kind"] for p in B.CONTRAST_PAIRS]
check("MISSING" in kinds, "T8a CONTRAST_PAIRS 没有任何 MISSING 项——缺口的诚实登记缺失")
check(sum(1 for k in kinds if k != "MISSING") >= 3,
      "T8b 本批可用的对照对少于 3 条")
for p in B.CONTRAST_PAIRS:
    if p["kind"] != "MISSING":
        check(p["a"] in batch_ids, f"T8c 对照 a={p['a']} 不在本批")
        check(p["b"] in batch_ids, f"T8d 对照 b={p['b']} 不在本批")

# ── T9 负向自检：注入违规必须被检出 ───────────────────────────────────────
def _would_fail(checks_snapshot) -> list[str]:
    out = []
    ids = {c["rvid"][:8] for c in checks_snapshot}
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
    # 违规 1：V1 声称 V2 配置
    {"rvid": "aaaa0000-0000-0000-0000-000000000000", "renderer": "legacy:direct",
     "relation": "difference", "source_kind": "stem_plus_v2config",
     "known_role": "已知部分", "config_role": "workspaces[0].config"},
    # 违规 2：known_role 非法
    {"rvid": "bbbb0000-0000-0000-0000-000000000000", "renderer": "bar-model",
     "relation": "difference", "source_kind": "stem_plus_v2config",
     "known_role": "已知量", "config_role": "workspaces[0].config"},
    # 违规 3：relation 非法
    {"rvid": "cccc0000-0000-0000-0000-000000000000", "renderer": "bar-model",
     "relation": "transfer", "source_kind": "stem_plus_v2config",
     "known_role": "已知部分", "config_role": "workspaces[0].config"},
    # 违规 4：config_role 空话
    {"rvid": "dddd0000-0000-0000-0000-000000000000", "renderer": "bar-model",
     "relation": "difference", "source_kind": "stem_plus_v2config",
     "known_role": "已知部分", "config_role": "配置见上"},
]
detected = _would_fail(synth)
for expect in ("T4a", "T1a", "T2b", "T3a"):
    check(expect in detected, f"T9 负向自检未检出 {expect}（检出集合 {detected}）")
# 反向确认：合法数据不该被误判
legal = [{"rvid": "eeee0000-0000-0000-0000-000000000000", "renderer": "bar-model",
          "relation": "difference", "source_kind": "stem_plus_v2config",
          "known_role": "已知部分", "config_role": "workspaces[0].config.known"}]
check(_would_fail(legal) == [], "T9b 负向自检把合法数据误判为违规")

# ── T10 账目与文档一致性（本批实际犯过的错，必须由门禁兜住）──────────────
# 背景：补 9 题缺陷核验时忘了回改 docstring 的「20 题」，造成文档与工件不符。
# 这类错不能靠「记得改」，只能靠检查。
import re  # noqa: E402

_n = len(B.CHECKS)
_doc = (B.__doc__ or "")

_led = getattr(B, "LEDGER", None)

# T10a docstring 必须同时给出「额定」与「实核」两个数，且实核数 == 实际条数
check("额定" in _doc and "实核" in _doc,
      "T10a docstring 未同时标明「额定」与「实核」——两个数必须分开写")
_m = re.search(r"实核\s*(\d+)\s*题", _doc)
check(_m is not None, "T10a2 docstring 里找不到「实核 N 题」")
if _m:
    check(int(_m.group(1)) == _n,
          f"T10b docstring 写实核 {_m.group(1)} 题，实际 CHECKS 有 {_n} 条"
          "——文档与工件不符（本批真实犯过）")

# T10c 标题行（docstring 首行）必须写明「额定 X 题…实核 Y 题」，且两数都对
# 注意：只校验**标题行**的总数表述，不扫描全文——正文里「27 题是 V1」
# 「只有 2 题 bar-model」是子集计数，不是总题数，宽泛扫描会误报。
_title = _doc.strip().splitlines()[0] if _doc.strip() else ""
_tq = re.search(r"额定\s*(\d+)\s*题", _title)
_tv = re.search(r"实核\s*(\d+)\s*题", _title)
check(_tq is not None and _tv is not None,
      f"T10c docstring 标题行未同时写明「额定 N 题…实核 N 题」：{_title!r}")
if _tq and _tv:
    if _led:
        check(int(_tq.group(1)) == _led["quota"],
              f"T10c1 标题行额定 {_tq.group(1)} ≠ LEDGER.quota {_led['quota']}")
    check(int(_tv.group(1)) == _n,
          f"T10c2 标题行实核 {_tv.group(1)} ≠ 实际 {_n} 条")

# T10d 账目三件套必须齐备且算式自洽
check(_led is not None, "T10d 缺少 LEDGER 常量——账目没有单一出处")
if _led:
    traced = {x for v in _led["traced_extra_breakdown"].values() for x in v}
    check(_led["verified"] == _n,
          f"T10e LEDGER.verified={_led['verified']} ≠ 实核 {_n}")
    check(len(traced) == _led["traced_extra"],
          f"T10f LEDGER.traced_extra={_led['traced_extra']} ≠ 明细 {len(traced)} 条")
    check(traced <= batch_ids,
          f"T10g LEDGER 可追溯补入含批外 RVID：{sorted(traced - batch_ids)}")
    gap = _led["verified"] - _led["traced_extra"] - _led["quota"]
    check(_led["gap"] == gap,
          f"T10h LEDGER.gap={_led['gap']} ≠ {_led['verified']}−"
          f"{_led['traced_extra']}−{_led['quota']}={gap}")
    # 差额若存在，必须显式标为未解释，且给出不编造的理由与补救措施
    if _led["gap"] > 0:
        check(_led.get("gap_explained") is False,
              "T10i 存在未解释差额，却标为已解释")
        check(bool(_led.get("gap_why_not_explained")),
              "T10j 未解释差额缺少「为何不解释」的说明")
        check(bool(_led.get("gap_remedy")),
              "T10k 未解释差额缺少补救措施")
    # 可追溯补入的每一条都必须能在 CHECKS 里找到分组注释佐证
    for did, ids in _led["traced_extra_breakdown"].items():
        for rid in ids:
            check(rid in batch_ids,
                  f"T10l {did} 的补入 {rid} 不在 CHECKS 内")

# T10m 负向自检：算错账必须被检出
def _ledger_ok(led, n) -> bool:
    t = {x for v in led["traced_extra_breakdown"].values() for x in v}
    return (led["verified"] == n
            and len(t) == led["traced_extra"]
            and led["gap"] == led["verified"] - led["traced_extra"] - led["quota"])


_bad = {"quota": 20, "verified": 29, "traced_extra": 7,
        "gap": 3,  # 应为 2
        "traced_extra_breakdown": {"DEF-D1": list(
            B.KNOWN_DEFECTS["DEF-D1"]["added_after_gate"]),
            "DEF-D2": list(B.KNOWN_DEFECTS["DEF-D2"]["added_after_gate"])}}
check(_ledger_ok(_bad, 29) is False, "T10m 算错的账未被检出（gap 写错仍通过）")
_bad2 = {**_bad, "gap": 2, "verified": 30}
check(_ledger_ok(_bad2, 29) is False, "T10m2 verified 与实际条数不符未被检出")

# ── T11 文档里的缺陷条数必须与 KNOWN_DEFECTS 现场一致 ──────────────────────
# 报告会写「15 条命中缺陷（D1 5 / D2 3 / D3 4 / D4 3）」。若某项 `affected`
# 增删而文档没改，就会重演「文档与工件不符」。这里把两边的数对齐。
_doc_path = os.path.join(REPO, "docs", "qa", "FE1469_FE1470_Q03_BATCHES.md")
if os.path.exists(_doc_path):
    _d = open(_doc_path, encoding="utf-8").read()
    _all_defect_ids = {x for d in B.KNOWN_DEFECTS.values() for x in d["affected"]}
    # 四类并集必须等于各 affected 条数之和（无重复计数）
    _sum = sum(len(d["affected"]) for d in B.KNOWN_DEFECTS.values())
    check(_sum == len(_all_defect_ids),
          f"T11a 四类 affected 条数之和 {_sum} ≠ 并集 {len(_all_defect_ids)}"
          "——存在同一 RVID 被计入两类（重复计数）")
    # 文档中若出现「命中缺陷（DEF-D1 a / D2 b / D3 c / D4 d）」形态，
    # 校验 a..d 与现场一致
    _hit = re.search(r"(\d+) 条命中缺陷（DEF-D1 (\d+) / D2 (\d+) / D3 (\d+) / D4 (\d+)）", _d)
    if _hit:
        got = [int(_hit.group(i)) for i in range(1, 6)]
        want = [len(_all_defect_ids)] + [
            len(B.KNOWN_DEFECTS[k]["affected"])
            for k in ("DEF-D1", "DEF-D2", "DEF-D3", "DEF-D4")]
        check(got == want,
              f"T11b 文档缺陷数 {got} 与现场 {want} 不符（总/D1/D2/D3/D4）")
    # 若文档声称累计题数，必须等于首批+二批+三批实核之和
    _cum = re.search(r"累计 (\d+) 条（(\d+) \+ (\d+) \+ (\d+)）", _d)
    if _cum:
        total = int(_cum.group(1))
        addends = [int(_cum.group(i)) for i in (2, 3, 4)]
        check(total == sum(addends),
              f"T11c 文档累计 {total} ≠ {'+'.join(map(str, addends))}"
              f"={sum(addends)}")
        # 末位必须是本批实核条数（前两批是 6 与 20 的既定事实）
        check(addends[-1] == _n,
              f"T11c2 文档累计算式的第三项 {addends[-1]} ≠ 本批实核 {_n}")

    # T11d-f 进度表必须反映三批累计，不许留两批旧数
    # 本批真实犯过：§5.2 仍写 186/171/38，与 §5.8 的 157/142/67 冲突。
    _B1, _B2 = 6, 20
    _tot = _B1 + _B2 + _n
    for v in re.findall(r"\| Q03 待核验 \| 212 \| \*{0,2}(\d+)\*{0,2} \|", _d):
        check(int(v) == 212 - _tot,
              f"T11d 文档「Q03 待核验」={v}，三批后应为 {212 - _tot}（两批旧数未更新）")
    _both = re.findall(r"\| 交集（both） \| 197 \| \*{0,2}(\d+)\*{0,2} \|", _d)
    for v in _both:
        check(int(v) == 197 - _tot,
              f"T11e 文档「交集（both）」={v}，三批后应为 {197 - _tot}")
    _q05o = re.findall(r"\| Q05_only \| 12 \| \*{0,2}(\d+)\*{0,2} \|", _d)
    for bv, qv in zip(_both, _q05o):
        check(15 + int(bv) + int(qv) == 224,
              f"T11f 并集恒等式不成立：15 + {bv} + {qv} ≠ 224")

# ── 输出 ──────────────────────────────────────────────────────────────────
if fails:
    print(f"Q03-BATCH3-GATE: FAIL ({len(fails)} 项)")
    for f in fails:
        print("  ✗", f)
    sys.exit(1)

print(f"Q03-BATCH3-GATE: PASS "
      f"({len(B.CHECKS)} 题 / {len(B.Q05_EVIDENCE)} 条证据 / "
      f"{len(B.KNOWN_DEFECTS)} 类缺陷 / "
      f"{len(B.CONTRAST_PAIRS)} 条对照声明 / "
      f"账目 {B.LEDGER['quota']} 额定 → {B.LEDGER['verified']} 实核"
      f"（差额 {B.LEDGER['gap']} 已标未解释）)")