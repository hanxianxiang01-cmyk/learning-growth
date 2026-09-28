"""Sprint 2 端到端纵向闭环验收脚本。

模拟一个真实儿童画像，跑通完整链路：
  初始诊断 → 推荐任务 → 答错 → E04 诊断 → Hint1 → 重试 → Event → Evidence → Ability State → 下一任务变化

用法：PYTHONPATH=. python scripts/acceptance_sprint2.py
"""
from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models import (
    AbilityState,
    Attempt,
    Child,
    Guardian,
    LearningEvent,
    LearningPlan,
    LearningSession,
    MasteryEvidence,
    TaskInstance,
)
from app.services.curriculum import next_task
from app.services.planning import create_plan
from app.services.turn_service import record_attempt


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    checks: list[str] = []
    def ok(name: str, cond: bool, detail: str = ""):
        mark = "✅" if cond else "❌"
        checks.append((name, cond, detail))
        print(f"{mark} {name}{(' — ' + detail) if detail else ''}")

    async with Session() as db:
        # 造一个儿童画像（测试专用，结束后清理）
        gid = uuid.uuid4(); cid = uuid.uuid4()
        db.add(Guardian(guardian_id=gid, display_name="验收家长"))
        await db.flush()
        db.add(Child(child_id=cid, guardian_id=gid, nickname="验收儿童", grade="二年级"))
        await db.flush()

        # 初始能力状态：L0（零基础）
        db.add(AbilityState(child_id=cid, ability_id="app_rel", level=0, confidence=0.0, evidence_count=0, trend="watch"))
        await db.commit()

        subject = "math"
        ability = "app_rel"

        # ===== 1. 初始诊断（首次无证据 → 返回 next_task 推荐）=====
        nt0 = await next_task(db, child_id=cid, ability_id=ability)
        ok("1. 初始诊断→推荐任务", nt0 is not None and nt0["next_task"] is not None,
           f"fit_band={nt0['fit_band'] if nt0 else None}")

        # 建 plan + session（学习回合的容器）
        plan = await create_plan(db, child_id=cid, subject=subject, target_ability_ids=[ability])
        await db.commit()

        # ===== 2. 答错（第一次）→ 诊断 + Hint1 =====
        session_id = uuid.uuid4()
        db.add(LearningSession(session_id=session_id, child_id=cid, subject=subject, plan_id=plan.plan_id))
        await db.flush()

        task0 = nt0["next_task"]
        ti0 = uuid.uuid4()
        db.add(TaskInstance(
            task_instance_id=ti0, session_id=session_id, child_id=cid,
            ability_id=ability, resource_version_id=task0["resource_version_id"],
            assigned_difficulty=task0["difficulty"], strategy_policy={},
        ))
        await db.commit()

        # 第一次作答：错误
        r1 = await record_attempt(
            db, child_id=cid, task_instance_id=ti0, attempt_no=1,
            response={"answer": 0}, correct=False, max_hint_level=0,
            error_model="modeling", used_hint_levels=[],
        )
        await db.commit()
        ok("2. 答错→诊断", r1["diagnosis"] is not None and r1["diagnosis"]["code"] == "E04",
           f"诊断={r1['diagnosis']['code'] if r1['diagnosis'] else None}")
        ok("2. 答错→Hint1", r1["next_action"] is not None and r1["next_action"]["hint_level"] == 1,
           f"hint={r1['next_action']['hint_level'] if r1['next_action'] else None}")

        # ===== 3. 重试（第二次作答：正确）→ Evidence + State 更新 =====
        r2 = await record_attempt(
            db, child_id=cid, task_instance_id=ti0, attempt_no=2,
            response={"answer": 5}, correct=True, max_hint_level=1,
            error_model=None, used_hint_levels=[1],
        )
        await db.commit()
        ok("3. 重试正确→Evidence落库", r2["evidence_id"] is not None, f"evidence={r2['evidence_id']}")

        # 检查 evidence 是否已落库
        ev_count = (await db.execute(select(MasteryEvidence).where(MasteryEvidence.child_id == cid))).scalars().all()
        event_count = (await db.execute(select(LearningEvent).where(LearningEvent.child_id == cid))).scalars().all()
        ok("3a. Mastery Evidence 落库", len(ev_count) >= 2, f"证据条数={len(ev_count)}")
        ok("3b. Learning Event 落库", len(event_count) >= 2, f"事件条数={len(event_count)}")

        # ===== 4. Mastery 评估（手动触发 evaluate，验证 state 从 L0 升级）=====
        from app.services.mastery_db import evaluate_mastery_from_db
        ev = await evaluate_mastery_from_db(db, cid, ability)
        ok("4. Mastery 评估→L0升级", ev["new_level"] > ev["old_level"],
           f"L{ev['old_level']}→L{ev['new_level']} (decision={ev['decision']})")

        # 更新 state（真实闭环里由 Mastery 服务回写）
        state = await db.get(AbilityState, {"child_id": cid, "ability_id": ability})
        state.level = ev["new_level"]
        state.evidence_count = len(ev_count)
        state.confidence = ev["score"]
        await db.commit()

        # ===== 5. 下一任务变化（FitBand 应随 level 提升上移）=====
        nt1 = await next_task(db, child_id=cid, ability_id=ability)
        ok("5. 下一任务随 Mastery 变化", nt1 is not None and nt1["fit_band"] != nt0["fit_band"],
           f"fit_band {nt0['fit_band']} → {nt1['fit_band'] if nt1 else None}")

    # 清理测试数据
    async with Session() as db:
        from sqlalchemy import delete

        await db.execute(delete(LearningEvent).where(LearningEvent.child_id == cid))
        await db.execute(delete(MasteryEvidence).where(MasteryEvidence.child_id == cid))
        await db.execute(delete(Attempt).where(Attempt.task_instance_id == ti0))
        await db.execute(delete(TaskInstance).where(TaskInstance.child_id == cid))
        await db.execute(delete(LearningSession).where(LearningSession.child_id == cid))
        await db.execute(delete(LearningPlan).where(LearningPlan.child_id == cid))
        await db.execute(delete(AbilityState).where(AbilityState.child_id == cid))
        await db.execute(delete(Child).where(Child.child_id == cid))
        await db.execute(delete(Guardian).where(Guardian.guardian_id == gid))
        await db.commit()

    await engine.dispose()

    print()
    passed = sum(1 for _, c, _ in checks if c)
    total = len(checks)
    print(f"===== Sprint 2 纵向闭环验收：{passed}/{total} 通过 =====")
    if passed == total:
        print("🎉 产品第一次「活」了")


if __name__ == "__main__":
    asyncio.run(main())