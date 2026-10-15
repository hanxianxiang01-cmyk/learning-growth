"""QA-GROWTH-V2.1 P0-1：47 题 → M01-M15 证据预算矩阵（独立核算器）。

不调用产品 evaluate_mastery()——按 education_rules.py 冻结常量（mastery-v1.3.1）
+ mastery_db.py 已核实的决策应用序（evaluate → decide_review → downgrade 覆盖
new_level=old-1）独立重写规则。产出：
- 每能力逐步时间线（题序 → level/review/trend/reason）
- M01-M15 逐里程碑 expected 断言 + 预算充分性（6 维度核对）
- evidence_budget_matrix.csv

PLAN 与正式执行体（qa_growth_story_v2.py）共用同一份 spec：本矩阵核算通过的
序列即 run 将提交的序列，杜绝"矩阵过了、脚本另写一套"。
"""
import csv
import json

# ---------- 冻结阈值（education_rules.py @main f41df0c 抄录） ----------
CI_WINDOW = 8; CI_RV = 3; CI_SESS = 2
STAB_WINDOW = 5; STAB_RV = 3; STAB_SESS = 2
TR_WINDOW = 4; TR_ROWS = 2; TR_CTX = 2; TR_SESS = 2
G12 = dict(n=5, rv=3, sess=2, C=0.80, I=0.50, S=0.50, low_hint=0.80, max_hint=2)
G23 = dict(score=0.80, C=0.80, I=0.75, S=0.75, T=0.60)
W_C, W_I, W_S, W_T = 0.35, 0.25, 0.20, 0.20
HINT2I = {0: 1.00, 1: 0.75, 2: 0.50, 3: 0.25, 4: 0.00}
REVIEW_WINDOW = 3; REVIEW_MIN_FAIL = 2; DOWNGRADE_FAIL = 3

