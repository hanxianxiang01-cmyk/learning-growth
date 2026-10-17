#!/usr/bin/env python3
"""FE-1462 覆盖矩阵静态对齐：manifest 实际 renderer 集 vs registry 发布集。

发现唯一消费 FE-1459 manifest（裁决 §一）；输出 renderer_coverage.json：
- 每 renderer：题数、schema 形态、契约用例登记状态（covered/partial/uncovered/
  blocked-unknown）、证据 spec 清单
- 未知 renderer（不在 registry 枚举）→ BLOCKED 显式，禁止静默
- 无运行家用例的 renderer 全部显式 UNCOVERED 在册（裁决 §三.3：不足→BLOCKED/
  UNCOVERED，不假通过）
"""
import argparse
import json
import re
import sys

REGISTRY_TS = "apps/child-web/src/features/task-renderer/rendererRegistry.ts"
LEGACY_KINDS = {"legacy:number-line", "legacy:objects", "legacy:bar-model", "legacy:direct"}


def registry_ids(repo):
    txt = open(f"{repo}/{REGISTRY_TS}").read()
    proto = re.findall(r'^\s*\| "([a-z-]+)"', txt, re.M)
    m = re.search(r"V2_RELEASE_RENDERER_IDS = \[(.*?)\] as const", txt, re.S)
    release = re.findall(r'"([a-z-]+)"', m.group(1)) if m else []
    return set(proto), set(release)


def e2e_specs(repo):
    """已存在 Playwright spec → renderer 关键词倒排（证据发现，不判质量）。"""
    import os
    e2d = f"{repo}/apps/child-web/e2e"
    idx = {}
    for fn in os.listdir(e2d):
        if not fn.endswith((".spec.mjs", ".spec.ts")):
            continue
        body = open(f"{e2d}/{fn}").read()
        for rid in re.findall(r'"([a-z-]{4,})"', body):
            idx.setdefault(rid, set()).add(fn)
    return idx


# 契约用例登记（裁决 §三首批真实案例）：只有针对性端到端契约才算 covered/partial。
# covered=有独立 E2E 契约用例且通过；partial=有判分/单测锁但缺完整 E2E；uncovered=体系待建。
CONTRACT_CASES = {
    "number-line": {"status": "covered", "evidence": [
        "fe1455-jump-sentinel.spec.mjs（跳步约束三态·双皮肤）",
        "revb-startfix-1ab893bf.spec.mjs（起点修复 0→7→14→21 无反向修正）",
        "q4-reva-contract.spec.mjs（数轴中间态原序可操作 before/after）"]},
    "shape-gallery": {"status": "covered", "evidence": [
        "q4-reva-contract.spec.mjs（卡名中性化零泄露·9 题）",
        "a11y BLOCKED：aria-label 全 null→QA-ACCESS-01 进行中"]},
    "formula-board": {"status": "partial", "evidence": [
        "减号 ASCII 等价 _judge 后端锁测（PoC #2 口径）",
        "缺：符号点击→提交→判分 端到端 Playwright 契约用例（待补）"]},
    "array-board": {"status": "partial", "evidence": [
        "R08 阵列 Gate 历史验证（B5 流水线）",
        "缺：常驻 e2e 结构证据(rows/cols≠仅总数)契约用例（待补）"]},
}
# 六测试面基线登记（裁决 §三 测试面）
FACES = {
    "number-line": {"process": "FE-1455 三态双皮肤 ✓", "start_reach": "起点修复 2/2 ✓"},
    "shape-gallery": {"a11y": "BLOCKED→QA-ACCESS-01（aria-label 全 null 实测）",
                      "leak": "中性化零泄露 ✓"},
    "formula-board": {"ascii": "减号 ASCII 等价 _judge 锁测 ✓（PoC #2）"},
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", default="runs/renderer_coverage.json")
    args = ap.parse_args()

    proto, release = registry_ids(args.repo)
    specs = e2e_specs(args.repo)
    man = json.load(open(args.manifest))

    agg = {}
    for it in man["items"]:
        r = (it.get("interaction") or {}).get("renderer") or "none"
        a = agg.setdefault(r, {"count": 0, "statuses": {}})
        a["count"] += 1
        a["statuses"][it["review_status"]] = a["statuses"].get(it["review_status"], 0) + 1

    unknown = [r for r in agg if not r.startswith("legacy:") and r != "none" and r not in proto]
    rows = []
    for r, a in sorted(agg.items(), key=lambda x: -x[1]["count"]):
        if r == "none":
            rows.append({"renderer": r, "count": a["count"], "class": "direct/无交互",
                         "runtime": "N/A 直接输入型", "faces": {}})
            continue
        if r.startswith("legacy:"):
            rows.append({"renderer": r, "count": a["count"], "class": "V1 Legacy",
                         "runtime": "V1 工作台常驻回归（197/197 历史线）",
                         "faces": FACES.get("number-line", {}) if r.endswith("number-line") else {}})
            continue
        known = r in proto
        cc = CONTRACT_CASES.get(r)
        status = ("BLOCKED-UNKNOWN-RENDERER" if not known else
                  (cc["status"] if cc else "uncovered"))
        rows.append({"renderer": r, "count": a["count"], "class": "V2",
                     "in_release_scope": r in release, "runtime": status,
                     "contract_evidence": (cc or {}).get("evidence", []),
                     "faces": FACES.get(r, {})})
    out = {"inventory_snapshot": man["snapshot_sha256"], "rules_via": "FE-1459 manifest",
           "registry_protocol_ids": len(proto), "release_scope": len(release),
           "renderers_in_inventory": len([r for r in agg if r != "none"]),
           "unknown_renderers": unknown,
           "covered": [x["renderer"] for x in rows if x.get("runtime") == "covered"],
           "partial": [x["renderer"] for x in rows if x.get("runtime") == "partial"],
           "uncovered_v2": [x["renderer"] for x in rows if x.get("runtime") == "uncovered"],
           "blocked": unknown,
           "summary": {
               "v2_covered": len([x for x in rows if x.get("runtime") == "covered"]),
               "v2_partial": len([x for x in rows if x.get("runtime") == "partial"]),
               "v2_total": len([x for x in rows if x.get("class") == "V2"]),
               "note": "uncovered≠题目有缺陷=验证体系尚未覆盖该 renderer 契约用例（显式在册，裁决 §三.3）"},
           "matrix": rows}
    json.dump(out, open(args.out, "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ("renderers_in_inventory", "unknown_renderers",
        "covered", "uncovered_v2", "summary")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
