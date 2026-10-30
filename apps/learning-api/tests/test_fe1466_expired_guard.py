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


class GuardFakeDB:
    """按**查询条件**分流的假会话（比顺序队列更严格）。

    FE-1466 复核补正：原 FakeDB 用"首次 execute 返回 task、其后依次 pop"
    的顺序队列，无法区分"按 submission_id 查"与"按 (task, attempt_no) 查"
    ——那样构造的负例其实是空查询的 A 场景，属假覆盖。本类改为读取编译后
    SQL 文本，按 where 条件决定返回哪条历史行，使"新 submission 借旧
    attempt_no"的绕过负例真正可测。
    """

    def __init__(self, task, history=None, rv=None):
        self.task = task
        self.rv = rv
        # history: list[FakeAttempt]
        self.history = list(history or [])
        self.evidence_rows = []
        self._got_task = False

    async def get(self, model, pk):
        name = getattr(model, "__name__", str(model))
        if name == "TaskInstance":
            return self.task
        return self.rv

    @staticmethod
    def _sql(stmt) -> str:
        try:
            return str(stmt.compile(compile_kwargs={"literal_binds": False}))
        except Exception:  # noqa: BLE001
            return str(stmt)

    @classmethod
    def _where(cls, stmt) -> str:
        """只取 WHERE 之后的条件文本。

        必须这样切：select(Attempt) 生成的 SQL 在**列清单**里就含有
        submission_id / attempt_no 等全部列名，用整条 SQL 判断会永远命中
        同一个分支——那样构造的负例仍会假通过（本次复核实测踩到）。
        """
        sql = cls._sql(stmt)
        up = sql.upper()
        i = up.find("WHERE")
        return sql[i:] if i >= 0 else ""

    async def execute(self, stmt):
        full = self._sql(stmt)
        where = self._where(stmt)
        # 1) FOR UPDATE 取 task（守卫入口）
        if "FOR UPDATE" in full.upper():
            self._got_task = True
            return FakeResult(self.task)
        # 2) 按 submission_id 查历史 attempt（V2 权威轨）——仅看 WHERE
        if "submission_id" in where:
            want = getattr(self, "wanted_sub", None)
            for a in self.history:
                if want is not None and a.submission_id == want:
                    return FakeResult(a)
            return FakeResult(None)
        # 3) 按 (task_instance_id, attempt_no) 查历史 attempt（V1 兼容轨）
        if "attempt_no" in where:
            want = getattr(self, "wanted_attempt_no", None)
            for a in self.history:
                if want is not None and a.attempt_no == want:
                    return FakeResult(a)
            return FakeResult(None)
        return FakeResult(None)

    async def flush(self):
        pass

    async def commit(self):
        pass


class FakeDB(GuardFakeDB):
    """兼容旧用例的最小队列版（保留既有 6 条断言不变）。

    注意：新用例一律用 GuardFakeDB——顺序队列无法区分查询条件。
    """
    def __init__(self, task, attempt_row, rv=None):
        super().__init__(task, history=([attempt_row] if attempt_row else []), rv=rv)
        self.queue = [attempt_row]
        self._got_task = False

    async def execute(self, stmt):
        if not self._got_task:
            self._got_task = True
            return FakeResult(self.task)
        row = self.queue.pop(0) if self.queue else None
        return FakeResult(row)


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
    db = FakeDB(task_of("cancelled"), attempt_row=None)
    out = call(db, submission_id=uuid.uuid4())
    assert out["expired"] is True and out["attempt_id"] is None
    assert out["correct"] is None and out["evidence_id"] is None
    assert out["next_action"]["policy_id"] == "task_expired"


# ---------- 复核补正：真正的"新 submission 借旧 attempt_no"绕过负例 ----------
# 用户复核意见（2026-10-21）：A 场景提交前 attempt 数为 0，B/C/D 各自覆盖
# 别的分支——三者都没有直接呈现"任务已有历史 Attempt + 新 submission_id +
# 旧 attempt_no"的绕过路径。以下两条补这一负例。

def test_expired_new_submission_reusing_old_attempt_no_not_bypassed():
    """已失效任务 + 已有历史 attempt(attempt_no=1) + 新 submission_id +
    旧 attempt_no=1 → 必须受控失效，**不得**返回旧 Attempt 冒充本次提交。

    这正是原实现（先按 (task,attempt_no) 命中即重放）的绕过路径：
    新请求只要猜中历史 attempt_no 就能拿到旧结果。
    """
    hist = FakeAttempt()          # attempt_no=1, submission_id=SUB_ID
    hist.attempt_no = 1
    db = GuardFakeDB(task_of("cancelled"), history=[hist])
    new_sub = uuid.uuid4()
    db.wanted_sub = new_sub       # 本次是新 submission
    db.wanted_attempt_no = 1      # 但复用了旧 attempt_no
    out = call(db, submission_id=new_sub, attempt_no=1,
               response={"answer": {"value": 99}})

    assert out["expired"] is True, "不得重放旧 Attempt"
    assert out["attempt_id"] is None, "不得把旧 attempt_id 冒充本次结果"
    assert out["evidence_id"] is None
    assert out["correct"] is None, "不得重新判分产出结果"
    assert out["next_action"]["policy_id"] == "task_expired"
    assert out["attempt_id"] != ATTEMPT_ID


def test_expired_new_submission_no_attempt_no_still_rejected():
    """已失效任务 + 已有历史 + 新 submission + 不带 attempt_no（默认 1）
    同样不得借历史命中——守卫依据是 submission_id，不是 attempt_no 巧合。"""
    hist = FakeAttempt()
    hist.attempt_no = 1
    db = GuardFakeDB(task_of("cancelled"), history=[hist])
    new_sub = uuid.uuid4()
    db.wanted_sub = new_sub
    db.wanted_attempt_no = 1
    out = call(db, submission_id=new_sub, attempt_no=1)
    assert out["expired"] is True and out["attempt_id"] is None


def test_expired_same_submission_replay_is_not_attempt_no_based():
    """对照组：命中只认 submission_id 相同——即使 attempt_no 不同也应重放。

    这条锁住"不回退到 (task,attempt_no) 判定"：若实现退回旧逻辑，本用例
    （submission 命中但 attempt_no 不同）会失败。
    """
    hist = FakeAttempt()          # submission_id=SUB_ID, attempt_no=1
    hist.attempt_no = 1
    db = GuardFakeDB(task_of("cancelled"), history=[hist])
    db.wanted_sub = SUB_ID
    db.wanted_attempt_no = 99     # attempt_no 不匹配
    out = call(db, submission_id=SUB_ID, attempt_no=99, response=dict(OLD_RESP))
    assert out["attempt_id"] == ATTEMPT_ID, "命中应只看 submission_id"
    assert out.get("expired") is None


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
