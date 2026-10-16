"""FE-1454 推荐策略回归（QA-ITEM-01 R2 决策③④，R2 §三/§四冻结口径）。

锁四件事（真实 DB 级主链 assign_next_task/submit_attempt）：
1. **跨 Session 曝光去重**：最近 EXPOSURE_WINDOW_SESSIONS 个 session 曝光过的资源
   不再重复——存在合格未曝光新题时必选新题（无依据重复率 0% 的机制面）；
2. **resource 级去重**：同一资源换 resource_version_id 不能绕过曝光窗口（R2 红线）；
3. **受控重复带原因**：新题耗尽/复习场景下允许重复，selection_reason ∈
   {spaced_review（task_purpose=review 且仍出同题——trend 走低链既有机制）,
    pool_exhausted（无复习依据的耗尽兜底）}，绝不静默重复；
4. **每 session ≤1 新能力配额**（决策③）：一个 session 最多引入 1 个新能力
   （引入=选中无 state 行的能力）；已引入能力继续练习不受限；真实行能力不占配额；
   事件记忆=strategy_policy.is_new_ability（作答建档后同 session 不丢失）。
"""
import asyncio
import datetime
import uuid

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
)
from app.services.learning import assign_next_task, submit_attempt

CHILD_ID = uuid.uuid5(uuid.NAMESPACE_DNS, "fe1454-child")
REL = "app_rel"
RD = "app_rd"
COND = "app_cond"


def _degrade():
    for tbl in Base.metadata.tables.values():
        for cst in list(tbl.constraints):
            if isinstance(cst, CheckConstraint):
                tbl.constraints.remove(cst)
    Base.metadata.tables["mastery_evidence"].columns["source_evidence_ids"].type = JSON()


def _rid(i):
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"fe1454-res-{i}")


def _rv(i):
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"fe1454-rv-{i}")


def _sid(i):
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"fe1454-sess-{i}")


def _run(specs, test_fn, extra_seed=None):
    """specs = [(idx, ability, difficulty)]；extra_seed(db) 在主数据后同步补种。"""
    _degrade()

    async def main():
        eng = create_async_engine("sqlite+aiosqlite:///:memory:")
        Session = async_sessionmaker(eng, expire_on_commit=False)
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with Session() as db:
            gid = uuid.uuid5(uuid.NAMESPACE_DNS, "fe1454-g")
            db.add(Guardian(guardian_id=gid, display_name="FE1454"))
            db.add(Child(child_id=CHILD_ID, guardian_id=gid, nickname="FE1454 QA",
                         grade="三年级"))
            for aid in (REL, RD, COND):
                db.add(AbilityNode(ability_id=aid, subject="math", domain_code="c",
                                   name=aid, definition="t", level_schema={}))
            for i, aid, diff in specs:
                db.add(Resource(resource_id=_rid(i), ability_id=aid, resource_type="task",
                                title=f"t{i}", status="active",
                                created_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)))
                db.add(ResourceVersion(
                    resource_version_id=_rv(i), resource_id=_rid(i), version_no=1,
                    difficulty=diff, task_type="numeric",
                    content={"goal": f"g{i}", "answer": "1"},
                    ui_schema={"schema_version": "1.0", "kind": "number"},
                    error_models=[], hint_policy={}, review_status="published",
                    created_at=datetime.datetime(2026, 1, 1, 0, i, tzinfo=datetime.timezone.utc)))
            db.add(LearningSession(session_id=_sid(0), child_id=CHILD_ID, subject="math"))
            if extra_seed:
                extra_seed(db)
            await db.commit()
        async with Session() as db:
            await test_fn(db)
        await eng.dispose()

    asyncio.run(main())


# ---- 1. 跨 Session 曝光去重：必出新题；耗尽后受控重复 ----

async def _exposure_body(db):
    out1 = await assign_next_task(db, child_id=CHILD_ID, session_id=_sid(0), subject="math")
    assert out1["resource_version_id"] == _rv(10)
    assert out1["strategy_policy"]["selection_reason"] == "new_item"

    # sid1（窗口含 sid0）：rid10 已曝光 → 必出未曝光 rid12
    db.add(LearningSession(session_id=_sid(1), child_id=CHILD_ID, subject="math"))
    await db.commit()
    out2 = await assign_next_task(db, child_id=CHILD_ID, session_id=_sid(1), subject="math")
    assert out2["resource_version_id"] == _rv(12), \
        f"窗口内已曝光资源不得重复（应 rv12，实发 {out2['resource_version_id']}）"

    # sid2：全部曝光 → 第二趟受控重复，reason=pool_exhausted（不空池死锁、不静默）
    db.add(LearningSession(session_id=_sid(2), child_id=CHILD_ID, subject="math"))
    await db.commit()
    out3 = await assign_next_task(db, child_id=CHILD_ID, session_id=_sid(2), subject="math")
    assert out3["task_instance_id"] is not None
    assert out3["strategy_policy"]["selection_reason"] == "pool_exhausted"


