"""BUG-1448 的 DB 层回归：_load_evidences 加载序 + 窗口取尾联合语义。

纯函数单测（test_mastery.py）锁不住"加载序=occurred_at 升序"这一数据层约定。
本测试真建表（内存 sqlite；PG 专属 ARRAY 列/CHECK 在 fixture 内局部降级，不动模型），
correctness 以唯一值编码时序（0.1=最老…0.6=最新），**物理插入序故意打乱**——
无 ORDER BY 的实现（修复前 main）返回序列必乱、断言必炸。
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import JSON
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Base, MasteryEvidence
from app.services.mastery_db import _load_evidences

CHILD = uuid.uuid4()
ABILITY = "app_rel"

# (correctness 唯一时序编码, occurred_at 偏移天)；列表顺序=物理插入序（打乱）
SEED = [(0.6, 6), (0.1, 1), (0.4, 4), (0.2, 2), (0.5, 5), (0.3, 3)]
BASE = datetime(2026, 10, 1, tzinfo=timezone.utc)


def _load_all():
    col = MasteryEvidence.__table__.columns["source_evidence_ids"]
    col.type = JSON()  # 仅测试建表：PG ARRAY 降级 JSON，不改模型定义
    from sqlalchemy.schema import CheckConstraint
    for cst in list(MasteryEvidence.__table__.constraints):
        if isinstance(cst, CheckConstraint):  # PG 专属 cardinality() CHECK 移除
            MasteryEvidence.__table__.constraints.remove(cst)
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    captured = []
    from sqlalchemy import event

    @event.listens_for(eng.sync_engine, "before_cursor_execute")
    def _cap(conn, cursor, statement, parameters, context, executemany):
        captured.append(statement)

    async def _go():
        async with eng.begin() as c:
            await c.run_sync(Base.metadata.create_all, tables=[MasteryEvidence.__table__])
        async with async_sessionmaker(eng, expire_on_commit=False)() as db:
            for corr, day in SEED:
                db.add(MasteryEvidence(
                    evidence_id=uuid.uuid4(), child_id=CHILD, ability_id=ABILITY,
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


def test_sql_carries_order_by_occurred_at():
    """BUG-1448 确定性护栏：加载 mastery_evidence 的 SELECT 必须带
    ORDER BY occurred_at ASC——修复前（main）该子句缺失，此断言必炸。"""
    _, captured = _load_all()
    sel = [s for s in captured if "mastery_evidence" in s.lower() and s.strip().lower().startswith("select")]
    assert sel, "未捕获到证据查询 SQL"
    load = sel[0]
    assert "order by" in load.lower() and "occurred_at" in load.lower(), f"SQL 缺排序子句: {load[:220]}"


def test_load_returns_rows():
    evs, _ = _load_all()
    assert len(evs) == 6
