"""GrowthService 单元测试 —— BUG-1449 修复验收（样本点 0/1/7/8/9 + 业务语义 + 结构不变）。

缺陷：build_report 自由引用 build_snapshot 局部名 insufficient_period_sample，
凡周期证据 <8 的月报路径必 NameError（原 7 行占位测试从未触达）。
修复：判定随快照 metrics.insufficient_sample 持久化，报告只读不算。
本测试用假 DB 驱动 build_snapshot→build_report **全链**（不是只喂假快照），
验证目标不是"NameError 消失"，而是**样本不足的真实业务判断正确**
（<8 → 观察中文案 + flag=true；≥8 → 正常报告与重点建议）。
"""
import asyncio
import uuid
from datetime import date

import pytest

from app.services.growth import (
    MIN_PERIOD_EVIDENCE,
    build_report,
    build_snapshot,
    report_to_dict,
)


class _FakeEvidence:
    def __init__(self):
        self.evidence_id = uuid.uuid4()


class _FakeState:
    def __init__(self, ability_id, level):
        self.ability_id = ability_id
        self.level = level
        self.confidence = 0.5
        self.evidence_count = 3
        self.trend = "stable"


class _FakeExec:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def scalar_one_or_none(self):
        return None


class _FakeDb:
    """按 SQL 命中的表名分派：ability_state→2 节点；mastery_evidence→N 条；growth_snapshot→无上一期。"""

    def __init__(self, n_evidence):
        self.n = n_evidence

    async def execute(self, stmt, *a, **k):
        s = str(stmt).lower()
        if "ability_state" in s:
            return _FakeExec([_FakeState("app_rel", 2), _FakeState("app_rd", 1)])
        if "mastery_evidence" in s:
            return _FakeExec([_FakeEvidence() for _ in range(self.n)])
        return _FakeExec([])  # 上一期快照 / 其它

    def add(self, obj):
        pass

    async def flush(self):
        pass


EXPECTED_KEYS = {"report_id", "child_id", "snapshot_id", "period", "summary",
                 "metrics", "ability_changes", "evidence_refs", "next_focus",
                 "insufficient_sample"}


def _run_cycle(n):
    child = uuid.uuid4()
    db = _FakeDb(n)
    snap = asyncio.run(build_snapshot(
        db, child_id=child, period_type="monthly",
        period_start=date(2026, 9, 1), period_end=date(2026, 10, 1)))
    report = asyncio.run(build_report(db, child_id=child, snapshot=snap))
    return snap, report_to_dict(report)


@pytest.mark.parametrize("n", [0, 1, 7])
def test_under_threshold_is_observing(n):
    """样本不足（<8）：旧代码此路径必 NameError；修复后业务判定必须真实正确。"""
    snap, d = _run_cycle(n)
    assert snap.metrics["insufficient_sample"] is True
    assert d["insufficient_sample"] is True
    assert "观察中" in d["summary"]
    assert set(d.keys()) == EXPECTED_KEYS            # 返回结构不变
    assert len(d["ability_changes"]) == 2


@pytest.mark.parametrize("n", [8, 9])
def test_at_or_above_threshold_is_full_report(n):
    snap, d = _run_cycle(n)
    assert snap.metrics["insufficient_sample"] is False
    assert d["insufficient_sample"] is False
    assert "观察中" not in d["summary"]
    assert d["next_focus"] == ["app_rd", "app_rel"]  # level 最低优先
    assert len(d["evidence_refs"]["evidence_ids"]) == n


def test_boundary_semantics_preserved():
    """口径校验：恰好 8=充足（原 <8 判定，业务语义零漂移）。"""
    _, d7 = _run_cycle(MIN_PERIOD_EVIDENCE - 1)
    _, d8 = _run_cycle(MIN_PERIOD_EVIDENCE)
    assert d7["insufficient_sample"] is True
    assert d8["insufficient_sample"] is False


def test_build_report_reads_only_from_snapshot_metrics():
    """护栏：报告函数体不再出现旧局部名；判定唯一来源=快照 metrics。"""
    import inspect
    from app.services import growth as g

    body = inspect.getsource(g.build_report)
    assert "insufficient_period_sample" not in body
    assert 'metrics.get("insufficient_sample"' in body
