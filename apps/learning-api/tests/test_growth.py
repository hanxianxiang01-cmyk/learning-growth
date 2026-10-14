"""GrowthService 单元测试 —— 样本不足观察中、证据引用、下一阶段重点。

BUG-1449 回归：build_report 曾自由引用未定义名 insufficient_period_sample
（定义在 build_snapshot 作用域），凡周期证据 <8 的月报路径必 NameError。
现判定由快照 metrics 承载；本测试用 stub DB 走通 build_report 两条分支，
并在源码层面断言未定义自由名不再出现。DB 集成（真实聚合）在端到端验收里覆盖。
"""
import asyncio
import uuid
from datetime import date

from app.services.growth import (
    MIN_PERIOD_EVIDENCE,
    build_report,
    report_to_dict,
)


class _FakeSnapshot:
    def __init__(self, total_evidence):
        self.snapshot_id = uuid.uuid4()
        self.child_id = uuid.uuid4()
        self.period_type = "monthly"
        self.period_start = date(2026, 9, 1)
        self.period_end = date(2026, 10, 1)
        self.ability_states = {
            "app_rel": {"level": 2, "confidence": 0.8, "evidence_count": 12, "trend": "stable"},
            "app_check": {"level": 1, "confidence": 0.4, "evidence_count": 5, "trend": "watch"},
        }
        self.metrics = {
            "total_evidence": total_evidence,
            "ability_count": 2,
            "average_level": 1.5,
            "insufficient_sample": total_evidence < MIN_PERIOD_EVIDENCE,
        }


class _FakeResult:
    def scalar_one_or_none(self):
        return None

    def scalars(self):
        return self

    def all(self):
        return []


class _FakeDb:
    async def execute(self, *a, **k):
        return _FakeResult()

    def add(self, obj):
        pass

    async def flush(self):
        pass


def _run(total):
    snap = _FakeSnapshot(total)
    report = asyncio.run(build_report(_FakeDb(), child_id=snap.child_id, snapshot=snap))
    return report, snap


def test_build_report_insufficient_sample_no_name_error():
    """周期证据 <8：走"观察中"分支——正是旧代码 NameError 的路径。"""
    report, _ = _run(MIN_PERIOD_EVIDENCE - 1)
    d = report_to_dict(report)
    assert d["insufficient_sample"] is True
    assert "观察中" in d["summary"]


def test_build_report_sufficient_sample_focus_list():
    report, _ = _run(MIN_PERIOD_EVIDENCE)
    d = report_to_dict(report)
    assert d["insufficient_sample"] is False
    assert d["next_focus"] == ["app_check", "app_rel"]  # level 升序取最低
    assert report.evidence_refs == {"evidence_ids": []}


def test_no_free_undefined_name_in_growth_module():
    """源码级护栏：build_report 函数体不再自由引用该局部名（历史注释不算）。"""
    import inspect
    import app.services.growth as g

    body = inspect.getsource(g.build_report)
    assert "insufficient_period_sample" not in body.replace("# BUG-1449", "")
    # 判定唯一来源=快照 metrics
    assert 'metrics.get("insufficient_sample"' in body