def test_cross_session_exposure_dedup():
    _run([(10, REL, 1), (12, REL, 1)], _exposure_body)


# ---- 2. resource 级去重：同资源换版本不能绕过 ----

async def _reskey_body(db):
    out1 = await assign_next_task(db, child_id=CHILD_ID, session_id=_sid(0), subject="math")
    assert out1["resource_version_id"] == _rv(20)  # rid20 v1（created_at asc）

    # rid20 追加 published v2 —— rid20 在窗口内已曝光 → 整资源（含 v2）必须排除
    db.add(ResourceVersion(
        resource_version_id=_rv(22), resource_id=_rid(20), version_no=2, difficulty=1,
        task_type="numeric", content={"goal": "g22", "answer": "1"},
        ui_schema={"schema_version": "1.0"}, error_models=[], hint_policy={},
        review_status="published",
        created_at=datetime.datetime(2026, 2, 1, tzinfo=datetime.timezone.utc)))
    db.add(LearningSession(session_id=_sid(1), child_id=CHILD_ID, subject="math"))
    await db.commit()

    out2 = await assign_next_task(db, child_id=CHILD_ID, session_id=_sid(1), subject="math")
    assert out2["resource_version_id"] == _rv(21), \
        "同一资源换 resource_version_id 不得绕过 resource 级曝光去重"


def test_resource_level_dedup_not_version():
    _run([(20, REL, 1), (21, REL, 1)], _reskey_body)


# ---- 3a. 新题耗尽 → pool_exhausted（可解释重复）----

async def _repeat_body(db):
    sid = _sid(0)
    out1 = await assign_next_task(db, child_id=CHILD_ID, session_id=sid, subject="math")
    assert out1["strategy_policy"]["selection_reason"] == "new_item"

    # 同 session 第二请求：rv30 已被 assigned_rvs+曝光排除 → 第一趟无新题 →
    # 第二趟重复，reason 必须落账
    out2 = await assign_next_task(db, child_id=CHILD_ID, session_id=sid, subject="math")
    assert out2["task_instance_id"] is not None, "新题耗尽不得空池死锁"
    assert out2["strategy_policy"]["selection_reason"] in ("pool_exhausted", "spaced_review")


def test_controlled_repeat_pool_exhausted():
    _run([(30, REL, 1)], _repeat_body)


# ---- 3b. trend 走低复习链 → spaced_review（走既有 retention 通道）----

def _seed_watch(db):
    db.add(AbilityState(child_id=CHILD_ID, ability_id=REL, level=1, confidence=0.5,
                        evidence_count=5, trend="watch"))


async def _review_body(db):
    # REL 唯一题已被 sid0 曝光？——直接在新 session 请求：真实行存在、带内有题但
    # rid=rv40 已曝光（sid0 出过）→ 第一趟无新题 → 第二趟：trend=watch → review 通道
    out = await assign_next_task(db, child_id=CHILD_ID, session_id=_sid(0), subject="math")
    assert out["strategy_policy"]["selection_reason"] == "new_item"
    db.add(LearningSession(session_id=_sid(1), child_id=CHILD_ID, subject="math"))
    await db.commit()
    out2 = await assign_next_task(db, child_id=CHILD_ID, session_id=_sid(1), subject="math")
    assert out2["task_instance_id"] is not None
    pol = out2["strategy_policy"]
    assert pol["selection_reason"] == "spaced_review", pol
    # 复习链与既有 evidence_role 机制咬合：watch+非迁移 → retention/review
    assert pol["task_purpose"] == "review" and pol["evidence_role"] == "retention"


def test_spaced_review_reason_and_retention_chain():
    _run([(40, REL, 1)], _review_body, extra_seed=_seed_watch)


# ---- 4. 每 session ≤1 新能力配额（决策③）----

def _seed_cond(db):
    # COND=已有真实行的能力（level0 conf0）：排序最先、练习不占引入配额
    db.add(AbilityState(child_id=CHILD_ID, ability_id=COND, level=0, confidence=0.0,
                        evidence_count=1, trend="stable"))


