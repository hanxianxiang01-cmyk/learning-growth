"""QA-GROWTH-V2.1：模拟儿童「小宇」12 逻辑周六能力成长全链。

设计（用户批准的计划 V2.0/V2.1 + 独立预算器 /tmp/budget_calc.py 手推验证的期望线）：
- 真实 API：sessions → pin tasks/next → attempts（真 Judge/Mastery/Review），零直写等级。
- 单 Task 单原子证据：Retry 不产第二条证据（作为断言点而非巧合）。
- 六能力剧本：rel→L3 / model→L2 / rd→L1+collect_evidence:resource_diversity /
  cond→L2→3连败降级L1→恢复 / check→L1慢积累 / strat→L1 hint 门槛受阻→补足→L2。
- 期望值全部由本文件独立核算表预置（不调用产品 evaluate_mastery 自证）。
- 全链只写 QA 池 child …0097（QA-Simulator-Growth）；后端须以 QA_CHILD_ID=…0097 运行。
- 导出：growth jsonl（逐操作）/ attempts csv / 周检查点 / gate 审计对照 / verdict。

用法（仓库根）：
  QA_CHILD_ID=00000000-0000-0000-0000-000000000097 \
  DATABASE_URL=... PYTHONPATH=apps/learning-api \
  python scripts/qa_growth_story.py --out /tmp/growth_run1
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, "apps/learning-api")
from httpx import AsyncClient, ASGITransport  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.main import app  # noqa: E402

CHILD = os.environ.get("QA_CHILD_ID", "00000000-0000-0000-0000-000000000097")
DB_URL = os.environ["DATABASE_URL"]
REAL_CHILD = "00000000-0000-0000-0000-000000000001"
assert CHILD != REAL_CHILD, "拒绝真实 child"

def sub_id(sid, tid, tag):
    return str(uuid.UUID(bytes=hashlib.sha256(f"{sid}|{tid}|{tag}".encode()).digest()[:16]))

# ---------- 预算表（期望线，独立核算）----------
# 每条: (ability, week, sess_no(会话内编号自动), correctness, hint, rv_kind, 预期事件)
#   rv_kind: 'std' 独立资源 / 'reuse1'..'reuseN' 复用第N个 / 'transfer' 迁移题
PLAN: list[dict] = [
    # app_rel：12 首答，9 标准全对(hint0-1) + 3 迁移(2类ctx, sess4/5)
    *[{"ab": "app_rel", "wk": 1, "c": 1.0, "h": 0, "rv": "std"} for _ in range(3)],
    *[{"ab": "app_rel", "wk": 1, "c": 1.0, "h": 0, "rv": "std"} for _ in range(3)],
    *[{"ab": "app_rel", "wk": 2, "c": 1.0, "h": 1, "rv": "std"} for _ in range(3)],
    {"ab": "app_rel", "wk": 2, "c": 1.0, "h": 0, "rv": "transfer"},
    {"ab": "app_rel", "wk": 2, "c": 1.0, "h": 0, "rv": "transfer", "new_sess": True},
    {"ab": "app_rel", "wk": 2, "c": 1.0, "h": 0, "rv": "transfer"},
    # app_model：6 题，第2题首答错（单败不降）→retry 对（retry 不加证据=断言点）
    {"ab": "app_model", "wk": 3, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_model", "wk": 3, "c": 0.0, "h": 1, "rv": "std", "retry_correct": True},
    {"ab": "app_model", "wk": 3, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_model", "wk": 4, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_model", "wk": 4, "c": 1.0, "h": 1, "rv": "std"},
    {"ab": "app_model", "wk": 4, "c": 1.0, "h": 0, "rv": "std"},
    # app_cond：10 题（5对升L2 → 6,7错=review → 8错=降级L1 → 9,10对=恢复观察）
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
    # app_strat：sess1 2题hint3+3题hint0 →60%被拒（断言 hint_threshold）→ 补5 hint0 →80% 升
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
    # app_rd：5 题全对但只 2 个资源版本（reuse）→collect_evidence:resource_diversity
    {"ab": "app_rd", "wk": 10, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_rd", "wk": 10, "c": 1.0, "h": 0, "rv": "reuse0"},
    {"ab": "app_rd", "wk": 10, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_rd", "wk": 11, "c": 1.0, "h": 0, "rv": "reuse1"},
    {"ab": "app_rd", "wk": 11, "c": 1.0, "h": 0, "rv": "reuse0"},
    # app_check：4 题（<5）终 L1 collect_evidence:not_enough
    {"ab": "app_check", "wk": 11, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_check", "wk": 11, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_check", "wk": 12, "c": 1.0, "h": 0, "rv": "std"},
    {"ab": "app_check", "wk": 12, "c": 1.0, "h": 0, "rv": "std"},
]

EXPECTED_FINAL = {"app_rel": 3, "app_model": 2, "app_rd": 1, "app_cond": 1,
                  "app_check": 1, "app_strat": 2}
# 中间里程碑断言（ability, 完成后该能力已提交次数）→ (期望level, 期望reason子串)
MILESTONES = {
    ("app_rel", 1): (1, "first_evidence"),
    ("app_rel", 5): (2, "l1_l2_gate"),
    ("app_rel", 12): (3, "l2_l3_gate"),
    ("app_cond", 5): (2, "l1_l2_gate"),
    ("app_cond", 7): (2, None),          # 2败 → review_required（level 不变，trend 变）
    ("app_cond", 8): (1, "downgrade"),
    ("app_strat", 5): (1, "hint_threshold"),
    ("app_strat", 10): (2, "l1_l2_gate"),
    ("app_rd", 5): (1, "resource_diversity"),
    ("app_check", 4): (1, "collect_evidence"),
}


class Runner:
    def __init__(self, outdir):
        self.out = outdir
        os.makedirs(outdir, exist_ok=True)
        self.run_id = datetime.now(timezone.utc).strftime("growth-%Y%m%d-%H%M%S")
        self.jsonl = open(f"{outdir}/growth_story.jsonl", "w")
        self.att_rows: list[dict] = []
        self.checkpoints: list[dict] = []
        self.sessions: dict[str, list[str]] = {}   # ability -> session_id 列表
        self.used_rv: dict[str, list[str]] = {}    # ability -> 已用 std rv（含 reuse）
        self.ctx_taken: dict[str, set] = {}

    def log(self, obj):
        obj["ts"] = datetime.now(timezone.utc).isoformat()
        self.jsonl.write(json.dumps(obj, ensure_ascii=False) + "\n")

    async def state(self, c, ability):
        r = await c.get(f"/v1/children/{CHILD}/abilities")
        data = r.json()
        abil = data if isinstance(data, list) else data.get("abilities", [])
        for a in abil:
            if a["ability_id"] == ability:
                return a
        return {"level": 0, "confidence": 0, "trend": None, "evidence_count": 0}

    async def ev_count(self, eng, task_id):
        async with eng.connect() as dbc:
            return (await dbc.execute(text(
                "select count(*) from mastery_evidence where task_instance_id=:t and valid=true"
                " and evidence_type in ('attempt_standard','attempt_transfer','retention_check','explanation')"),
                {"t": uuid.UUID(task_id)})).scalar()

    async def pick_rv(self, eng, ab, spec, idx):
        async with eng.connect() as dbc:
            used = self.used_rv.setdefault(ab, [])
            if spec["rv"] == "transfer":
                rows = (await dbc.execute(text(
                    "select rv.resource_version_id, rv.content, rv.mastery_rule from resource_version rv "
                    "join resource r using(resource_id) where r.ability_id=:a and rv.review_status='published' "
                    "and rv.transfer_distance is not null and rv.ui_schema::text like '%workspaces%' "
                    "order by resource_version_id"), {"a": ab})).fetchall()
                want_ctx = None
                got = self.ctx_taken.setdefault(ab, set())
                picked = None
                for rvid, content, mr in rows:
                    ctx = (mr or {}).get("context_family") or "ANY"
                    if want_ctx is None:
                        if str(ctx) not in got:
                            got.add(str(ctx)); picked = (rvid, content); break
                    else:
                        if str(ctx) == want_ctx:
                            picked = (rvid, content); break
                else:
                    picked = (rows[0][0], rows[0][1])
                return str(picked[0]), {"content": picked[1]}
            if spec["rv"].startswith("reuse"):
                n = int(spec["rv"][-1])
                if n < len(used) and n >= 0:
                    rvid = used[n]
                    r = (await dbc.execute(text("select content, ui_schema from resource_version where resource_version_id=:i"),
                                           {"i": uuid.UUID(rvid)})).fetchone()
                    return rvid, {"content": r[0], "ui_schema": r[1]}
            rows = (await dbc.execute(text(
                "select rv.resource_version_id, rv.content from resource_version rv "
                "join resource r using(resource_id) where r.ability_id=:a and rv.review_status='published' "
                "and rv.transfer_distance is null order by resource_version_id limit 40"), {"a": ab})).fetchall()
            for rvid, content in rows:
                if str(rvid) not in used:
                    used.append(str(rvid))
                    return str(rvid), {"content": content}
            raise SystemExit(f"{ab} 题池耗尽")

    async def submit(self, c, eng, sid, tid, ans, hint, tag, ui, expected_c, week, ab):
        if "workspaces" in ui and ui["workspaces"]:
            ws = ui["workspaces"][0]
            env = {"schema_version": "2.0", "type": ws["renderer"].replace("-", "_"),
                   "ui_revision": ui["ui_revision"], "answer": str(ans),
                   "workspaces": [{"workspace_id": ws["workspace_id"], "data": {}}],
                   "interaction_events": []}
        else:
            # legacy kind-form ui（V1 numeric 信封；Judge 读 response.answer）
            env = {"schema_version": "1.0", "type": "numeric", "answer": str(ans)}
        r = await c.post("/v1/learning/attempts", json={
            "child_id": CHILD, "task_instance_id": tid, "attempt_no": 1 if "r" not in tag else 2,
            "response": env, "used_hint_levels": [hint], "submission_id": sub_id(sid, tid, tag)})
        b = r.json() if r.status_code == 200 else {"error": r.status_code, "detail": r.text[:200]}
        correct = b.get("correct")
        self.att_rows.append({"week": week, "ability": ab, "task": tid[:8], "answer": str(ans),
                              "expected_correctness": expected_c, "judge_correct": correct,
                              "hint": hint, "tag": tag, "next_action": (b.get("next_action") or {}).get("type")})
        self.log({"op": "attempt", "week": week, "ab": ab, "sid": sid, "tid": tid, "hint": hint,
                  "resp": b if r.status_code == 200 else b})
        assert (correct is True) == (expected_c == 1.0), f"Judge 与预期不符 {tag}: {correct} vs {expected_c}"
        return b

    async def run(self):
        eng = create_async_engine(DB_URL)
        async with eng.begin() as dbc:
            gid = (await dbc.execute(text("select guardian_id from guardian limit 1"))).scalar()
            ex = (await dbc.execute(text("select 1 from child where child_id=:i"), {"i": uuid.UUID(CHILD)})).fetchone()
            if not ex:
                await dbc.execute(text("insert into child (child_id,guardian_id,nickname,grade,status) values (:i,:g,'QA-Simulator-Growth','2','active')"), {"i": uuid.UUID(CHILD), "g": gid})
            hist = (await dbc.execute(text("select count(*) from mastery_evidence where child_id=:i"), {"i": uuid.UUID(CHILD)})).scalar()
            assert hist == 0, f"卫生红线：{CHILD} 已有 {hist} 条历史证据，换 run 号"
        sess_seq = 0
        cur = {}   # ability -> (sid, remaining_q)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            for i, spec in enumerate(PLAN):
                ab = spec["ab"]; wk = spec["wk"]
                if spec.get("new_sess"):
                    cur.pop(ab, None)
                if ab not in cur:
                    sid = (await c.post("/v1/learning/sessions", json={
                        "child_id": CHILD, "subject": "math", "requested_minutes": 15})).json()["session_id"]
                    sess_seq += 1
                    cur[ab] = [sid, 0]
                    self.sessions.setdefault(ab, []).append(sid)
                sid = cur[ab][0]
                cur[ab][1] += 1
                if cur[ab][1] >= 3:   # 每会话最多3题（真实节奏 + session 多样性）
                    cur.pop(ab)
                rvid, blob = await self.pick_rv(eng, ab, spec, i)
                expected = str((blob.get("content") or {}).get("answer"))
                t = (await c.post("/v1/learning/tasks/next", json={
                    "child_id": CHILD, "session_id": sid, "subject": "math",
                    "pin_resource_version_id": rvid})).json()
                tid = t.get("task_instance_id")
                if tid is None:
                    self.log({"op": "pin_rejected", "week": wk, "ab": ab, "rvid": rvid[:8], "reason": t.get("reason")})
                    continue
                ui = t["ui_schema"]
                assert t.get("ability_id") == ab, f"pin 能力漂移 {rvid}"
                spec = dict(spec); spec["_pin_rejected"] = False
                ans = expected if spec["c"] == 1.0 else "999999"
                await self.submit(c, eng, sid, tid, ans, spec["h"], f"q{i}", ui, spec["c"], wk, ab)
                if spec.get("retry_correct"):
                    # 断言：retry 前该 task 原子证据=1（错答即形成）
                    ev1 = await self.ev_count(eng, tid)
                    assert ev1 == 1, f"单Task单证据前提破坏（retry 前={ev1}）"
                    await self.submit(c, eng, sid, tid, expected, min(spec["h"] + 1, 4), f"q{i}rr", ui, 1.0, wk, ab)
                    ev2 = await self.ev_count(eng, tid)
                    assert ev2 == 1, f"Retry 产生了第二条原子证据（{ev2}）——教学语义被破坏"
                    self.log({"op": "retry_no_new_evidence", "tid": tid[:8]})
                st = await self.state(c, ab)
                key = (ab, sum(1 for s in PLAN[:i + 1] if s["ab"] == ab))
                if key in MILESTONES:
                    lvl0, why0 = MILESTONES[key]
                    self.log({"op": "milestone", "ab": ab, "n": key[1], "want_level": lvl0,
                              "want_reason": why0, "actual": st})
            # 周检查点（末态按能力汇总；时间戳真实，logical_week 自记）
            states = (await c.get(f"/v1/children/{CHILD}/abilities")).json()
            if isinstance(states, dict):
                states = states.get("abilities", [])
            self.checkpoints.append({"week": 12, "server_ts": datetime.now(timezone.utc).isoformat(),
                                     "states": states})
            with open(f"{self.out}/weekly_checkpoints.json", "w") as f:
                json.dump(self.checkpoints, f, ensure_ascii=False)
            # 能力全量快照
            final_states = (await c.get(f"/v1/children/{CHILD}/abilities")).json()
            self.log({"op": "final_states", "data": final_states})
            # 月报实链（BUG-1449 修后首次真链）
            r = await c.get(f"/v1/reports/monthly?child_id={CHILD}")
            self.log({"op": "monthly_report", "status": r.status_code, "body": r.json() if r.status_code == 200 else r.text[:300]})
            # profile
            p = (await c.get(f"/v1/children/{CHILD}/profile")).json()
            self.log({"op": "profile", "data": p})
        await eng.dispose()
        # 导出
        with open(f"{self.out}/attempts.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=self.att_rows[0].keys()); w.writeheader(); w.writerows(self.att_rows)
        with open(f"{self.out}/meta.json", "w") as f:
            json.dump({"run_id": self.run_id, "child": CHILD, "sessions": sess_seq,
                       "attempts_first_answer": len(PLAN), "total_attempts": len(self.att_rows)}, f)
        print(f"完成：{sess_seq} sessions / {len(self.att_rows)} attempts → {self.out}")

asyncio.run(Runner(sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else "/tmp/growth_run1").run())
