"""FE-1422a QA 确定性钉题——路由层契约单测（不依赖 DB，CI 无库运行）。

守三件事（全在 403/参数解析之前短路，db=None 安全）：
1. pin_resource_version_id 仅 QA child 可用——真实 child → 403；
2. pin 缺省/None → 不 403（生产路径行为不变，向后兼容）；
3. is_qa_child 对 str/UUID/脏值的容忍度。
"""
import asyncio
import uuid

import pytest
from fastapi import HTTPException

from app.api.learning import next_task
from app.core.qa import QA_CHILD_ID, is_qa_child
from app.api.content import router as content_router

REAL_CHILD = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ---- is_qa_child 判定 ----

def test_qa_child_constants():
    assert QA_CHILD_ID == uuid.UUID("00000000-0000-0000-0000-000000000099")
    assert is_qa_child(QA_CHILD_ID)
    assert is_qa_child(str(QA_CHILD_ID))
    assert not is_qa_child(REAL_CHILD)
    assert not is_qa_child("not-a-uuid")
    assert not is_qa_child(None)


# ---- next_task 路由守卫（db=None：403 必须在触库前抛出）----

def _call(payload):
    return asyncio.run(next_task(payload, db=None))


def test_pin_by_real_child_rejected_403():
    with pytest.raises(HTTPException) as e:
        _call({
            "child_id": str(REAL_CHILD),
            "session_id": str(uuid.uuid4()),
            "subject": "math",
            "pin_resource_version_id": str(uuid.uuid4()),
        })
    assert e.value.status_code == 403


def test_pin_by_qa_child_passes_guard():
    # 过守卫后会触库（db=None → AttributeError），证明 403 没有误伤 QA 路径
    with pytest.raises(AttributeError):
        _call({
            "child_id": str(QA_CHILD_ID),
            "session_id": str(uuid.uuid4()),
            "subject": "math",
            "pin_resource_version_id": str(uuid.uuid4()),
        })


def test_no_pin_never_403():
    with pytest.raises(AttributeError):
        _call({
            "child_id": str(REAL_CHILD),
            "session_id": str(uuid.uuid4()),
            "subject": "math",
            "ability_id": "app_rel",
        })


# ---- catalog 端点存在性（冻结 OpenAPI 之外的新增只读，路径唯一口径）----

def test_v2_catalog_route_registered():
    paths = {(r.path, tuple(sorted(r.methods))) for r in content_router.routes}
    assert ("/content/v2-catalog", ("GET",)) in paths
