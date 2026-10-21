#!/usr/bin/env python3
"""FE-1467：以**当前 Published RVID** 重建 Q05 / Q03 工作清单（Q07 关闭后归位）。

背景（用户 2026-10-21 终审 §五）：
    「下一批应使用当前 Published RVID 重新整理 Q05和Q03工作清单。
      211／212 是此前基线中的待办数量，不应未经复扫就继续作为当前精确数量；
      历史报告保持不变，新基线另行归档。」

实现原则：**不扩建工具、不新造规则**。判定一律走既有 `scripts/iqc/scan.py`
（--audit-only published），本脚本只做三件事：

  1 用既有 inventory 取当前 published 集合（对象口径唯一来源）
  2 用既有 scan 产出 findings（规则口径唯一来源）
  3 把 findings 按 Q05 / Q03 分组成工作清单，并显式标注历史 211/212 已降级

只读：scan 与 inventory 全程 SELECT，本脚本不写库。

用法：
  DATABASE_URL=postgresql://... python scripts/iqc/rt1464/rebuild_q05_q03_baseline.py \
      [--out scripts/iqc/runs/FE1467_q05_q03_baseline.json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", ".."))
REPO = os.path.abspath(os.path.join(SCRIPTS, ".."))
PY = sys.executable


def _db_url() -> str:
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        sys.exit("缺少 DATABASE_URL")
    return raw


def _run(args: list[str], step: str) -> None:
    r = subprocess.run([PY] + args, capture_output=True, text=True, cwd=REPO)
    if r.returncode != 0:
        sys.exit(f"{step} FAIL（显式报错不静默）rc={r.returncode}\n{r.stderr[-600:]}")
    print(r.stdout.strip()[:500])


def read_historical_provenance(repo: str = REPO) -> dict:
    """从历史工件里**读回** 211 / 212 的出处，而不是由脚本作者手写断言。

    为什么要这段：终审 §五 要求把 211/212 降级为历史基线数量。既然要降级，
    就必须说得清它们当初是在哪个对象集合上数出来的——否则「211 是历史数」
    只是一句无法核验的话，读者无从判断能不能拿来和当前 209/212 比。

    出处（脚本内可复算，非人工记忆）：
      scripts/iqc/runs/FE1464_first_full_report.json
        → fe1464_first_full_baseline.current_published_findings
    该段是 2026-10-17 首轮全量基线，对象集合 published=443，
    status 分布 REVISION_REQUIRED=211（即 Q05 待办）、UNVERIFIED=212（即 Q03 待办）。

    纯度：只做读取+校验，不 sys.exit（供 pr_gate 的 DB-free 测试直接复用）。
    校验不过一律 raise ValueError，由调用方决定是退出还是判 FAIL。
    """
    p = os.path.join(repo, "scripts/iqc/runs/FE1464_first_full_report.json")
    if not os.path.exists(p):
        raise ValueError(f"历史基线工件缺失，无法证明 211/212 出处：{p}")
    cur = json.load(open(p))["fe1464_first_full_baseline"]["current_published_findings"]
    pub_n = cur["n"]
    st = cur["status"]
    rv, un = st.get("REVISION_REQUIRED"), st.get("UNVERIFIED")
    # 恒等式：四类结论逐条覆盖每一条 published，不多不少。
    total = sum(st.values())
    if total != pub_n:
        raise ValueError(f"历史基线自相矛盾：status 合计 {total} != published {pub_n}")
    if (rv, un) != (211, 212):
        raise ValueError(
            f"历史基线 drifted：REVISION_REQUIRED/UNVERIFIED = {rv}/{un}，"
            f"与终审引用的 211/212 不符——先查清再降级，不要照抄旧数")
    return {
        "source_artifact": "scripts/iqc/runs/FE1464_first_full_report.json",
        "source_path": "fe1464_first_full_baseline.current_published_findings",
        "historical_published": pub_n,
        "historical_status_distribution": st,
        "identity_check": f"{'+'.join(f'{k}({v})' for k, v in st.items())} = {total} = published({pub_n})",
        "mapping": {"Q05_211": "status.REVISION_REQUIRED",
                    "Q03_212": "status.UNVERIFIED"},
        "note": "211/212 出自同名 status 枚举，不是独立计数器；"
                "该工件按终审 §五『历史报告保持不变』未改动，本次只读取不重写。",
    }


def _historical_212_211_provenance() -> dict:
    try:
        return read_historical_provenance()
    except ValueError as e:
        sys.exit(str(e))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(
        REPO, "scripts/iqc/runs/FE1467_q05_q03_baseline.json"))
    args = ap.parse_args()
    db = _db_url()
    tmp = tempfile.mkdtemp(prefix="fe1467_")

    # 1 当前库存（全状态；用于对象口径与状态分布）
    inv_p = os.path.join(tmp, "inventory.json")
    _run([os.path.join(SCRIPTS, "iqc/inventory.py"), "--db", db, "--out", inv_p],
         "INVENTORY")
    inv = json.load(open(inv_p))
    pub_rvids = {i["resource_version_id"] for i in inv["items"]
                 if i["review_status"] == "published"}
    title_of = {i["resource_version_id"]: i.get("title") for i in inv["items"]}
    ability_of = {i["resource_version_id"]: i.get("ability_id") for i in inv["items"]}
    rend_of = {i["resource_version_id"]: (i.get("interaction") or {}).get("renderer") or "none"
               for i in inv["items"]}

    # 2 既有 scan，published 口径
    find_p = os.path.join(tmp, "findings.jsonl")
    _run([os.path.join(SCRIPTS, "iqc/scan.py"),
          "--manifest", inv_p, "--db", db,
          "--mapping", os.path.join(SCRIPTS, "iqc/version_migration_map.csv"),
          "--audit-only", "published", "--out", find_p], "SCAN(published)")
    fs = [json.loads(l) for l in open(find_p)]

    # 3 同样跑一次 all（审计追溯口径，仅参考，不混入治理基线）
    find_all_p = os.path.join(tmp, "findings_all.jsonl")
    _run([os.path.join(SCRIPTS, "iqc/scan.py"),
          "--manifest", inv_p, "--db", db,
          "--mapping", os.path.join(SCRIPTS, "iqc/version_migration_map.csv"),
          "--audit-only", "all", "--out", find_all_p], "SCAN(all)")
    fs_all = [json.loads(l) for l in open(find_all_p)]

    def group(findings, rule):
        return sorted({f["rvid"] for f in findings if f["rule_id"] == rule})

    def detail(rvids, findings, rule):
        ev = {f["rvid"]: f.get("evidence_pointer") for f in findings if f["rule_id"] == rule}
        return [
            {
                "rank": i + 1,
                "rvid": r,
                "title": title_of.get(r),
                "ability_id": ability_of.get(r),
                "renderer": rend_of.get(r),
                "evidence": ev.get(r),
            }
            for i, r in enumerate(rvids)
        ]

    q05 = group(fs, "Q05-HOMOGENEOUS")
    q03u = group(fs, "Q03-UNVERIFIED")
    q03ok = group(fs, "Q03-OK")
    q03mm = group(fs, "Q03-ANSWER_MISMATCH")

    q05_all = group(fs_all, "Q05-HOMOGENEOUS")
    q03u_all = group(fs_all, "Q03-UNVERIFIED")

    by_rule_pub = Counter(f["rule_id"] for f in fs)
    by_sev_pub = Counter(f["severity"] for f in fs)
    pub_only = [r for r in {f["rvid"] for f in fs} if r in pub_rvids]

    hist = _historical_212_211_provenance()

    payload = {
        "title": "FE-1467｜Q05 / Q03 工作清单重建（以当前 Published RVID 为口径）",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "why": "用户 2026-10-21 终审 §五：211/212 是此前基线中的待办数量，"
               "不应未经复扫就继续作为当前精确数量。本文件是新基线；历史报告保持不变。",
        "method": {
            "object_scope_source": "scripts/iqc/inventory.py（review_status='published'）",
            "rule_source": "scripts/iqc/scan.py --audit-only published（复用既有规则，未新造）",
            "read_only": True,
            "inventory_snapshot": inv.get("snapshot_sha256"),
            "inventory_total": inv.get("discovered_total"),
            "rules_version": (fs[0]["rules_version"] if fs else None),
        },
        "object_scope": {
            "published_count": len(pub_rvids),
            "all_versions_count": len(inv["items"]),
            "status_distribution": inv.get("status_distribution"),
            "schema_distribution": inv.get("schema_distribution"),
            "note": "published = 现行治理口径（可下发）；all_versions = 审计追溯口径。"
                    "两个口径不得混用，本文件所有『当前数量』均指 published。",
        },
        "baseline_downgrade": {
            "rule": "211／212 降级为历史基线数量，不沿用、不回填、不改历史报告。",
            "provenance": hist,
            "Q05_211": {
                "status": "HISTORICAL_BASELINE_ONLY",
                "original": 211,
                "original_context": f"2026-10-17 基线，当时 published="
                                    f"{hist['historical_published']}；"
                                    f"211 = {hist['mapping']['Q05_211']}",
                "current": len(q05),
                "reason": f"对象集合由 {hist['historical_published']} 变为 "
                          f"{len(pub_rvids)}；旧数字是不同集合上的待办数，不可直接比较",
            },
            "Q03_212": {
                "status": "HISTORICAL_BASELINE_ONLY",
                "original": 212,
                "original_context": f"2026-10-17 基线，当时 published="
                                    f"{hist['historical_published']}；"
                                    f"212 = {hist['mapping']['Q03_212']}",
                "current": len(q03u),
                "reason": "同上",
            },
        },
        "current_published_baseline": {
            "findings_total": len(fs),
            "rvids_with_findings": len(pub_only),
            "by_rule": dict(by_rule_pub),
            "by_severity": dict(by_sev_pub),
            "Q05_HOMOGENEOUS": {
                "n": len(q05),
                "by_ability": dict(Counter(ability_of.get(r) for r in q05).most_common()),
                "by_renderer": dict(Counter(rend_of.get(r) for r in q05).most_common()),
            },
            "Q03_UNVERIFIED": {
                "n": len(q03u),
                "by_ability": dict(Counter(ability_of.get(r) for r in q03u).most_common()),
                "by_renderer": dict(Counter(rend_of.get(r) for r in q03u).most_common()),
            },
            "Q03_OK": {"n": len(q03ok)},
            "Q03_ANSWER_MISMATCH": {"n": len(q03mm), "rvids": q03mm},
        },
        "worklist_Q05": detail(q05, fs, "Q05-HOMOGENEOUS"),
        "worklist_Q03_unverified": detail(q03u, fs, "Q03-UNVERIFIED"),
        "audit_only_all_versions": {
            "note": "全 304 条（含 superseded/qa_retired/qa_staged）口径，仅供审计追溯，"
                    "不作为治理待办数。",
            "Q05_HOMOGENEOUS_n": len(q05_all),
            "Q03_UNVERIFIED_n": len(q03u_all),
            "findings_total": len(fs_all),
        },
        "regression_assets_from_q07": [
            "verify_bypass_negative_case.py（N1-N4 绕过负例）",
            "test_fe1466_expired_guard.py（9 条，含假会话 WHERE 分流）",
            "verify_expiry_lock_concurrency.py（T0-T6 锁测 + 样本归属）",
            "exec_mode.py + test_exec_mode_gate.py（只读/写入双模式，PR-IQC-GATE 硬阻断）",
            "postmerge_evidence_scope_ledger（证据分账，不夸大覆盖范围）",
        ],
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    # 两清单的集合关系：排期必须按并集，不能按 209+212 相加。
    rvids_with_findings = {f["rvid"] for f in fs}
    not_in_either = sorted(rvids_with_findings - set(q05) - set(q03u))
    payload["worklist_union"] = {
        "note": "两清单按 RVID 合并后的真实待办量——排期必须按并集，不能按数量相加。",
        "Q05_n": len(q05), "Q03_n": len(q03u),
        "intersection": len(set(q05) & set(q03u)),
        "Q05_only": len(set(q05) - set(q03u)),
        "Q03_only": len(set(q03u) - set(q05)),
        "union": len(set(q05) | set(q03u)),
        "not_in_either": [
            {"rvid": r, "rules": sorted({f["rule_id"] for f in fs if f["rvid"] == r})}
            for r in not_in_either
        ],
        "identity_check": f"Q03-UNVERIFIED({len(q03u)})+Q03-OK({len(q03ok)})"
                          f"={len(q03u) + len(q03ok)}=published({len(pub_rvids)})",
        "priority": f"交集 {len(set(q05) & set(q03u))} 条优先（一题同时改两件事）",
    }

    # 与历史 findings_fe1460_225.jsonl 的逐 RVID 差异归因。
    # 历史文件按用户 §五「历史报告保持不变」不改，这里只做只读比对。
    hist_p = os.path.join(REPO, "scripts/iqc/runs/findings_fe1460_225.jsonl")
    if os.path.exists(hist_p):
        hist = [json.loads(l) for l in open(hist_p)]
        h_rvids = {f["rvid"] for f in hist}
        only_old = sorted(h_rvids - rvids_with_findings)
        only_new = sorted(rvids_with_findings - h_rvids)
        payload["delta_vs_history_225"] = {
            "note": "与历史 findings_fe1460_225.jsonl 逐 RVID 集合对比。历史文件按终审 §五"
                    "『历史报告保持不变』未改动；本段只做归因，不改历史。",
            "history_artifact": os.path.basename(hist_p),
            "old_distinct_rvids": len(h_rvids),
            "new_distinct_rvids": len(rvids_with_findings),
            "overlap": len(h_rvids & rvids_with_findings),
            "only_old": len(only_old),
            "only_new": len(only_new),
            "only_old_rvids": only_old,
            "only_new_rvids": only_new,
            "attribution": "only_old 应为治理中被替代的 superseded 版本（应退出 published 口径）；"
                           "only_new 应为 Q07 资源替代后新进入口径的 published 版本。"
                           "归属状态请由重建时的 inventory.status_distribution 与 DB review_status 交叉核对。",
            "by_rule_delta": (
                {r: {"old": sum(1 for f in hist if f["rule_id"] == r),
                     "new": sum(1 for f in fs if f["rule_id"] == r)}
                 for r in sorted({f["rule_id"] for f in hist} | {f["rule_id"] for f in fs})}
            ),
        }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    print(json.dumps({
        "published": len(pub_rvids),
        "Q05_HOMOGENEOUS": len(q05),
        "Q03_UNVERIFIED": len(q03u),
        "Q03_OK": len(q03ok),
        "Q03_ANSWER_MISMATCH": len(q03mm),
        "findings_total": len(fs),
        "union": payload["worklist_union"]["union"],
        "intersection": payload["worklist_union"]["intersection"],
    }, ensure_ascii=False, indent=1))
    print("out:", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())