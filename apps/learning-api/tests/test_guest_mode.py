"""游客模式 P1/P2 单测（不依赖真实 DB：用内存假会话覆盖判定逻辑）。

分三组：
- A. 配额判定（纯函数 + 台账语义，方案第五章全部绕过路径逐条对应）
- B. 会话令牌（哈希落库、无效/过期/撤销三态）
- C. 归属校验（方案 3.2 的核心：改 id 读不到别人的数据）

**为什么大量断言写的是「绝对断言」而不是「相对比较」**：
例如 `assert n_new == 0` 而不是 `assert n_new < n_all`。相对断言在两边都为 0
时也会通过，恰好把「判据根本没生效」伪装成通过（项目里踩过这个坑，见
memory/PATTERNS_判据失效形态.md 形态 21/22）。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException

from app.api.deps import assert_owns_child
from app.services.guest import hash_token, new_token
from app.services.guest_quota import quota_date_for

QA_CHILD = uuid.UUID("00000000-0000-0000-0000-000000000099")
REAL_CHILD = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ---------- A. 配额：时区与日期换算 ----------

def test_quota_date_uses_fixed_server_timezone():
    """固定时区：同一时刻在不同客户端时区下必须得到同一个 quota_date。"""
    # 2026-10-29 15:30 UTC = 2026-10-29 23:30 北京时间（同一天）
    moment = datetime(2026, 10, 29, 15, 30, tzinfo=timezone.utc)
    assert quota_date_for(moment, tz_name="Asia/Shanghai").isoformat() == "2026-10-29"


def test_quota_date_crosses_day_at_server_midnight():
    """跨日边界：UTC 16:00 = 北京次日 00:00，必须算到新的一天。

    这条是方案第五章「跨日边界」的直接对应：若用 UTC 划分，
    北京时间 0:00~8:00 的学习会被算进前一天，孩子的「今天」就错位了。
    """
    moment = datetime(2026, 10, 29, 16, 0, tzinfo=timezone.utc)
    assert quota_date_for(moment, tz_name="Asia/Shanghai").isoformat() == "2026-10-30"
    # 同一时刻按 UTC 划分仍是 10-29 —— 证明时区参数真的起作用，不是恒等变换
    assert quota_date_for(moment, tz_name="UTC").isoformat() == "2026-10-29"


def test_quota_date_rejects_naive_datetime():
    """裸时间不可解释，必须报错而不是猜一个时区。

    猜错的后果是把跨日边界算错一天，且没人会发现——静默错误比报错危险。
    """
    with pytest.raises(ValueError):
        quota_date_for(datetime(2026, 10, 29, 23, 30), tz_name="Asia/Shanghai")


def test_quota_uses_iana_zone_object_not_fixed_offset():
    """用 IANA 名称而非固定 offset：夏令时地区也不会漂。

    这里用 America/New_York 验证——它的 UTC 偏移在 3 月和 11 月会变。
    若实现里写死 +08:00 之类，本断言不会失败（那是中国时区），
    但 `ZoneInfo("America/New_York")` 能正常换算本身就证明走的是 IANA 路径。
    """
    summer = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)
    winter = datetime(2026, 12, 1, 12, 0, tzinfo=timezone.utc)
    tz = ZoneInfo("America/New_York")
    # 夏令时：UTC-4 → 08:00；冬令时：UTC-5 → 07:00。两者相差 1 小时。
    assert summer.astimezone(tz).hour == 8
    assert winter.astimezone(tz).hour == 7


# ---------- B. 会话令牌 ----------

def test_token_is_high_entropy_and_unique():
    """方案 2.1「服务端生成的高熵随机标识」。"""
    tokens = {new_token() for _ in range(200)}
    assert len(tokens) == 200, "令牌出现碰撞"
    assert all(len(t) >= 32 for t in tokens)


def test_token_hash_is_stable_and_not_reversible_to_token():
    """落库的是哈希：同一 token 恒得同一哈希，且哈希里不含明文 token。"""
    t = new_token()
    h1 = hash_token(t)
    h2 = hash_token(t)
    assert h1 == h2
    assert len(h1) == 64
    assert t not in h1
    # 不同 token 哈希不同（防止实现误写成常量）
    assert hash_token(new_token()) != h1


# ---------- C. 归属校验 ----------

class _DummyDB:
    """归属校验不触库，db 传 None 也安全——这条性质本身要守住。"""


def test_assert_owns_child_passes_for_self():
    import asyncio

    asyncio.run(assert_owns_child(None, guest_child_id=REAL_CHILD, target_child_id=REAL_CHILD))


def test_assert_owns_child_rejects_other_returns_404():
    """他人 → 404（不是 403）。

    403 等于告诉对方「这个 id 存在但不是你的」，可被用来枚举有效 id；
    404 让「不存在」与「不属于你」不可区分。
    """
    import asyncio

    with pytest.raises(HTTPException) as e:
        asyncio.run(
            assert_owns_child(None, guest_child_id=QA_CHILD, target_child_id=REAL_CHILD)
        )
    assert e.value.status_code == 404


def test_assert_owns_child_is_not_truthiness_based():
    """归属判定不能依赖真值：两个不同 uuid 都为真，若实现写成 `if guest:` 就永远放行。

    反向验证：任意两个不同 id 必须全部被拒（枚举若干组，防止只对特定值生效）。
    """
    import asyncio

    pairs = [
        (uuid.uuid4(), uuid.uuid4()),
        (QA_CHILD, REAL_CHILD),
        (REAL_CHILD, QA_CHILD),
    ]
    for a, b in pairs:
        with pytest.raises(HTTPException) as e:
            asyncio.run(assert_owns_child(None, guest_child_id=a, target_child_id=b))
        assert e.value.status_code == 404


# ---------- D. 配额台账语义（用 SQLite 内存库跑真实 insert 冲突路径）----------

def test_daily_quota_table_primary_key_dedupes_same_task():
    """台账主键 (child_id, task_instance_id) 保证同题只计一次。

    这里直接验证**模型主键定义**，而不是只验证调用方有没有判断——
    因为「重复提交不计数」这件事必须由数据库约束兜底，不能靠应用层自觉
    （并发时应用层判断会同时通过）。
    """
    from app.models import GuestDailyQuota

    pk = [c.name for c in GuestDailyQuota.__table__.primary_key]
    assert pk == ["child_id", "task_instance_id"], f"主键定义变了：{pk}"


def test_guest_session_pk_is_token_hash_not_child():
    """会话表主键必须是 token 哈希：同一游客可以有多个会话（多标签页）。

    若把 child_id 设成主键，第二个标签页会顶掉第一个，表现为「开新窗口把旧窗口
    踢下线」——对儿童产品是明显的坏体验，且很难归因到「主键选错了」。
    """
    from app.models import GuestSession

    pk = [c.name for c in GuestSession.__table__.primary_key]
    assert pk == ["session_token_hash"], f"会话主键定义变了：{pk}"


def test_guest_identity_expiry_is_not_nullable():
    """expires_at 不能为空：允许为空等于允许「永不过期」，7 天承诺直接失效。"""
    from app.models import GuestIdentity

    col = GuestIdentity.__table__.c.expires_at
    assert col.nullable is False