async def _quota_body(db):
    sid = _sid(0)
    # 排序=level asc 弱项优先：真实 COND(0,0) 行在前，虚拟 [app_rd, app_rel] 其后
    # ① 首题走**真实能力继续练习**（不占配额，is_new_ability=False）——
    #    裁决"当前能力继续学习不受配额限制"的直接体现
    out1 = await assign_next_task(db, child_id=CHILD_ID, session_id=sid, subject="math")
    assert out1["ability_id"] == COND and out1["strategy_policy"]["is_new_ability"] is False

    # ② COND 新题耗尽 → 第二趟继续 COND；**此时才轮到新能力引入**：
    #    第一趟 RD 虚拟带内题（rv40）未曝光应命中——配额未用时引入 RD（事件 1/1）
    out2 = await assign_next_task(db, child_id=CHILD_ID, session_id=sid, subject="math")
    assert out2["ability_id"] == RD and out2["strategy_policy"]["is_new_ability"] is True, \
        f"首次引入应是 RD（实发 {out2['ability_id']}）"

    # ③ 配额已满：REL 不得再引入（无状态、未引入、事件数≥1）→ 第二趟受控重复，
    #    可选 RD（已引入不重复计数）或 COND（真实行不占配额）
    out3 = await assign_next_task(db, child_id=CHILD_ID, session_id=sid, subject="math")
    assert out3["task_instance_id"] is not None, "不得因配额空池死锁"
    assert out3["ability_id"] != REL, "配额=1：不得引入第二个新能力 REL"
    assert out3["strategy_policy"]["selection_reason"] in ("spaced_review", "pool_exhausted")

    # ④ RD 有效作答 → 建档；同 session 后续请求仍不得引入 REL（事件记忆不因建档丢失
    #    ——若丢，introduced=∅，REL 虚拟可再引入，即"引入→建档→又引下一个"漏洞）
    res = await submit_attempt(db, task_instance_id=out2["task_instance_id"],
                               attempt_no=1, response={"answer": "1"})
    assert res["correct"] is True
    out4 = await assign_next_task(db, child_id=CHILD_ID, session_id=sid, subject="math")
    assert out4["ability_id"] != REL, "作答建档后同 session 不得引入第二个新能力"

    # ⑤ 新 session：配额刷新——未引入的 REL 应可获得首题（拓展不死）
    db.add(LearningSession(session_id=_sid(1), child_id=CHILD_ID, subject="math"))
    await db.commit()
    out5 = await assign_next_task(db, child_id=CHILD_ID, session_id=_sid(1), subject="math")
    assert out5["task_instance_id"] is not None
    # sid1 排序：真实 RD(建档后 level 可能升) / COND(0,0)…REL 虚拟最后——
    # REL 若带内无未曝光题则不引入（引入前提=难度带有合格资源，R2 §三），
    # 受控空池/重复皆合法；核心锁=不因"永远不引入"而死锁：
    # 直接指定请求 REL（正式策略允许口子）必有题
    out6 = await assign_next_task(db, child_id=CHILD_ID, session_id=_sid(1),
                                  subject="math", ability_id=REL)
    assert out6["ability_id"] == REL and out6["task_instance_id"] is not None


def test_new_ability_intro_quota_per_session():
    # sid0 曝光链：COND rv42 首出；RD rv40 引入；第二趟重复候选…；REL rv44 留 sid1
    _run([(40, RD, 1), (42, COND, 1), (44, REL, 1)], _quota_body,
         extra_seed=_seed_cond)


# ---- 4'. 真实行能力不占配额 ----

def _seed_rel(db):
    db.add(AbilityState(child_id=CHILD_ID, ability_id=REL, level=1, confidence=0.5,
                        evidence_count=5, trend="stable"))


async def _real_body(db):
    # RD 虚拟但题难度5（L0 带[1,1]无题）；REL 真实 level1 conf0.5 band[1,2]
    # 排序=真实(1,0.5) vs 虚拟(0,0)：虚拟在前但无题 → REL 命中，不占配额
    out = await assign_next_task(db, child_id=CHILD_ID, session_id=_sid(0), subject="math")
    assert out["ability_id"] == REL
    assert out["strategy_policy"]["is_new_ability"] is False
    assert out["strategy_policy"]["selection_reason"] == "new_item"
    # 同 session 再来一题：REL 新题耗尽后受控重复；RD 虚拟无题不中；COND 宇宙无题
    out2 = await assign_next_task(db, child_id=CHILD_ID, session_id=_sid(0), subject="math")
    assert out2["strategy_policy"]["is_new_ability"] is False, "无任何新能力被引入"


def test_real_state_abilities_not_quota_consumers():
    _run([(50, REL, 1), (51, RD, 5)], _real_body, extra_seed=_seed_rel)
