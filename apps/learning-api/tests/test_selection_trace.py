"""QA-ITEM-01 selection-trace 只读追踪端点——路由契约单测（不依赖 DB，CI 无库运行）。

守三件事：
1. 非 QA child 调用 → 403（与 pin 同红线，且 403 在触库前短路，db=None 安全）；
2. QA child 过守卫后进入服务层（db=None → AttributeError，证明未误伤 QA 路径）；
3. trace_next_selection 返回值承诺 read_only 标记 + 无 TaskInstance 构造依赖
   （源码级护栏：函数体不得含 commit/add/TaskInstance( 构造）。
"""
import asyncio
import inspect
import uuid

import pytest
from fastapi import HTTPException

from app.api.learning import selection_trace
from app.core.qa import QA_CHILD_ID
from app.services.learning import trace_next_selection

REAL_CHILD = uuid.UUID("00000000-0000-0000-0000-000000000001")


def test_trace_by_real_child_rejected_403():
    with pytest.raises(HTTPException) as e:
        asyncio.run(selection_trace(child_id=str(REAL_CHILD), session_id=str(uuid.uuid4()), db=None))
    assert e.value.status_code == 403


def test_trace_by_qa_child_passes_guard():
    with pytest.raises(AttributeError):
        asyncio.run(selection_trace(child_id=str(QA_CHILD_ID), session_id=str(uuid.uuid4()), db=None))


def test_trace_dirty_params_422_after_guard():
    # QA child + 非法 session_id → UUID 解析 ValueError → 422（在触库前的参数校验）
    with pytest.raises(HTTPException) as e:
        asyncio.run(selection_trace(child_id=str(QA_CHILD_ID), session_id="not-a-uuid", db=None))
    assert e.value.status_code == 422


def test_trace_function_is_read_only_by_contract():
    """源码护栏：追踪函数零写入——不得 commit / add / 构造 TaskInstance。"""
    src = inspect.getsource(trace_next_selection)
    body = src.split('"""', 2)[2] if src.count('"""') >= 2 else src
    for forbidden in ("db.add(", "await db.commit(", "TaskInstance("):
        assert forbidden not in body, f"只读追踪出现写入原语：{forbidden}"
    assert '"read_only": True' in src
