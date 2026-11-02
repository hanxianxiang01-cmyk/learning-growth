"""2026-11-01 产品规则调整的护栏：

- 每日题数硬限制**取消**：没有任何计数能拒绝一次正常作答；
- 接口频率限流**保留**：防脚本，不是限制孩子学习量；
- 真实作答数**保留**：只是记录，不参与掌握程度推导。

这些测试的存在意义是防止「取消上限」被下一次改动悄悄加回去，
以及防止「去掉配额」连带把防滥用一起删掉——后者是典型的顺手动刀。
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from app.core import education_rules
from app.services import guest_activity, rate_limit

CHILD = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ---------- A. 每日上限确实不在了 ----------


def test_daily_cap_functions_are_gone():
    """「每日上限」不是一个被关掉的开关，而是函数整个不存在。

    如果只是把 limit 调大到 99999，代码里仍然留着一条「数够了就拒绝」的路径，
    下一个人把配置改回去，孩子就又被挡住——所以这里断言的是**能力不存在**。
    """
    assert not hasattr(guest_activity, "is_over_limit")
    assert not hasattr(guest_activity, "remaining")


def test_no_daily_limit_config_remains():
    """配置里也不能再留 `guest_daily_task_limit`，否则会被人重新接上。"""
    from app.core.config import Settings

    fields = Settings.model_fields
    assert "guest_daily_task_limit" not in fields
    # 限流阈值必须在：防滥用被保留，且是新的一套（分钟级），不是每日题数
    assert "submit_rate_limit_per_minute" in fields
    assert "next_task_rate_limit_per_minute" in fields


def test_submit_path_no_longer_raises_daily_quota_code():
    """提交路径里不能再有每日配额的 429 分支。

    断言精确到字典字面量 `"code": "LE-4291"`，而不是全文搜 LE-4291——
    注释里提到这个码是**为了对照说明已取消**，那不算实现。
    """
    from app.api import learning as learning_api

    src = Path(learning_api.__file__).read_text(encoding="utf-8")
    assert '"code": "LE-4291"' not in src
    assert '"code": "LE-4292"' in src  # 限流那条还在


# ---------- B. 作答数只剩「记录」语义 ----------


@pytest.mark.asyncio
async def test_activity_summary_has_no_limit_fields(monkeypatch):
    """活动摘要只回答「今天做了几道」，不回答「还剩几道」。

    留着 `limit/remaining/exhausted` 会让前端再次长出一条配额条，
    也让下一个读者以为上限还在、只是数值很大。
    """
    async def fake_count(db, *, child_id, day):
        return 41  # 故意超过历史上限 30

    monkeypatch.setattr(guest_activity, "count_for_day", fake_count)
    summary = await guest_activity.activity_summary(db=None, child_id=uuid.uuid4())

    assert summary["answered_today"] == 41
    for forbidden in ("limit", "remaining", "exhausted"):
        assert forbidden not in summary


@pytest.mark.asyncio
async def test_answering_more_than_old_limit_is_still_recorded(monkeypatch):
    """第 41 题照样计入真实作答数——取消上限后「多做的题」不该凭空消失。"""
    async def fake_count(db, *, child_id, day):
        return 30

    monkeypatch.setattr(guest_activity, "count_for_day", fake_count)
    summary = await guest_activity.activity_summary(db=None, child_id=uuid.uuid4())
    assert summary["answered_today"] == 30


# ---------- C. 频率限流：放行 / 拒绝 / 恢复 / 隔离 ----------


def test_rate_limit_allows_within_window():
    rate_limit.reset()
    for _ in range(3):
        rate_limit.check(bucket="submit", key="c1", limit=3, now=1000.0)
    assert rate_limit.current_hits("submit", "c1") == 3


def test_rate_limit_rejects_after_limit_and_reports_wait():
    rate_limit.reset()
    for _ in range(3):
        rate_limit.check(bucket="submit", key="c1", limit=3, now=1000.0)
    with pytest.raises(rate_limit.RateLimited) as exc:
        rate_limit.check(bucket="submit", key="c1", limit=3, now=1000.5)
    # 最早一次命中在 1000.0，窗口 60s → 还需等约 59.5s，向上取整到 60
    assert exc.value.retry_after_seconds == 60


def test_rate_limit_window_slides():
    """窗口滑动后必须重新放行——否则「限流」会退化成永久封禁。"""
    rate_limit.reset()
    for _ in range(3):
        rate_limit.check(bucket="submit", key="c1", limit=3, now=1000.0)
    with pytest.raises(rate_limit.RateLimited):
        rate_limit.check(bucket="submit", key="c1", limit=3, now=1030.0)
    # 61 秒后，三次旧命中全部滑出窗口
    rate_limit.check(bucket="submit", key="c1", limit=3, now=1061.0)
    assert rate_limit.current_hits("submit", "c1") == 1


def test_rate_limit_isolated_per_child_and_bucket():
    rate_limit.reset()
    for _ in range(3):
        rate_limit.check(bucket="submit", key="c1", limit=3, now=1000.0)
    # 另一个孩子不受影响
    rate_limit.check(bucket="submit", key="c2", limit=3, now=1000.0)
    # 同一孩子的取题额度也不被提交额度挤占
    rate_limit.check(bucket="next_task", key="c1", limit=3, now=1000.0)
    assert rate_limit.current_hits("submit", "c1") == 3
    assert rate_limit.current_hits("submit", "c2") == 1
    assert rate_limit.current_hits("next_task", "c1") == 1


def test_rate_limit_window_does_not_grow_forever():
    """长期运行不能把每个来访者的 key 永久留在内存里。

    这个断言不是洁癖：窗口字典只增不减的话，跑上几个月就是一个缓慢的内存泄漏，
    而它发生在「防滥用」模块里——出问题时最不容易被怀疑到的地方。
    清理必须**只清彻底过期**的 key，所以同时验证「刚用过的 key 还在」。
    """
    rate_limit.reset()
    base = 1000.0
    # 造一批「很久以前来过」的 key
    for i in range(rate_limit._SWEEP_THRESHOLD + 1):
        rate_limit.check(bucket="submit", key=f"old{i}", limit=5, now=base)
    # 一小时后再来一个人：旧 key 全部过期，应被清掉
    rate_limit.check(bucket="submit", key="fresh", limit=5, now=base + 3600)
    window = rate_limit._WINDOWS["submit"]
    assert "fresh" in window, "刚来过的 key 不能被清掉（否则等于抹掉它的历史）"
    assert sum(1 for k in window if k.startswith("old")) == 0, "过期 key 应被清理"


def test_rate_limit_can_be_disabled_explicitly():
    """limit<=0 表示显式关闭（演练用），不能变成「一次都不许过」。"""
    rate_limit.reset()
    for _ in range(50):
        rate_limit.check(bucket="submit", key="c1", limit=0, now=1000.0)
    assert rate_limit.current_hits("submit", "c1") == 0


# ---------- D. 端到端：第 35 题照样能提交 ----------


class _FakeDB:
    async def commit(self):
        return None


@pytest.mark.asyncio
async def test_submit_endpoint_accepts_attempt_beyond_old_daily_limit(monkeypatch):
    """直接调一次提交端点 35 次（全同一天），一次都不该被「今天够了」拒绝。

    这是本次改动的核心断言：把「作答数很大」当作拒绝理由的代码路径已经不存在。
    限流在这里被临时放开（`rate_limit.check` 换成 no-op），因为要验的是
    **没有每日上限**，不是限流阈值——两者混在一起测会让人分不清红的是哪条。
    """
    from app.api import learning as learning_api
    from app.api.deps import GuestContext

    monkeypatch.setattr(learning_api.rate_limit, "check", lambda **_: None)

    async def fake_task_owner(db, task_id):
        return CHILD

    async def fake_assert_owns(db, *, guest_child_id, target_child_id):
        return None

    async def fake_submit(db, **kwargs):
        return {"correct": True, "next_action": {"type": "NEXT_TASK"}}

    async def fake_record(db, *, child_id, task_instance_id):
        return True

    async def fake_touch(db, *, child_id):
        return None

    monkeypatch.setattr(learning_api, "_task_owner", fake_task_owner)
    monkeypatch.setattr(learning_api, "assert_owns_child", fake_assert_owns)
    monkeypatch.setattr(learning_api, "submit_attempt", fake_submit)
    monkeypatch.setattr(learning_api.guest_activity, "record_task_consumed", fake_record)
    monkeypatch.setattr(learning_api, "touch_activity", fake_touch)

    guest = GuestContext(child_id=CHILD)
    for i in range(35):
        result = await learning_api.submit(
            payload={"task_instance_id": str(uuid.uuid4()), "attempt_no": 1},
            guest=guest,
            db=_FakeDB(),
        )
        assert result["correct"] is True, f"第 {i + 1} 次提交被判失败"



# ---------- E. 掌握程度不由题数推导 ----------


def test_mastery_weights_have_no_task_count_dimension():
    """「做了多少题」不是掌握的证据：四维权重里没有题数项。"""
    assert set(education_rules.MASTERY_WEIGHTS) == {
        "correctness",
        "independence",
        "stability",
        "transfer",
    }
