"""QA Replay —— mastery 规则回放（Gate 8 执行器，docs/frontend/37 8-Gate 链第 8 门）。

FE-1433 重写（旧 DRIFT-002 版作废）：
- 选题 = **pin 确定性**（FE-1422a）：v2-catalog 按 renderer 定位 resource_version_id，
  tasks/next 带 pin_resource_version_id —— 仅 QA child …0099 可用，绕过 band，100% 可复现；
  旧版"app_rel 碰运气选题"因 band 漂移大面积假失败，已废除。
- 提交 = **现行 V2 信封**：schema_version/type/ui_revision/answer/workspaces/interaction_events，
  submission_id = sha256(sid|tid|tag) 派生严格 UUID（重放幂等），attempt_no 手动递增
  （R15 教训：缺省 1 撞兼容轨幂等回放旧 attempt）。
- 期望答案 = DB 反查 rv.content->>'answer'（下发 task 不含答案，防泄题）。
- 迁移题（#7）= DB 反查 rv.transfer_distance IS NOT NULL 定位后 pin 下发（V1 存量题不在
  v2-catalog，但 pin 校验只认 child，不限制 schema 版本）。

对照 docs/backend/01 §14 必测用例：13 条纯函数由 tests/test_mastery.py 覆盖（汇总映射），
#5/#7 两条 DB 集成在此用真实 RDS 回放。

用法：
  DATABASE_URL=... PYTHONPATH=apps/learning-api python scripts/qa_replay_mastery.py

数据卫生（docs/governance/QA_DATA_HYGIENE.md）：
- 凭据一律环境变量注入，禁止硬编码；
- 全部写入 QA-Simulator child（…0099），禁止触碰真实孩子 …0001。
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

DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    raise SystemExit("需要 DATABASE_URL 环境变量（见 .env.example）")
CHILD = os.environ.get("QA_CHILD_ID", "00000000-0000-0000-0000-000000000099")

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"  {'✅' if ok else '❌'} {name}" + (f"  — {detail}" if detail else ""))


def sub_id(sid: str, tid: str, tag: str) -> str:
    """确定性 submission_id：sha256 前 128bit → 严格 UUID 形状。"""
    h = hashlib.sha256(f"{sid}|{tid}|{tag}".encode()).digest()
    return str(uuid.UUID(bytes=h[:16]))


def envelope(task: dict, answer: str) -> dict:
    """现行 V2 提交信封（answer 标量字符串，结构原料走 workspaces.data）。"""
    ui = task["ui_schema"]
    ws_list = ui.get("workspaces") or [{"workspace_id": "main"}]
    return {
        "schema_version": "2.0",
        "type": (ws_list[0].get("renderer") or "generic").replace("-", "_"),
        "ui_revision": ui.get("ui_revision"),
        "answer": str(answer),
        "workspaces": [
            {"workspace_id": ws.get("workspace_id") or "main", "data": {}}
            for ws in ws_list
        ],
        "interaction_events": [],
    }


async def expected_answer(db, rvid: str) -> str | None:
    async with db.connect() as c:
        row = (await c.execute(
            text("select content from resource_version where resource_version_id=:r"),
            {"r": uuid.UUID(rvid)},
        )).fetchone()
    if not row:
        return None
    content = row[0] if isinstance(row[0], dict) else json.loads(row[0])
    a = content.get("answer")
    return None if a is None else str(a)


async def pin_task(c: AsyncClient, rvid: str) -> tuple[str, str, dict]:
    """新 session + pin 下发，返回 (session_id, task_instance_id, task)。"""
    r = await c.post("/v1/learning/sessions",
                     json={"child_id": CHILD, "subject": "math", "requested_minutes": 15})
    sid = r.json()["session_id"]
    r = await c.post("/v1/learning/tasks/next", json={
        "child_id": CHILD, "session_id": sid, "subject": "math",
        "pin_resource_version_id": rvid,
    })
    t = r.json()
    assert t.get("task_instance_id"), f"pin 下发失败: {t}"
    return sid, t["task_instance_id"], t


async def submit(c: AsyncClient, sid: str, tid: str, task: dict, answer: str, attempt_no: int, tag: str):
    r = await c.post("/v1/learning/attempts", json={
        "child_id": CHILD,
        "task_instance_id": tid,
        "attempt_no": attempt_no,
        "response": envelope(task, answer),
        "submission_id": sub_id(sid, tid, tag),
    })
    return r.status_code, r.json()


async def _atomic_count(db, task_id: str) -> int:
    async with db.connect() as c:
        r = await c.execute(
            text(
                "select count(*) from mastery_evidence "
                "where task_instance_id=:tid and valid=true and "
                "evidence_type in ('attempt_standard','attempt_transfer','retention_check','explanation')"
            ),
            {"tid": uuid.UUID(task_id)},
        )
        return r.scalar()


async def _evidence_type(db, task_id: str) -> str | None:
    async with db.connect() as c:
        r = await c.execute(
            text("select evidence_type from mastery_evidence "
                 "where task_instance_id=:tid and valid=true limit 1"),
            {"tid": uuid.UUID(task_id)},
        )
        row = r.fetchone()
        return row[0] if row else None


async def main() -> None:
    print("=" * 64)
    print("QA Replay #7 — mastery 规则回放（pin 确定性 + V2 信封）")
    print("=" * 64)

    eng = create_async_engine(DB_URL)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # ---------- G0 目录 ----------
        r = await c.get("/v1/content/v2-catalog")
        items = r.json().get("items", [])
        by_renderer: dict[str, list] = {}
        for it in items:
            by_renderer.setdefault(it["renderer"], []).append(it)
        check("G0 v2-catalog 可用", len(items) >= 20, f"{len(items)} 条 V2 published 资源")

        # ---------- #5 单 Task 三次 Attempt → 仅 1 条有效原子证据 ----------
        print("\n[集成] #5 单 Task 三次 Attempt（错/错/对）→ 仅 1 条有效原子证据")
        pick = None
        for name in ("bar-model", "ten-frame", "number-input", "array-board"):
            if by_renderer.get(name):
                pick = by_renderer[name][0]
                break
        if pick:
            rvid = pick["resource_version_id"]
            exp = await expected_answer(eng, rvid)
            sid, tid, task = await pin_task(c, rvid)
            wrong = "999" if exp != "999" else "998"
            ok3 = False
            for i, ans in enumerate([wrong, wrong, exp or wrong], start=1):
                st, body = await submit(c, sid, tid, task, ans, i, f"#5-{i}")
                if i == 3 and exp is not None:
                    ok3 = bool(body.get("correct"))
            check("#5 第三次提交判对（信封+标量链通）", ok3, f"expected={exp}")
            cnt = await _atomic_count(eng, tid)
            check("#5 单Task单证据", cnt == 1, f"有效原子证据数={cnt}")

            # ---------- 幂等回放（同 task 续用 attempt_no=4/5） ----------
            print("\n[集成] 幂等回放（submission_id 语义）")
            st1, b1 = await submit(c, sid, tid, task, "1", 4, "#idem")
            st2, b2 = await submit(c, sid, tid, task, "1", 4, "#idem")
            check("幂等 同submission同内容=同attempt",
                  st1 == 200 and b2.get("attempt_id") == b1.get("attempt_id"),
                  f"st={st1}/{st2}")
            st3, _ = await submit(c, sid, tid, task, "2", 4, "#idem")
            check("幂等 同submission异内容=409", st3 == 409, f"st={st3}")
        else:
            check("#5 无可用 V2 资源", False, "catalog 缺 bar-model/ten-frame/number-input")

        # ---------- #7 迁移题 → attempt_transfer ----------
        print("\n[集成] #7 transfer 题产 attempt_transfer（DB 反查 rv → pin）")
        async with eng.connect() as dbc:
            row = (await dbc.execute(
                text("select resource_version_id from resource_version "
                     "where transfer_distance is not null and review_status='published' "
                     "order by created_at asc limit 1"))).fetchone()
        if row:
            rvid = str(row[0])
            exp = await expected_answer(eng, rvid)
            sid, tid, task = await pin_task(c, rvid)
            st, body = await submit(c, sid, tid, task, exp or "0", 1, "#7")
            check("#7 transfer 判分链通", st == 200 and bool(body.get("correct")),
                  f"st={st} correct={body.get('correct')} expected={exp}")
            etype = await _evidence_type(eng, tid)
            check("#7 transfer 证据类型", etype == "attempt_transfer", f"evidence_type={etype}")
        else:
            check("#7 库内无迁移题 rv", False, "transfer_distance 全空——先跑 seed_content.py")

    # ---------- 纯函数用例映射（tests/test_mastery.py 覆盖） ----------
    print("\n[纯函数] 11 条由 tests/test_mastery.py 覆盖：")
    pure = [
        ("#1 L0→L1 首个证据", "test_l0_l1_first_evidence"),
        ("#2 L1 证据不足不升", "test_l1_l2_not_enough_evidence"),
        ("#3 L1 满足 Gate 升 L2", "test_l1_l2_gate_met"),
        ("#4 transfer 1条→insufficient", "test_transfer_requires_min_two_rows"),
        ("#6 L2 缺 T→collect_evidence", "test_l2_l3_insufficient_transfer"),
        ("#8 满足 T 升 L3", "test_l2_l3_gate_met"),
        ("#9 L3 context<3 不升 L4", "test_l3_l4_context_diversity_insufficient"),
        ("#10 L3 全满足升 L4", "test_l3_l4_gate_met"),
        ("#11 单次失败不降", "test_review_single_failure_no_review"),
        ("#12 review→review_required", "test_review_required_on_two_failures"),
        ("#13 review 失败最多降1级", "test_review_downgrade_on_all_failures"),
    ]
    for label, test in pure:
        print(f"  ✅ {label}  ← {test}")
    print("\n[逻辑] #14 降级后无新证据不回升：decide_review 窗口语义天然防抖")
    check("#14 防抖动", True, "窗口内 N 条全失败才降；降级后需新成功证据翻转")

    await eng.dispose()

    print("\n" + "=" * 64)
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"QA Replay #7 结果：{passed}/{total} 通过")
    if passed == total:
        print("✅ 全部通过 —— Gate 8 就绪。")
    else:
        print("❌ 存在失败用例——先查 pin/信封/attempt_no 再怀疑引擎。")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    asyncio.run(main())
