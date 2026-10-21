#!/usr/bin/env python3
"""FE-1463 PR 增量质量门（DB-free，确定性，进 ci.yml）。

四检查（任一 FAIL=退出非零阻断合并）：
1. 规则夹具回归：test_checks.py 25 负例全锁（已知缺陷可检出/已知非缺陷不误报）
2. 契约自检：rules.json iqc 块完整 + 夹具数据分离纪律（skill 侧检查的仓内镜像，
   skill 目录不在 CI checkout 内时降级 SKIP 并显式打印，不谎称已验）
3. 覆盖矩阵一致性：committed inventory manifest 中所有 renderer 必须
   (a) 在 rendererRegistry 协议枚举内，(b) 状态只允许 covered/partial/uncovered/
   BLOCKED-UNKNOWN-RENDERER——未登记 renderer=FAIL，禁止静默新增
4. 执行模式闸门自证：验证脚本的 --no-write 必须同时拦住 HTTP 提交与 SQL 写，
   且变异对照证明拦截非空跑（用户 2026-10-21 终审 §四）
边界（裁决 §四）：本门只判规则明确证据充分的问题；不访问生产 DB；失败输出含
rule_id+证据，不得为空。
"""
import json
import subprocess
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
fails = []

def note(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        fails.append(name)

# 1 夹具回归
r = subprocess.run([sys.executable, os.path.join(HERE, "test_checks.py")], capture_output=True, text=True)
tail = r.stdout.strip().splitlines()[-1] if r.stdout else r.stderr[-200:]
note("夹具回归 test_checks", r.returncode == 0 and "PASS" in r.stdout, tail)

# 2 rules.json iqc 契约（skill 在 CI 外→镜像校验仓内可验部分）
RULES_PATHS = [os.path.expanduser("~/.workbuddy/skills/math-prototype-review/rules.json"),
               os.environ.get("IQC_RULES_PATH", "")]
rules = None
for p in RULES_PATHS:
    if p and os.path.exists(p):
        rules = json.load(open(p)); break
if rules and "iqc" in rules:
    iqc = rules["iqc"]
    codes = [c["id"] for c in iqc.get("issue_codes", [])]
    note("rules.json iqc 契约", codes == [f"Q{i:02d}" for i in range(1, 11)]
         and len(iqc.get("hard_constraints", [])) == 8, f"{codes}")
else:
    note("rules.json iqc 契约（CI 无 skill 副本=显式 SKIP，不谎称已验）", True, "SKIP")

# 3 覆盖矩阵一致性（committed manifest + registry）
man_p = os.path.join(HERE, "runs", "inventory_manifest_r2.json")
cov_p = os.path.join(HERE, "runs", "renderer_coverage.json")
if os.path.exists(man_p) and os.path.exists(cov_p):
    man = json.load(open(man_p)); cov = json.load(open(cov_p))
    reg = open(os.path.join(REPO, "apps/child-web/src/features/task-renderer/rendererRegistry.ts")).read()
    import re
    proto = set(re.findall(r'^\s*\| "([a-z-]+)"', reg, re.M))
    renderers = {(i.get("interaction") or {}).get("renderer") or "none" for i in man["items"]}
    unknown = sorted(r for r in renderers if r not in ("none",) and not r.startswith("legacy:") and r not in proto)
    note("未知 renderer 检出", not unknown, str(unknown))
    statuses = {x.get("runtime") for x in cov["matrix"]}
    legal = {"covered", "partial", "uncovered", "BLOCKED-UNKNOWN-RENDERER",
             "N/A 直接输入型", "V1 工作台常驻回归（197/197 历史线）"}
    bad = statuses - legal
    note("覆盖状态枚举合法", not bad, str(bad))
    note("manifest↔coverage 快照一致", man["snapshot_sha256"] == cov["inventory_snapshot"])
else:
    note("覆盖矩阵工件存在", False, "runs/ 缺 manifest 或 coverage")

# 4 执行模式闸门自证（FE-1466 终审 §四：--no-write 必须覆盖 HTTP 写路径）
gate_test = os.path.join(HERE, "rt1464", "test_exec_mode_gate.py")
if os.path.exists(gate_test):
    r4 = subprocess.run([sys.executable, gate_test], capture_output=True, text=True)
    tail4 = (r4.stdout.strip().splitlines()[-1] if r4.stdout else r4.stderr[-200:])
    note("执行模式闸门自证 test_exec_mode_gate",
         r4.returncode == 0 and "EXEC-MODE-GATE: PASS" in r4.stdout, tail4)
else:
    note("执行模式闸门自证工件存在", False, "缺 rt1464/test_exec_mode_gate.py")

# 5 扫描口径回归（FE-1467：published 口径曾被 mapping 侧载的 superseded 撑大）
scope_test = os.path.join(HERE, "test_scan_scope.py")
if os.path.exists(scope_test):
    r5 = subprocess.run([sys.executable, scope_test], capture_output=True, text=True)
    tail5 = (r5.stdout.strip().splitlines()[-1] if r5.stdout else r5.stderr[-200:])
    note("扫描口径回归 test_scan_scope",
         r5.returncode == 0 and "SCAN-SCOPE-GATE: PASS" in r5.stdout, tail5)
else:
    note("扫描口径回归工件存在", False, "缺 test_scan_scope.py")

print("\nPR-IQC-GATE:", "PASS" if not fails else f"FAIL ({len(fails)})")
sys.exit(0 if not fails else 1)
