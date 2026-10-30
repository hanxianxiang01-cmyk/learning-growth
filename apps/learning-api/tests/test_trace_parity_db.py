"""FE-1452 v2：trace 预测与真实选题 **DB 级对账**（R2 §二.4——新策略下重新对账，
不沿用第一轮 99/99 旧证明）。

同库同状态下逐请求比较 trace_next_selection.predicted_selected/predicted_policy
与 assign_next_task 实发（ability/rvid/selection_reason/is_new_ability/
new_ability_source）。覆盖新策略全决策序：虚拟 L0、配额门、曝光排除、
两趟重复原因、显式通道。任一漂移=FAIL（追踪只读承诺+镜像正确性双锁）。
"""
import asyncio
import datetime
import uuid

from sqlalchemy import JSON
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CheckConstraint

from app.models import (
    AbilityNode,
    AbilityState,
    Base,
    Child,
    Guardian,
    LearningSession,
    Resource,
    ResourceVersion,
)
from app.services.learning import assign_next_task, trace_next_selection

CHILD_ID = uuid.uuid5(uuid.NAMESPACE_DNS, "tracepar-child")
SID0 = uuid.uuid5(uuid.NAMESPACE_DNS, "tracepar-s0")
SID1 = uuid.uuid5(uuid.NAMESPACE_DNS, "tracepar-s1")
REL, RD, COND = "app_rel", "app_rd", "app_cond"


def _rid(i):
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"tp-res-{i}")


def _rv(i):
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"tp-rv-{i}")


def _run(test_fn):
    for tbl in Base.metadata.tables.values():
        for cst in list(tbl.constraints):
            if isinstance(cst, CheckConstraint):
                tbl.constraints.remove(cst)
    Base.metadata.tables["mastery_evidence"].columns["source_evidence_ids"].type = JSON()

    async def main():
        eng = create_async_engine("sqlite+aiosqlite:///:memory:")
        Session = async_sessionmaker(eng, expire_on_commit=False)
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with Session() as db:
            gid = uuid.uuid5(uuid.NAMESPACE_DNS, "tp-g")
            db.add(Guardian(guardian_id=gid))
            db.add(Child(child_id=CHILD_ID, guardian_id=gid, nickname="t", grade="3"))
            for aid in (REL, RD, COND):
                db.add(AbilityNode(ability_id=aid, subject="math", domain_code="c",
                                   name=aid, definition="t", level_schema={}))
            specs = [(70, RD, 1), (71, RD, 1), (72, COND, 1), (73, REL, 1)]
            for i, aid, diff in specs:
                db.add(Resource(resource_id=_rid(i), ability_id=aid, resource_type="task",
                                title=f"t{i}", status="active",
                                created_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)))
                db.add(ResourceVersion(
                    resource_version_id=_rv(i), resource_id=_rid(i), version_no=1,
                    difficulty=diff, task_type="numeric",
                    content={"goal": f"g{i}", "answer": "1"},
                    ui_schema={"schema_version": "1.0"}, error_models=[],
                    hint_policy={}, review_status="published",
                    created_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
                               + datetime.timedelta(minutes=i)))
            db.add(LearningSession(session_id=SID0, child_id=CHILD_ID, subject="math"))
            db.add(LearningSession(session_id=SID1, child_id=CHILD_ID, subject="math"))
            await db.commit()
        async with Session() as db:
            await test_fn(db)
        await eng.dispose()

    asyncio.run(main())


async def _pair(db, sid, **kw):
    tr = await trace_next_selection(db, child_id=CHILD_ID, session_id=sid, **kw)
    out = await assign_next_task(db, child_id=CHILD_ID, session_id=sid, subject="math", **kw)
    pred = tr["predicted_selected"]
    if out["task_instance_id"] is None:
        assert pred is None, f"实发空池但 trace 预测 {pred}"
        return tr, out
    assert pred is not None, "trace 预测出题但实发空池"
    assert pred["resource_version_id"] == str(out["resource_version_id"]), \
        f"预测 {pred} vs 实发 {out['resource_version_id']}"
    assert pred["ability_id"] == out["ability_id"]
    pol = out["strategy_policy"]
    tp = tr["predicted_policy"]
    if tp:  # auto/explicit 通道有 reason 分账
        assert tp["selection_reason"] == pol["selection_reason"], (tp, pol)
        assert tp["is_new_ability"] == pol["is_new_ability"]
        assert tp["new_ability_source"] == pol["new_ability_source"]
    return tr, out


async def _body(db):
    # 冷启动：虚拟宇宙按 ability_id asc=[app_cond, app_rd, app_rel]，cond 带内有题先中
    tr, out = await _pair(db, SID0)
    assert out["ability_id"] == COND
    assert tr["per_ability"][0]["is_virtual"] is True

    # session 内第二请求：72 已曝光/已发 → 继续 RD 第二题 or 受控重复——预测=实发即可
    await _pair(db, SID0)
    # 第三请求（配额仍满）
    await _pair(db, SID0)
    # 新 session：曝光窗口内多资源已曝光 → 大概率第二趟重复，仍须一致
    await _pair(db, SID1)
    # 显式通道对账
    await _pair(db, SID1, ability_id=REL)


def test_trace_matches_production_sequence():
    _run(_body)
