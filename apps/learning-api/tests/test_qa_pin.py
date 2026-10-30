"""FE-1422a QA 确定性钉题——路由层契约单测（不依赖 DB，CI 无库运行）。

守三件事（全在 403/参数解析之前短路，db=None 安全）：
1. pin_resource_version_id 仅 QA child 可用——真实 child → 403；
2. pin 缺省/None → 不 403（生产路径行为不变，向后兼容）；
3. is_qa_child 对 str/UUID/脏值的容忍度。

V1.4 游客模式适配（FE-1475）：`next_task` 的身份来源从 body.child_id 改为会话
（`guest: GuestContext`）。本测试改为直接构造 GuestContext 模拟「会话身份是谁」，
这样测的仍然是**同一条红线**——pin 只对 QA child 放行——只是身份的注入点变了。
"""
import asyncio
import uuid

import pytest
from fastapi import HTTPException

from app.api.deps import GuestContext
from app.api.learning import next_task
from app.core.qa import QA_CHILD_ID, is_qa_child
from app.api.content import router as content_router

REAL_CHILD = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _guest(child_id):
    """模拟已解析的会话身份（绕过 Cookie→DB 那一段，本测试不测那段）。"""
    return GuestContext(child_id=child_id)


# ---- is_qa_child 判定 ----

def test_qa_child_constants():
    assert QA_CHILD_ID == uuid.UUID("00000000-0000-0000-0000-000000000099")
    assert is_qa_child(QA_CHILD_ID)
    assert is_qa_child(str(QA_CHILD_ID))
    assert not is_qa_child(REAL_CHILD)
    assert not is_qa_child("not-a-uuid")
    assert not is_qa_child(None)


# ---- next_task 路由守卫（db=None：403 必须在触库前抛出）----

def _call(payload, guest_child):
    return asyncio.run(next_task(payload, guest=_guest(guest_child), db=None))


def test_pin_by_real_child_rejected_403():
    with pytest.raises(HTTPException) as e:
        _call({
            "session_id": str(uuid.uuid4()),
            "subject": "math",
            "pin_resource_version_id": str(uuid.uuid4()),
        }, REAL_CHILD)
    assert e.value.status_code == 403


def test_pin_by_qa_child_passes_guard():
    # 过守卫后会触库（db=None → AttributeError），证明 403 没有误伤 QA 路径
    with pytest.raises(AttributeError):
        _call({
            "session_id": str(uuid.uuid4()),
            "subject": "math",
            "pin_resource_version_id": str(uuid.uuid4()),
        }, QA_CHILD_ID)


def test_no_pin_never_403():
    with pytest.raises(AttributeError):
        _call({
            "session_id": str(uuid.uuid4()),
            "subject": "math",
            "ability_id": "app_rel",
        }, REAL_CHILD)


def test_body_child_id_of_others_is_rejected():
    """游客模式：body 里写别人的 child_id 必须被拒（方案 3.2 归属校验）。

    这是 V1.4 新增的一条：原实现 body.child_id 就是授权依据，写谁就是谁。
    """
    with pytest.raises(HTTPException) as e:
        _call({
            "child_id": str(REAL_CHILD),
            "session_id": str(uuid.uuid4()),
            "subject": "math",
        }, QA_CHILD_ID)
    assert e.value.status_code == 404

    # 反向验证：同一个人写自己的 id 不会被误拒（继续走到触库 → AttributeError）
    with pytest.raises(AttributeError):
        _call({
            "child_id": str(REAL_CHILD),
            "session_id": str(uuid.uuid4()),
            "subject": "math",
            "ability_id": "app_rel",
        }, REAL_CHILD)


# ---- session 归属校验（10-29 验收 3.4 抓到的真实漏洞，永久钉住）----

