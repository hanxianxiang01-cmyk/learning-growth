"""FE-1453 冷启动死锁 + 能力视野锁死 统一修复回归（QA-ITEM-01 ITEM01-01/02，P0）。

共同根因：auto 分支把"已有 ability_state 行"当完整候选集。修复后候选宇宙 =
真实行 ∪ 有已发布可下发资源的未开启能力（虚拟 L0）。本测试真建表（内存 sqlite，
PG 专属 CHECK/ARRAY 局部降级；seed 与断言同一 asyncio loop，内存库同 loop 才存活）锁：
1. 零行账号 auto 首题能出（冷启动闭环），且**选题本身零落 ability_state**（不伪造证据）；
2. 已有行账号可自然触达未开启能力（视野拓展），真实同级行先于虚拟能力；
3. 虚拟能力带内无题 → 受控跳过继续下一候选；全空仍返回空池 reason 不乱发题；
4. 显式 ability_id 分支（挑战卡 fallback_to_lowest）行为不变。
"""
import asyncio
import datetime
import uuid
from typing import Any

from sqlalchemy import JSON, select
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
    TaskInstance,
)
from app.services.learning import _candidate_abilities, assign_next_task

CHILD_ID = uuid.uuid5(uuid.NAMESPACE_DNS, "fe1453-child")
SESSION_ID = uuid.uuid5(uuid.NAMESPACE_DNS, "fe1453-session")
REL = "app_rel"
RD = "app_rd"


def _degrade_pg_extras():
    for tbl in Base.metadata.tables.values():
        for cst in list(tbl.constraints):
            if isinstance(cst, CheckConstraint):
                tbl.constraints.remove(cst)
    Base.metadata.tables["mastery_evidence"].columns["source_evidence_ids"].type = JSON()


def _v1_ui() -> dict[str, Any]:
    # V1 形态：不受 _v2_assignable 门控影响（恒可下发），聚焦候选集逻辑本身
    return {"schema_version": "1.0", "kind": "number"}


def _states_select():
    return select(AbilityState).where(AbilityState.child_id == CHILD_ID)


def _run_with(resource_specs, test_fn, extra_seed=None):
    """seed（建表+数据）与 test_fn 在同一 asyncio loop 内执行——
    内存 sqlite 的连接与库生命周期都绑 loop，分开 loop 必失。"""
    _degrade_pg_extras()

    async def main():
        eng = create_async_engine("sqlite+aiosqlite:///:memory:")
        # expire_on_commit=False 与生产 AsyncSessionLocal 同配置
        # （否则 commit 后 rv 属性过期，返回 dict 读 rv.difficulty 会触发 MissingGreenlet）
        Session = async_sessionmaker(eng, expire_on_commit=False)
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with Session() as db:
            gid = uuid.uuid5(uuid.NAMESPACE_DNS, "fe1453-guardian")
            db.add(Guardian(guardian_id=gid, display_name="FE1453 QA 家长"))
            db.add(Child(child_id=CHILD_ID, guardian_id=gid, nickname="FE1453 QA",
                         grade="三年级"))
            for aid in (REL, RD):
                db.add(AbilityNode(ability_id=aid, subject="math", domain_code="cognition",
                                   name=aid, definition="test", level_schema={}))
            for i, (aid, diff) in enumerate(resource_specs):
                rid = uuid.uuid5(uuid.NAMESPACE_DNS, f"fe1453-res-{i}")
                db.add(Resource(resource_id=rid, ability_id=aid, resource_type="task",
                                title=f"t{i}", status="active",
                                created_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)))
                db.add(ResourceVersion(
                    resource_version_id=uuid.uuid5(uuid.NAMESPACE_DNS, f"fe1453-rv-{i}"),
                    resource_id=rid, version_no=1, difficulty=diff, task_type="numeric",
                    content={"goal": f"g{i}"}, ui_schema=_v1_ui(), error_models=[],
                    hint_policy={}, review_status="published",
                    created_at=datetime.datetime(2026, 1, 1 + i, tzinfo=datetime.timezone.utc)))
            db.add(LearningSession(session_id=SESSION_ID, child_id=CHILD_ID, subject="math"))
            if extra_seed:
                extra_seed(db)
            await db.commit()
        async with Session() as db:
            await test_fn(db)
        await eng.dispose()

    asyncio.run(main())


