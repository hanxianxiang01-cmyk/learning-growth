#!/usr/bin/env python3
"""FE-1463 PR 增量质量门（DB-free，确定性，进 ci.yml）。

七检查（任一 FAIL=退出非零阻断合并）：
1. 规则夹具回归：test_checks.py 25 负例全锁（已知缺陷可检出/已知非缺陷不误报）
2. 契约自检：rules.json iqc 块完整 + 夹具数据分离纪律（skill 侧检查的仓内镜像，
   skill 目录不在 CI checkout 内时降级 SKIP 并显式打印，不谎称已验）
3. 覆盖矩阵一致性：committed inventory manifest 中所有 renderer 必须
   (a) 在 rendererRegistry 协议枚举内，(b) 状态只允许 covered/partial/uncovered/
   BLOCKED-UNKNOWN-RENDERER——未登记 renderer=FAIL，禁止静默新增
4. 执行模式闸门自证：--no-write 须覆盖 POST + 有副作用的 GET + SQL；且用注入
   transport **计数**证明（而非"捕获到异常"证明），含属性恢复回归锁（终审 §四）
5. 扫描口径回归：published 口径不得被 mapping 侧载的 superseded 撑大（FE-1467）
6. 基线降级出处回归：211/212 须能从历史工件复算、单位口径须是 findings 数、
   历史工件哈希须冻结（FE-1467 §五 + 2026-10-21 复审 §二.3）
7. 静态可调用性：禁止"调用了未定义的辅助函数"与"except Exception 静默吞掉"
   （2026-10-21 复审：_post 定义被删却仍被调用，靠静默 except 躲过两轮）
8. 语义族判据回归：分族是启发式，错判不报错只会静默改结果，所以用真实题面
   锁住已知事故（乘号 × 被当判断词、构造动词漏词、判据互为冗余兜底）（FE-1468）
9. 核验结果与输入绑定：Q03 结论必须能指到冻结清单里的题目哈希，
   引用≠重算即漂移、缺原件即漂移；q05 只写候选不写结论（FE-1469）
10. 比对效力边界：改存储答案只能证明比较器非永真，改配置独立事实才能证明
    推导依赖题面；必要条件不成立必须受控拒绝（FE-1470）
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

# 6 基线降级出处回归（FE-1467 §五：211/212 降级必须有可复算出处，且工件被篡改要报错）
prov_test = os.path.join(HERE, "rt1464", "test_baseline_provenance.py")
if os.path.exists(prov_test):
    r6 = subprocess.run([sys.executable, prov_test], capture_output=True, text=True)
    tail6 = (r6.stdout.strip().splitlines()[-1] if r6.stdout else r6.stderr[-200:])
    note("基线降级出处回归 test_baseline_provenance",
         r6.returncode == 0 and "BASELINE-PROVENANCE-GATE: PASS" in r6.stdout, tail6)
else:
    note("基线降级出处回归工件存在", False, "缺 rt1464/test_baseline_provenance.py")

# 7 静态可调用性（2026-10-21 复审：_post 定义被删、调用点却留着，
#   而 submitter 里的 except Exception 把 NameError 吞掉了两轮）
static_test = os.path.join(HERE, "test_static_callables.py")
if os.path.exists(static_test):
    r7 = subprocess.run([sys.executable, static_test], capture_output=True, text=True)
    tail7 = (r7.stdout.strip().splitlines()[-1] if r7.stdout else r7.stderr[-200:])
    note("静态可调用性 test_static_callables",
         r7.returncode == 0 and "STATIC-CALLABLE-GATE: PASS" in r7.stdout, tail7)
else:
    note("静态可调用性工件存在", False, "缺 test_static_callables.py")

# 8 语义族判据回归（FE-1468：分族是启发式，判错不会有任何报错，
#   只能靠真实题面做定点回归。已知事故：× 当判断词、动词漏词、规则冗余兜底）
fam_test = os.path.join(HERE, "rt1468", "test_worklist_family.py")
if os.path.exists(fam_test):
    r8 = subprocess.run([sys.executable, fam_test], capture_output=True, text=True)
    tail8 = (r8.stdout.strip().splitlines()[-1] if r8.stdout else r8.stderr[-200:])
    note("语义族判据回归 test_worklist_family",
         r8.returncode == 0 and "FAMILY-GATE: PASS" in r8.stdout, tail8)
else:
    note("语义族判据回归工件存在", False, "缺 rt1468/test_worklist_family.py")

# 9 核验结果与输入绑定（FE-1469 复审 §一.1：结论必须能指到冻结原件的哈希。
#   这里锁的是判定逻辑本身：引用≠重算 / 缺原件 / 两者皆缺，都必须算漂移——
#   否则"题目改了还沿用旧结论"和"没原件也当通过"都会静默发生）
bind_test = os.path.join(HERE, "rt1469", "test_q03_binding.py")
if os.path.exists(bind_test):
    r9 = subprocess.run([sys.executable, bind_test], capture_output=True, text=True)
    tail9 = (r9.stdout.strip().splitlines()[-1] if r9.stdout else r9.stderr[-200:])
    note("核验输入绑定回归 test_q03_binding",
         r9.returncode == 0 and "BINDING-GATE: PASS" in r9.stdout, tail9)
else:
    note("核验输入绑定回归工件存在", False, "缺 rt1469/test_q03_binding.py")

# 10 比对效力边界（FE-1470 复审 §三：改存储答案只能证明比较器非永真，
#    不能证明题干解析正确。这里锁 B/C 两组：改配置独立事实输出必须变、
#    必要条件不成立必须受控拒绝——这两组才是"推导真的读了题面"的证据）
neg_test = os.path.join(HERE, "rt1470", "test_batch2_negative.py")
if os.path.exists(neg_test):
    r10 = subprocess.run([sys.executable, neg_test], capture_output=True, text=True)
    tail10 = (r10.stdout.strip().splitlines()[-1] if r10.stdout else r10.stderr[-200:])
    note("比对效力边界 test_batch2_negative",
         r10.returncode == 0 and "BATCH2-NEGATIVE-GATE: PASS" in r10.stdout, tail10)
else:
    note("比对效力边界工件存在", False, "缺 rt1470/test_batch2_negative.py")

# 11 Q05 可观察证据逐题具体化（FE-1470 复审 §二.4：上一版 22 条
#    `requirement` 全是同一句通用说明，等于「免责只写在 not_concluded、
#    其余字段仍在直接诊断孩子」。这里锁两件事：不许套模板、不许空口诊断）
q05_test = os.path.join(HERE, "rt1470", "test_q05_evidence.py")
if os.path.exists(q05_test):
    r11 = subprocess.run([sys.executable, q05_test], capture_output=True, text=True)
    tail11 = (r11.stdout.strip().splitlines()[-1] if r11.stdout else r11.stderr[-200:])
    note("Q05 证据逐题具体化 test_q05_evidence",
         r11.returncode == 0 and "Q05-EVIDENCE-GATE: PASS" in r11.stdout, tail11)
else:
    note("Q05 证据回归工件存在", False, "缺 rt1470/test_q05_evidence.py")

# 12 Q03 第三批题意建模契约（FE-1471 §七：①known 角色不天然是独立事实
#    ②保留手工推导真实性质 ③五类关系题面层判据）。
#
#    ★ 2026-10-21 复审实锤：本项此前是 `if os.path.exists(...)` 包裹的，
#    删掉 test_batch3_contract.py 后第 12 项会**静默消失**并在第 13 项位置
#    补一条「缺工件」——但如果只在末尾按 fails 判断，缺文件时整段被跳过，
#    门禁仍然 PASS。缺了验证对象却报通过，是比失败更坏的结果。
#    因此本项改为**缺失即显式 note(False)**，且额外把冻结输入快照一起纳入存在性检查。
b3_test = os.path.join(HERE, "rt1471", "test_batch3_contract.py")
b3_snap = os.path.join(HERE, "rt1471", "batch3_frozen_inputs.json")
if not os.path.exists(b3_test):
    note("Q03 第三批题意建模契约工件存在", False,
         "缺 rt1471/test_batch3_contract.py——不允许静默跳过")
elif not os.path.exists(b3_snap):
    note("Q03 第三批冻结输入快照存在", False,
         "缺 rt1471/batch3_frozen_inputs.json——没有快照，"
         "门禁无法离线回放 evaluate()，会退化成只查结构的空转门禁")
else:
    r12 = subprocess.run([sys.executable, b3_test], capture_output=True, text=True)
    tail12 = (r12.stdout.strip().splitlines()[-1] if r12.stdout else r12.stderr[-200:])
    note("Q03 第三批题意建模契约 test_batch3_contract",
         r12.returncode == 0 and "Q03-BATCH3-GATE: PASS" in r12.stdout, tail12)

# 13 第四批进度账实核（FE-1472）
#
#    动机是真实事故：§5.8.5 上一版把 `Q05_only` 写成「38 + 29 = 67」，
#    实际它是**固定集合归属**、一直是 12 且从未被消耗。这类"文档里按减法
#    外推"的数字靠人算抓不住——必须逐条数出来并进 CI。
#    因此本项核对：并集口径六个数字 + 各批产物是否存在且自洽 + 去重完成数。
#    同样**缺失即失败**，不静默跳过。
prog_check = os.path.join(HERE, "rt1472", "check_progress.py")
if not os.path.exists(prog_check):
    note("第四批进度账实核工件存在", False,
         "缺 rt1472/check_progress.py——不允许静默跳过")
else:
    r13 = subprocess.run([sys.executable, prog_check],
                         capture_output=True, text=True)
    # 失败时不能只取 stdout 最后一行——那是统计输出，会把真正的原因盖掉。
    # 优先取 stderr/stdout 里的 ✗ 行。
    _boom = [ln.strip() for ln in (r13.stderr + r13.stdout).splitlines()
             if "✗" in ln]
    tail13 = (_boom[0] if _boom
              else (r13.stdout.strip().splitlines() or [""])[-1])
    note("第四批进度账实核 check_progress",
         r13.returncode == 0 and "账实相符" in r13.stdout, tail13)

# 14 第四批核验器区分力自证（FE-1472）
#
#    第四批 20 题全 MATCH——"全过"必须被证伪，否则等于没验。
#    本项不是重跑核验，而是检查核验器**确实具备区分力**：
#      · evaluate() 对篡改后的 answer 必须给 MISMATCH；
#      · 逐题 Q05 不得跨题引用他人 RVID、不得并列同值错法。
#    前者是本批实做过的变异（20/20 检出 + 7/7 配置篡改检出），
#    这里固化为回归，防止后续改 derive() 时把区分力改没。
b4_script = os.path.join(HERE, "rt1472", "q03_batch4.py")
b4_quota = os.path.join(HERE, "rt1472", "batch4_quota_list.json")
if not os.path.exists(b4_script):
    note("第四批核验器工件存在", False,
         "缺 rt1472/q03_batch4.py——不允许静默跳过")
elif not os.path.exists(b4_quota):
    note("第四批选题清单存在", False,
         "缺 rt1472/batch4_quota_list.json——没有先冻结选题集合，"
         "核验范围无法自证")
else:
    r14 = subprocess.run([sys.executable, b4_script, "--selftest"],
                         capture_output=True, text=True)
    _boom14 = [ln.strip() for ln in (r14.stderr + r14.stdout).splitlines()
               if "✗" in ln]
    tail14 = (_boom14[0] if _boom14
              else (r14.stdout.strip().splitlines() or [""])[-1])
    note("第四批核验器区分力自证 q03_batch4 --selftest",
         r14.returncode == 0 and "Q03-BATCH4-SELFTEST: PASS" in r14.stdout, tail14)

print("\nPR-IQC-GATE:", "PASS" if not fails else f"FAIL ({len(fails)})")
sys.exit(0 if not fails else 1)
