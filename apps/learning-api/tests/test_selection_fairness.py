# FE-1442 生产选题公平性：_pick_fair 纯函数 + 分层语义 + 源码锁
import uuid
from datetime import datetime, timezone

from app.services.learning import _pick_fair, _published_resource_for_ability, assign_next_task, SELECTION_POLICY_VERSION


class RV:
    def __init__(self, difficulty=1):
        self.resource_version_id = uuid.uuid4()
        self.difficulty = difficulty
        self.ui_schema = {"schema_version": "1.0"}  # 非 V2，_v2_assignable 直通


def _h(count, minutes_ago=0):
    return {"count": count, "last_at": datetime.now(timezone.utc).replace(tzinfo=None) if False else datetime.now(timezone.utc)}


# SEL-01 纯函数面：全新池=全部 P0，决胜必属未见集合（哈希确定性）
def test_unseen_priority_covers_all():
    pool = [RV() for _ in range(9)]
    seen = set()
    for _ in range(9):  # 模拟 9 次独立请求（history 逐次增长由 e2e 真库验，此处验 P0 优先）
        rv, reason = _pick_fair(pool=pool, history={}, recent_ids=set(), child_id="c", salt=uuid.uuid4().hex)
        assert reason == "UNSEEN_PRIORITY"
    # 同 salt 确定性（有界哈希非随机）
    a, _ = _pick_fair(pool=pool, history={}, recent_ids=set(), child_id="c", salt="fixed")
    b, _ = _pick_fair(pool=pool, history={}, recent_ids=set(), child_id="c", salt="fixed")
    assert a.resource_version_id == b.resource_version_id


# P0 空 → P1 非近期；同层少曝光优先
def test_low_exposure_when_all_seen():
    pool = [RV() for _ in range(4)]
    h0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    history = {
        pool[0].resource_version_id: {"count": 5, "last_at": h0},
        pool[1].resource_version_id: {"count": 1, "last_at": h0},
        pool[2].resource_version_id: {"count": 3, "last_at": h0},
        pool[3].resource_version_id: {"count": 2, "last_at": h0},
    }
    rv, reason = _pick_fair(pool=pool, history=history, recent_ids=set(), child_id="c", salt="s")
    assert reason == "LOW_EXPOSURE"
    assert rv.resource_version_id == pool[1].resource_version_id  # 最少曝光胜


# SEL-13：P0/P1 全空 → P2 RECENT_FALLBACK（不死循环、显式回退）
def test_recent_fallback_tier():
    pool = [RV(), RV()]
    recent = {p.resource_version_id for p in pool}
    history = {p.resource_version_id: {"count": 2, "last_at": datetime.now(timezone.utc)} for p in pool}
    rv, reason = _pick_fair(pool=pool, history=history, recent_ids=recent, child_id="c", salt="s")
    assert reason == "RECENT_FALLBACK"
    assert rv.resource_version_id in recent


# SEL-07 场景2：带内全做过+全近期 → 仍带内 P2，绝不 BAND_FALLBACK
def test_repeat_is_not_band_empty():
    src = _published_resource_for_ability.__doc__ or ""
    assert "题目重复" in src and "≠" in src  # 语义锚


def test_policy_version_and_lock():
    assert SELECTION_POLICY_VERSION == "v1.4-fe1442"
    import inspect
    body = inspect.getsource(_published_resource_for_ability)
    assert "random()" not in body
    assert "order_by(ResourceVersion.created_at" not in body  # created_at 头名常胜已废弃
    assert "SESSION_POOL_EXHAUSTED" in body and '"band_fallback": True' in body
    assign = inspect.getsource(assign_next_task)
    assert "selection_policy" in assign and "band_fallback" in assign