# ---- 1. 冷启动：零行账号 auto 首题 ----

async def _coldstart_body(db):
    cands = await _candidate_abilities(db, child_id=CHILD_ID, session_id=SESSION_ID)
    assert sorted(c[0] for c in cands) == [RD, REL]
    assert all(virt for _, virt in cands)  # 全部为虚拟 L0

    out = await assign_next_task(db, child_id=CHILD_ID, session_id=SESSION_ID,
                                 subject="math")
    # RD 虚拟 L0 band[1,1] 无题（唯一题难度3）→ 受控跳过 → REL band[1,1] 难度1 命中
    assert out["ability_id"] == REL and out["difficulty"] == 1, out
    assert out["strategy_policy"]["fit_band"] == [1, 1]
    # **不伪造证据**：选题本身零落 ability_state
    assert (await db.execute(_states_select())).scalars().all() == []
    # 任务落库正常
    t = (await db.execute(
        select(TaskInstance).where(TaskInstance.session_id == SESSION_ID))).first()
    assert t is not None


def test_coldstart_zero_state_gets_first_task():
    _run_with([(REL, 1), (RD, 3)], _coldstart_body)


# ---- 2. 视野拓展：有行账号能触达未开启能力 ----

def _expansion_seed(db):
    db.add(AbilityState(child_id=CHILD_ID, ability_id=REL, level=2,
                        confidence=0.8, evidence_count=9, trend="stable"))


async def _expansion_body(db):
    cands = await _candidate_abilities(db, child_id=CHILD_ID, session_id=SESSION_ID)
    got = dict(cands)  # ability -> is_virtual
    assert got == {REL: False, RD: True}
    # 未开启能力按 L0 参与排序：level asc 语义下排在已练强的 REL 之前（弱项/新能力优先）
    assert [a for a, _ in cands] == [RD, REL]

    out = await assign_next_task(db, child_id=CHILD_ID, session_id=SESSION_ID,
                                 subject="math")
    assert out["ability_id"] == RD, "未开启能力必须可被 auto 选中（视野不再锁死）"
    assert out["strategy_policy"]["fit_band"] == [1, 1]


def test_existing_rows_still_reach_virtual_abilities():
    _run_with([(REL, 1), (RD, 1)], _expansion_body, extra_seed=_expansion_seed)


def _realzero_seed(db):
    db.add(AbilityState(child_id=CHILD_ID, ability_id=RD, level=0,
                        confidence=0.0, evidence_count=1, trend="watch"))


async def _realzero_body(db):
    cands = await _candidate_abilities(db, child_id=CHILD_ID, session_id=SESSION_ID)
    assert [a for a, _ in cands] == [RD, REL]  # 真实(0,0,False)先于虚拟(0,0,True)
    assert cands[0][1] is False and cands[1][1] is True


def test_real_zero_level_rows_order_before_virtual():
    _run_with([(REL, 1), (RD, 1)], _realzero_body, extra_seed=_realzero_seed)


# ---- 3. 受控空池：全候选带内无题 → reason 明示，不乱发题 ----

async def _emptyband_body(db):
    out = await assign_next_task(db, child_id=CHILD_ID, session_id=SESSION_ID,
                                 subject="math")
    assert out["task_instance_id"] is None
    assert out["reason"] == "no_published_resource_in_band"
    assert (await db.execute(_states_select())).scalars().all() == []


def test_all_virtual_out_of_band_returns_empty_reason():
    _run_with([(REL, 4), (RD, 5)], _emptyband_body)


# ---- 4. 显式能力分支行为不变 ----

async def _explicit_body(db):
    # 零行 + 显式 REL：L0 band[1,1] 无题 → fallback_to_lowest 仍出题（原行为）
    out = await assign_next_task(db, child_id=CHILD_ID, session_id=SESSION_ID,
                                 subject="math", ability_id=REL)
    assert out["ability_id"] == REL and out["difficulty"] == 3, out


def test_explicit_ability_branch_unchanged():
    _run_with([(REL, 3), (RD, 1)], _explicit_body)
