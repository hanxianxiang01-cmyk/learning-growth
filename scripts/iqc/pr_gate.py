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
11. Q05 证据逐题具体化：候选证据必须逐题生成，不得跨题引用他人 RVID、
    不得并列同值错法（FE-1472）
12. Q03 第三批题意建模契约：T1–T11 含**离线回放层**（冻结快照让 CI 无库也真跑
    evaluate() 并做正负断言）；缺工件必须显式 FAIL，不得 `if os.path.exists` 静默跳过
13. 进度账实核（check_progress）：并集口径六个数字逐条实测并校验恒等式；
    **禁止减法外推**——`Q05_only` 曾被写成「38+29=67」，实际恒为 12（FE-1472）
14. 第四批核验器区分力自证：答案篡改 20/20、配置篡改 8/8 必须检出（FE-1472）
15. 第五批核验器区分力自证：**题干数字变异必须改变 computed**——证明推导读的是
    题面而非 config。这是前四批做不到的证伪方式（FE-1472）
16. 第五批语义观察项账实核：汇总 `observation_counts` 必须等于逐题重算；
    选题清单↔产物 RVID 集合、名额、过程校验声明、题干哈希逐项对账。
    针对「改总表 ≠ 改生成物」这一同型缺陷（D2 撤回时已踩过一次）（FE-1472）
17. 第六批核验器区分力自证：**题干每个数字位逐个变异**（首版只改第一个数字，
    四类题全报"未变"——是变异打偏了，不是判据失效）+ **可完成性变异**必须检出
    （题面边长改成 9 格 → INFEASIBLE），且不可完成集合精确等于 `['8b41e648']`
    （不能要求"全部 FEASIBLE"，那会逼检测器对真实缺陷说假话）（FE-1472）
18. 第六批账实核：名额按 **solve_path** 核（该族内 renderer 与 solve_path 不一一
    对应）；可完成性三个失败模式逐一核（汇总↔逐题、判 INFEASIBLE↔有观察项、
    不可完成≠免除答案核验）；全族 process_constraint 覆盖逐 renderer 交叉
    （针对「笔记写 54 题全带、现场实为 37/54」）（FE-1472）
19. 独立性口径复核（check_independence）：表达式数字来源必须 ⊆ 题干 ∪ 已登记
    编码常量；语义族覆盖必须现场重算。三类变异自证（注入题干外数字、清空分诊表、
    跨批次搜索）必须全部检出（FE-1472）
20. 第六批语义族覆盖登记：`115/212` 不能读作「各类型题都验过」——前五批 95 题
    全在 numeric_judge 一族。产物必须显式记录族名/本批数/全族数，且与逐题
    solve_path 自洽（FE-1472）
21. 第七批核验器区分力自证：**模板歧义必须 rc=2 而非 rc=1**（抽不到≠核验失败）、
    题干数字变异 16/16 模板必须检出、可完成性变异 1 检出且合法 3/3 通过
    （不能要求全部 FEASIBLE），且 `--crossbatch` 证明第六批 20 题在新规则下
    仍 MATCH（改方法不得让旧结论漂移）（FE-1472）
22. 第七批账实核 + **结构性判据**：verdict 必须与题面模板相容
    （`VERDICT_TEMPLATE_WHITELIST`）。这一项防的是自洽检查拦不住的**强洗白**：
    改 verdict + 同步汇总 + 补一条伪造观察项 + 改 verdict_note，所有自洽检查
    全部通过、0 条报警。九类变异必须全部检出（FE-1472）
23. 进度账实核**自证**：`check_progress --selftest`。本脚本此前从未自证过，
    而第七批新增的「族级清零」恰是最容易被读成「已核完」的一句。
    新增两道分母防线（改分母 54→34、清零行取声明表）都必须 FAIL（FE-1472）
24. 文档数字可复现性：`check_doc_claims`。第十三章几十个数字（35/32/54-54/
    150/62/42 条常量…）此前**全部手写、无脚本核过**，而本批已实测到一次真实
    事故（§13.3.2 把 35 写成 33，同一句还错了两处）。本项要求文档数字与产物
    逐条一致，且历史章节（十/十一/十二）不参与核对（那里的数字是当时实测值）（FE-1472）

