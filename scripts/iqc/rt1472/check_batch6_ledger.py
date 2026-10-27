#!/usr/bin/env python3
"""FE-1472 第六批：选题清单 ↔ 核验产物 账实核（离线，不连库）

## 与第五批脚本的三处差别（都不是改名，是判据本身变了）

1. **名额按 solve_path 核，不再按 renderer**
   第六批的选题规则是「四类 solve_path 各 5 题」。若仍按 renderer 核，
   `pattern-board` 会被拆成 numeric_exact 1 + sequence_order 3，
   而 quota 里写的是 renderer 总数——两边根本不同维度。
   `quota_by_solve_path` 与 `summary.by_solve_path` 必须逐类相等。

2. **新增「题面可完成性」对账**
   本批引入 `feasibility` 维度（答案算得出、界面画不出）。它有三个最容易被
   写成漂亮话的失败模式，必须逐条核：
     a) 汇总写 `infeasible_on_component: 1`，但逐题 `feasibility.verdict`
        一条都不是 INFEASIBLE；
     b) 逐题判了 INFEASIBLE，却没登记对应观察项 `INFEASIBLE_ON_COMPONENT`
        （结论游离在观察项之外，读者只看观察项会漏掉）；
     c) 判 INFEASIBLE 的题**没有独立推导结论**（MATCH/MISMATCH 缺失）——
        该维度不能替代答案核验。

3. **新增「全族 process_constraint 覆盖」对账**
   上一轮笔记记的是「54 题全部带 process_constraint」，本批实核 20 题只有 17。
   这类「笔记与现场不符」只能靠现场重算发现，故把
   `family_scope.process_constraint_coverage.with_process_constraint`
   与 `without_process_constraint` + 逐题 `evidence_enforcement` 三方对齐。

## 保留第五批的两条硬教训

- **建字典之前先核唯一性**：`{it["rvid"]: it}` 会让重复 RVID 后行覆盖前行，
  而集合检查看不出异常。
- **哈希必须同函数**：冻结侧用 canonical JSON 的 sha256，
  对账侧若写 `sha256(stem.encode())` 会带不带引号的差异，20 题全报不符。

## 变异性

`--selftest` 构造六种内存篡改（不写盘），全部检出才 PASS：

  M1 汇总 observation_counts 某类 +1
  M2 逐题删一条 observation（汇总不动）
  M3 名额按 solve_path +1（总量仍 20）
  M4 题干改一个字符（哈希必须变）
  M5 汇总 infeasible +1（可完成性汇总虚报）
  M6 覆盖统计的 with_process_constraint 改错（笔记与现场不符）

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
    """REPO 退级要被拦住（`scripts/scripts/` 已经踩过两次）。

    但**不能只写 `assert`**：assert 触发时进程以 1 结束，与「1 = 对账失败」
    撞码。直接解压交付件（扁平目录）跑就会 rc=1，被误读成账目不平。
    2026-10-23 统一改为：布局不对 → 2（环境问题），对账不平 → 1。
    """
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

QUOTA_PATH = os.path.join(HERE, "batch6_quota_list.json")
RESULT_PATH = os.path.join(REPO, "scripts", "iqc", "runs", "FE1472_q03_batch6.json")

fails: list[str] = []


def fail(msg: str) -> None:
    fails.append(msg)
    print(f"  ✗ {msg}")


def _need(path: str, what: str) -> None:
    if not os.path.exists(path):
        print(f"MISSING: {what} → {path}", file=sys.stderr)
        sys.exit(2)


def canon_sha256(obj) -> str:
    """与 freeze_batch6.py::_sha 逐比特一致（canonical JSON）。"""
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


def audit(quota: dict, result: dict) -> list[str]:
    """对账主体。返回失败列表（空 = 通过）。

    单独抽成函数，是为了让 `--selftest` 能把篡改后的副本喂进来，
    而不是复制一套判据——复制出来的第二套判据无法证明第一条真在跑。
    """
    bad: list[str] = []

    def bad_if(cond: bool, msg: str) -> None:
        if cond:
            bad.append(msg)

    q_items = quota.get("items") or []
    r_items = result.get("items") or []
    summary = result.get("summary") or {}
    fscope = result.get("family_scope") or {}
    fdim = result.get("feasibility_dimension") or {}

    # ── A 台账 ───────────────────────────────────────────────────────────
    bad_if(len(q_items) != quota.get("quota_n"),
           f"选题清单 items={len(q_items)} ≠ 声明 quota_n={quota.get('quota_n')}")
    bad_if(fscope.get("verified_here") != len(r_items),
           f"family_scope.verified_here={fscope.get('verified_here')} "
           f"≠ 实际核验 {len(r_items)} 题")
    bad_if(fscope.get("total_in_family") is None,
           "family_scope.total_in_family 缺失——本次核验的族总量未声明")
    bad_if(fscope.get("pool_size") != quota.get("pool_size"),
           f"family_scope.pool_size={fscope.get('pool_size')} "
           f"≠ 选题清单 {quota.get('pool_size')}")
    # 第四批踩过的坑：额定 20、实核 29，差额无法反查
    bad_if(len(q_items) != len(r_items),
           f"额定 {len(q_items)} 题 vs 实核 {len(r_items)} 题，"
           f"差额 {len(r_items) - len(q_items)}")

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

    # ── C 名额：**按 solve_path**（本批与第五批的不同维度）───────────────
    quota_sp = quota.get("quota_by_solve_path") or {}
    by_sp = summary.get("by_solve_path") or {}
    for sp, n in quota_sp.items():
        got = (by_sp.get(sp) or {}).get("n")
        bad_if(got != n, f"名额 {sp}: 声明 {n} 题，实核 {got} 题")
    for sp in by_sp:
        bad_if(sp not in quota_sp, f"实核出现未分配名额的 solve_path：{sp}")
    bad_if(sum((by_sp.get(sp) or {}).get("n") or 0 for sp in quota_sp) != len(r_items),
           "逐 solve_path 实核数之和 ≠ 实核总题数")
    # 逐题的 solve_path 必须与该题在选题清单里的一致（防产物改标签）
    for it in r_items:
        rv = it.get("rvid")
        if rv in q_by:
            bad_if(it.get("solve_path") != q_by[rv].get("solve_path"),
                   f"题目 {str(rv)[:8]}：产物 solve_path="
                   f"{it.get('solve_path')} ≠ 选题清单 "
                   f"{q_by[rv].get('solve_path')}")

    # ── D 观察项（本项目最高价值的对账）───────────────────────────────────
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

    # ── E 过程校验声明（现场重算，不写死）─────────────────────────────────
    declared = 0
    for it in r_items:
        ee = it.get("evidence_enforcement") or {}
        pc = ee.get("process_constraint")
        has = pc not in (None, {}, [])
        declared += 1 if has else 0
        bad_if(bool(ee.get("enforced_by_backend")) != has,
               f"题目 {str(it.get('rvid'))[:8]}：enforced_by_backend 与 "
               f"process_constraint 不一致")
        # 没有 process_constraint 时，必须登记「该 renderer 无校验器」或
        # 「证据已声明但未启用」之一——不能静默什么都不写。
        if not has:
            codes = {o.get("code") for o in (it.get("semantic_observations") or [])
                     if isinstance(o, dict)}
            ok_codes = {"NO_PROCESS_VALIDATOR_FOR_RENDERER",
                        "EVIDENCE_DECLARED_BUT_NOT_ENFORCED"}
            bad_if(not (codes & ok_codes),
                   f"题目 {str(it.get('rvid'))[:8]}：无 process_constraint，"
                   f"却未登记任何过程校验缺失观察项（codes={sorted(codes)}）")
        # 有 process_constraint 就必须登记「已启用」
        if has:
            codes = {o.get("code") for o in (it.get("semantic_observations") or [])
                     if isinstance(o, dict)}
            bad_if("PROCESS_CONSTRAINT_ENABLED" not in codes,
                   f"题目 {str(it.get('rvid'))[:8]}：process_constraint 非空，"
                   f"却未登记 PROCESS_CONSTRAINT_ENABLED")
    bad_if(summary.get("process_constraint_declared") != declared,
           f"process_constraint 声明数：汇总写 "
           f"{summary.get('process_constraint_declared')}，逐题重算 {declared}")

    # ── E2 全族覆盖对齐 ──────────────────────────────────────────────────
    #
    # **不能把「全族 with_process_constraint」直接和「本批逐题重算」比**：
    # 前者是 54 题口径（37），后者是 20 题口径（17），两者本来就不同。
    # 首版这么比，立刻报「37 ≠ 17」——是判据错，不是数据错
    # （项目铁律：判据写错时先怀疑判据）。正确做法是**分维度交叉核对**：
    #   ① 全族内部自洽：with + without == family_total
    #   ② 与本批口径的族总量一致
    #   ③ 逐 renderer 交叉：全族声明「该 renderer 0 题带 pc」→ 本批同类必须 0；
    #      全族声明「全部带」→ 本批同类也须全带
    # ③ 才是真正有区分力的对照，①② 只是防统计自相矛盾。
    cov = fscope.get("process_constraint_coverage") or {}
    if not cov:
        bad.append("family_scope.process_constraint_coverage 缺失——"
                   "本批结论依赖该缺口，不能只在正文里说")
    else:
        wt = cov.get("with_process_constraint") or 0
        wo = cov.get("without_process_constraint") or 0
        bad_if(wt + wo != cov.get("family_total"),
               f"全族覆盖 {wt}+{wo} ≠ family_total {cov.get('family_total')}")
        bad_if(cov.get("family_total") != fscope.get("total_in_family"),
               f"全族覆盖 family_total={cov.get('family_total')} ≠ "
               f"family_scope.total_in_family={fscope.get('total_in_family')}")
        br = cov.get("by_renderer") or {}
        # 逐 renderer 交叉核对（本批 vs 全族）
        batch_by_r: dict[str, dict] = {}
        for it in r_items:
            r = it.get("renderer")
            pc = (it.get("evidence_enforcement") or {}).get("process_constraint")
            b = batch_by_r.setdefault(r, {"n": 0, "with_pc": 0})
            b["n"] += 1
            if pc not in (None, {}, []):
                b["with_pc"] += 1
        for r, b in batch_by_r.items():
            fam = br.get(r)
            if fam is None:
                bad.append(f"本批含 renderer {r}，但全族覆盖统计里没有它"
                           f"（覆盖统计漏了类别）")
                continue
            if (fam.get("with_pc") or 0) == 0:
                bad_if(b["with_pc"] != 0,
                       f"renderer {r}：全族声明 0 题带 process_constraint，"
                       f"但本批 {b['with_pc']}/{b['n']} 题带（矛盾的现场）")
            elif (fam.get("with_pc") or 0) == (fam.get("n") or 0):
                bad_if(b["with_pc"] != b["n"],
                       f"renderer {r}：全族声明全部带 process_constraint"
                       f"（{fam.get('with_pc')}/{fam.get('n')}），"
                       f"但本批只有 {b['with_pc']}/{b['n']} 题带")
        # 缺口 renderer 列表必须与 by_renderer 里 with_pc==0 的项一致
        zero = sorted(r for r, v in br.items() if (v.get("with_pc") or 0) == 0)
        bad_if(zero != sorted(cov.get("renderers_without_any_pc") or []),
               f"缺口 renderer 列表 {cov.get('renderers_without_any_pc')} "
               f"≠ by_renderer 中 with_pc==0 的 {zero}")
        bad_if(not cov.get("backend_supported_modes"),
               "全族覆盖未记录后端支持的 mode 列表——"
               "无法证明缺口是「能力缺口」而非「漏配」")
        bad_if(wo and not cov.get("why_the_gap"),
               "有缺口但未记录 why_the_gap（缺口原因）")

    # ── F 题面↔config 一致性计数 ─────────────────────────────────────────
    inconsistent = sum(1 for it in r_items
                       if (it.get("config_vs_stem") or {}).get("status") != "CONSISTENT")
    bad_if(summary.get("config_inconsistent") != inconsistent,
           f"config 不一致题数：汇总写 {summary.get('config_inconsistent')}，"
           f"逐题重算 {inconsistent}")

    # ── G 输入绑定哈希 ───────────────────────────────────────────────────
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

    # ── H 可完成性维度（本批新增，三个失败模式逐一核）────────────────────
    infeas_rows = [it for it in r_items
                   if (it.get("feasibility") or {}).get("verdict")
                   == "INFEASIBLE_ON_COMPONENT"]
    bad_if(summary.get("infeasible_on_component") != len(infeas_rows),
           f"可完成性汇总写 {summary.get('infeasible_on_component')}，"
           f"逐题重算 {len(infeas_rows)}")
    bad_if(fdim.get("infeasible_count") != len(infeas_rows),
           f"feasibility_dimension.infeasible_count="
           f"{fdim.get('infeasible_count')} ≠ 逐题重算 {len(infeas_rows)}")
    # a) 汇总说有、逐题必须有
    for it in r_items:
        f = it.get("feasibility")
        if not f:
            continue
        codes = {o.get("code") for o in (it.get("semantic_observations") or [])
                 if isinstance(o, dict)}
        if f.get("verdict") == "INFEASIBLE_ON_COMPONENT":
            # b) 判了不可完成，必须有对应观察项
            bad_if("INFEASIBLE_ON_COMPONENT" not in codes,
                   f"题目 {str(it.get('rvid'))[:8]}：feasibility 判 INFEASIBLE，"
                   f"却未登记 INFEASIBLE_ON_COMPONENT 观察项"
                   f"（结论游离在观察项之外）")
            # c) 不可完成不等于不算答案——仍必须有判定
            bad_if(it.get("verdict") not in ("MATCH", "MISMATCH"),
                   f"题目 {str(it.get('rvid'))[:8]}：判 INFEASIBLE 但答案判定缺失"
                   f"（可完成性不能替代答案核验）")
            # 判据内部自洽：不能既说题面自洽又说能放进组件
            bad_if(f.get("fits_component_board") is not False,
                   f"题目 {str(it.get('rvid'))[:8]}：判 INFEASIBLE 但 "
                   f"fits_component_board={f.get('fits_component_board')}（自相矛盾）")
    # 反向：没判 INFEASIBLE 的题不得挂 INFEASIBLE 观察项
    for it in r_items:
        codes = {o.get("code") for o in (it.get("semantic_observations") or [])
                 if isinstance(o, dict)}
        f = it.get("feasibility") or {}
        if "INFEASIBLE_ON_COMPONENT" in codes and f.get("verdict") != "INFEASIBLE_ON_COMPONENT":
            bad.append(f"题目 {str(it.get('rvid'))[:8]}：登记了 INFEASIBLE 观察项，"
                       f"但 feasibility.verdict={f.get('verdict')}（不一致）")

    # ── I 判定与计数 ─────────────────────────────────────────────────────
    match = sum(1 for it in r_items if it.get("verdict") == "MATCH")
    mismatch = sum(1 for it in r_items if it.get("verdict") == "MISMATCH")
    bad_if(summary.get("match") != match,
           f"MATCH 数：汇总 {summary.get('match')} ≠ 逐题 {match}")
    bad_if(summary.get("mismatch") != mismatch,
           f"MISMATCH 数：汇总 {summary.get('mismatch')} ≠ 逐题 {mismatch}")
    bad_if(match + mismatch != len(r_items),
           f"MATCH+MISMATCH={match + mismatch} ≠ 总题数 {len(r_items)}（有题未判定）")

    # ── J 独立性元数据：每题必须有推导表达式且不得为空 ────────────────────
    for it in r_items:
        d = it.get("derivation") or {}
        bad_if(not d.get("expr"),
               f"题目 {str(it.get('rvid'))[:8]}：derivation.expr 为空，"
               f"无法复核推导")
        # 题干外数字必须全部被分诊（purpose 不能留 UNCLASSIFIED）
        for ec in (d.get("encoding_constants") or []):
            bad_if(ec.get("purpose") == "UNCLASSIFIED",
                   f"题目 {str(it.get('rvid'))[:8]}：表达式含未分诊的题干外数字 "
                   f"{ec.get('value')}")

    return bad


def report(quota: dict, result: dict, tag: str = "BATCH6-LEDGER") -> int:
    bad = audit(quota, result)
    summary = result.get("summary") or {}
    r_items = result.get("items") or []
    fscope = result.get("family_scope") or {}
    cov = fscope.get("process_constraint_coverage") or {}
    print(f"\n{tag}: {len(r_items)} 题 / "
          f"{summary.get('match')} MATCH / {summary.get('mismatch')} MISMATCH")
    print(f"  语义族：{fscope.get('semantic_family')} "
          f"（本批 {fscope.get('verified_here')} / 全族 {fscope.get('total_in_family')}）")
    print(f"  观察项重算：{_recount(r_items)}")
    print(f"  process_constraint（本批）："
          f"{sum(1 for it in r_items if (it.get('evidence_enforcement') or {}).get('process_constraint') not in (None, {}, []))} 题")
    print(f"  process_constraint（全族）：{cov.get('with_process_constraint')}/"
          f"{cov.get('family_total')}；缺口 renderer="
          f"{cov.get('renderers_without_any_pc')}")
    bec = sum(1 for it in r_items
              if (it.get("feasibility") or {}).get("verdict") == "INFEASIBLE_ON_COMPONENT")
    print(f"  题面不可完成：{bec} 题")
    if bad:
        for b in bad:
            print(f"  ✗ {b}")
        return 1
    print("  账实相符。")
    return 0


def selftest(quota: dict, result: dict) -> int:
    """六种篡改必须全部检出。每种都单独跑一遍 audit()。"""
    print("\n── 变异性自证（内存篡改，不写盘）──")
    caught = 0
    total = 6

    # M1 汇总虚报
    m1 = copy.deepcopy(result)
    oc = m1["summary"]["observation_counts"]
    k = sorted(oc)[0]
    oc[k] += 1
    if audit(quota, m1):
        caught += 1
        print(f"  ✓ M1 汇总虚报（{k} +1）已检出")
    else:
        print(f"  ✗ M1 汇总虚报（{k} +1）**未被检出**")

    # M2 逐题删一条 observation
    m2 = copy.deepcopy(result)
    victim = next((it for it in m2["items"] if it.get("semantic_observations")), None)
    if victim is None:
        print("  ✗ M2 无法构造：没有任何题带 observation")
    else:
        victim["semantic_observations"].pop(0)
        if audit(quota, m2):
            caught += 1
            print(f"  ✓ M2 逐题删一条（{str(victim.get('rvid'))[:8]}）已检出")
        else:
            print("  ✗ M2 逐题删一条 **未被检出**")

    # M3 名额按 solve_path +1（总量不变）
    m3 = copy.deepcopy(quota)
    qs = m3["quota_by_solve_path"]
    kk = sorted(qs)[0]
    qs[kk] += 1
    if audit(m3, result):
        caught += 1
        print(f"  ✓ M3 名额篡改（{kk} +1）已检出")
    else:
        print(f"  ✗ M3 名额篡改（{kk} +1）**未被检出**")

    # M4 题干改一个字符
    m4 = copy.deepcopy(result)
    t = m4["items"][0]
    t["stem"] = (t.get("stem") or "") + "。"
    if audit(quota, m4):
        caught += 1
        print("  ✓ M4 题干篡改（哈希不符）已检出")
    else:
        print("  ✗ M4 题干篡改 **未被检出**")

    # M5 可完成性汇总虚报（本批新增维度必须自身可证伪）
    m5 = copy.deepcopy(result)
    m5["summary"]["infeasible_on_component"] += 1
    if audit(quota, m5):
        caught += 1
        print("  ✓ M5 可完成性汇总虚报已检出")
    else:
        print("  ✗ M5 可完成性汇总虚报 **未被检出**")

    # M6 全族覆盖统计改错（"笔记与现场不符"必须被抓住）
    m6 = copy.deepcopy(result)
    cov = m6["family_scope"]["process_constraint_coverage"]
    cov["with_process_constraint"] = cov["with_process_constraint"] + 1
    if audit(quota, m6):
        caught += 1
        print("  ✓ M6 全族覆盖统计改错已检出")
    else:
        print("  ✗ M6 全族覆盖统计改错 **未被检出**")

    print(f"\nBATCH6-LEDGER-SELFTEST: "
          f"{'PASS' if caught == total else 'FAIL'}（{caught}/{total} 检出）")
    return 0 if caught == total else 1


def main() -> int:
    _need(QUOTA_PATH, "第六批选题清单")
    _need(RESULT_PATH, "第六批核验产物")
    with open(QUOTA_PATH, encoding="utf-8") as f:
        quota = json.load(f)
    with open(RESULT_PATH, encoding="utf-8") as f:
        result = json.load(f)

    if "--selftest" in sys.argv:
        return selftest(quota, result)

    return report(quota, result)


if __name__ == "__main__":
    sys.exit(main())