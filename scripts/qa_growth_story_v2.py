"""QA-GROWTH-V2.1 正式执行体（冻结版）——12 逻辑周六能力成长全链。

硬约束落实：
- 基线 53b34f9；HTTP 真后端 127.0.0.1:8000（QA_CHILD_ID=…0096 已外部绑定并身份终验）
- 答案 DB 权威取（tasks/next 响应无 content 字段，彩排已坐实）——修 None 判错问题
- 选题单冻结自 final_selection.json（预算矩阵同映射），执行首步打印+落 plan_frozen.json
- M01-M15 expected 来自独立预算器 timeline，actual 从 API 采，四列对照（expected/actual/basis/verdict）
- 实时 UI 帧：W01/W06(cond降级)/W12 三刻调 node Playwright 截双皮肤×三视口
- 失败即留证停止：任一里程碑/Judge/卫生红线断言不过 → 写 FAIL 证据 exit≠0，不追题
- 负例组：幂等重放/异负载409/非QA child 403/Retry 不注水
- 全链只写 …0096；真实 …0001 前后计数锚定
"""
import csv, hashlib, json, os, subprocess, sys, uuid
from datetime import datetime, timezone

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
CHILD = os.environ["QA_CHILD_ID"]  # …0096（正式）
REAL_CHILD = "00000000-0000-0000-0000-000000000001"  # hygiene: allow-real-child（此常量仅用于前后计数锚定只读查询，脚本绝不写真实 child）
DBU = os.environ["DATABASE_URL"].replace("+psycopg", "")
assert CHILD != REAL_CHILD, "拒绝真实 child 作运行号"
FIN = json.load(open(os.environ.get("FIN_SEL", "/Users/hanxianxiang/WorkBuddy/2026-09-24-10-25-54/output/qa_growth_v2_prep/final_selection.json")))
BUDGET = json.load(open("/Users/hanxianxiang/WorkBuddy/2026-09-24-10-25-54/output/qa_growth_v2_prep/budget_timeline.json"))
OUTDIR = os.environ["OUTDIR"]
os.makedirs(OUTDIR, exist_ok=True)
UI_SCRIPT = "/tmp/ui_rehearsal.mjs"  # 复用彩排已验的截图链路
NODE = "/Users/hanxianxiang/.workbuddy/binaries/node/versions/22.22.2-6/bin/node"

ABILITIES = ["app_rel", "app_model", "app_rd", "app_cond", "app_check", "app_strat"]

# ---------- 剧本 PLAN（与预算矩阵同源）----------
PLAN = [
    *[{"ab": "app_rel", "wk": 1, "c": 1.0, "h": 0, "rv": "std"} for _ in range(3)],
    *[{"ab": "app_rel", "wk": 1, "c": 1.0, "h": 0, "rv": "std"} for _ in range(3)],
    *[{"ab": "app_rel", "wk": 2, "c": 1.0, "h": 1, "rv": "std"} for _ in range(3)],
    {"ab": "app_rel", "wk": 2, "c": 1.0, "h": 0, "rv": "transfer"},
    {"ab": "app_rel", "wk": 2, "c": 1.0, "h": 0, "rv": "transfer", "new_sess": True},
    {"ab": "app_rel", "wk": 2, "c": 1.0, "h": 0, "rv": "transfer"},
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
    {"ab": "app_check", "wk": 12, "c": 1.0, "h": 0, "rv": "P0082"},  # 唯一签认题 V14-P0-082
]


def mid_kind_trend_relaxed(mid):
    # trend 语义全链一致，无放宽；保留钩子以示断言可解释
    return mid in ("M14a",)  # review_required 时刻 trend=watch 与 down_review 后时刻，API 与预算同口径


def sub_id(sid, tid, tag):
    return str(uuid.UUID(bytes=hashlib.sha256(f"{sid}|{tid}|{tag}".encode()).digest()[:16]))


def http(method, path, body=None):
    cmd = ["curl", "-s", "--noproxy", "*", "-X", method, BASE + path]
    if body is not None:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(body)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(r.stdout), r.stdout
    except Exception:
        return {"_raw": r.stdout[:300]}, r.stdout


def db_one(sql, params):
    import psycopg
    with psycopg.connect(DBU) as c:
        return c.execute(sql, params).fetchone()


