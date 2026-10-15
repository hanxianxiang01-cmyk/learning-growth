"""评审 skill learning_path 实链验收：QA 孩子 app_rel L1→L2 升级全链。

链路：pin 5 道不同 published app_rel 题 → 2 个 session 全对提交（hint=0，无错答）
→ mastery_evidence 落 5 原子证据（≥3 资源、≥2 会话、correctness≥0.8、low_hint≥0.8）
→ 后端判定 upgraded(L2) → ability_state level 变色 → session_result 决策可查。

只写 QA-Simulator …0099。用法：DATABASE_URL=… python scripts/l1_to_l2_upgrade_e2e.py
"""
import asyncio, hashlib, json, os, sys, uuid
sys.path.insert(0, "apps/learning-api")
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.main import app

DB_URL = os.environ["DATABASE_URL"]
CHILD = os.environ.get("QA_CHILD_ID", "00000000-0000-0000-0000-000000000099")
ABILITY = "app_rel"

def sub_id(sid, tid, tag):
    h = hashlib.sha256(f"{sid}|{tid}|{tag}".encode()).digest()
    return str(uuid.UUID(bytes=h[:16]))

async def main():
    eng = create_async_engine(DB_URL)
    async with eng.connect() as dbc:
        rows = (await dbc.execute(text(
            "select rv.resource_version_id, rv.content from resource_version rv "
            "join resource r using(resource_id) "
            "where rv.review_status='published' and r.ability_id=:a "
            "order by r.title limit 5"), {"a": ABILITY})).fetchall()
    assert len(rows) == 5, "题不足 5"
    before = None
    async with eng.connect() as dbc:
        before = (await dbc.execute(text(
            "select level, confidence, evidence_count from ability_state "
            "where child_id=:c and ability_id=:a"), {"c": CHILD, "a": ABILITY})).fetchone() or (0, 0, 0)
    print(f"前置态: {ABILITY} level={before[0]} conf={before[1]} ev={before[2]}")

    decisions = []
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        for si in range(2):
            sess_q = rows[:3] if si == 0 else rows[3:]
            r = await c.post("/v1/learning/sessions", json={"child_id": CHILD, "subject": "math", "requested_minutes": 15})
            sid = r.json()["session_id"]
            for rvid, content in sess_q:
                content = content if isinstance(content, dict) else json.loads(content)
                expected = str(content.get("answer"))
                t = (await c.post("/v1/learning/tasks/next", json={
                    "child_id": CHILD, "session_id": sid, "subject": "math",
                    "pin_resource_version_id": str(rvid)})).json()
                tid = t["task_instance_id"]
                ws = t["ui_schema"]["workspaces"][0]
                env = {"schema_version": "2.0",
                       "type": ws["renderer"].replace("-", "_"),
                       "ui_revision": t["ui_schema"]["ui_revision"],
                       "answer": expected,
                       "workspaces": [{"workspace_id": ws["workspace_id"], "data": {}}],
                       "interaction_events": []}
                a = await c.post("/v1/learning/attempts", json={
                    "child_id": CHILD, "task_instance_id": tid, "attempt_no": 1,
                    "response": env, "submission_id": sub_id(sid, tid, "up")})
                b = a.json()
                decisions.append((str(rvid)[:8], b.get("correct"), b.get("next_action", {}).get("type")))
                print(f"  sess{si+1} {str(rvid)[:8]} correct={b.get('correct')}")
            sr = (await c.get(f"/v1/learning/sessions/{sid}/result?child_id={CHILD}")).json()
            for d in (sr.get("mastery_decisions") or []):
                print(f"  session_result[{si+1}] decision={d.get('decision')} old={d.get('old_level')} new={d.get('new_level')} reasons={d.get('reason_codes')}")

    async with eng.connect() as dbc:
        after = (await dbc.execute(text(
            "select level, confidence, evidence_count, trend from ability_state "
            "where child_id=:c and ability_id=:a"), {"c": CHILD, "a": ABILITY})).fetchone()
        ev = (await dbc.execute(text(
            "select count(distinct me.task_instance_id), count(distinct t.session_id) from mastery_evidence me left join task_instance t on t.task_instance_id=me.task_instance_id "
            "where child_id=:c and ability_id=:a and valid=true "
            "and evidence_type in ('attempt_standard','retention_check') "
            "and created_at > now() - interval '30 minutes'"), {"c": CHILD, "a": ABILITY})).fetchone()
    print(f"终态: level={after[0]} conf={after[1]} ev={after[2]} trend={after[3]} | 近30分证据 资源数={ev[0]} 会话数={ev[1]}")
    ok = after[0] == 2
    print("RESULT:", "L1→L2 upgraded 实链贯通 ✅" if ok else f"未升到 L2（level={after[0]}）——核对上面 decision 输出")
    await eng.dispose()
    sys.exit(0 if ok else 1)

asyncio.run(main())
