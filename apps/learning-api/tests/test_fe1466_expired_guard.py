"""FE-1466 Q07 submit_attempt 失效守卫单测（不依赖 DB，进 CI backend-tests）。

裁决 21:26 §二 行为表逐项 + §四"关键边界进入持续回归"：
1 失效任务+新 submission → expired 受控结果（即使该任务有其他历史 Attempt
  也不能绕过守卫——命中依据是"本次请求=历史那次提交"，不是"以前答过"）
2 失效任务+同 submission_id 同内容 → 重放原 Attempt（不判分/不新增）
3 失效任务+同 submission_id 异内容 → SubmissionConflict（API 层=409），
  不被 expired 掩盖
4 失效任务+V1（无 submission）同 (task,attempt_no) → 重放既有旧轨
5 正常 assigned 任务 → 不进守卫（原流程）
"""
import asyncio
import uuid
from types import SimpleNamespace

import pytest

from app.services.learning import submit_attempt
from app.services.turn_service import SubmissionConflict

TASK_ID = uuid.uuid4()
SUB_ID = uuid.uuid4()
ATTEMPT_ID = uuid.uuid4()
OLD_RESP = {"schema_version": "2.0", "answer": {"value": 12}}


class FakeAttempt:
    attempt_id = ATTEMPT_ID
    task_instance_id = TASK_ID
    submission_id = SUB_ID
    response = OLD_RESP
    correct = True
    max_hint_level = 0
    client_elapsed_ms = None
    submitted_at = None


class FakeResult:
    def __init__(self, row):
        self._row = row
    def scalar_one_or_none(self):
        return self._row


class FakeDB:
    """get(TaskInstance/ResourceVersion) + execute(select(Attempt)→首个结果,
    select(LearningEvent)→None)。守卫内 Attempt 查询至多一次，其后为事件查询。"""
    def __init__(self, task, attempt_row, rv=None):
        self.task = task
        self.rv = rv
        self.queue = [attempt_row]
        self._got_task = False
    async def get(self, model, pk):
        name = getattr(model, "__name__", str(model))
        if name == "TaskInstance":
            return self.task
        return self.rv
    async def execute(self, stmt):
        # 首查=FOR UPDATE 取 task；其后守卫内 Attempt 查询=attempt_row；
        # 再后（LearningEvent 等）返回 None。
        if not self._got_task:
            self._got_task = True
            return FakeResult(self.task)
        row = self.queue.pop(0) if self.queue else None
        return FakeResult(row)
    async def flush(self):
        pass
    async def commit(self):
        pass


def task_of(status):
    return SimpleNamespace(
        task_instance_id=TASK_ID, resource_version_id=uuid.uuid4(),
        child_id=uuid.uuid4(), session_id=uuid.uuid4(), ability_id="app_rel",
        status=status, strategy_policy=None)


def call(db, submission_id, response=None, attempt_no=1):
    return asyncio.run(submit_attempt(
        db, task_instance_id=TASK_ID, attempt_no=attempt_no,
        response=response or {"answer": {"value": 99}}, used_hint_levels=[],
        client_elapsed_ms=None, submission_id=submission_id))


def test_expired_new_submission_controlled_reject():
    # 任务已有"别的"历史 attempt（不同 submission/attempt_no）——不得绕过守卫
    other = FakeAttempt()
    other.submission_id = uuid.uuid4()
    db = FakeDB(task_of("cancelled"), attempt_row=None)
    out = call(db, submission_id=uuid.uuid4())
    assert out["expired"] is True and out["attempt_id"] is None
    assert out["correct"] is None and out["evidence_id"] is None
    assert out["next_action"]["policy_id"] == "task_expired"


def test_expired_same_submission_same_content_replays():
    db = FakeDB(task_of("cancelled"), attempt_row=FakeAttempt())
    out = call(db, submission_id=SUB_ID, response=dict(OLD_RESP))
    assert out["attempt_id"] == ATTEMPT_ID and out.get("expired") is None


def test_expired_same_submission_different_content_conflicts():
    db = FakeDB(task_of("cancelled"), attempt_row=FakeAttempt())
    with pytest.raises(SubmissionConflict):
        call(db, submission_id=SUB_ID, response={"answer": {"value": 7}})


def test_expired_v1_same_attempt_no_replays():
    a = FakeAttempt()
    a.submission_id = None
    db = FakeDB(task_of("cancelled"), attempt_row=a)
    out = call(db, submission_id=None, attempt_no=1)
    assert out["attempt_id"] == ATTEMPT_ID


def test_expired_v1_new_attempt_no_rejected_despite_history():
    # V1 兼容轨：(task, attempt_no=2) 无历史行 → 即使该任务有 attempt_no=1，
    # execute 按条件查询返回 None → 受控失效（不因"以前答过"而放行/重放）
    db = FakeDB(task_of("cancelled"), attempt_row=None)
    out = call(db, submission_id=None, attempt_no=2)
    assert out["expired"] is True


def test_assigned_task_not_hit_guard(monkeypatch):
    """正常任务不进守卫：走原流程（rv 缺失 → correct=None 正常记录路径）。"""
    from app.services import learning as L
    called = {}
    async def fake_record_attempt(db, **kw):
        called["ok"] = True
        return {"attempt_id": None, "correct": None, "next_action": None,
                "diagnosis": None, "evidence_id": None}
    monkeypatch.setattr(L, "record_attempt", fake_record_attempt)
    rv = SimpleNamespace(content={"answer": 5}, ui_schema={"schema_version": "1.0"},
                         error_models=None)
    db = FakeDB(task_of("assigned"), attempt_row=None, rv=rv)
    out = call(db, submission_id=uuid.uuid4(), response={"answer": {"value": 5}})
    assert called.get("ok") and out.get("expired") is None
