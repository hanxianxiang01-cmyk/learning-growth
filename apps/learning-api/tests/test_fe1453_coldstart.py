"""FE-1453 冷启动死锁 + 能力视野锁死 统一修复回归（QA-ITEM-01 ITEM01-01/02，P0）。

共同根因：auto 分支把"已有 ability_state 行"当完整候选集。修复后候选宇宙 =
真实行 ∪ 有已发布可下发资源的未开启能力（虚拟 L0）。本测试真建表（内存 sqlite，
PG 专属 CHECK/ARRAY 局部降级；seed 与断言同一 asyncio loop，内存库同 loop 才存活）锁：
1. 零行账号 auto 首题能出（冷启动闭环），且**选题本身零落 ability_state**（不伪造证据）；
2. 已有行账号可自然触达未开启能力（视野拓展），真实同级行先于虚拟能力；
3. 虚拟能力带内无题 → 受控跳过继续下一候选；全空仍返回空池 reason 不乱发题；
4. 显式 ability_id 分支（挑战卡 fallback_to_lowest）行为不变。

R2 合并条件五项边界补测（QA-ITEM-01 R2 裁决 §二，**全部走 assign/submit 真实 DB
级主链**，不只查 _candidate_abilities 返回值）：
R2-1 零记录新孩子有合法 L0 题 → 直接获得首题；
R2-2 某虚拟能力带内无题 → 跳过继续找其他合格能力；
R2-3 全部无适配题 → 受控空池且零虚假状态（ability_state/evidence 双零）；
R2-4 选题阶段零 Mastery Evidence；首次有效作答后 persist_mastery_state 自然建档；
R2-5 app_transfer 观察项**不自动纳入虚拟引入**（即使其带内有题也不引入；
     已有真实行 / 显式 ability_id 不受限——"除非正式策略明确允许"的口子在显式意图）。
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
    MasteryEvidence,
    Resource,
    ResourceVersion,
    TaskInstance,
)
from app.services.learning import (
    _candidate_abilities,
    assign_next_task,
    submit_attempt,
)

CHILD_ID = uuid.uuid5(uuid.NAMESPACE_DNS, "fe1453-child")
SESSION_ID = uuid.uuid5(uuid.NAMESPACE_DNS, "fe1453-session")
REL = "app_rel"
RD = "app_rd"
TR = "app_transfer"


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


def _evidences_select():
    return select(MasteryEvidence).where(MasteryEvidence.child_id == CHILD_ID)


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
            for aid in (REL, RD, TR):
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
                    # content.answer=唯一"1"，配合 response {"answer":"1"} 判对（_judge 数值比对）
                    content={"goal": f"g{i}", "answer": "1"}, ui_schema=_v1_ui(),
                    error_models=[], hint_policy={}, review_status="published",
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


# =====================================================================
# R2 合并条件五项边界补测（QA-ITEM-01 R2 裁决 §二）——全部真实 DB 级主链
# =====================================================================

# ---- R2-1 零记录新孩子 + 有合法 L0 题 → 直接获得首题（非 Pin/非 Bootstrap）----

async def _r21_body(db):
    out = await assign_next_task(db, child_id=CHILD_ID, session_id=SESSION_ID,
                                 subject="math")
    assert out["task_instance_id"] is not None, f"冷启动首题失败: {out}"
    assert out["ability_id"] == REL and out["difficulty"] == 1
    assert out["strategy_policy"]["fit_band"] == [1, 1]


def test_r2_1_coldstart_first_task_no_pin():
    _run_with([(REL, 1)], _r21_body)


# ---- R2-2 虚拟能力带内无题 → 跳过继续找其他合格能力（不得整体空池）----
# 场景=裁决点名的复发风险：候选排序靠前的能力（RD）带内无题，
# 若实现"选中最先候选即终止"，明明 REL 有 L0 题孩子仍无法学习。

async def _r22_body(db):
    cands = await _candidate_abilities(db, child_id=CHILD_ID, session_id=SESSION_ID)
    assert [a for a, _ in cands] == [RD, REL], "RD 虚拟 L0 排序在前"
    # 前置条件坐实：RD 唯一题难度 3，虚拟 L0 带 [1,1] 必空
    out = await assign_next_task(db, child_id=CHILD_ID, session_id=SESSION_ID,
                                 subject="math")
    assert out["task_instance_id"] is not None, \
        f"带内无题的虚拟能力不得阻断整体选题: {out}"
    assert out["ability_id"] == REL, "跳过 RD 后必须命中 REL"


def test_r2_2_skip_virtual_ability_with_empty_band():
    _run_with([(RD, 3), (REL, 1)], _r22_body)


# ---- R2-3 全部能力无适配题 → 受控空池，零虚假状态（state/evidence 双零）----

async def _r23_body(db):
    out = await assign_next_task(db, child_id=CHILD_ID, session_id=SESSION_ID,
                                 subject="math")
    assert out["task_instance_id"] is None
    assert out["reason"] == "no_published_resource_in_band"
    assert (await db.execute(_states_select())).scalars().all() == []
    assert (await db.execute(_evidences_select())).scalars().all() == []
    assert (await db.execute(
        select(TaskInstance).where(TaskInstance.session_id == SESSION_ID)
    )).scalars().all() == [], "空池不得落任何任务"


def test_r2_3_full_empty_pool_no_fake_state():
    _run_with([(REL, 4), (RD, 5)], _r23_body)


# ---- R2-4 选题零证据；首次有效作答后 persist_mastery_state 自然建档 ----

async def _r24_body(db):
    # ① 选题阶段：任务落库但 evidence/state 双零
    out = await assign_next_task(db, child_id=CHILD_ID, session_id=SESSION_ID,
                                 subject="math")
    assert out["task_instance_id"] is not None
    assert (await db.execute(_evidences_select())).scalars().all() == []
    assert (await db.execute(_states_select())).scalars().all() == []

    # ② 非法作答（answer 缺失，correct=None）：不建档——"有效作答"口径
    res = await submit_attempt(db, task_instance_id=out["task_instance_id"],
                               attempt_no=1, response={})
    assert res["correct"] is None
    assert (await db.execute(_states_select())).scalars().all() == [], \
        "无效/缺答案作答不得建档"

    # ③ 首次有效作答（正确）：evidence 产 1 条，ability_state 自然建档
    res2 = await submit_attempt(db, task_instance_id=out["task_instance_id"],
                                attempt_no=2, response={"answer": "1"})
    assert res2["correct"] is True
    evs = (await db.execute(_evidences_select())).scalars().all()
    assert len(evs) == 1, "一题一原子证据（retry 不重复产）"
    sts = (await db.execute(_states_select())).scalars().all()
    assert [s.ability_id for s in sts] == [REL], "建档仅发生在有效作答之后"
    assert sts[0].evidence_count == 1
    # level 由 Mastery 引擎判定（L0→L1 是否跳级属冻结决策序，本测试不锁死，只锁建档发生）


def test_r2_4_no_evidence_until_valid_submission():
    _run_with([(REL, 1)], _r24_body)


# ---- R2-5 app_transfer 观察项：不自动纳入虚拟引入范围（R2 裁决 §二.5）----
# 排除只作用于"未开启能力的虚拟引入"；已有真实行 / 显式 ability_id 不受限。

async def _r25_body(db):
    # TR 带内**有**难度1题——若入虚拟宇宙必然可被 auto 选中；裁决要求不引入
    cands = await _candidate_abilities(db, child_id=CHILD_ID, session_id=SESSION_ID)
    got = [a for a, _ in cands]
    assert TR not in got, "app_transfer 不得自动进入虚拟引入候选"
    assert got == [RD], "其余能力正常（REL 无发布题不入宇宙）"

    # RD 无题、TR 有题但不引入 → auto 受控空池（不因观察项题救场）
    out = await assign_next_task(db, child_id=CHILD_ID, session_id=SESSION_ID,
                                 subject="math")
    assert out["task_instance_id"] is None
    assert out["reason"] == "no_published_resource_in_band"

    # 口子1：显式 ability_id=TR（挑战卡/正式策略）仍可出题
    out2 = await assign_next_task(db, child_id=CHILD_ID, session_id=SESSION_ID,
                                  subject="math", ability_id=TR)
    assert out2["ability_id"] == TR and out2["task_instance_id"] is not None

    # 口子2：TR 已有真实行 → 正常参与候选（观察项限制=只限虚拟引入）
    db.add(AbilityState(child_id=CHILD_ID, ability_id=TR, level=0,
                        confidence=0.0, evidence_count=1, trend="watch"))
    await db.commit()
    cands2 = await _candidate_abilities(db, child_id=CHILD_ID, session_id=SESSION_ID)
    assert (TR, False) in cands2, "真实行不受观察项排除影响"


def test_r2_5_transfer_observer_not_auto_introduced():
    # RD 题难度 3（虚拟 L0 带[1,1] 内无题）；TR 题难度 1（若误入虚拟宇宙必被选中）
    _run_with([(TR, 1), (RD, 3)], _r25_body)
