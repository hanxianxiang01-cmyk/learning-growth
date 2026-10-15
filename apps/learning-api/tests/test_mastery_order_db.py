"""BUG-1448 / G0-02 的 DB 层回归：_load_evidences 加载序 + 同时间戳二级稳定键。

纯函数单测（test_mastery.py）锁不住"加载序=occurred_at 升序 + evidence_id 稳定次键"
这一数据层约定。本测试真建表（内存 sqlite；PG 专属 ARRAY 列/CHECK 在 fixture 内局部降级，
不动模型），correctness 以唯一值编码时序，**物理插入序故意打乱**——
无 ORDER BY 的实现返回序列必乱；无二级键的实现同时间戳次序不确定。
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import JSON, event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CheckConstraint

from app.models import Base, MasteryEvidence
from app.services.mastery_db import _load_evidences

CHILD = uuid.uuid5(uuid.NAMESPACE_DNS, "qa-growth-order-child")
ABILITY = "app_rel"
BASE = datetime(2026, 10, 1, tzinfo=timezone.utc)

# 默认时序样例：(correctness, occurred_at 偏移天, evidence_id)——物理插入序打乱
def _eid(n): return uuid.uuid5(uuid.NAMESPACE_TEST if hasattr(uuid,"NAMESPACE_TEST") else uuid.NAMESPACE_DNS, "qa-order-%02d" % n)


def _suid(u): return str(u)
_DEFAULT_EIDS = [_eid(n) for n in (5, 1, 4, 2, 6, 3)]
SEED = [(0.6, 6, _DEFAULT_EIDS[0]), (0.1, 1, _DEFAULT_EIDS[1]),
        (0.4, 4, _DEFAULT_EIDS[2]), (0.2, 2, _DEFAULT_EIDS[3]),
        (0.5, 5, _DEFAULT_EIDS[4]), (0.3, 3, _DEFAULT_EIDS[5])]


def _prepare_table():
    # 仅测试环境：PG 专属类型在内存 sqlite 上降级，不改模型定义
    col = MasteryEvidence.__table__.columns["source_evidence_ids"]
    col.type = JSON()
    for cst in list(MasteryEvidence.__table__.constraints):
        if isinstance(cst, CheckConstraint):
            MasteryEvidence.__table__.constraints.remove(cst)


def _load_all(seed=None):
    seed = seed or SEED
    _prepare_table()
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    captured = []

    @event.listens_for(eng.sync_engine, "before_cursor_execute")
    def _cap(conn, cursor, statement, parameters, context, executemany):
        captured.append(statement)

    async def _go():
        async with eng.begin() as c:
            await c.run_sync(Base.metadata.create_all, tables=[MasteryEvidence.__table__])
        async with async_sessionmaker(eng, expire_on_commit=False)() as db:
            for corr, day, eid in seed:
                db.add(MasteryEvidence(
                    evidence_id=eid, child_id=CHILD, ability_id=ABILITY,
                    task_instance_id=uuid.uuid4(), attempt_id=None,
                    evidence_type="attempt_standard", correctness=corr,
                    independence=None, source_evidence_ids=None, context_family=None,
                    rule_version="test", valid=True, metadata_={},
                    occurred_at=BASE + timedelta(days=day),
                ))
            await db.commit()
        async with async_sessionmaker(eng, expire_on_commit=False)() as db:
            return await _load_evidences(db, CHILD, ABILITY)
    evs = asyncio.run(_go())
    asyncio.run(eng.dispose())
    return evs, captured


def test_sql_carries_order_by_occurred_at_and_tiebreak():
    """G0-01/G0-02 护栏：查询必带 ORDER BY occurred_at ASC + evidence_id 二级稳定键。"""
    _, captured = _load_all()
    sel = [s for s in captured if "mastery_evidence" in s.lower() and s.strip().lower().startswith("select")]
    assert sel, "未捕获到证据查询 SQL"
    load = " ".join(sel[0].lower().split())
    assert "order by" in load and "occurred_at" in load, f"SQL 缺 occurred_at 排序: {load[:220]}"
    ob = load.split("order by", 1)[1]
    assert "evidence_id" in ob, f"SQL 缺同时间戳二级稳定键 evidence_id: ob={ob[:200]}"


def test_load_returns_rows_ascending():
    evs, _ = _load_all()
    assert len(evs) == 6
    assert [round(e.correctness, 2) for e in evs] == [0.1, 0.2, 0.3, 0.4, 0.5, 0.6], "加载序非 occurred_at 升序"


def test_same_timestamp_stable_tiebreak():
    """G0-02 核心：4 条**完全相同 occurred_at**，物理插入序打乱，
    返回顺序必须恒按 evidence_id 升序（同刻证据相对序确定，不受 DB 计划影响）。"""
    e1, e2, e3, e4 = (_eid(10), _eid(40), _eid(20), _eid(30))
    seed = [(0.1, 0, e2), (0.2, 0, e4), (0.3, 0, e1), (0.4, 0, e3)]  # 同 day=0
    run1, _ = _load_all(seed)
    ids1 = [str(e.evidence_id) for e in run1]
    want = sorted(str(x) for x in (e1, e2, e3, e4))
    assert ids1 == want, f"同刻未按 evidence_id 升序: {ids1} != {want}"
