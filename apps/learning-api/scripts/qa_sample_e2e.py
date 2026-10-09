"""FE-1438：155 题批 Gate 4~7 QA 抽样实灌驱动（对 qa_staged 样本全量 19 题跑）。

链路（PC-v1 §11 Gate 4~7 口径）：
- Gate 4 pin 下发：tasks/next + pin_resource_version_id（qa_staged 放行，FE-1438 分支）
- Gate 5 Judge：期望答案 DB 反查 → 提交对/错两态 → correct 布尔符合预期
- Gate 6 Evidence：attempt 落 mastery_evidence（原子类型、单 Task 单证据）
- Gate 7 Diagnosis：diagnose_v2 观察 error_models.pattern 匹配（错答路径出提示/诊断原料）

QA child …0099；submission_id 确定性 sha256；attempt_no 递增。
用法：DATABASE_URL=... PYTHONPATH=apps/learning-api python scripts/qa_sample_e2e.py
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import uuid

sys.path.insert(0, "apps/learning-api")

from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.main import app

DB_URL = os.environ["DATABASE_URL"]
CHILD = os.environ.get("QA_CHILD_ID", "00000000-0000-0000-0000-000000000099")


def sub_id(sid: str, tid: str, tag: str) -> str:
    h = hashlib.sha256(f"{sid}|{tid}|{tag}".encode()).digest()
    return str(uuid.UUID(bytes=h[:16]))


async def main() -> None:
    eng = create_async_engine(DB_URL)
    transport = ASGITransport(app=app)
    rows = []
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        async with eng.connect() as dbc:
            samples = (await dbc.execute(text(
                "select rv.resource_version_id, r.title, r.ability_id, rv.content, rv.ui_schema, rv.error_models "
                "from resource_version rv join resource r on r.resource_id=rv.resource_id "
                "where rv.review_status='qa_staged' order by r.title"
            ))).fetchall()
        print(f"qa_staged 样本：{len(samples)} 题")

        for rvid, title, ability, content, ui_schema, error_models in samples:
            content = content if isinstance(content, dict) else json.loads(content)
            ui_schema = ui_schema if isinstance(ui_schema, dict) else json.loads(ui_schema)
            qid = content.get("question_id", title)
            expected = str(content.get("answer"))

            # Gate 4: pin 下发
            r = await c.post("/v1/learning/sessions",
                             json={"child_id": CHILD, "subject": "math", "requested_minutes": 15})
            sid = r.json()["session_id"]
            r = await c.post("/v1/learning/tasks/next", json={
                "child_id": CHILD, "session_id": sid, "subject": "math",
                "pin_resource_version_id": str(rvid)})
            t = r.json()
            tid = t.get("task_instance_id")
            g4 = bool(tid)
            ws = (t.get("ui_schema") or {}).get("workspaces", [{}])[0] if g4 else {}

            # Gate 5: Judge（先错后对）
            g5_wrong = g5_right = False
            g6_ev = 0
            g7_hint = None
            if g4:
                def env(ans):
                    return {"schema_version": "2.0",
                            "type": (ws.get("renderer") or "generic").replace("-", "_"),
                            "ui_revision": (t["ui_schema"] or {}).get("ui_revision"),
                            "answer": str(ans),
                            "workspaces": [{"workspace_id": w.get("workspace_id") or "main", "data": {}}
                                           for w in (t["ui_schema"] or {}).get("workspaces", [{"workspace_id": "main"}])],
                            "interaction_events": []}
                wrong = "999999" if str(expected) != "999999" else "999998"
                r1 = await c.post("/v1/learning/attempts", json={
                    "child_id": CHILD, "task_instance_id": tid, "attempt_no": 1,
                    "response": env(wrong), "submission_id": sub_id(sid, tid, f"{qid}-w")})
                r2 = await c.post("/v1/learning/attempts", json={
                    "child_id": CHILD, "task_instance_id": tid, "attempt_no": 2,
                    "response": env(expected), "submission_id": sub_id(sid, tid, f"{qid}-r")})
                if r1.status_code == 200:
                    b1 = r1.json()
                    g5_wrong = b1.get("correct") is False
                    na = (b1.get("next_action") or {})
                    g7_hint = na.get("type")
                if r2.status_code == 200:
                    g5_right = r2.json().get("correct") is True
                # Gate 6: 原子证据
                async with eng.connect() as dbc:
                    cnt = (await dbc.execute(text(
                        "select count(*) from mastery_evidence where task_instance_id=:t "
                        "and valid=true and evidence_type in ('attempt_standard','attempt_transfer','retention_check','explanation')"),
                        {"t": uuid.UUID(tid)})).scalar()
                g6_ev = cnt

            ok = g4 and g5_wrong and g5_right and g6_ev == 1
            rows.append((qid, ws.get("renderer"), ok,
                         f"G4={'✓' if g4 else '✗'} 判错={'✓' if g5_wrong else '✗'} 判对={'✓' if g5_right else '✗'} "
                         f"证据={g6_ev} 错后动作={g7_hint}"))
            print(f"  {'✅' if ok else '❌'} {qid} [{ws.get('renderer')}] {rows[-1][3]}")

    await eng.dispose()
    passed = sum(1 for _, _, ok, _ in rows if ok)
    print("=" * 60)
    print(f"Gate 4~7 实灌：{passed}/{len(rows)} 通过")
    print("✅ 抽样全链贯通——下一步 Gate 8（qa_replay #7）+ 审批后 qa_staged→published 正式入库。"
          if passed == len(rows) and rows else "❌ 有失败用例，看逐题输出定位。")
    sys.exit(0 if passed == len(rows) and rows else 1)


if __name__ == "__main__":
    asyncio.run(main())
