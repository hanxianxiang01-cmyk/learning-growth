"""FE-1442 SEL 矩阵：真实 RDS 跨 Session 公平选题回归（QA child …0099）。

SEL 映射（裁决裁剪后）：
- SEL-01/02：app_cond（带内 9 题=8 T155+1 金题）跨 18 session → 全覆盖且每资源 2±1 次
  （起始历史非零容忍偏移——公平性本质=无系统性头名，非理想零历史特例）
- SEL-03：单 session 内 3 连申请不重复
- SEL-04/13：app_rd diff1 仅 3 题 → 小池轮转+P2 RECENT_FALLBACK 不死循环
- SEL-06/14：全程 selected 不得出现 qa_retired/qa_staged 资源（未审批不混入+取消发布排除）
- SEL-07：四场景——①带内 100%（app_cond 全部 selected_difficulty∈带）②带内重复走 P2
  不触发兜底 ③app_transfer（池只有 diff4/5，level0 band=(1,1) 空）→ BAND_FALLBACK
  +requested/selected 记因 ④strategy_policy.assigned_difficulty=真实资源难度（Mastery 源）
- SEL-11：pin 回归（qa_replay 8/8 另行，本脚本验 pin 仍绕过公平采样=task 无 selection_policy）
- SEL-12：起始 history 快照随报告（HISTORY_PARTIAL 申明）

用法：DATABASE_URL=... PYTHONPATH=apps/learning-api python scripts/qa_selection_fairness_e2e.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from collections import Counter

sys.path.insert(0, "apps/learning-api")

from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.main import app

DB_URL = os.environ["DATABASE_URL"]
CHILD = os.environ.get("QA_CHILD_ID", "00000000-0000-0000-0000-000000000099")

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = ""):
    results.append((name, ok, detail))
    print(f"  {'✅' if ok else '❌'} {name}" + (f" — {detail}" if detail else ""))


async def next_task(c, ability=None):
    r = await c.post("/v1/learning/sessions",
                     json={"child_id": CHILD, "subject": "math", "requested_minutes": 15})
    sid = r.json()["session_id"]
    body = {"child_id": CHILD, "session_id": sid, "subject": "math"}
    if ability:
        body["ability_id"] = ability
    r = await c.post("/v1/learning/tasks/next", json=body)
    return r.json(), sid


async def main():
    eng = create_async_engine(DB_URL)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # 起始历史快照（SEL-12 口径）
        async with eng.connect() as dbc:
            hist = (await dbc.execute(text(
                "select ability_id, count(*) from task_instance where child_id=:c group by 1"),
                {"c": uuid.UUID(CHILD)})).fetchall()
        print(f"[SEL-12] HISTORY_PARTIAL 起始快照: {dict(hist)}")

        # 合法资源状态集合（SEL-06/14 断言用）
        async with eng.connect() as dbc:
            status_map = {str(r[0]): r[1] for r in (await dbc.execute(text(
                "select resource_version_id::text, review_status from resource_version"))).fetchall()}

        def illegal(rv_id):
            return status_map.get(rv_id, "MISSING") not in ("published",)

        # ---------- SEL-01/02：app_cond 18 session 公平覆盖 ----------
        picks = []
        metas = []
        for _ in range(18):
            t, _ = await next_task(c, "app_cond")
            if t.get("task_instance_id"):
                picks.append(t["resource_version_id"])
                metas.append(t.get("strategy_policy") or {})
        uniq = len(set(picks))
        per = Counter(picks)
        mx, mn = max(per.values()), min(per.values())
        check("SEL-01/02 app_cond 18 次覆盖唯一数≥9", uniq >= 9,
              f"唯一={uniq} 分布 max-min={mx-mn}")
        check("SEL-02 无系统性头名（max≤3）", mx <= 3, f"counts={dict(per)}")
        check("SEL-07① 全部带内+溯源字段齐", all(
            m.get("selection_policy") == "v1.4-fe1442" and m.get("selection_reason") in
            ("UNSEEN_PRIORITY", "LOW_EXPOSURE", "RECENT_FALLBACK") for m in metas),
              f"sample={metas[0] if metas else {}}")
        check("SEL-07② 带内重复走 P2 不跨带", all(not m.get("band_fallback") for m in metas))

        # ---------- SEL-03：单 session 3 连不重复 ----------
        r = await c.post("/v1/learning/sessions",
                         json={"child_id": CHILD, "subject": "math", "requested_minutes": 15})
        sid = r.json()["session_id"]
        seq = []
        for _ in range(3):
            t = (await c.post("/v1/learning/tasks/next", json={
                "child_id": CHILD, "session_id": sid, "subject": "math",
                "ability_id": "app_rel"})).json()
            if t.get("task_instance_id"):
                seq.append(t["resource_version_id"])
        check("SEL-03 同 session 3 连不重复", len(seq) == 3 and len(set(seq)) == 3, f"n={len(seq)}")

        # ---------- SEL-04：单 session 带内耗尽=精确 reason，绝不借道跨带 ----------
        r = await c.post("/v1/learning/sessions",
                         json={"child_id": CHILD, "subject": "math", "requested_minutes": 15})
        sid = r.json()["session_id"]
        async with eng.connect() as dbc:
            nband = (await dbc.execute(text(
                "select count(*) from resource_version rv join resource r on r.resource_id=rv.resource_id "
                "where r.ability_id='app_rd' and rv.review_status='published' "
                "and rv.ui_schema->>'schema_version'='2.0' and rv.difficulty in (1,2)"))).scalar()
        last = None
        for _ in range(nband + 1):
            last = (await c.post("/v1/learning/tasks/next", json={
                "child_id": CHILD, "session_id": sid, "subject": "math",
                "ability_id": "app_rd"})).json()
        check("SEL-04 单 session 带内耗尽=SESSION_POOL_EXHAUSTED（不跨带）",
              last.get("task_instance_id") is None
              and last.get("reason") == "SESSION_POOL_EXHAUSTED",
              f"band={nband} reason={last.get('reason')}")

        # ---------- SEL-04/13：小池轮转不死循环 ----------
        small = []
        for _ in range(10):
            t, _ = await next_task(c, "app_rd")  # diff1 池仅 3
            if t.get("task_instance_id"):
                small.append(t["resource_version_id"])
        check("SEL-13 小池 10 次不死循环且唯一≤池", 0 < len(small) <= 10 and len(set(small)) <= 5,
              f"n={len(small)} uniq={len(set(small))}")

        # ---------- SEL-07③：BAND_FALLBACK 显式兜底（band 低于池最低难度的能力） ----------
        async with eng.connect() as dbc:
            minmap = {r[0]: r[1] for r in (await dbc.execute(text(
                "select r.ability_id, min(rv.difficulty) from resource_version rv "
                "join resource r on r.resource_id=rv.resource_id "
                "where rv.review_status='published' and rv.ui_schema->>'schema_version'='2.0' "
                "group by 1"))).fetchall()}
            states = (await dbc.execute(text(
                "select ability_id, level from ability_state where child_id=:c"),
                {"c": uuid.UUID(CHILD)})).fetchall()
        # 选一个 level 带不含其池难度的能力（兜底活体样本）
        fb_ability = next((a for a, lv in states
                           if minmap.get(a) is not None and minmap[a] > lv + 1), None)
        if fb_ability:
            t, _ = await next_task(c, fb_ability)
            m = (t.get("strategy_policy") or {})
            check("SEL-07③ 兜底记录 BAND_FALLBACK", t.get("task_instance_id")
                  and m.get("band_fallback") is True
                  and m.get("fallback_reason") == "TARGET_BAND_EMPTY",
                  f"ability={fb_ability} policy={m}")
            async with eng.connect() as dbc:
                rv = (await dbc.execute(text(
                    "select difficulty from resource_version where resource_version_id=:r"),
                    {"r": uuid.UUID(t["resource_version_id"])})).fetchone()
            check("SEL-07④ selected_difficulty=真实资源难度（Mastery 源）",
                  m.get("selected_difficulty") == rv[0], f"真={rv[0]}")
            check("SEL-06/14 下发资源=published", not illegal(t["resource_version_id"]))
        else:
            check("SEL-07③ 兜底记录 BAND_FALLBACK", False, "当前 band 态无兜底活体样本")

        # ---------- SEL-06/14：全程 selected 无一非 published ----------
        bad = [p for p in picks + seq + small if illegal(p)]
        check("SEL-06/14 全程无未审批/退役资源混入", not bad, f"违例={len(bad)}")

        # ---------- SEL-11：pin 路径不带公平采样痕迹 ----------
        async with eng.connect() as dbc:
            gold = (await dbc.execute(text(
                "select resource_version_id::text from resource_version rv "
                "join resource r on r.resource_id=rv.resource_id "
                "where rv.review_status='published' and r.title not like '[T155]%' "
                "and rv.ui_schema->>'schema_version'='2.0' limit 1"))).fetchone()
        r = await c.post("/v1/learning/sessions",
                         json={"child_id": CHILD, "subject": "math", "requested_minutes": 15})
        sid = r.json()["session_id"]
        t = (await c.post("/v1/learning/tasks/next", json={
            "child_id": CHILD, "session_id": sid, "subject": "math",
            "pin_resource_version_id": gold[0]})).json()
        m = t.get("strategy_policy") or {}
        check("SEL-11 pin 路径=pinned 且无 selection_policy 采样", t.get("task_instance_id")
              and m.get("pinned") is True and m.get("selection_policy") is None, f"policy={m}")

    await eng.dispose()
    passed = sum(1 for _, ok, _ in results if ok)
    print("=" * 60)
    print(f"SEL 矩阵：{passed}/{len(results)} 通过")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    asyncio.run(main())