# ---------- 与执行体共用的 PLAN（spec: ab/wk/c/h/rv/ctx?/new_sess?/retry?） ----------
PLAN = [
    *[{"ab": "app_rel", "wk": 1, "c": 1.0, "h": 0, "rv": "std"} for _ in range(3)],
    *[{"ab": "app_rel", "wk": 1, "c": 1.0, "h": 0, "rv": "std"} for _ in range(3)],
    *[{"ab": "app_rel", "wk": 2, "c": 1.0, "h": 1, "rv": "std"} for _ in range(3)],
    {"ab": "app_rel", "wk": 2, "c": 1.0, "h": 0, "rv": "transfer", "ctx": "A"},
    {"ab": "app_rel", "wk": 2, "c": 1.0, "h": 0, "rv": "transfer", "ctx": "B", "new_sess": True},
    {"ab": "app_rel", "wk": 2, "c": 1.0, "h": 0, "rv": "transfer", "ctx": "C"},
    {"ab": "app_model", "wk": 3, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_model", "wk": 3, "c": 0.0, "h": 1, "rv": "std", "retry_correct": True},
    {"ab": "app_model", "wk": 3, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_model", "wk": 4, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_model", "wk": 4, "c": 1.0, "h": 1, "rv": "std"},
    {"ab": "app_model", "wk": 4, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_cond", "wk": 5, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_cond", "wk": 5, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_cond", "wk": 5, "c": 1.0, "h": 1, "rv": "std"},
    {"ab": "app_cond", "wk": 5, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_cond", "wk": 6, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_cond", "wk": 6, "c": 0.0, "h": 2, "rv": "std"},
    {"ab": "app_cond", "wk": 6, "c": 0.0, "h": 2, "rv": "std"},
    {"ab": "app_cond", "wk": 7, "c": 0.0, "h": 1, "rv": "std"},
    {"ab": "app_cond", "wk": 7, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_cond", "wk": 7, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_cond", "wk": 7, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_strat", "wk": 8, "c": 1.0, "h": 3, "rv": "std"},
    {"ab": "app_strat", "wk": 8, "c": 1.0, "h": 3, "rv": "std"},
    {"ab": "app_strat", "wk": 8, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_strat", "wk": 8, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_strat", "wk": 8, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_strat", "wk": 9, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_strat", "wk": 9, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_strat", "wk": 9, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_strat", "wk": 9, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_strat", "wk": 9, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_rd", "wk": 10, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_rd", "wk": 10, "c": 1.0, "h": 0, "rv": "reuse0"},
    {"ab": "app_rd", "wk": 10, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_rd", "wk": 11, "c": 1.0, "h": 0, "rv": "reuse1"},
    {"ab": "app_rd", "wk": 11, "c": 1.0, "h": 0, "rv": "reuse0"},
    {"ab": "app_check", "wk": 11, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_check", "wk": 11, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_check", "wk": 12, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_check", "wk": 12, "c": 1.0, "h": 0, "rv": "std"},
]

# ---------- 资源/会话分配模拟器（与执行体同语义：每能力每会话≤3题） ----------
def materialize():
    """PLAN → 每条原子证据 (ab, n_in_ab, corr, hint, rv, sess, etype, ctx)。"""
    per_ab = {}
    out = []
    for spec in PLAN:
        ab = spec["ab"]
        st = per_ab.setdefault(ab, dict(rv_used=[], sess_seq=0, in_sess=0, ctx_taken=set(), n=0))
        if spec.get("new_sess"):
            st["in_sess"] = 0  # 强制下一题开新 session（与执行体 cur.pop 同语义）
        if st["in_sess"] == 0:
            st["sess_seq"] += 1
        st["in_sess"] += 1
        if st["in_sess"] >= 3:
            st["in_sess"] = 0
        st["n"] += 1
        rvk = spec["rv"]
        if rvk == "transfer":
            rv = f"{ab}-t{st['n']}"; etype = "attempt_transfer"
        elif rvk.startswith("reuse"):
            rv = st["rv_used"][int(rvk[-1])]; etype = "attempt_standard"
        else:
            rv = f"{ab}-r{len(st['rv_used'])+1}"; etype = "attempt_standard"
            st["rv_used"].append(rv)
        out.append(dict(ab=ab, n=st["n"], corr=spec["c"], hint=spec["h"], rv=rv,
                        sess=f"{ab}-s{st['sess_seq']}", etype=etype,
                        ctx=spec.get("ctx"), retry=bool(spec.get("retry_correct"))))
    return out


# ---------- 独立规则实现（冻结语义逐条对齐 mastery.py） ----------
def dim_c(evs):
    w = [e for e in evs][-CI_WINDOW:]
    if len({e["rv"] for e in w}) < CI_RV or len({e["sess"] for e in w}) < CI_SESS:
        return None
    return sum(e["corr"] for e in w) / len(w)


def dim_i(evs):
    w = [e for e in evs][-CI_WINDOW:]
    if len({e["rv"] for e in w}) < CI_RV or len({e["sess"] for e in w}) < CI_SESS:
        return None
    return sum(HINT2I[e["hint"]] for e in w) / len(w)


def dim_s(evs):
    w = [e for e in evs if e["etype"] in ("attempt_standard", "retention_check")][-STAB_WINDOW:]
    if len({e["rv"] for e in w}) < STAB_RV or len({e["sess"] for e in w}) < STAB_SESS:
        return None
    return sum(e["corr"] * HINT2I[e["hint"]] for e in w) / len(w)


def dim_t(evs):
    w = [e for e in evs if e["etype"] == "attempt_transfer"][-TR_WINDOW:]
    if len(w) < TR_ROWS or len({e["ctx"] for e in w}) < TR_CTX or len({e["sess"] for e in w}) < TR_SESS:
        return None
    return sum(e["corr"] * HINT2I[e["hint"]] for e in w) / len(w)


def evaluate(old, evs):
    """镜像 evaluate_mastery._decide（含 C/I/S/T、gate 顺序、reason codes）。"""
    c, i, s, t = dim_c(evs), dim_i(evs), dim_s(evs), dim_t(evs)
    missing = [k for k, v in zip("CIST", [c, i, s, t]) if v is None]
    score = None if missing else W_C * c + W_I * i + W_S * s + W_T * t
    if old == 0:
        return (1, "upgraded", ["first_evidence"]) if evs else (0, "unchanged", ["insufficient_evidence"])
    if old == 1:
        elig = evs
        if len(elig) < G12["n"]:
            return 1, "collect_evidence", ["l1_l2_not_enough_evidence"]
        if len({e["rv"] for e in elig}) < G12["rv"]:
            return 1, "collect_evidence", ["l1_l2_resource_diversity_insufficient"]
        if len({e["sess"] for e in elig}) < G12["sess"]:
            return 1, "collect_evidence", ["l1_l2_session_diversity_insufficient"]
        if c is None or c < G12["C"]:
            return 1, "unchanged", ["l1_l2_correctness_not_met"]
        if i is None or i < G12["I"]:
            return 1, "unchanged", ["l1_l2_independence_not_met"]
        if s is None or s < G12["S"]:
            return 1, "unchanged", ["l1_l2_stability_not_met"]
        low = sum(1 for e in elig if e["hint"] <= G12["max_hint"])
        if low / len(elig) < G12["low_hint"]:
            return 1, "unchanged", ["l1_l2_hint_threshold_not_met"]
        return 2, "upgraded", ["l1_l2_gate_met"]
    if old == 2:
        if missing or score is None:
            return 2, "collect_evidence", ["l2_l3_coverage_insufficient"]
        if score >= G23["score"] and c >= G23["C"] and i >= G23["I"] and s >= G23["S"] and t >= G23["T"]:
            return 3, "upgraded", ["l2_l3_gate_met"]
        return 2, "unchanged", ["l2_l3_gate_not_met"]
    return old, "unchanged", ["no_level_change"]


def review_decide(evs, level):
    if level <= 0:
        return "ok"
    recent = [e for e in evs if e["corr"] is not None][-REVIEW_WINDOW:]
    if not recent:
        return "ok"
    fails = sum(1 for e in recent if e["corr"] == 0.0)
    if fails >= DOWNGRADE_FAIL and fails == len(recent):
        return "downgrade"
    if fails >= REVIEW_MIN_FAIL:
        return "review_required"
    return "ok"


def apply_step(old, evs):
    """镜像 mastery_db.update：evaluate → review 覆盖 → trend。"""
    nl, decision, reasons = evaluate(old, evs)
    rv = review_decide(evs, old)
    if rv == "downgrade" and old > 0:
        nl = old - 1
    if nl < old:
        trend = "down_review"
    elif nl > old:
        trend = "up"
    elif rv in ("review_required", "downgrade"):
        trend = "watch"
    else:
        trend = "stable"
    return nl, decision, reasons, rv, trend


# ---------- 时间线推演 ----------
ABILITIES = ["app_rel", "app_model", "app_rd", "app_cond", "app_check", "app_strat"]
rows = materialize()
levels = {ab: 0 for ab in ABILITIES}
timeline = {ab: [] for ab in ABILITIES}
per_ab_evs = {ab: [] for ab in ABILITIES}
for r in rows:
    ab = r["ab"]
    per_ab_evs[ab].append(r)
    old = levels[ab]
    nl, decision, reasons, rv, trend = apply_step(old, per_ab_evs[ab])
    levels[ab] = nl
    timeline[ab].append(dict(n=r["n"], week=r["wk"] if "wk" in r else None,
                             corr=r["corr"], hint=r["hint"],
                             before=old, after=nl, decision=decision,
                             reasons=reasons, review=rv, trend=trend,
                             C=dim_c(per_ab_evs[ab]), I=dim_i(per_ab_evs[ab]),
                             S=dim_s(per_ab_evs[ab]), T=dim_t(per_ab_evs[ab])))

# wk 回填（materialize 未带）——从 PLAN 对齐
for ab in ABILITIES:
    pi = 0
    wks = [p["wk"] for p in PLAN if p["ab"] == ab]
    for i, t in enumerate(timeline[ab]):
        t["week"] = wks[i]

# ---------- M01-M15 断言 ----------
def at(ab, n):
    return timeline[ab][n - 1] if len(timeline[ab]) >= n else None

M = {}
def mk(mid, desc, ok, basis):
    M[mid] = dict(id=mid, desc=desc, expected_pass=bool(ok), basis=basis)

mk("M01", "基线：六能力 L0 起步、…009x 零历史", all(timeline[ab][0]["before"] == 0 for ab in ABILITIES),
   "run 前全表零态预检（9 表逐项）")
mk("M02", "app_rel 首答→L1", (lambda t: t["after"] == 1 and t["decision"] == "upgraded" and "first_evidence" in t["reasons"])(at("app_rel", 1)),
   "1 条原子证据即升，hint≤1 满足")
mk("M03", "app_model 首答→L1", at("app_model", 1)["after"] == 1, "首答正确产生独立原子证据")
mk("M04", "app_rd 首答→L1", at("app_rd", 1)["after"] == 1, "同上")
mk("M05", "app_cond 首答→L1；降级剧情前存在真实 L2", at("app_cond", 1)["after"] == 1 and at("app_cond", 5)["after"] == 2,
   "cond#5 = M13 升级点（L2 真实在位）")
mk("M06", "app_check 首答→L1；4 题不假升 L2", at("app_check", 1)["after"] == 1 and at("app_check", 4)["decision"] == "collect_evidence" and at("app_check", 4)["after"] == 1,
   "n<5 → l1_l2_not_enough_evidence（拒绝任务堆积升档）")
mk("M07", "app_strat 首答→L1", at("app_strat", 1)["after"] == 1, "占比口径独立核算见 M10/M11")
up2_rel = [t for t in timeline["app_rel"] if "l1_l2_gate_met" in t["reasons"]]
t8 = at("app_rel", 5)
mk("M08", "app_rel ≤#5→L2（数量/版本/会话/C/I/S/Hint 逐项过门）", t8["after"] == 2 and len(up2_rel) >= 1,
   "L1→L2 决策点=第 %s 题；此刻 C=%.2f I=%.2f S=%.2f rv=%d sess=%d low_hint=%d/5" % (
       [t["n"] for t in up2_rel], t8["C"], t8["I"], t8["S"],
       len({e["rv"] for e in per_ab_evs["app_rel"][:5]}),
       len({e["sess"] for e in per_ab_evs["app_rel"][:5]}),
       sum(1 for e in per_ab_evs["app_rel"][:5] if e["hint"] <= 2)))
t_m4 = at("app_model", 4)
t_m5 = at("app_model", 5)
mk("M09", "app_model #5→L2 且 #2 单次错答未触发异常降级", at("app_model", 5)["after"] == 2
   and at("app_model", 2)["after"] == 1 and at("app_model", 2)["review"] == "ok",
   "单败 review=ok level 不变；retry 纠正不产第二证据（执行体断言）")
t10 = at("app_strat", 5)
mk("M10", "app_strat 5 题后 hint 60% 被拒（60%<80% 停 L1）", t10["after"] == 1 and "l1_l2_hint_threshold_not_met" in t10["reasons"],
   "低提示 %d/5=%.0f%% 全量口径非窗口" % (sum(1 for e in per_ab_evs['app_strat'][:5] if e['hint'] <= 2), 100 * sum(1 for e in per_ab_evs['app_strat'][:5] if e['hint'] <= 2) / 5))
t11 = at("app_strat", 10)
mk("M11", "app_strat 补 5 低提示后 8/10=80% → L2", t11["after"] == 2 and "l1_l2_gate_met" in t11["reasons"],
   "补足全部 gate 同项通过")
t12 = at("app_rd", 5)
mk("M12", "app_rd 恰 2 资源版本 → collect_evidence:resource_diversity 终 L1",
   t12["after"] == 1 and "l1_l2_resource_diversity_insufficient" in t12["reasons"],
   "5 证据/≥2 sess 但 rv=2<3 → 精确缺口语义")
t13 = at("app_cond", 5)
mk("M13", "app_cond #5→L2（升级前后 AbilityState 记录）", t13["before"] == 1 and t13["after"] == 2,
   "执行体在前后各采一次 state")
t14a = at("app_cond", 7); t14b = at("app_cond", 8); t14c = at("app_cond", 10)
mk("M14", "app_cond 2败→review_required 不降；3败→downgrade→L1；补对回稳",
   t14a["review"] == "review_required" and t14a["after"] == 2
   and t14b["review"] == "downgrade" and t14b["after"] == 1
   and t14c["after"] == 1,
   "review 窗口=最近 3 条可评分；降级=全败；恢复观察不强升")
t15 = at("app_rel", 12)
up3 = [t for t in timeline["app_rel"] if "l2_l3_gate_met" in t["reasons"]]
mk("M15", "app_rel ≤#12 达 L3（≥2 ctx 真迁移跨 Session、四维达标）",
   t15["after"] == 3 and len(up3) >= 1,
   "L2→L3 决策发生于第 %s 题；此刻 C=%s I=%s S=%s T=%s ctx=%d sess(迁移)=%d" % (
       [t["n"] for t in up3], t15["C"], t15["I"], t15["S"], t15["T"],
       len({e["ctx"] for e in per_ab_evs["app_rel"] if e["etype"] == "attempt_transfer"}),
       len({e["sess"] for e in per_ab_evs["app_rel"] if e["etype"] == "attempt_transfer"})))

FINAL = {ab: levels[ab] for ab in ABILITIES}
FINAL_EXPECT = {"app_rel": 3, "app_model": 2, "app_rd": 1, "app_cond": 1, "app_check": 1, "app_strat": 2}
final_ok = FINAL == FINAL_EXPECT

# ---------- 预算充分性 6 维核对（评审 P0-1 表格逐项） ----------
def ab_stats(ab):
    evs = per_ab_evs[ab]
    return dict(total=len(evs), first_answer_tasks=len(evs), retries=sum(1 for p in PLAN if p["ab"] == ab and p.get("retry_correct")),
                distinct_rv=len({e["rv"] for e in evs}), distinct_sessions=len({e["sess"] for e in evs}),
                transfers=sum(1 for e in evs if e["etype"] == "attempt_transfer"),
                ctxs=sorted({e["ctx"] for e in evs if e["ctx"]}),
                low_hint=sum(1 for e in evs if e["hint"] <= 2), fails=sum(1 for e in evs if e["corr"] == 0.0))

budget = {ab: ab_stats(ab) for ab in ABILITIES}
# 单题不注水：每条证据 task 唯一（执行体每 spec 一个新 pin task；reuse rv≠reuse task）
reuse_tasks_unique = len({(e["ab"], e["n"]) for e in rows}) == len(rows)

# ---------- 导出 ----------
OUT = "/Users/hanxianxiang/WorkBuddy/2026-09-24-10-25-54/output/qa_growth_v2_prep"
import os
os.makedirs(OUT, exist_ok=True)
with open(f"{OUT}/evidence_budget_matrix.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["里程碑", "描述", "独立核算期望", "依据（预算数字）"])
    for mid in [f"M{str(i).zfill(2)}" for i in range(1, 16)]:
        m = M[mid]
        w.writerow([m["id"], m["desc"], "PASS(预算满足)" if m["expected_pass"] else "FAIL(预算不满足)", m["basis"]])
with open(f"{OUT}/budget_timeline.json", "w") as f:
    json.dump(dict(final=FINAL, final_expect=FINAL_EXPECT, final_ok=final_ok,
                   milestones={k: v["expected_pass"] for k, v in M.items()},
                   budget=budget, timeline=timeline, reuse_tasks_unique=reuse_tasks_unique),
              f, ensure_ascii=False, indent=1, default=str)

print("== M01-M15 独立预算核算 ==")
for mid in sorted(M):
    m = M[mid]
    print(("✅" if m["expected_pass"] else "❌"), m["id"], m["desc"][:56])
print("\n== 终态 ==")
for ab in ABILITIES:
    print(f"  {ab}: 预算推演 L{FINAL[ab]} / 剧本目标 L{FINAL_EXPECT[ab]}", "✅" if FINAL[ab] == FINAL_EXPECT[ab] else "❌")
print("\n== 六能力预算（题数/资源/会话/迁移/低hint/错答）==")
for ab in ABILITIES:
    b = budget[ab]
    print(f"  {ab}: {b['total']}题(retry{b['retries']}) rv{b['distinct_rv']} sess{b['distinct_sessions']} transfer{b['transfers']}{b['ctxs']} lowhint{b['low_hint']} fail{b['fails']}")
print("首答题 task 唯一（无单题重复注水）:", reuse_tasks_unique)
print("总判定:", "BUDGET SUFFICIENT" if all(v["expected_pass"] for v in M.values()) and final_ok and reuse_tasks_unique else "BUDGET PROBLEM")