class _FakeSessionOwnerDB:
    """假 db：_session_owner 查询恒返回预设的 owner_child_id。

    只模拟「session → child_id」这一次查询，让 next_task 的归属校验能在
    **不连真库**的情况下被离线验证。漏洞本质：docstring 承诺「session 必须
    属于当前游客，否则 404」，但初版代码从未校验 session_id 归属——改一个
    session_id 就能往别人会话里塞题。本测试就是那条承诺的可执行形式。
    """

    def __init__(self, owner_child_id):
        self._owner = owner_child_id

    async def execute(self, *_a, **_k):
        return self

    def scalar_one_or_none(self):
        return self._owner


def test_next_task_rejects_other_guests_session_404():
    """B 拿 A 的 session_id 取题 → 404（不泄露该 session 存在）。"""
    db = _FakeSessionOwnerDB(owner_child_id=REAL_CHILD)  # session 属于 REAL_CHILD
    with pytest.raises(HTTPException) as e:
        # 当前会话身份是 QA_CHILD，但 session 属于 REAL_CHILD → 越权
        asyncio.run(next_task(
            {"session_id": str(uuid.uuid4()), "subject": "math"},
            guest=_guest(QA_CHILD_ID), db=db,
        ))
    assert e.value.status_code == 404


def test_next_task_allows_own_session():
    """本人拿自己的 session 不被误拒：过归属校验后走到 assign_next_task 触库。

    反向验证——若归属校验写死拒绝一切，本用例会 404 而非 AttributeError，
    证明 404 确实是「他人」触发，不是校验无差别拦截（形态 22：反向验证靠
    无关红线通过）。这里 db 是假的，assign_next_task 会因缺字段抛异常，
    只要**不是 404** 就说明归属校验放行了本人。
    """
    db = _FakeSessionOwnerDB(owner_child_id=REAL_CHILD)
    try:
        asyncio.run(next_task(
            {"session_id": str(uuid.uuid4()), "subject": "math"},
            guest=_guest(REAL_CHILD), db=db,
        ))
    except HTTPException as e:
        assert e.status_code != 404, "本人 session 被误判为越权"
    except Exception:
        pass  # assign_next_task 用假 db 触发的任何非 HTTP 异常都属预期


def test_next_task_missing_session_returns_404():
    """session_id 缺失/非法 → 404（不 500，不把内部错误泄给调用方）。"""
    with pytest.raises(HTTPException) as e:
        asyncio.run(next_task(
            {"subject": "math"},  # 没有 session_id
            guest=_guest(REAL_CHILD), db=None,
        ))
    assert e.value.status_code == 404


# ---- catalog 端点存在性（冻结 OpenAPI 之外的新增只读，路径唯一口径）----

def test_v2_catalog_route_registered():
    paths = {(r.path, tuple(sorted(r.methods))) for r in content_router.routes}
    assert ("/content/v2-catalog", ("GET",)) in paths


# ---- FE-1438 qa_staged：pin 放行 / catalog 不可见（隔离语义锁）----

def test_pin_accepts_qa_staged_status():
    """服务层 pin 分支放行状态集合必须含 qa_staged（抽样实灌隔离通道）。"""
    import inspect
    from app.services import learning
    src = inspect.getsource(learning.assign_next_task)
    assert '"published", "qa_staged"' in src or '"qa_staged"' in src


def test_qa_staged_not_in_catalog_or_production_pool():
    """catalog 与生产选题查询的 SQL 谓词必须仍只认 published（qa_staged 双不可见）。"""
    import inspect
    from app.services import learning
    cat = inspect.getsource(learning.list_v2_catalog)
    prod = inspect.getsource(learning._published_resource_for_ability)
    for src in (cat, prod):
        assert '== "published"' in src
        assert "qa_staged" not in src


# ---- FE-1441：catalog 金题优先排序锁（155 交付题 published 后 E2E 首位稳定性）----

def test_catalog_gold_first_ordering():
    """list_v2_catalog 必须以「非 [T155] 优先」为排序首要键——
    否则交付题（difficulty 常更低）顶掉金题组首位，19 个 E2E spec 全崩。"""
    import inspect
    from app.services import learning
    src = inspect.getsource(learning.list_v2_catalog)
    assert "notlike(\"[T155]%\")" in src and ".desc()" in src
