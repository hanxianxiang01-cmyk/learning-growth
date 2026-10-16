"""QA-ITEM-01 selection-trace 端点——路由契约单测（不依赖 DB，CI 无库运行）。

R2 §二安全收口后的双层门禁：
1. **默认关闭 → 404**：生产不启用调试入口（不暴露存在性）——不加 monkeypatch 即测；
2. 启用后：非 QA child → 403（与 pin 同红线，触库前短路，db=None 安全）；
3. QA child 过守卫进入服务层（db=None → AttributeError，证明未误伤 QA 路径）；
4. 脏参数 422；
5. trace_next_selection 源码护栏零写入（commit/add/TaskInstance( 构造禁止）
   + read_only 标记。
"""
import asyncio
import inspect
import uuid

import pytest
from fastapi import HTTPException

import app.api.learning as learning_api
from app.api.learning import selection_trace
from app.core.qa import QA_CHILD_ID
from app.services.learning import trace_next_selection

REAL_CHILD = uuid.UUID("00000000-0000-0000-0000-000000000001")


class _S:
    selection_trace_enabled = True


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setattr(learning_api, "get_settings", lambda: _S())


def test_disabled_by_default_404():
    """生产默认（无 monkeypatch）：端点关闭 → 404，不暴露存在性。"""
    # 防御：显式把 settings 换成 enabled=False 的对象（get_settings lru_cache 不受环境污染）
    class _Off:
        selection_trace_enabled = False
    original = learning_api.get_settings
    learning_api.get_settings = lambda: _Off()
    try:
        with pytest.raises(HTTPException) as e:
            asyncio.run(selection_trace(child_id=str(QA_CHILD_ID),
                                        session_id=str(uuid.uuid4()), db=None))
        assert e.value.status_code == 404
    finally:
        learning_api.get_settings = original


def test_trace_by_real_child_rejected_403(enabled):
    with pytest.raises(HTTPException) as e:
        asyncio.run(selection_trace(child_id=str(REAL_CHILD), session_id=str(uuid.uuid4()), db=None))
    assert e.value.status_code == 403


def test_trace_by_qa_child_passes_guard(enabled):
    with pytest.raises(AttributeError):
        asyncio.run(selection_trace(child_id=str(QA_CHILD_ID), session_id=str(uuid.uuid4()), db=None))


def test_trace_dirty_params_422_after_guard(enabled):
    with pytest.raises(HTTPException) as e:
        asyncio.run(selection_trace(child_id=str(QA_CHILD_ID), session_id="not-a-uuid", db=None))
    assert e.value.status_code == 422


def test_trace_function_is_read_only_by_contract():
    src = inspect.getsource(trace_next_selection)
    body = src.split('"""', 2)[2] if src.count('"""') >= 2 else src
    for forbidden in ("db.add(", "await db.commit(", "TaskInstance("):
        assert forbidden not in body, f"只读追踪出现写入原语：{forbidden}"
    assert '"read_only": True' in src


def test_trace_output_has_no_answer_fields():
    """R2 §二红线：QA 路由不得返回答案。trace **函数体**（docstring 之外）字段
    白名单静态护栏——只允许 rvid/难度/标题/transfer/画像，无 content/answer/expected。"""
    src = inspect.getsource(trace_next_selection)
    body = src.split('"""', 2)[2] if src.count('"""') >= 2 else src
    for forbidden in ("rv.content", "content.get(", '"answer"', "expected"):
        assert forbidden not in body, f"trace 函数体含答案面引用：{forbidden}"