边界（裁决 §四）：本门只判规则明确证据充分的问题；不访问生产 DB；失败输出含
rule_id+证据，不得为空。

四条硬规则（历次踩坑固化，勿放宽）：
  · 门禁不得逼内容说错话——禁止"必须至少一条 MISSING""文案必须唯一"这类
    逼人改题的条款；文档校验用正向必要内容清单而非禁词表
  · 缺工件即 `note(False)`，不静默跳过——`if os.path.exists` 式跳过是空转根因
  · 两类失效都要防：①空转（不执行核验）②误拦（合规内容被判失败）。
    第二类只能靠"合法样本必须 PASS"的定向对照证明
  · 失败时 tail 优先取含 `✗` 的行，否则真因会被统计行盖掉
"""
import json
import re
import subprocess
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
fails = []
_notes = []          # (name, ok, detail)：收尾时用于自数行数，见文件末尾
_sealed = [False]    # 行数审计是否已跑过；跑过后再 note() 即判失败

def note(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    # **封口检查**：收尾那段「门禁行数」对账一旦跑过，就把 `_sealed` 置真。
    # 此后再有 `note()` 就说明有人把新检查加在了审计**之后**——那些行不会
    # 被计数，文档写的行数会静默偏少。实测过一次：把模拟项插在审计之后，
    # 总行数由 31 变 32 而判据仍报「一致」、rc=0（反证 G 无效）。
    # 这不是靠"记得把审计放最后"，而是**让忘了这件事立刻变红**。
    if _sealed[0]:
        fails.append(f"审计后新增了未计入行数的检查项「{name}」"
                     f"——应移到审计之前，或同步更新文档行数")
    _notes.append((name, ok, detail))
    if not ok:
        fails.append(name)

def info(name, detail=""):
    """打印但不计入「PASS 行数」——给「统计/对账」类输出用。

    与 `note()` 的区别是它**不改变被统计的量**。收尾那项「门禁行数」若用
    `note()` 打，自己占一行，行数由 31 变 32，判据立刻自相矛盾。
    """
    print(f"INFO  {name}" + (f"  — {detail}" if detail else ""))

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

# 15 第五批核验器区分力自证（FE-1472）
#
#    第五批的方法学变了：前四批 `derive()` 直接读 config 算数，只能证明
#    config 内部自洽；第五批改为**先从题干文本抽数**，config 只做交叉校验。
#    因此本批的"全过"要能被三种方式证伪：
#      · 答案篡改 → 必须 MISMATCH（证明比较器不是永真）
#      · 题干数字变异 → computed 必须变（证明推导真读题面，不是读 config）
#      · config 已知量改错 → 必须 INCONSISTENT（证明一致性检查非空转）
#    第二类是前四批**做不到**的——这就是本批值得单独锁的原因。
b5_script = os.path.join(HERE, "rt1472", "q03_batch5.py")
b5_quota = os.path.join(HERE, "rt1472", "batch5_quota_list.json")
if not os.path.exists(b5_script):
    note("第五批核验器工件存在", False,
         "缺 rt1472/q03_batch5.py——不允许静默跳过")
elif not os.path.exists(b5_quota):
    note("第五批选题清单存在", False,
         "缺 rt1472/batch5_quota_list.json——没有先冻结选题集合，"
         "核验范围无法自证（第四批踩过：额定 20 实核 29，差额无法反查）")
else:
    r15 = subprocess.run([sys.executable, b5_script, "--selftest"],
                         capture_output=True, text=True)
    _boom15 = [ln.strip() for ln in (r15.stderr + r15.stdout).splitlines()
               if "✗" in ln]
    tail15 = (_boom15[0] if _boom15
              else (r15.stdout.strip().splitlines() or [""])[-1])
    note("第五批核验器区分力自证 q03_batch5 --selftest",
         r15.returncode == 0 and "Q03-BATCH5-SELFTEST: PASS" in r15.stdout, tail15)

# 16 第五批语义观察项账实核（FE-1472）
#
#    **这一项针对本项目反复出现的同型缺陷**：改总表 ≠ 改生成物。
#    2026-10-22 D2 撤回时就踩过——`KNOWN_DEFECTS` 总表改完了，
#    但 `CHECKS`/`Q05_EVIDENCE` 的字段被 `evaluate()` 原样写进结果，
#    产物里仍然写着"不可完成"。当时就是靠"生成物逐条复读"才抓到。
#    第五批的 `observation_counts` 是同类风险面：汇总说 18 条
#    `EVIDENCE_DECLARED_BUT_NOT_ENFORCED`，逐题可能一条都没有，
#    而报告依旧显示"20/20 MATCH + 18 条观察项"。
#    因此本项做纯离线逐条对账：集合 / 名额 / 观察项 / 过程校验声明 /
#    一致性计数 / 题干哈希（与冻结清单比，证明核的就是冻结那一版）。
#    脚本自带 --selftest（四种篡改必须检出），本项同时跑它。
b5_ledger = os.path.join(HERE, "rt1472", "check_batch5_ledger.py")
b5_result = os.path.join(HERE, "runs", "FE1472_q03_batch5.json")
if not os.path.exists(b5_ledger):
    note("第五批账实核工件存在", False,
         "缺 rt1472/check_batch5_ledger.py——不允许静默跳过")
elif not os.path.exists(b5_result):
    note("第五批核验产物存在", False,
         "缺 runs/FE1472_q03_batch5.json——没有产物，"
         "汇总数字无从对账，门禁会退化成只查脚本存在")
else:
    # 16a 对账本体
    r16 = subprocess.run([sys.executable, b5_ledger], capture_output=True, text=True)
    _boom16 = [ln.strip() for ln in (r16.stderr + r16.stdout).splitlines()
               if "✗" in ln]
    tail16 = (_boom16[0] if _boom16
              else (r16.stdout.strip().splitlines() or [""])[-1])
    note("第五批账实核 check_batch5_ledger",
         r16.returncode == 0 and "账实相符" in r16.stdout, tail16)

    # 16b 对账器自身区分力："账实相符"必须能被证伪
    r16s = subprocess.run([sys.executable, b5_ledger, "--selftest"],
                          capture_output=True, text=True)
    _boom16s = [ln.strip() for ln in (r16s.stderr + r16s.stdout).splitlines()
                if "✗" in ln]
    tail16s = (_boom16s[0] if _boom16s
               else (r16s.stdout.strip().splitlines() or [""])[-1])
    note("第五批账实核区分力自证 check_batch5_ledger --selftest",
         r16s.returncode == 0 and "BATCH5-LEDGER-SELFTEST: PASS" in r16s.stdout,
         tail16s)

# 17 第六批核验器区分力自证（FE-1472）
#
#    第六批换维度：前五批核的 95 题**全部是 numeric_judge**，
#    construct_constraint 54 题 0 完成。本批首次开族，因此核验器多出两类
#    前五批不存在的东西，都必须能被证伪：
#      · 题干数字变异 → computed 必须变。**注意变异构造**：首版盲目改题干
#        第一个数字，四类题全报"未变"——复查确认是变异打偏了（place-value
#        改的是卡片池而非位名指派、shape-canvas 改的是纸张尺寸而非边长、
#        sorting-board 改的是卡数量而非卡片值），不是判据失效。
#        修法是逐位试，只要有一处能让 computed 变即可。
#      · 可完成性变异 → 题面边长改成 9 格必须判 INFEASIBLE。
#        这一条如果空转，`feasibility` 整个维度就是装饰。
#    同时**反向对照**：不可完成集合必须精确等于 ['8b41e648']。
#    不能要求"全部 FEASIBLE"——那会逼检测器对真实缺陷说假话。
b6_script = os.path.join(HERE, "rt1472", "q03_batch6.py")
b6_quota = os.path.join(HERE, "rt1472", "batch6_quota_list.json")
if not os.path.exists(b6_script):
    note("第六批核验器工件存在", False,
         "缺 rt1472/q03_batch6.py——不允许静默跳过")
elif not os.path.exists(b6_quota):
    note("第六批选题清单存在", False,
         "缺 rt1472/batch6_quota_list.json——没有先冻结选题集合，"
         "核验范围无法自证")
else:
    r17 = subprocess.run([sys.executable, b6_script, "--selftest"],
                         capture_output=True, text=True)
    _boom17 = [ln.strip() for ln in (r17.stderr + r17.stdout).splitlines()
               if "✗" in ln]
    tail17 = (_boom17[0] if _boom17
              else (r17.stdout.strip().splitlines() or [""])[-1])
    note("第六批核验器区分力自证 q03_batch6 --selftest",
         r17.returncode == 0 and "Q03-BATCH6-SELFTEST: PASS" in r17.stdout, tail17)

# 18 第六批账实核（FE-1472）
#
#    本项的对账维度与第 16 项不同，不是复制：
#      · 名额按 **solve_path** 核（该族内 renderer 与 solve_path 不一一对应，
#        按 renderer 核会让 pattern-board 被拆成两半而看不出覆盖）
#      · **可完成性三个失败模式**逐一核：汇总说有→逐题必须有；判了 INFEASIBLE
#        →必须有对应观察项（否则结论游离在观察项之外）；判了 INFEASIBLE
#        →答案判定不得缺失（可完成性不能替代答案核验）
#      · **全族 process_constraint 覆盖**逐 renderer 交叉：全族说某 renderer
#        0 题带 pc，本批同类必须也是 0。这条针对"笔记与现场不符"——
#        上一轮笔记写"54 题全部带 pc"，现场实为 37/54。
b6_ledger = os.path.join(HERE, "rt1472", "check_batch6_ledger.py")
b6_result = os.path.join(HERE, "runs", "FE1472_q03_batch6.json")
if not os.path.exists(b6_ledger):
    note("第六批账实核工件存在", False,
         "缺 rt1472/check_batch6_ledger.py——不允许静默跳过")
elif not os.path.exists(b6_result):
    note("第六批核验产物存在", False,
         "缺 runs/FE1472_q03_batch6.json——没有产物，"
         "汇总数字无从对账，门禁会退化成只查脚本存在")
else:
    r18 = subprocess.run([sys.executable, b6_ledger], capture_output=True, text=True)
    _boom18 = [ln.strip() for ln in (r18.stderr + r18.stdout).splitlines()
               if "✗" in ln]
    tail18 = (_boom18[0] if _boom18
              else (r18.stdout.strip().splitlines() or [""])[-1])
    note("第六批账实核 check_batch6_ledger",
         r18.returncode == 0 and "账实相符" in r18.stdout, tail18)

    r18s = subprocess.run([sys.executable, b6_ledger, "--selftest"],
                          capture_output=True, text=True)
    _boom18s = [ln.strip() for ln in (r18s.stderr + r18s.stdout).splitlines()
                if "✗" in ln]
    tail18s = (_boom18s[0] if _boom18s
               else (r18s.stdout.strip().splitlines() or [""])[-1])
    note("第六批账实核区分力自证 check_batch6_ledger --selftest",
         r18s.returncode == 0 and "BATCH6-LEDGER-SELFTEST: PASS" in r18s.stdout,
         tail18s)

# 19 独立性口径复核（check_independence，FE-1472）
#
#    动机：文档里"95 题都做了独立推导"这句话，如果没有脚本可重现，
#    就只是某次人工编辑的快照（项目铁律）。本项锁两条可机器判定的口径：
#      A 表达式数字来源：derivation.expr 里的每个数字，要么在题干里，
#        要么已显式登记为编码常量（位权）。**只有分诊表能判决**——
#        "编码常量"与"抄 config"在数字层面无法区分，脚本只出线索。
#      B 语义族覆盖：分族统计必须现场重算，不能沿用上一轮的结论。
#    本项的三类变异：注入题干外数字必须被检出、清空分诊表必须报错、
#    跨批次搜索必须能找到目标题（首版只在最后一批里找，误报"未被检出"
#    ——那是变异构造错，不是判据失效）。
indep = os.path.join(HERE, "rt1472", "check_independence.py")
if not os.path.exists(indep):
    note("独立性口径复核工件存在", False,
         "缺 rt1472/check_independence.py——不允许静默跳过")
else:
    r19 = subprocess.run([sys.executable, indep, "--selftest"],
                         capture_output=True, text=True)
    _boom19 = [ln.strip() for ln in (r19.stderr + r19.stdout).splitlines()
               if "✗" in ln]
    tail19 = (_boom19[0] if _boom19
              else (r19.stdout.strip().splitlines() or [""])[-1])
    note("独立性口径复核自证 check_independence --selftest",
         r19.returncode == 0 and "INDEPENDENCE-SELFTEST: PASS" in r19.stdout,
         tail19)

# 20 第六批语义族覆盖缺口登记（FE-1472）
#
#    **这一项防的是"数字掩盖事实"**：「115/212 完成」听起来过半，
#    但前五批 95 题全在一个族里，第六批才刚开第二个族，第三个族仍是 0。
#    若只看总数，会误判"各类型题都验过了"。因此本项要求产物里
#    显式记录族覆盖，且覆盖数与逐题结论自洽（不是抄一个常量）。
#    判据：construct_constraint 本批完成数 == 产物题数；family_total 有据；
#    且 check_progress 的族覆盖与产物相互印证。
if not os.path.exists(b6_result):
    note("语义族覆盖登记工件存在", False,
         "缺 runs/FE1472_q03_batch6.json")
else:
    _b6 = json.load(open(b6_result, encoding="utf-8"))
    _fs = _b6.get("family_scope") or {}
    _n = len(_b6.get("items") or [])
    _ok20 = (
        _fs.get("semantic_family") == "construct_constraint"
        and _fs.get("verified_here") == _n
        and isinstance(_fs.get("total_in_family"), int)
        and _fs["total_in_family"] > _n
        and sum(1 for it in _b6.get("items") or []
                if (it.get("solve_path") or "") in
                (("digit_config", "geometry_constraint",
                  "numeric_exact", "sequence_order"))) == _n
    )
    note("第六批语义族覆盖登记", _ok20,
         f"family={_fs.get('semantic_family')} 本批 {_fs.get('verified_here')}"
         f"/全族 {_fs.get('total_in_family')}；题数 {_n}")

# 21 第七批核验器区分力自证（FE-1472）
#
#    第七批的方法学又变了一层：第六批「边写边补正则」只覆盖那 20 题的写法，
#    本批 35 题实测会让第六批规则**静默算错 1 题**（money-board 靠「另一件」
#    三字判两件相加，缺这三个字就只取首个标价 10，真值 15——不报错、不崩溃，
#    静默产出错值，然后被判成 MISMATCH，看起来像题库错了）。
#    故本批改成**题面模板显式登记**，每题必须恰好命中一个模板。
#    本项锁四件事：
#      · 答案篡改 32/32 必须检出（比较器非永真）
#      · 题干数字变异 16/16 模板必须检出（推导真读题面）
#      · 可完成性变异 1 检出、**合法 3/3 通过**——不能要求「全部 FEASIBLE」，
#        那会逼检测器对真实缺陷说假话（唯一不可完成的 8b41e648 在第六批）
#      · `--crossbatch`：第六批 20 题在新规则下必须仍 MATCH。这一条防的是
#        「为让新批好看，把旧批的判据也悄悄改松」——改方法不得让旧结论漂移
b7_script = os.path.join(HERE, "rt1472", "q03_batch7.py")
b7_quota = os.path.join(HERE, "rt1472", "batch7_quota_list.json")
if not os.path.exists(b7_script):
    note("第七批核验器工件存在", False,
         "缺 rt1472/q03_batch7.py——不允许静默跳过")
elif not os.path.exists(b7_quota):
    note("第七批选题清单存在", False,
         "缺 rt1472/batch7_quota_list.json——没有先冻结选题集合，"
         "「两族清零」这句话就无法自证是 35 题全取而非抽样")
else:
    r21 = subprocess.run([sys.executable, b7_script, "--selftest"],
                         capture_output=True, text=True)
    _boom21 = [ln.strip() for ln in (r21.stderr + r21.stdout).splitlines()
               if "✗" in ln]
    tail21 = (_boom21[0] if _boom21
              else (r21.stdout.strip().splitlines() or [""])[-1])
    note("第七批核验器区分力自证 q03_batch7 --selftest",
         r21.returncode == 0 and "Q03-BATCH7-SELFTEST: PASS" in r21.stdout, tail21)

    # 21b 跨批回归：新规则跑旧批，结论不得漂移
    r21b = subprocess.run([sys.executable, b7_script, "--crossbatch"],
                          capture_output=True, text=True)
    _boom21b = [ln.strip() for ln in (r21b.stderr + r21b.stdout).splitlines()
                if "✗" in ln]
    tail21b = (_boom21b[0] if _boom21b
               else (r21b.stdout.strip().splitlines() or [""])[-1])
    note("第七批跨批回归 q03_batch7 --crossbatch",
         r21b.returncode == 0 and "CROSSBATCH: PASS" in r21b.stdout, tail21b)

# 22 第七批账实核 + 结构性判据（FE-1472）
#
#    **本项防的是自洽检查拦不住的「强洗白」**（本批最重要的发现）：
#    把一道已核题改 verdict + 同步汇总 + 补一条伪造观察项 + 改 verdict_note，
#    于是「汇总=逐题」「观察项↔verdict 对应」「note 与 verdict 相符」全部通过，
#    **0 条报警**——因为它保持了内部一致性，而自洽检查只查一致性。
#    唯一有效解法是**结构性判据**：verdict 必须与题面模板相容
#    （`VERDICT_TEMPLATE_WHITELIST`）。依据是语义而不是数据：
#    `UNVERIFIABLE_FROM_STEM` 的含义决定了只有 estimation 模板可能适用。
b7_ledger = os.path.join(HERE, "rt1472", "check_batch7_ledger.py")
b7_result = os.path.join(HERE, "runs", "FE1472_q03_batch7.json")
if not os.path.exists(b7_ledger):
    note("第七批账实核工件存在", False,
         "缺 rt1472/check_batch7_ledger.py——不允许静默跳过")
elif not os.path.exists(b7_result):
    note("第七批核验产物存在", False,
         "缺 runs/FE1472_q03_batch7.json——没有产物，"
         "「两族清零」无从对账，门禁会退化成只查脚本存在")
else:
    r22 = subprocess.run([sys.executable, b7_ledger], capture_output=True, text=True)
    _boom22 = [ln.strip() for ln in (r22.stderr + r22.stdout).splitlines()
               if "✗" in ln]
    tail22 = (_boom22[0] if _boom22
              else (r22.stdout.strip().splitlines() or [""])[-1])
    note("第七批账实核 check_batch7_ledger",
         r22.returncode == 0 and "账实相符" in r22.stdout, tail22)

    r22s = subprocess.run([sys.executable, b7_ledger, "--selftest"],
                          capture_output=True, text=True)
    _boom22s = [ln.strip() for ln in (r22s.stderr + r22s.stdout).splitlines()
                if "✗" in ln]
    tail22s = (_boom22s[0] if _boom22s
               else (r22s.stdout.strip().splitlines() or [""])[-1])
    note("第七批账实核区分力自证 check_batch7_ledger --selftest",
         r22s.returncode == 0 and "BATCH7-LEDGER-SELFTEST: PASS" in r22s.stdout,
         tail22s)

# 23 进度账实核自证（check_progress --selftest，FE-1472）
#
#    第 13 项只跑 audit（账实是否相符），**从不自证**。
#    而第七批新增的「族级清零」是整份文档里最容易被读成「已核完」的一句话，
#    若它恒真，读者无法分辨「54/54」与「34/34 被当成清零」。
#    本项锁两道分母防线（都是本轮新增）：
#      P4 把全族总量 54 改成 34 → 必须 FAIL（只核分子时改分母可洗成 100%）
#      P6 清零行若取声明表 → 打印 n/n 恒真式，必须 FAIL
#    P6 的判据第一版无效（未清零行也打印 54/54，能蒙过），
#    现已改成「让分子分母故意不等」——取产物打印 53/54，取声明表打印 53/53。
#
#    **P6 又出过一次真实漏洞（#135 独立复核发现）**：
#    实现里 `cleared` 用 `EXPECTED_FAMILY_TOTAL`（人工声明）当分母，
#    声明被同步改小时该族被判为「覆盖完成」；而判据只问「有没有 53/54」，
#    没问它落在哪一栏，于是错误实现照样 PASS。
#    现修法有三条，缺一可绕：
#      · `cleared` / `not_cleared` 一律取实测 `fam_total`；
#      · P6 定向断言 `53/54` **在**「未覆盖完成」栏、**不在**「覆盖完成」栏；
#      · P6b 未在声明表登记的族仍须出现在缺口栏（防缺口枚举退回声明表）。
#    反向对照：注入「声明分母」→ 8/9 FAIL；注入「缺口枚举取声明表」→ 9/10 FAIL。
if not os.path.exists(prog_check):
    note("进度账实核自证工件存在", False, "缺 rt1472/check_progress.py")
else:
    r23 = subprocess.run([sys.executable, prog_check, "--selftest"],
                         capture_output=True, text=True)
    _boom23 = [ln.strip() for ln in (r23.stderr + r23.stdout).splitlines()
               if "✗" in ln]
    tail23 = (_boom23[0] if _boom23
              else (r23.stdout.strip().splitlines() or [""])[-1])
    note("进度账实核自证 check_progress --selftest",
         r23.returncode == 0 and "PROGRESS-SELFTEST: PASS" in r23.stdout, tail23)

# 24 文档数字可复现性（check_doc_claims，FE-1472）
#
#    项目铁律：「产物里的分析结论若不能由脚本重现，就只是某次人工编辑的快照」。
#    第十三章有几十个数字，此前**全部手写、没有任何脚本核过**，
#    而本批已经实测到一次真实事故：§13.3.2 把「32+3」算成 33（应为 35），
#    同一句还把容差说成对三题都适用——两处错，通读发现不了。
#    本项要求文档数字与产物逐条一致。
#    **历史章节（十/十一/十二）不参与核对**：那里的数字是当时实测值，
#    改成今天的值反而是错的——本脚本按 `## 十三、` 起点截断。
doc_check = os.path.join(HERE, "rt1472", "check_doc_claims.py")
doc_path = os.path.join(REPO, "docs", "qa", "FE1469_FE1470_Q03_BATCHES.md")
if not os.path.exists(doc_check):
    note("文档数字核对工件存在", False,
         "缺 rt1472/check_doc_claims.py——不允许静默跳过")
elif not os.path.exists(doc_path):
    note("第七批文档存在", False, f"缺 {doc_path}")
else:
    r24 = subprocess.run([sys.executable, doc_check], capture_output=True, text=True)
    _boom24 = [ln.strip() for ln in (r24.stderr + r24.stdout).splitlines()
               if "✗" in ln]
    tail24 = (_boom24[0] if _boom24
              else (r24.stdout.strip().splitlines() or [""])[-1])
    note("文档数字可复现性 check_doc_claims",
         r24.returncode == 0 and "文档数字与产物一致" in r24.stdout, tail24)

    r24s = subprocess.run([sys.executable, doc_check, "--selftest"],
                          capture_output=True, text=True)
    _boom24s = [ln.strip() for ln in (r24s.stderr + r24s.stdout).splitlines()
                if "✗" in ln]
    tail24s = (_boom24s[0] if _boom24s
               else (r24s.stdout.strip().splitlines() or [""])[-1])
    note("文档数字核对区分力自证 check_doc_claims --selftest",
         r24s.returncode == 0 and "DOC-CLAIMS-SELFTEST: PASS" in r24s.stdout,
         tail24s)

# ── 门禁行数与文档对账（**自数自核**）──
#
# 「24 项」与「31 个 PASS 行」**不是一个量**：一项可能打多行（第 3 项拆成
# 3 行；第五/六/七批各是「账实核 + 自证」两行；第 24 项拆成 audit + 自证）。
# 此前文档与交接记录都写「32 行 PASS」，实为 31——**写错了 1，且全靠手记**。
# 现有判据全查不出：本门自己报 `24/24 PASS`（只说项数，不说行数），
# `check_doc_claims` 核的是别的数字。**两个都写着 PASS 的不同量，最容易被
# 当成同一个数**——「总数正确、分类错误」那个错型换了个壳。
#
# 两处必须小心，都是本轮实踩的：
#
#  ① 不能用 `note()`。第一版写成 `note(...)`，于是**检查自己占了一行**，
#     行数由 31 变 32、判据立刻 FAIL。这就是「判据的存在改变了被测量」：
#     一旦它算进自己，所谓"核对 31 行"就永远自相矛盾；若再顺手把文档
#     改成 32，下次加任何一项又要改文档——**数字随判据漂移**。
#     故这里用 `info()`：打印但不计入行数，失败仍走 `fails` 硬 FAIL。
#  ② 不能由 `check_doc_claims` 反向调本脚本核：
#     `pr_gate → check_doc_claims → pr_gate` 递归，实测 SIGTERM 137。
#     **计数主体自己数自己，才不循环**。
# 「24 项」也不能手写：它同样是会随加项漂移的量。项数取**头部编号清单
# 的行数**（`NN.` 开头那几行），那是本文件对"一共有几项门禁"的唯一声明。
_here = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(_here, "pr_gate.py"), encoding="utf-8").read()
_doc = _src.split('"""')[1] if _src.count('"""') >= 2 else ""
_n_items = sum(1 for _ln in _doc.splitlines()
               if re.match(r"^\s*\d+\.\s", _ln))
# 防「解析失败被当成 0 项」：清单被改格式（如改成 `1)` 或去掉编号）时，
# `_n_items` 会静默变 0，而文档里若也写 0 项就"一致"了——**解析失配冒充正确结论**。
if _n_items < 10:
    fails.append(f"门禁项数解析异常：只解析出 {_n_items} 项"
                 f"——头部编号清单格式被改动了？")
_n_pass = sum(1 for _n, _ok, _d in _notes if _ok)
_n_fail = sum(1 for _n, _ok, _d in _notes if not _ok)
_docp = os.path.join(REPO, "docs", "qa", "FE1469_FE1470_Q03_BATCHES.md")
_want = f"门禁 **{_n_items} 项 / {_n_pass} 个 PASS 行**（0 FAIL）"
_ok_row = False
if not os.path.isfile(_docp):
    fails.append(f"门禁行数对账：缺 {_docp}")
else:
    _txt = open(_docp, encoding="utf-8").read()
    _ok_row = (_n_fail == 0 and _want in _txt)
    if not _ok_row:
        fails.append(
            f"门禁行数与文档不一致：实测 {_n_pass} 个 PASS 行 / "
            f"{_n_fail} 个 FAIL 行，文档应为「{_want}」")
_sealed[0] = True   # 之后任何 note() 都会被抓（见 note() 内封口检查）
info("门禁行数（不计入行数本身）",
     f"{_n_pass} 个 PASS 行 / {_n_fail} 个 FAIL 行"
     f" → 文档{'一致' if _ok_row else '不一致'}")

# ── 失败明细必须打印出来（**否则 FAIL 只是一句骂人话**）──
#
# 实测踩到：收尾两项对账失败时只印 `PR-IQC-GATE: FAIL (2)`，
# **两条原因一条都没输出**——因为 `fails` 里存的是名字/字符串，而收尾
# 从来没有把内容打出来。`note()` 失败时会印一行，但**直接
# `fails.append(...)` 的（收尾对账就是这种）不会**。
# 读者拿到的信息量等于「有个东西错了」，与「无输出」没区别。
# 这与本项目记的「报错吞掉判据 = 空转」是同一边的：**失败不可诊断，
# 与不失败同效**——都会被下一个人当成噪音跳过。
print("\nPR-IQC-GATE:", "PASS" if not fails else f"FAIL ({len(fails)})")
# 明细打在结论**之后**：stderr 与 stdout 交错时，明细若在前会被后面几十行
# PASS 冲散，读 CI 日志的人照样看不见。结论+明细连在一起才有用。
if fails:
    print("\n**门禁失败明细**：")
    for _i, _f in enumerate(fails, 1):
        print(f"  {_i}. {_f}")
sys.exit(0 if not fails else 1)