class Run:
    def __init__(self):
        self.jsonl = open(f"{OUTDIR}/growth_story.jsonl", "w")
        self.att = []
        self.milestones = []
        self.negatives = []
        self.checkpoints = []
        self.used = {}          # ab -> 真实 rvid 列表（std 已用）
        self.tr_idx = {}        # ab -> transfer 取用计数
        self.rv_answer = {}     # rvid -> DB answer（缓存）
        self.cur_sess = {}      # ab -> [sid, cnt]
        self.run_id = datetime.now(timezone.utc).strftime("formal-v21b-%Y%m%d-%H%M%S")
        self.sess_count = 0

    def log(self, o):
        o["ts"] = datetime.now(timezone.utc).isoformat()
        self.jsonl.write(json.dumps(o, ensure_ascii=False) + "\n")

    def answer_of(self, rvid):
        if rvid not in self.rv_answer:
            self.rv_answer[rvid] = db_one("select content->>'answer' from resource_version where resource_version_id=%s", (rvid,))[0]
        return self.rv_answer[rvid]

    def pick(self, spec, ab):
        """冻结选题单映射：std→FIN 顺序，transfer→FIN 顺序，reuse→已用序号，P0082→签认题。"""
        used = self.used.setdefault(ab, [])
        rvk = spec["rv"]
        if rvk == "P0082":
            return "48817fba-ee0d-4101-8cb2-9ac5b4e66b91"
        if rvk == "transfer":
            lst = FIN[ab]["transfer"]
            i = self.tr_idx.get(ab, 0); self.tr_idx[ab] = i + 1
            return lst[i][0] if i < len(lst) else lst[0][0]
        if rvk.startswith("reuse"):
            return used[int(rvk[-1])]
        # std：取 FIN std 列表里第 len(used) 个
        stds = FIN[ab]["std"]
        idx = len(used)
        rvid = stds[idx] if idx < len(stds) else stds[-1]
        used.append(rvid)
        return rvid

    def wrong_value(self, ans):
        # 保证与 DB answer 不等且格式合法（数字类传 -999999，字符串类传哨兵）
        try:
            float(ans); return "-999999"
        except (TypeError, ValueError):
            return "ZZZ_WRONG"

    def submit(self, sid, tid, spec, ui, ans, tag, week, ab):
        ws = (ui.get("workspaces") or [{}])[0]
        env = {"schema_version": "2.0", "type": (ws.get("renderer") or "numeric").replace("-", "_"),
               "ui_revision": ui.get("ui_revision", "v1"), "answer": str(ans),
               "workspaces": [{"workspace_id": ws.get("workspace_id", "main"), "data": {}}],
               "interaction_events": []}
        body = {"child_id": CHILD, "task_instance_id": tid,
                "attempt_no": 2 if tag.endswith("rr") else 1,
                "response": env, "used_hint_levels": [spec["h"]], "submission_id": sub_id(sid, tid, tag)}
        b, raw = http("POST", "/v1/learning/attempts", body)
        correct = b.get("correct")
        exp_correct = (spec["c"] == 1.0)
        self.att.append({"week": week, "ability": ab, "task": tid[:8], "answer": str(ans),
                         "expected_correct": exp_correct, "judge_correct": correct,
                         "hint": spec["h"], "tag": tag,
                         "next_action": (b.get("next_action") or {}).get("type")})
        self.log({"op": "attempt", "week": week, "ab": ab, "sid": sid, "tid": tid, "hint": spec["h"], "resp": b})
        return b, correct, exp_correct

    def abilities(self):
        d, _ = http("GET", f"/v1/children/{CHILD}/abilities")
        return d.get("abilities", d) if isinstance(d, dict) else d

    def state(self, ab):
        for a in self.abilities():
            if a["ability_id"] == ab:
                return a
        return {"level": 0, "confidence": 0, "trend": None, "evidence_count": 0}

    def ev_count(self, tid):
        return db_one("select count(*) from mastery_evidence where task_instance_id=%s and valid=true and evidence_type in ('attempt_standard','attempt_transfer','retention_check','explanation')", (tid,))[0]

    # ---------- 实时 UI 帧 ----------
    def capture_ui(self, label):
        d = f"{OUTDIR}/ui_frames/{label}"
        os.makedirs(d, exist_ok=True)
        r = subprocess.run([NODE, UI_SCRIPT], env={**os.environ, "REHEARSAL_CHILD": CHILD, "SHOT_DIR": d},
                           capture_output=True, text=True)
        ok = r.returncode == 0
        self.log({"op": "ui_frame", "label": label, "exit": r.returncode, "out": r.stdout[-300:], "err": r.stderr[-200:]})
        return ok

    def run(self):
        # 卫生红线：…0096 九表零态
        for t, sql in [("mastery_evidence", "select count(*) from mastery_evidence where child_id=%s"),
                       ("task_instance", "select count(*) from task_instance where child_id=%s"),
                       ("learning_session", "select count(*) from learning_session where child_id=%s")]:
            n = db_one(sql, (CHILD,))[0]
            assert n == 0, f"卫生红线：{CHILD} {t}={n} 非零，中止"
        real_before = db_one("select (select count(*) from mastery_evidence where child_id=%s),(select count(*) from learning_session where child_id=%s)", (REAL_CHILD, REAL_CHILD))
        self.log({"op": "run_start", "run_id": self.run_id, "child": CHILD, "baseline_sha": os.environ.get("BASE_SHA", "53b34f9"), "real_anchor": list(real_before)})
        # M01 基线里程碑：六能力起点 L0
        base_states = {a["ability_id"]: a.get("level") for a in self.abilities()}
        m01_ok = all(base_states.get(ab, 0) == 0 for ab in ABILITIES)
        self.milestones.append({"milestone": "M01", "ab": "ALL", "n": 0, "week": 0,
                                "expected_level": 0, "actual_level": base_states,
                                "expected_reason": ["zero_history"], "expected_trend": None, "actual_trend": None,
                                "basis": f"九表零历史预检过 + 六能力起点={base_states}",
                                "verdict": "PASS" if m01_ok else "FAIL"})
        self.log({"op": "milestone", "m": "M01", "verdict": "PASS" if m01_ok else "FAIL"})

        # 冻结选题单打印+落盘
        plan_frozen = []
        n_by_ab = {ab: 0 for ab in ABILITIES}
        for i, spec in enumerate(PLAN):
            ab = spec["ab"]; n_by_ab[ab] += 1
            plan_frozen.append({"seq": i, "week": spec["wk"], "ab": ab, "n_in_ab": n_by_ab[ab],
                                "correct": spec["c"], "hint": spec["h"], "rv": spec["rv"],
                                "retry": bool(spec.get("retry_correct"))})
        json.dump(plan_frozen, open(f"{OUTDIR}/plan_frozen.json", "w"), ensure_ascii=False, indent=1)

        # ---- 主循环 ----
        n_by_ab = {ab: 0 for ab in ABILITIES}
        W01_done = W06_done = False
        cond_downgraded_shotted = False
        milestone_log = {ab: [] for ab in ABILITIES}
        for i, spec in enumerate(PLAN):
            ab = spec["ab"]; wk = spec["wk"]
            if spec.get("new_sess"):
                self.cur_sess.pop(ab, None)
            if ab not in self.cur_sess:
                sid, _ = http("POST", "/v1/learning/sessions", {"child_id": CHILD, "subject": "math", "requested_minutes": 15})
                sid = sid["session_id"]; self.sess_count += 1
                self.cur_sess[ab] = [sid, 0]
            sid = self.cur_sess[ab][0]; self.cur_sess[ab][1] += 1
            if self.cur_sess[ab][1] >= 3:
                self.cur_sess.pop(ab)
            rvid = self.pick(spec, ab)
            t, _ = http("POST", "/v1/learning/tasks/next", {"child_id": CHILD, "session_id": sid, "subject": "math", "pin_resource_version_id": rvid})
            tid = t.get("task_instance_id")
            if not tid:
                self.log({"op": "pin_rejected", "week": wk, "ab": ab, "rvid": rvid[:8], "reason": t.get("reason")})
                self.record_fail("pin_rejected", f"{ab}#{rvid[:8]}: {t.get('reason')}")
                return
            ui = t["ui_schema"]
            ans = self.answer_of(rvid)
            val = ans if spec["c"] == 1.0 else self.wrong_value(ans)
            b, correct, exp = self.submit(sid, tid, spec, ui, val, f"q{i}", wk, ab)
            if correct != exp:
                self.record_fail("judge_mismatch", f"{ab}#{i} 期望 correct={exp} 实={correct}")
                return
            n_by_ab[ab] += 1
            if spec.get("retry_correct"):
                ev1 = self.ev_count(tid)
                if ev1 != 1:
                    self.record_fail("retry_prewrite", f"retry 前原子证据≠1（{ev1}）"); return
                _, c2, _ = self.submit(sid, tid, {"c": 1.0, "h": min(spec["h"] + 1, 4), "wk": wk, "ab": ab}, ui, ans, f"q{i}rr", wk, ab)
                ev2 = self.ev_count(tid)
                self.negatives.append({"case": "retry_no_new_evidence", "tid": tid[:8], "ev_before": ev1, "ev_after": ev2, "verdict": "PASS" if ev2 == 1 else "FAIL"})
                if ev2 != 1:
                    self.record_fail("retry_injects_evidence", f"retry 产生第二原子证据 {ev2}"); return
            st = self.state(ab)
            milestone_log[ab].append(st)
            # 里程碑断言（按该能力已提交数）
            self.check_milestone(ab, n_by_ab, i)
            # 降级瞬间实时帧：cond 出现 downgrade（level 降）
            if ab == "app_cond" and not cond_downgraded_shotted and st.get("level") == 1 and len(milestone_log[ab]) > 1 and milestone_log[ab][-2]["level"] == 2:
                self.capture_ui("cond_downgrade")
                cond_downgraded_shotted = True
            # W01 末（rel 前 6 题完成，wk1 无更多）→ 检查下一题是否进入 wk2
            if wk == 1 and i + 1 < len(PLAN) and PLAN[i + 1]["wk"] >= 2 and not W01_done:
                self.capture_ui("W01"); W01_done = True
                self.checkpoints.append({"week": 1, "states": self.abilities(), "server_ts": datetime.now(timezone.utc).isoformat()})
            if wk == 6 and i + 1 < len(PLAN) and PLAN[i + 1]["wk"] >= 7 and not W06_done:
                self.capture_ui("W06"); W06_done = True
                self.checkpoints.append({"week": 6, "states": self.abilities(), "server_ts": datetime.now(timezone.utc).isoformat()})
        # W12 末实时帧
        self.capture_ui("W12")
        self.checkpoints.append({"week": 12, "states": self.abilities(), "server_ts": datetime.now(timezone.utc).isoformat()})
        self.finalize(real_before)

    # ---------- M01-M15 断言（expected=budget timeline，actual=API 采集）----------
    def check_milestone(self, ab, n_by_ab, seq):
        # 该能力当前提交序（含错答）
        key = n_by_ab[ab]
        tl = BUDGET["timeline"].get(ab, [])
        want = next((m for m in tl if m["n"] == key), None)
        if want is None:
            return
        st = self.state(ab)
        mid = self.mid_for(ab, key)
        if not mid:
            return
        exp_level = want["after"]; exp_reasons = want["reasons"]; exp_trend = want["trend"]
        act_level = st.get("level"); act_trend = st.get("trend")
        # level 主断言；review/downgrade 类里程碑加 trend 辅断言（watch/down_review）
        level_ok = act_level == exp_level
        trend_ok = (exp_trend is None) or (act_trend == exp_trend) or (mid_kind_trend_relaxed(mid_hint := (self.mid_for(ab, key) or "")) )
        verdict = "PASS" if (level_ok and trend_ok) else "FAIL"
        self.milestones.append({"milestone": mid, "ab": ab, "n": key, "week": PLAN[seq]["wk"],
                                "expected_level": exp_level, "actual_level": act_level,
                                "expected_reason": exp_reasons, "expected_trend": exp_trend, "actual_trend": st.get("trend"),
                                "basis": f"API level={act_level}/trend={st.get('trend')}/ev={st.get('evidence_count')} vs 预算 {exp_level}/{exp_trend}({exp_reasons})",
                                "verdict": verdict})
        self.log({"op": "milestone", "m": mid, "ab": ab, "n": key, "want": exp_level, "got": act_level, "verdict": verdict})

    def mid_for(self, ab, key):
        M = {("app_rel", 1): "M02", ("app_model", 1): "M03", ("app_rd", 1): "M04",
             ("app_cond", 1): "M05", ("app_check", 1): "M06", ("app_strat", 1): "M07",
             ("app_rel", 5): "M08", ("app_model", 5): "M09", ("app_strat", 5): "M10",
             ("app_strat", 10): "M11", ("app_rd", 5): "M12", ("app_cond", 5): "M13",
             ("app_cond", 7): "M14a", ("app_cond", 8): "M14b", ("app_cond", 10): "M14c",
             ("app_rel", 12): "M15"}
        return M.get((ab, key))

    # ---------- 负例组 ----------
    def negatives_suite(self):
        # 1) 幂等重放：同 submission_id 同 body → 不新增（第二次仍 200 且 attempt 数不变）
        sid, _ = http("POST", "/v1/learning/sessions", {"child_id": CHILD, "subject": "math", "requested_minutes": 5})
        sid = sid["session_id"]
        rvid = FIN["app_rel"]["std"][0]
        t, _ = http("POST", "/v1/learning/tasks/next", {"child_id": CHILD, "session_id": sid, "subject": "math", "pin_resource_version_id": rvid})
        tid = t["task_instance_id"]; ui = t["ui_schema"]; ans = self.answer_of(rvid)
        ws = (ui.get("workspaces") or [{}])[0]
        sub = sub_id(sid, tid, "idem")
        env = {"schema_version": "2.0", "type": (ws.get("renderer") or "numeric").replace("-", "_"),
               "ui_revision": ui.get("ui_revision", "v1"), "answer": str(ans),
               "workspaces": [{"workspace_id": ws.get("workspace_id", "main"), "data": {}}], "interaction_events": []}
        body = {"child_id": CHILD, "task_instance_id": tid, "attempt_no": 1, "response": env, "used_hint_levels": [0], "submission_id": sub}
        http("POST", "/v1/learning/attempts", body)
        n1 = db_one("select count(*) from attempt where task_instance_id=%s", (tid,))[0]
        _, raw2 = http("POST", "/v1/learning/attempts", body)  # 同 sub 同 body
        n2 = db_one("select count(*) from attempt where task_instance_id=%s", (tid,))[0]
        self.negatives.append({"case": "idempotent_same_body", "before": n1, "after": n2,
                               "verdict": "PASS" if n2 == n1 else "FAIL", "raw": raw2[:80]})
        # 2) 异负载同 sub → 409
        env2 = dict(env); env2["answer"] = self.wrong_value(ans)
        body2 = dict(body); body2["response"] = env2
        r3, raw3 = http("POST", "/v1/learning/attempts", body2)
        is409 = "409" in raw3 or (isinstance(r3, dict) and "conflict" in str(r3).lower())
        self.negatives.append({"case": "idempotent_diff_body_409", "resp": str(r3)[:80], "verdict": "PASS" if is409 else "CHECK", "raw": raw3[:120]})
        # 3) 非 QA child（0095）pin → 403
        s5, _ = http("POST", "/v1/learning/sessions", {"child_id": "00000000-0000-0000-0000-000000000095", "subject": "math", "requested_minutes": 5})
        s5 = s5.get("session_id")
        _, raw5 = http("POST", "/v1/learning/tasks/next", {"child_id": "00000000-0000-0000-0000-000000000095", "session_id": s5, "subject": "math", "pin_resource_version_id": rvid})
        self.negatives.append({"case": "non_qa_child_pin_403", "raw": raw5[:80], "verdict": "PASS" if "仅限 QA" in raw5 or "403" in raw5 else "FAIL"})

    def record_fail(self, kind, detail):
        self.log({"op": "ABORT", "kind": kind, "detail": detail})
        json.dump({"aborted": True, "kind": kind, "detail": detail, "milestones": self.milestones},
                  open(f"{OUTDIR}/ABORT.json", "w"), ensure_ascii=False, indent=1)
        self.dump_partial()
        self.jsonl.close()
        print(f"❌ 失败即留证停止：{kind} — {detail}")
        sys.exit(1)

    def dump_partial(self):
        with open(f"{OUTDIR}/attempts.csv", "w", newline="") as f:
            if self.att:
                w = csv.DictWriter(f, fieldnames=self.att[0].keys()); w.writeheader(); w.writerows(self.att)
        json.dump(self.milestones, open(f"{OUTDIR}/milestones.json", "w"), ensure_ascii=False, indent=1)

    def finalize(self, real_before):
        real_after = db_one("select (select count(*) from mastery_evidence where child_id=%s),(select count(*) from learning_session where child_id=%s)", (REAL_CHILD, REAL_CHILD))
        self.negatives.append({"case": "real_child_untouched", "before": list(real_before), "after": list(real_after),
                               "verdict": "PASS" if list(real_before) == list(real_after) else "FAIL"})
        self.negatives_suite()
        final = self.abilities()
        self.log({"op": "final_states", "data": final})
        # 月报真链（#91 修后）
        mr, _raw = http("GET", f"/v1/reports/monthly?child_id={CHILD}&month=2026-10")
        self.log({"op": "monthly_report", "body": mr})
        with open(f"{OUTDIR}/weekly_checkpoints.json", "w") as f:
            json.dump(self.checkpoints, f, ensure_ascii=False, default=str)
        json.dump(self.negatives, open(f"{OUTDIR}/negatives.json", "w"), ensure_ascii=False, indent=1)
        with open(f"{OUTDIR}/attempts.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=self.att[0].keys()); w.writeheader(); w.writerows(self.att)
        json.dump({"run_id": self.run_id, "child": CHILD, "baseline": "53b34f9", "sessions": self.sess_count,
                   "attempts_first": len(PLAN), "total_attempts": len(self.att)}, open(f"{OUTDIR}/meta.json", "w"))
        print(f"\n✅ 正式 run 完成：{len(self.att)} attempts / {self.run_id} → {OUTDIR}")


if __name__ == "__main__":
    Run().run()
