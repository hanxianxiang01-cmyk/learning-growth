#!/usr/bin/env python3
"""FE-1472 第七批：选题清单 ↔ 核验产物 账实核（离线，不连库）

## 与第六批脚本的三处判据变更（都不是改名）

1. **「MATCH + MISMATCH == 总题数」这条断言必须换掉**
   第六批只有两种 verdict，该等式成立。本批引入了四类非 MATCH verdict，
   照抄该等式会立刻报「32+0 ≠ 35」，看起来像账目不平，其实**判据本身过期了**。
   改为：① 总数守恒（各类 verdict 求和 == 总题数）；② 每个 verdict 必须在
   `verdict_definition` 里有定义；③ MATCH / MISMATCH 各自单独对账。
   **这不是放宽**：把「有题未判定」与「有题判成没登记的类别」都拦住了。

2. **新增「题面模板」维度对账**
   本批的核心方法学是「每题必须恰好命中一个登记模板」。若产物里有题
   `stem_template` 为空，说明它没走模板抽取——那条推导的来源就不可追溯。
   同时核：产物里出现的模板 id 必须都在 `q03_batch7.STEM_TEMPLATES` 中登记过
   （防止有人绕过登记表临时加分支）。

3. **新增「非 MATCH 必须带理由」对账**
   本批有 3 题非 MATCH。若不强制理由，这 3 题就会被读成「大概没问题」。
   逐条核：非 MATCH 必须有 `verdict_note`，且 `input_basis` 必须显式写明
   「为什么不能核 / 为什么不算独立推导」。

## 保留第六批的三条硬教训

- **建字典之前先核唯一性**：重复 RVID 会让后行覆盖前行，集合检查看不出。
- **哈希必须同函数**：冻结侧 canonical JSON sha256，对账侧必须同款。
- **两个不同分母不能强行相等**：全族 54 与本批 34 不同口径，
  只能分维度交叉，不能直接比。

## 变异性

`--selftest` 构造八种内存篡改（不写盘），全部检出才 PASS：

  M1 汇总 observation_counts 某类 +1
  M2 逐题删一条 observation（汇总不动）
  M3 名额按 solve_path +1（总量仍 35）
  M4 题干改一个字符（哈希必须变）
  M5 汇总 infeasible +1
  M6 把一个 MATCH 偷偷改成 UNVERIFIABLE_FROM_STEM（**用非 MATCH 洗白**：
     若只有总数守恒，这条改动会被「总和仍 35」放过）
  M7 删掉某题的 stem_template（推导来源不可追溯）
  M8 把 MATCH 改成未登记的 verdict（必须被定义表拦住）

退出码：0 通过 / 1 断言失败 / 2 工件或环境缺失
（rc 区分是硬要求：崩溃曾把 rc=2 误读成"检出成功"）
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


def _check_layout() -> int:
    """REPO 退级要被拦住；**不能只写 assert**（assert 触发即 rc=1，撞「对账失败」码）。"""
    if not os.path.isdir(os.path.join(REPO, "apps")):
        print(f"REPO 推导错误：{REPO}（其下没有 apps/）", file=sys.stderr)
        print(f"  本脚本预期位于 <repo>/scripts/iqc/rt1472/，当前实际在：{HERE}",
              file=sys.stderr)
        print("  退出码 2 = 环境/布局问题，**不是对账失败**。", file=sys.stderr)
        return 2
    return 0


_L = _check_layout()
if _L:
    sys.exit(_L)

QUOTA_PATH = os.path.join(HERE, "batch7_quota_list.json")
RESULT_PATH = os.path.join(REPO, "scripts", "iqc", "runs", "FE1472_q03_batch7.json")

# 非 MATCH verdict 的**模板白名单**：哪一类题面模板才允许产生这个 verdict。
#
# 为什么必须有这张表：E2 那组判据（非 MATCH 需带 verdict_note / 需带对应观察项）
# 只能验证「标签之间自洽」，**验证不了「这个标签适用于这道题」**。实测构造一个
# 「强洗白」——把某道 MATCH 题改成 UNVERIFIABLE_FROM_STEM、同步改汇总、
# 再补一条伪造的 ANSWER_NOT_DERIVABLE_FROM_STEM 观察项——则**所有自洽检查
# 全部通过，0 条报警**。这类改动会把「已核通过的题」洗成「不可核」，
# 从而悄悄降低 MATCH 覆盖率却不被发现。
#
# 判据的结构性依据：`UNVERIFIABLE_FROM_STEM` 的含义是「答案所需信息不在题面」。
# 本批 35 题里，实测只有 `estimation_reference_round_ten` 这一模板满足
# （题面只给参照量 10 与「多得多」，actual=38/expected=40 都只在 config）。
# 其余模板的答案都能从题面抽出，故一律不得记 UNVERIFIABLE。
#
# 若将来真的发现新的不可核题型，必须显式往这里加一项——那次改动是可见的、
# 需要评审的，而不是在产物里悄悄多一个 UNVERIFIABLE。
VERDICT_TEMPLATE_WHITELIST = {
    "UNVERIFIABLE_FROM_STEM": {"estimation_reference_round_ten"},
    "STEM_UNDERDETERMINED": {"pv_constraint_only"},
    "STEM_GIVEN_ANSWER_AGREES": {"pv_goal_direct", "shape_area_only"},
    "STEM_GIVEN_ANSWER_DISAGREES": {"pv_goal_direct", "shape_area_only"},
}

fails: list[str] = []


def _need(path: str, what: str) -> None:
    if not os.path.exists(path):
        print(f"MISSING: {what} → {path}", file=sys.stderr)
        sys.exit(2)


def canon_sha256(obj) -> str:
    """与 freeze_batch7.py::_sha 逐比特一致（canonical JSON）。"""
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _recount(items: list) -> dict:
    out: dict[str, int] = {}
    for it in items:
        for obs in (it.get("semantic_observations") or []):
            code = obs.get("code") if isinstance(obs, dict) else str(obs)
            out[code] = out.get(code, 0) + 1
    return dict(sorted(out.items()))


def _registered_templates() -> set[str]:
    """从核验器源码里取已登记的模板 id 集合（**不复制一份清单**）。

    复制清单的风险：源码加了模板、对账脚本的副本没加，于是产物里出现
    未登记模板却查不出来。这里直接 import 源码，保证同源。
    若源码不可 import，退化为「跳过该检查并显式报告」，**不静默通过**。
    """
    import importlib.util
    p = os.path.join(HERE, "q03_batch7.py")
    if not os.path.exists(p):
        return set()
    spec = importlib.util.spec_from_file_location("_b7_for_ledger", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return {t["id"] for t in m.STEM_TEMPLATES}


def audit(quota: dict, result: dict) -> list[str]:
    """对账主体。返回失败列表（空 = 通过）。

    单独抽成函数，是为了让 `--selftest` 把篡改后的副本喂进来，
    而不是复制一套判据——复制出的第二套判据无法证明第一条真在跑。
    """
    bad: list[str] = []

    def bad_if(cond: bool, msg: str) -> None:
        if cond:
            bad.append(msg)

    q_items = quota.get("items") or []
    r_items = result.get("items") or []
    summary = result.get("summary") or {}
    scope = result.get("scope") or {}
    vdef = result.get("verdict_definition") or {}

    # ── A 台账 ───────────────────────────────────────────────────────────
    bad_if(len(q_items) != quota.get("quota_n"),
           f"选题清单 items={len(q_items)} ≠ 声明 quota_n={quota.get('quota_n')}")
    bad_if(len(q_items) != len(r_items),
           f"额定 {len(q_items)} 题 vs 实核 {len(r_items)} 题，"
           f"差额 {len(r_items) - len(q_items)}")
    bad_if(scope.get("pool_size") != quota.get("pool_size"),
           f"scope.pool_size={scope.get('pool_size')} ≠ 选题清单 "
           f"{quota.get('pool_size')}")
    # 本批是全取批：池内数必须等于额定数（不等于说明题库或基线变了）
    bad_if(quota.get("pool_size") != quota.get("quota_n"),
           f"全取批：pool_size={quota.get('pool_size')} ≠ "
           f"quota_n={quota.get('quota_n')}")

    # ── B 集合（建字典之前先核唯一性）─────────────────────────────────────
    q_rvids = [it.get("rvid") for it in q_items]
    r_rvids = [it.get("rvid") for it in r_items]
    bad_if(len(set(q_rvids)) != len(q_rvids), "选题清单内 RVID 重复")
    bad_if(len(set(r_rvids)) != len(r_rvids), "核验产物内 RVID 重复")
    q_by = {it["rvid"]: it for it in q_items}
    r_by = {it["rvid"]: it for it in r_items}
    bad_if(len(q_by) != len(q_rvids), "选题清单 RVID 建字典后数量变了")
    bad_if(len(r_by) != len(r_rvids), "核验产物 RVID 建字典后数量变了")
    missing = sorted(set(q_by) - set(r_by))
    extra = sorted(set(r_by) - set(q_by))
    bad_if(bool(missing),
           f"选题清单里有 {len(missing)} 题没出现在产物中：{[m[:8] for m in missing]}")
    bad_if(bool(extra),
           f"产物里出现 {len(extra)} 题不在选题清单中：{[e[:8] for e in extra]}")

    # ── C 名额：按 solve_path ────────────────────────────────────────────
    quota_sp = quota.get("quota_by_solve_path") or {}
    by_sp = summary.get("by_solve_path") or {}
    for sp, n in quota_sp.items():
        got = (by_sp.get(sp) or {}).get("n")
        bad_if(got != n, f"名额 {sp}: 声明 {n} 题，实核 {got} 题")
    for sp in by_sp:
        bad_if(sp not in quota_sp, f"实核出现未分配名额的 solve_path：{sp}")
    bad_if(sum((by_sp.get(sp) or {}).get("n") or 0 for sp in quota_sp) != len(r_items),
           "逐 solve_path 实核数之和 ≠ 实核总题数")
    for it in r_items:
        rv = it.get("rvid")
        if rv in q_by:
            bad_if(it.get("solve_path") != q_by[rv].get("solve_path"),
                   f"题目 {str(rv)[:8]}：产物 solve_path={it.get('solve_path')} "
                   f"≠ 选题清单 {q_by[rv].get('solve_path')}")
            bad_if(it.get("renderer") != q_by[rv].get("renderer"),
                   f"题目 {str(rv)[:8]}：产物 renderer={it.get('renderer')} "
                   f"≠ 选题清单 {q_by[rv].get('renderer')}")
            bad_if(it.get("semantic_family") != q_by[rv].get("semantic_family"),
                   f"题目 {str(rv)[:8]}：产物 family={it.get('semantic_family')} "
                   f"≠ 选题清单 {q_by[rv].get('semantic_family')}")

    # ── D 观察项 ─────────────────────────────────────────────────────────
    recount = _recount(r_items)
    stated = summary.get("observation_counts") or {}
    for code in sorted(set(stated) | set(recount)):
        s, c = stated.get(code), recount.get(code)
        bad_if(s != c,
               f"观察项 {code}: 汇总写 {s}，逐题重算 {c}"
               + ("（汇总虚报，逐题一条都没有）" if c is None else "")
               + ("（逐题有但汇总漏登记）" if s is None else ""))
    for it in r_items:
        for obs in (it.get("semantic_observations") or []):
            if not isinstance(obs, dict):
                bad.append(f"题目 {str(it.get('rvid'))[:8]}：观察项不是对象，无法追溯")
                continue
            if not obs.get("why") or not obs.get("evidence"):
                bad.append(f"题目 {str(it.get('rvid'))[:8]} 的观察项 "
                           f"{obs.get('code')} 缺 why/evidence，无法独立复核")

    # ── E verdict 体系（**本批判据变更的核心**）──────────────────────────
    bad_if(not vdef, "verdict_definition 缺失——非 MATCH 的类别没有定义，"
                     "读者无法知道「非 MATCH」是什么意思")
    from collections import Counter
    vc_actual = Counter(it.get("verdict") for it in r_items)
    vc_stated = summary.get("verdict_counts") or {}
    for v in sorted(set(vc_actual) | set(vc_stated), key=str):
        a, s = vc_actual.get(v, 0), vc_stated.get(v, 0)
        bad_if(a != s, f"verdict {v}: 汇总写 {s}，逐题重算 {a}")
    # 每个 verdict 必须在定义表里
    for v in vc_actual:
        bad_if(v not in vdef,
               f"产物出现未定义的 verdict：{v}（必须在 verdict_definition 登记）")
    # **总数守恒**（替代第六批的 match+mismatch==total）
    bad_if(sum(vc_actual.values()) != len(r_items),
           f"verdict 各类求和 {sum(vc_actual.values())} ≠ 总题数 {len(r_items)}"
           f"（有题未判定）")
    bad_if(summary.get("match") != vc_actual.get("MATCH", 0),
           f"MATCH 数：汇总 {summary.get('match')} ≠ 逐题 "
           f"{vc_actual.get('MATCH', 0)}")
    bad_if(summary.get("mismatch") != vc_actual.get("MISMATCH", 0),
           f"MISMATCH 数：汇总 {summary.get('mismatch')} ≠ 逐题 "
           f"{vc_actual.get('MISMATCH', 0)}")
    bad_if(summary.get("not_match_total") != len(r_items) - vc_actual.get("MATCH", 0),
           f"not_match_total={summary.get('not_match_total')} ≠ "
           f"{len(r_items) - vc_actual.get('MATCH', 0)}")

    # ── E2 非 MATCH 必须带理由（否则会被读成「大概没问题」）───────────────
    for it in r_items:
        v = it.get("verdict")
        if v == "MATCH":
            continue
        bad_if(not it.get("verdict_note"),
               f"题目 {str(it.get('rvid'))[:8]}：verdict={v} 但无 verdict_note"
               f"（非 MATCH 必须写明理由）")
        bad_if(not (it.get("input_basis") or "").strip(),
               f"题目 {str(it.get('rvid'))[:8]}：verdict={v} 但 input_basis 为空"
               f"（无法判断推导依据）")
        # 非 MATCH 的 computed 与 stated 关系必须与类别相符
        c, s = it.get("computed"), it.get("stated_answer")
        if v == "STEM_GIVEN_ANSWER_AGREES":
            bad_if(abs(float(c) - float(str(s).strip())) >= 1e-9,
                   f"题目 {str(it.get('rvid'))[:8]}：记 STEM_GIVEN_ANSWER_AGREES "
                   f"但 computed={c} ≠ stated={s!r}")
        if v == "STEM_GIVEN_ANSWER_DISAGREES":
            bad_if(abs(float(c) - float(str(s).strip())) < 1e-9,
                   f"题目 {str(it.get('rvid'))[:8]}：记 STEM_GIVEN_ANSWER_DISAGREES "
                   f"但 computed={c} == stated={s!r}（应记 AGREES）")
        if v == "UNVERIFIABLE_FROM_STEM":
            # 必须真的存在「信息不在题面」的证据，不能只贴个标签
            codes = {o.get("code") for o in (it.get("semantic_observations") or [])
                     if isinstance(o, dict)}
            bad_if("ANSWER_NOT_DERIVABLE_FROM_STEM" not in codes,
                   f"题目 {str(it.get('rvid'))[:8]}：记 UNVERIFIABLE_FROM_STEM "
                   f"但未登记 ANSWER_NOT_DERIVABLE_FROM_STEM 观察项"
                   f"（结论游离在观察项之外）")

    # ── F 题面模板（本批新增维度）─────────────────────────────────────────
    #
    # F2 是**结构性**判据：verdict 必须与题面模板相容。E2 那组只知道
    # 「非 MATCH 要带理由」，拦不住「把 MATCH 洗成不可核 + 补一条伪造观察项」。
    # 实测过：那种强洗白会让 E2 全部通过、0 条报警。F2 是唯一能拦住它的判据。
    for it in r_items:
        v = it.get("verdict")
        allowed = VERDICT_TEMPLATE_WHITELIST.get(v)
        if allowed is not None:
            t = it.get("stem_template")
            bad_if(t not in allowed,
                   f"题目 {str(it.get('rvid'))[:8]}：verdict={v} 但模板 "
                   f"{t} 不在该类允许的模板集 {sorted(allowed)} 内"
                   f"（verdict 与题面模板不相容——可能把已核题洗成非 MATCH）")

    reg = _registered_templates()
    if not reg:
        bad.append("q03_batch7.py 里的 STEM_TEMPLATES 取不到——"
                   "无法核对模板登记（**不静默跳过**）")
    for it in r_items:
        t = it.get("stem_template")
        bad_if(not t,
               f"题目 {str(it.get('rvid'))[:8]}：stem_template 为空"
               f"（推导未走模板抽取，来源不可追溯）")
        if reg and t:
            bad_if(t not in reg,
                   f"题目 {str(it.get('rvid'))[:8]}：stem_template={t} "
                   f"不在 STEM_TEMPLATES 登记表中（绕过登记表加分支）")
    # 产物声明的模板使用统计必须与逐题重算一致
    tpl_stated = (result.get("template_discipline") or {}).get("templates_used") or {}
    tpl_actual = dict(Counter(it.get("stem_template") for it in r_items))
    for t in sorted(set(tpl_stated) | set(tpl_actual), key=str):
        s, a = tpl_stated.get(t, 0), tpl_actual.get(t, 0)
        bad_if(s != a, f"模板使用统计 {t}: 汇总写 {s}，逐题重算 {a}")
    # 登记的模板都必须被用到（登记了却不用的模板=装饰品；本批是全取批）
    if reg:
        unused = sorted(reg - {it.get("stem_template") for it in r_items})
        bad_if(bool(unused),
               f"登记了但本批一题都没用到的模板：{unused}"
               f"（全取批下这类模板要么多余、要么漏了题型）")

    # ── G 过程约束 ───────────────────────────────────────────────────────
    declared = 0
    for it in r_items:
        ee = it.get("evidence_enforcement") or {}
        pc = ee.get("process_constraint")
        has = pc not in (None, {}, [])
        declared += 1 if has else 0
        bad_if(bool(ee.get("enforced_by_backend")) != has,
               f"题目 {str(it.get('rvid'))[:8]}：enforced_by_backend 与 "
               f"process_constraint 不一致")
        codes = {o.get("code") for o in (it.get("semantic_observations") or [])
                 if isinstance(o, dict)}
        if not has:
            ok_codes = {"NO_PROCESS_VALIDATOR_FOR_RENDERER",
                        "EVIDENCE_DECLARED_BUT_NOT_ENFORCED",
                        "ANSWER_NOT_DERIVABLE_FROM_STEM"}
            bad_if(not (codes & ok_codes),
                   f"题目 {str(it.get('rvid'))[:8]}：无 process_constraint，"
                   f"却未登记任何过程校验缺失观察项（codes={sorted(codes)}）")
        if has:
            bad_if("PROCESS_CONSTRAINT_ENABLED" not in codes,
                   f"题目 {str(it.get('rvid'))[:8]}：process_constraint 非空，"
                   f"却未登记 PROCESS_CONSTRAINT_ENABLED")
    bad_if(summary.get("process_constraint_effective") != declared,
           f"process_constraint 生效数：汇总写 "
           f"{summary.get('process_constraint_effective')}，逐题重算 {declared}")

    # ── H 全族覆盖（两族）────────────────────────────────────────────────
    fcov = scope.get("family_coverage") or {}
    fams = ("construct_constraint", "open_estimate")
    for fam in fams:
        c = fcov.get(fam)
        if not c:
            bad.append(f"scope.family_coverage 缺 {fam}——"
                       f"本批的两族清零口径依赖该统计")
            continue
        wt = c.get("with_process_constraint") or 0
        wo = c.get("without_process_constraint") or 0
        bad_if(wt + wo != c.get("family_total"),
               f"{fam}：{wt}+{wo} ≠ family_total {c.get('family_total')}")
        br = c.get("by_renderer") or {}
        # 逐 renderer 与本批交叉核对（**两个不同分母，只能分维度比**）
        batch_by_r: dict[str, dict] = {}
        for it in r_items:
            if it.get("semantic_family") != fam:
                continue
            r = it.get("renderer")
            pc = (it.get("evidence_enforcement") or {}).get("process_constraint")
            b = batch_by_r.setdefault(r, {"n": 0, "with_pc": 0})
            b["n"] += 1
            if pc not in (None, {}, []):
                b["with_pc"] += 1
        for r, b in batch_by_r.items():
            f = br.get(r)
            if f is None:
                bad.append(f"{fam} 含 renderer {r}，但全族覆盖统计里没有它")
                continue
            if (f.get("with_pc") or 0) == 0:
                bad_if(b["with_pc"] != 0,
                       f"{fam}/{r}：全族声明 0 题带 pc，"
                       f"但本批 {b['with_pc']}/{b['n']} 带上（矛盾）")
            elif (f.get("with_pc") or 0) == (f.get("n") or 0):
                bad_if(b["with_pc"] != b["n"],
                       f"{fam}/{r}：全族声明全部带，"
                       f"但本批只有 {b['with_pc']}/{b['n']} 带")
        # 本批核验的题数不能超过全族总量
        bad_if(len(batch_by_r) and
               sum(b["n"] for b in batch_by_r.values()) > c.get("family_total"),
               f"{fam}：本批题数超过全族总量 {c.get('family_total')}")

    # ── I config ↔ 题面一致性 ────────────────────────────────────────────
    inconsistent = sum(1 for it in r_items
                       if (it.get("config_vs_stem") or {}).get("status")
                       != "CONSISTENT")
    bad_if(summary.get("config_inconsistent") != inconsistent,
           f"config 不一致题数：汇总写 {summary.get('config_inconsistent')}，"
           f"逐题重算 {inconsistent}")

    # ── J 输入绑定哈希 ───────────────────────────────────────────────────
    for it in r_items:
        rv = it.get("rvid")
        bind = (it.get("input_binding") or {}).get("stem_sha256")
        real = canon_sha256(it.get("stem") or "")
        bad_if(bind != real,
               f"题目 {str(rv)[:8]}：stem_sha256 与现场重算不符"
               f"（题干被改过但哈希没跟着变）")
        if rv in q_by:
            frozen = q_by[rv].get("stem_sha256")
            bad_if(frozen and frozen != real,
                   f"题目 {str(rv)[:8]}：产物的题干与选题清单冻结时不是同一版")
            fb = (q_by[rv].get("ui_schema_sha256"))
            rb = (it.get("input_binding") or {}).get("ui_schema_sha256")
            bad_if(fb and rb and fb != rb,
                   f"题目 {str(rv)[:8]}：ui_schema 与选题清单冻结时不是同一版")

    # ── K 可完成性维度 ───────────────────────────────────────────────────
    infeas_rows = [it for it in r_items
                   if (it.get("feasibility") or {}).get("verdict")
                   == "INFEASIBLE_ON_COMPONENT"]
    bad_if(summary.get("infeasible_on_component") != len(infeas_rows),
           f"可完成性汇总写 {summary.get('infeasible_on_component')}，"
           f"逐题重算 {len(infeas_rows)}")
    for it in r_items:
        f = it.get("feasibility")
        if not f:
            continue
        codes = {o.get("code") for o in (it.get("semantic_observations") or [])
                 if isinstance(o, dict)}
        if f.get("verdict") == "INFEASIBLE_ON_COMPONENT":
            bad_if("INFEASIBLE_ON_COMPONENT" not in codes,
                   f"题目 {str(it.get('rvid'))[:8]}：feasibility 判 INFEASIBLE，"
                   f"却未登记 INFEASIBLE_ON_COMPONENT 观察项")
            bad_if(f.get("fits_component_board") is not False
                   and f.get("area_reachable_on_component") is not False,
                   f"题目 {str(it.get('rvid'))[:8]}：判 INFEASIBLE 但"
                   f"fits/area_reachable 都不是 False（自相矛盾）")
        if ("INFEASIBLE_ON_COMPONENT" in codes
                and f.get("verdict") != "INFEASIBLE_ON_COMPONENT"):
            bad.append(f"题目 {str(it.get('rvid'))[:8]}：登记了 INFEASIBLE 观察项，"
                       f"但 feasibility.verdict={f.get('verdict')}")
        # 只给面积的题：必须走 FEASIBLE_AREA_ONLY，不得混进 FEASIBLE
        if it.get("stem_template") == "shape_area_only":
            bad_if(f.get("verdict") != "FEASIBLE_AREA_ONLY",
                   f"题目 {str(it.get('rvid'))[:8]}：shape_area_only 模板"
                   f"应判 FEASIBLE_AREA_ONLY，实测 {f.get('verdict')}")

    # ── L 推导可复核 ────────────────────────────────────────────────────
    for it in r_items:
        d = it.get("derivation") or {}
        bad_if(not d.get("expr"),
               f"题目 {str(it.get('rvid'))[:8]}：derivation.expr 为空")
        for ec in (d.get("encoding_constants") or []):
            bad_if(ec.get("purpose") == "UNCLASSIFIED",
                   f"题目 {str(it.get('rvid'))[:8]}：表达式含未分诊的题干外数字 "
                   f"{ec.get('value')}")

    return bad


def report(quota: dict, result: dict, tag: str = "BATCH7-LEDGER") -> int:
    bad = audit(quota, result)
    summary = result.get("summary") or {}
    r_items = result.get("items") or []
    scope = result.get("scope") or {}
    fcov = scope.get("family_coverage") or {}
    print(f"\n{tag}: {len(r_items)} 题 / {summary.get('match')} MATCH / "
          f"{summary.get('mismatch')} MISMATCH / "
          f"{summary.get('not_match_total')} 非 MATCH")
    print(f"  verdict 分布：{summary.get('verdict_counts')}")
    print(f"  语义族：{scope.get('families')}")
    for fam, c in sorted(fcov.items()):
        print(f"    {fam:22s} 全族 {c.get('family_total')}；"
              f"带 pc {c.get('with_process_constraint')}")
    print(f"  观察项重算：{_recount(r_items)}")
    print(f"  模板使用：{(result.get('template_discipline') or {}).get('templates_used')}")
    bec = sum(1 for it in r_items
              if (it.get("feasibility") or {}).get("verdict")
              == "INFEASIBLE_ON_COMPONENT")
    print(f"  题面不可完成：{bec} 题")
    if bad:
        for b in bad:
            print(f"  ✗ {b}")
        return 1
    print("  账实相符。")
    return 0


def selftest(quota: dict, result: dict) -> int:
    """八种篡改必须全部检出。每种单独跑一遍 audit()。"""
    print("\n── 变异性自证（内存篡改，不写盘）──")
    caught = 0
    total = 9

    def check(n: int, name: str, q, r) -> int:
        if audit(q, r):
            print(f"  ✓ M{n} {name}已检出")
            return 1
        print(f"  ✗ M{n} {name}**未被检出**")
        return 0

    # M1 汇总虚报
    m1 = copy.deepcopy(result)
    oc = m1["summary"]["observation_counts"]
    k = sorted(oc)[0]
    oc[k] += 1
    caught += check(1, f"汇总虚报（{k} +1）", quota, m1)

    # M2 逐题删一条 observation
    m2 = copy.deepcopy(result)
    victim = next((it for it in m2["items"] if it.get("semantic_observations")), None)
    if victim is None:
        print("  ✗ M2 无法构造：没有任何题带 observation")
    else:
        victim["semantic_observations"].pop(0)
        caught += check(2, f"逐题删一条（{str(victim.get('rvid'))[:8]}）",
                        quota, m2)

    # M3 名额按 solve_path +1
    m3 = copy.deepcopy(quota)
    kk = sorted(m3["quota_by_solve_path"])[0]
    m3["quota_by_solve_path"][kk] += 1
    caught += check(3, f"名额篡改（{kk} +1）", m3, result)

    # M4 题干改一个字符
    m4 = copy.deepcopy(result)
    m4["items"][0]["stem"] = (m4["items"][0].get("stem") or "") + "。"
    caught += check(4, "题干篡改（哈希不符）", quota, m4)

    # M5 可完成性汇总虚报
    m5 = copy.deepcopy(result)
    m5["summary"]["infeasible_on_component"] += 1
    caught += check(5, "可完成性汇总虚报", quota, m5)

    # M6 **把 MATCH 偷偷改成 UNVERIFIABLE_FROM_STEM**
    #    这是本批最需要防的一种：只查「总数守恒」会放过它，
    #    因为总和仍是 35。必须靠「非 MATCH 需带对应观察项」拦住。
    m6 = copy.deepcopy(result)
    tgt = next((it for it in m6["items"] if it.get("verdict") == "MATCH"
                and it.get("stem_template") != "estimation_reference_round_ten"),
               None)
    if tgt is None:
        print("  ✗ M6 无法构造：没有可改的 MATCH 题")
    else:
        # 先同步改汇总，使「总数守恒」这条判据看不出问题——模拟真实洗白
        m6["summary"]["verdict_counts"]["MATCH"] -= 1
        m6["summary"]["verdict_counts"]["UNVERIFIABLE_FROM_STEM"] = (
            m6["summary"]["verdict_counts"].get("UNVERIFIABLE_FROM_STEM", 0) + 1)
        m6["summary"]["match"] -= 1
        m6["summary"]["not_match_total"] += 1
        tgt["verdict"] = "UNVERIFIABLE_FROM_STEM"
        caught += check(6, f"MATCH 洗白成 UNVERIFIABLE（{str(tgt.get('rvid'))[:8]}）",
                        quota, m6)

    # M7 删掉某题的 stem_template
    m7 = copy.deepcopy(result)
    m7["items"][0]["stem_template"] = None
    caught += check(7, "删 stem_template（来源不可追溯）", quota, m7)

    # M8 改成未登记的 verdict
    m8 = copy.deepcopy(result)
    m8["items"][0]["verdict"] = "LOOKS_FINE"
    caught += check(8, "未登记 verdict（LOOKS_FINE）", quota, m8)

    # M9 **强洗白**：改 verdict + 同步汇总 + 补伪造观察项 + 改 verdict_note。
    #
    # 这条是本轮真实发现的漏洞：加 F2（模板白名单）之前，这种改法能让
    # **所有自洽检查全部通过、0 条报警**——因为 E2 那组只验证「标签之间是否
    # 自洽」，验证不了「这个标签是否适用于这道题」。
    # 危害：把已核通过的 MATCH 题洗成「不可核」，MATCH 覆盖率会悄悄下降。
    # 修法不是加强自洽检查（那永远拦不住），而是加**结构性**判据 F2：
    # verdict 必须与题面模板相容。M9 固化它，防以后退化。
    m9 = copy.deepcopy(result)
    t9 = next((it for it in m9["items"]
               if it.get("verdict") == "MATCH"
               and it.get("stem_template") != "estimation_reference_round_ten"),
              None)
    if t9 is None:
        print("  ✗ M9 无法构造：没有可洗白的 MATCH 题")
    else:
        t9["verdict"] = "UNVERIFIABLE_FROM_STEM"
        t9["verdict_note"] = m9["verdict_definition"]["UNVERIFIABLE_FROM_STEM"]
        t9["semantic_observations"].append({
            "code": "ANSWER_NOT_DERIVABLE_FROM_STEM", "severity": "risk",
            "why": "（自证用伪造）", "evidence": "（自证用伪造）",
            "consequence": "（自证用伪造）", "not_concluded": "（自证用伪造）"})
        vcv = m9["summary"]["verdict_counts"]
        vcv["MATCH"] -= 1
        vcv["UNVERIFIABLE_FROM_STEM"] = vcv.get("UNVERIFIABLE_FROM_STEM", 0) + 1
        m9["summary"]["match"] -= 1
        m9["summary"]["not_match_total"] += 1
        m9["summary"]["observation_counts"]["ANSWER_NOT_DERIVABLE_FROM_STEM"] = (
            m9["summary"]["observation_counts"]
            .get("ANSWER_NOT_DERIVABLE_FROM_STEM", 0) + 1)
        caught += check(9, f"强洗白 MATCH→UNVERIFIABLE（{str(t9.get('rvid'))[:8]}）",
                        quota, m9)

    print(f"\nBATCH7-LEDGER-SELFTEST: "
          f"{'PASS' if caught == total else 'FAIL'}（{caught}/{total} 检出）")
    return 0 if caught == total else 1


def main() -> int:
    _need(QUOTA_PATH, "第七批选题清单")
    _need(RESULT_PATH, "第七批核验产物")
    with open(QUOTA_PATH, encoding="utf-8") as f:
        quota = json.load(f)
    with open(RESULT_PATH, encoding="utf-8") as f:
        result = json.load(f)

    if "--selftest" in sys.argv:
        return selftest(quota, result)

    return report(quota, result)


if __name__ == "__main__":
    sys.exit(main())