#!/usr/bin/env python3
"""FE-1472 第五批：选题清单 ↔ 核验产物 账实核（离线，不连库）

## 为什么需要这个脚本

第五批的结论里有两类数字最容易"看起来正常"：

  1. **汇总写了、逐题没有**。`summary.observation_counts` 说
     `MODE_STEM_MISMATCH: 2`，但若逐题 `semantic_observations` 里其实
     一条都没有，报告仍然是"20/20 MATCH + 2 条观察项"。
     这与 2026-10-22 D2 撤回时踩到的缺陷同型：改总表 ≠ 改生成物。
     当时 `CHECKS` / `Q05_EVIDENCE` 的字段被 `evaluate()` 原样写进结果，
     只改一处就会产出"报告说撤回了、结果里还写着"的矛盾。
  2. **名额分配写了、实核挑的不是那几题**。`quota_by_renderer` 说
     ruler 4 题，若实核挑了 ruler 5 题、ten-frame 3 题，总数仍是 20，
     总量检查完全看不见。

因此本脚本不重跑核验、不连数据库，只做**逐条对账**：

  A 台账：quota / verified / pool_size 与选题清单一致，且"先冻结后核验"为真
  B 集合：产物 RVID 集合 == 选题清单 RVID 集合（缺一题 / 多一题 / 重复都要报）
  C 名额：`quota_by_renderer` 逐类 == 实测 `by_renderer[r].n`
  D 观察项：`observation_counts` == 逐题 `semantic_observations` 重算
  E 过程校验：`process_constraint_declared` == 逐题 `evidence_enforcement`
     `process_constraint` 非空的题数（**不写死 0**，按现场重算对比）
  F 一致性：`config_inconsistent` == 逐题 `config_vs_stem.status` != CONSISTENT 的题数
  G 输入绑定：每题 `input_binding.stem_sha256` == 现场从 `stem` 重算的 sha256

## 为什么不写成"检查某几个数字等于常量"

把 `EXPECTED = 18` 写进脚本，第一次能过，之后任何一次核验改动都要人来改
常量——这就是"文档里按减法外推"的同型病。所以本脚本一律**现场重算**，
只保留"自洽"与"集合相等"两类断言。

## 变异性

`--selftest` 在内存里构造四种篡改（不写盘），每一种都必须被检出：

  M1 汇总 observation_counts 某类 +1
  M2 逐题删掉一条 observation（汇总不动 → 总数对不上）
  M3 quota_by_renderer 某类 +1（总量仍是 20）
  M4 stem 改一个字符（哈希必须变）

四种全部检出才打印 PASS。任何一项漏检即 rc=1——"全过"本身必须能被证伪。

退出码：0 通过 / 1 断言失败 / 2 工件或环境缺失
（rc 区分是硬要求：历史上解释器错导致 ModuleNotFoundError 崩溃时，
曾把 `rc=2` 的崩溃读成"检出成功"）
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
# REPO 退级要被 assert 拦住——`scripts/scripts/` 已经踩过两次
assert os.path.isdir(os.path.join(REPO, "apps")), f"REPO 推导错误：{REPO}"

QUOTA_PATH = os.path.join(HERE, "batch5_quota_list.json")
RESULT_PATH = os.path.join(REPO, "scripts", "iqc", "runs", "FE1472_q03_batch5.json")

fails: list[str] = []


def fail(msg: str) -> None:
    fails.append(msg)
    print(f"  ✗ {msg}")


def _need(path: str, what: str) -> bool:
    if not os.path.exists(path):
        print(f"MISSING: {what} → {path}")
        sys.exit(2)
    return True


def canon_sha256(obj) -> str:
    """与 freeze_batch5.py::_sha 逐比特一致（canonical JSON）。

    第一版这里写成 `sha256(stem.encode())`，对着现场 20 题全部报"哈希不符"——
    是判据错、不是数据错。冻结侧用的是
    `json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",",":"))`，
    对字符串会带上引号。必须同函数，否则对账永远为假。
    """
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


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
    ledger = result.get("ledger") or {}

    # ── A 台账 ───────────────────────────────────────────────────────────
    bad_if(len(q_items) != quota.get("quota_n"), 
           f"选题清单 items={len(q_items)} ≠ 声明 quota_n={quota.get('quota_n')}")
    bad_if(ledger.get("quota") != len(q_items),
           f"产物 ledger.quota={ledger.get('quota')} ≠ 选题清单 {len(q_items)} 题")
    bad_if(ledger.get("verified") != len(r_items),
           f"产物 ledger.verified={ledger.get('verified')} ≠ 实际核验 {len(r_items)} 题")
    bad_if(ledger.get("quota_frozen_before_verify") is not True,
           "ledger.quota_frozen_before_verify 不是 True——"
           "选题集合没有在核验前落盘，核验范围无法自证")
    bad_if(ledger.get("pool_size") != quota.get("pool_size"),
           f"ledger.pool_size={ledger.get('pool_size')} ≠ 选题清单 {quota.get('pool_size')}")
    # 第四批踩过的坑：额定 20、实核 29，差额无法反查
    bad_if(len(q_items) != len(r_items),
           f"额定 {len(q_items)} 题 vs 实核 {len(r_items)} 题，差额 {len(r_items) - len(q_items)}")

    # ── B 集合（建字典之前先核唯一性）─────────────────────────────────────
    q_rvids = [it.get("rvid") for it in q_items]
    r_rvids = [it.get("rvid") for it in r_items]
    bad_if(len(set(q_rvids)) != len(q_rvids), "选题清单内 RVID 重复")
    bad_if(len(set(r_rvids)) != len(r_rvids), "核验产物内 RVID 重复")
    # 字典推导 `{it["rvid"]: it}` 会让重复 RVID 后行覆盖前行且集合检查看不出异常，
    # 所以先核唯一性、再建字典、再核数量。
    q_by = {it["rvid"]: it for it in q_items}
    r_by = {it["rvid"]: it for it in r_items}
    bad_if(len(q_by) != len(q_rvids), "选题清单 RVID 建字典后数量变了")
    bad_if(len(r_by) != len(r_rvids), "核验产物 RVID 建字典后数量变了")
    missing = sorted(set(q_by) - set(r_by))
    extra = sorted(set(r_by) - set(q_by))
    bad_if(bool(missing), f"选题清单里有 {len(missing)} 题没出现在产物中：{[m[:8] for m in missing]}")
    bad_if(bool(extra), f"产物里出现 {len(extra)} 题不在选题清单中：{[e[:8] for e in extra]}")

    # ── C 名额 ───────────────────────────────────────────────────────────
    quota_by = quota.get("quota_by_renderer") or {}
    by_renderer = summary.get("by_renderer") or {}
    for r, n in quota_by.items():
        got = (by_renderer.get(r) or {}).get("n")
        bad_if(got != n, f"名额 {r}: 声明 {n} 题，实核 {got} 题")
    for r in by_renderer:
        bad_if(r not in quota_by, f"实核出现未分配名额的 renderer：{r}")
    # 逐类实核数之和必须等于总额
    bad_if(sum((by_renderer.get(r) or {}).get("n") or 0 for r in quota_by) != len(r_items),
           "逐类实核数之和 ≠ 实核总题数")

    # ── D 观察项（本项目最高价值的对账）───────────────────────────────────
    recount: dict[str, int] = {}
    for it in r_items:
        for obs in (it.get("semantic_observations") or []):
            code = obs.get("code") if isinstance(obs, dict) else str(obs)
            recount[code] = recount.get(code, 0) + 1
    stated = summary.get("observation_counts") or {}
    for code in sorted(set(stated) | set(recount)):
        s, c = stated.get(code), recount.get(code)
        bad_if(s != c,
               f"观察项 {code}: 汇总写 {s}，逐题重算 {c}"
               + ("（汇总虚报，逐题一条都没有）" if c is None else "")
               + ("（逐题有但汇总漏登记）" if s is None else ""))
    # 逐题观察项必须是"一句可读的解释 + 一条证据"，不能只有一个 code。
    # 实际字段是 severity/why/evidence/consequence/not_concluded（比 detail 更全），
    # 因此这里核 why 与 evidence 两个必填项。
    for it in r_items:
        for obs in (it.get("semantic_observations") or []):
            if not isinstance(obs, dict):
                bad.append(f"题目 {str(it.get('rvid'))[:8]}：观察项不是对象，无法追溯")
                continue
            if not obs.get("why") or not obs.get("evidence"):
                bad.append(f"题目 {str(it.get('rvid'))[:8]} 的观察项 "
                           f"{obs.get('code')} 缺 why/evidence，无法独立复核")

    # ── E 过程校验声明（按现场重算，不写死 0）────────────────────────────
    declared = 0
    for it in r_items:
        ee = it.get("evidence_enforcement") or {}
        pc = ee.get("process_constraint")
        if pc not in (None, {}, []):
            declared += 1
        # 只有 process_constraint 非空，后端才会调 process_validate；
        # 声明了 evidence_targets 却没有 process_constraint 的，必须被登记成观察项，
        # 否则"有过程证据"会被误读成"过程参与判分"。
        if (ee.get("evidence_targets") not in (None, {}, [])
                and pc in (None, {}, [])
                and not any((o or {}).get("code") == "EVIDENCE_DECLARED_BUT_NOT_ENFORCED"
                            for o in (it.get("semantic_observations") or []))):
            bad.append(f"题目 {str(it.get('rvid'))[:8]}：声明了 evidence_targets 但 "
                       "process_constraint 为空，且未登记 EVIDENCE_DECLARED_BUT_NOT_ENFORCED")
        # enforced_by_backend 必须与 process_constraint 一致
        bad_if(bool(ee.get("enforced_by_backend")) != (pc not in (None, {}, [])),
               f"题目 {str(it.get('rvid'))[:8]}：enforced_by_backend 与 process_constraint 不一致")
    bad_if(summary.get("process_constraint_declared") != declared,
           f"process_constraint 声明数：汇总写 {summary.get('process_constraint_declared')}，"
           f"逐题重算 {declared}")

    # ── F 题面↔config 一致性计数 ─────────────────────────────────────────
    inconsistent = sum(1 for it in r_items
                       if (it.get("config_vs_stem") or {}).get("status") != "CONSISTENT")
    bad_if(summary.get("config_inconsistent") != inconsistent,
           f"config 不一致题数：汇总写 {summary.get('config_inconsistent')}，逐题重算 {inconsistent}")

    # ── G 输入绑定哈希 ───────────────────────────────────────────────────
    for it in r_items:
        rv = it.get("rvid")
        bind = (it.get("input_binding") or {}).get("stem_sha256")
        real = canon_sha256(it.get("stem") or "")
        bad_if(bind != real,
               f"题目 {str(rv)[:8]}：stem_sha256 与现场重算不符（题干被改过但哈希没跟着变）")
        # 与选题清单的冻结哈希比——证明核验的就是冻结时那一版
        if rv in q_by:
            frozen = q_by[rv].get("stem_sha256")
            bad_if(frozen and frozen != real,
                   f"题目 {str(rv)[:8]}：产物的题干与选题清单冻结时不是同一版")

    # ── 判定与计数 ───────────────────────────────────────────────────────
    match = sum(1 for it in r_items if it.get("verdict") == "MATCH")
    mismatch = sum(1 for it in r_items if it.get("verdict") == "MISMATCH")
    bad_if(summary.get("match") != match, f"MATCH 数：汇总 {summary.get('match')} ≠ 逐题 {match}")
    bad_if(summary.get("mismatch") != mismatch,
           f"MISMATCH 数：汇总 {summary.get('mismatch')} ≠ 逐题 {mismatch}")
    bad_if(match + mismatch != len(r_items),
           f"MATCH+MISMATCH={match + mismatch} ≠ 总题数 {len(r_items)}（有题未判定）")

    return bad


def report(quota: dict, result: dict, tag: str = "BATCH5-LEDGER") -> int:
    bad = audit(quota, result)
    summary = result.get("summary") or {}
    r_items = result.get("items") or []
    print(f"\n{tag}: {len(r_items)} 题 / "
          f"{summary.get('match')} MATCH / {summary.get('mismatch')} MISMATCH")
    print(f"  选题清单↔产物 RVID 集合一致：{'是' if not any('RVID' in b or '没出现在产物' in b or '不在选题清单' in b for b in bad) else '否'}")
    print(f"  观察项重算：{ {k: v for k, v in _recount(r_items).items()} }")
    print(f"  process_constraint 声明：{sum(1 for it in r_items if (it.get('evidence_enforcement') or {}).get('process_constraint') not in (None, {}, []))} 题")
    if bad:
        for b in bad:
            print(f"  ✗ {b}")
        return 1
    print("  账实相符。")
    return 0


def _recount(items: list) -> dict:
    out: dict[str, int] = {}
    for it in items:
        for obs in (it.get("semantic_observations") or []):
            code = obs.get("code") if isinstance(obs, dict) else str(obs)
            out[code] = out.get(code, 0) + 1
    return dict(sorted(out.items()))


def selftest(quota: dict, result: dict) -> int:
    """四种篡改必须全部检出。每种都单独跑一遍 audit()。"""
    print("\n── 变异性自证（内存篡改，不写盘）──")
    caught = 0
    total = 4

    # M1 汇总虚报：observation_counts 某类 +1
    m1 = copy.deepcopy(result)
    oc = m1["summary"]["observation_counts"]
    k = sorted(oc)[0]
    oc[k] += 1
    if audit(quota, m1):
        caught += 1
        print(f"  ✓ M1 汇总虚报（{k} +1）已检出")
    else:
        print(f"  ✗ M1 汇总虚报（{k} +1）**未被检出**——"
              "observation_counts 没有和逐题对账")

    # M2 逐题删一条 observation（汇总不动）
    m2 = copy.deepcopy(result)
    victim = next((it for it in m2["items"] if it.get("semantic_observations")), None)
    if victim is None:
        print("  ✗ M2 无法构造：没有任何题带 observation，"
              "本批观察项全空则此变异无意义")
    else:
        victim["semantic_observations"].pop(0)
        if audit(quota, m2):
            caught += 1
            print(f"  ✓ M2 逐题删一条（{str(victim.get('rvid'))[:8]}）已检出")
        else:
            print("  ✗ M2 逐题删一条 **未被检出**")

    # M3 名额分配篡改：某类 +1（总量仍 20，只有逐类对账能看见）
    m3 = copy.deepcopy(quota)
    qr = m3["quota_by_renderer"]
    kk = sorted(qr)[0]
    qr[kk] += 1
    if audit(m3, result):
        caught += 1
        print(f"  ✓ M3 名额篡改（{kk} +1）已检出")
    else:
        print(f"  ✗ M3 名额篡改（{kk} +1）**未被检出**")

    # M4 题干改一个字符（哈希与冻结版都不符）
    m4 = copy.deepcopy(result)
    t = m4["items"][0]
    t["stem"] = (t.get("stem") or "") + "。"
    if audit(quota, m4):
        caught += 1
        print("  ✓ M4 题干篡改（哈希不符）已检出")
    else:
        print("  ✗ M4 题干篡改 **未被检出**")

    print(f"\nBATCH5-LEDGER-SELFTEST: "
          f"{'PASS' if caught == total else 'FAIL'}（{caught}/{total} 检出）")
    return 0 if caught == total else 1


def main() -> int:
    _need(QUOTA_PATH, "第五批选题清单")
    _need(RESULT_PATH, "第五批核验产物")
    with open(QUOTA_PATH, encoding="utf-8") as f:
        quota = json.load(f)
    with open(RESULT_PATH, encoding="utf-8") as f:
        result = json.load(f)

    if "--selftest" in sys.argv:
        return selftest(quota, result)

    rc = report(quota, result)
    return rc


if __name__ == "__main__":
    sys.exit(main())