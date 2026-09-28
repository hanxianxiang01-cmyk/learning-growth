"""SessionResultService 单元测试 —— 聚合纯逻辑（不连库）。

学习行为判定 / 下一阶段重点 / 时长是纯函数，可用假对象测试。
DB 集成（真实聚合）在端到端验收里覆盖。

注意：V1.2 起后端输出对齐前端 canonical contract——
learning_behaviors 是 list[{code,label,achieved}]，next_recommendation 是 {type,title,ability_id}。
"""
import uuid
from datetime import datetime, timezone

from app.services.session_result import (
    _learning_behaviors,
    _next_recommendation,
    _session_duration_ms,
)


class _FakeTask:
    def __init__(self, tid):
        self.task_instance_id = tid


class _FakeAttempt:
    def __init__(self, tid, correct, hint=0):
        self.task_instance_id = tid
        self.correct = correct
        self.max_hint_level = hint
        self.submitted_at = datetime(2026, 9, 28, 12, 0, 0, tzinfo=timezone.utc)


class _FakeSession:
    def __init__(self, started, ended):
        self.started_at = started
        self.ended_at = ended


def _by_code(behaviors, code):
    return next((b for b in behaviors if b["code"] == code), None)


def test_learning_behaviors_list_shape():
    t1 = _FakeTask(uuid.uuid4())
    attempts = [
        _FakeAttempt(t1.task_instance_id, False),
        _FakeAttempt(t1.task_instance_id, True),
    ]
    correct_by_task = {t1.task_instance_id: True}
    b = _learning_behaviors([t1], attempts, correct_by_task)
    assert isinstance(b, list)
    assert _by_code(b, "RETRY_AFTER_ERROR")["achieved"] is True
    assert _by_code(b, "COMPLETED_FINAL_TASK")["achieved"] is True
    assert _by_code(b, "SESSION_COMPLETED")["achieved"] is True


def test_learning_behaviors_no_persist():
    t1 = _FakeTask(uuid.uuid4())
    attempts = [_FakeAttempt(t1.task_instance_id, False)]
    correct_by_task = {}
    b = _learning_behaviors([t1], attempts, correct_by_task)
    assert _by_code(b, "RETRY_AFTER_ERROR")["achieved"] is False
    assert _by_code(b, "COMPLETED_FINAL_TASK")["achieved"] is False
    assert _by_code(b, "SESSION_COMPLETED")["achieved"] is False


def test_hint_reasonable_threshold():
    t1 = _FakeTask(uuid.uuid4())
    a = [_FakeAttempt(t1.task_instance_id, False, hint=4)]
    b = _learning_behaviors([t1], a, {})
    assert _by_code(b, "HINT_USED_APPROPRIATELY")["achieved"] is False


def test_next_recommendation_lowest_level():
    changes = [
        {"ability_id": "A", "name": "能力A", "after_level": 3, "confidence": 0.8},
        {"ability_id": "B", "name": "能力B", "after_level": 1, "confidence": 0.5},
        {"ability_id": "C", "name": "能力C", "after_level": 2, "confidence": 0.6},
    ]
    r = _next_recommendation(changes)
    assert r["ability_id"] == "B"
    assert "title" in r
    assert r["type"] == "CONTINUE_ABILITY"


def test_next_recommendation_empty():
    r = _next_recommendation([])
    assert r["ability_id"] is None
    assert r["type"] == "NEXT"


def test_duration_uses_ended_at():
    started = datetime(2026, 9, 28, 12, 0, 0, tzinfo=timezone.utc)
    ended = datetime(2026, 9, 28, 12, 5, 0, tzinfo=timezone.utc)
    s = _FakeSession(started, ended)
    ms = _session_duration_ms(s, [])
    assert ms == 5 * 60 * 1000


def test_duration_falls_back_to_last_attempt():
    started = datetime(2026, 9, 28, 12, 0, 0, tzinfo=timezone.utc)
    s = _FakeSession(started, None)
    a = _FakeAttempt(uuid.uuid4(), True)
    a.submitted_at = datetime(2026, 9, 28, 12, 2, 0, tzinfo=timezone.utc)
    ms = _session_duration_ms(s, [a])
    assert ms == 2 * 60 * 1000