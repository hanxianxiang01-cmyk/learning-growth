"""FE-1405 V2 纵向链（A5 后端切片）单测。

核心思想：seed 产物必须通过 packages/contracts 的 V2 可执行契约校验——
契约、seed、下发门控三层在 CI 里互相咬合，防漂移。
"""
from __future__ import annotations

import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = API_ROOT.parents[1]
sys.path.insert(0, str(REPO_ROOT / "packages" / "contracts"))
sys.path.insert(0, str(REPO_ROOT / "apps" / "learning-api" / "scripts"))

from contracts.validate import validate_ui_schema_v2  # noqa: E402

from app.content.resource_seed_v2 import GOLD_RESOURCES_V2  # noqa: E402
from app.services.learning import _v2_assignable  # noqa: E402


# ---- _v2_assignable 门控 ----

def test_v1_schema_always_assignable():
    assert _v2_assignable({"schema_version": "1.0", "kind": "number"}) is True
    assert _v2_assignable(None) is True  # 异常数据放行（V1 行为不变）


def test_v2_implemented_assignable():
    doc = {
        "schema_version": "2.0",
        "workspaces": [{"workspace_id": "main", "renderer": "number-line"}],
    }
    assert _v2_assignable(doc) is True


def test_v2_off_protocol_rejected():
    # FE-1409 后 23 协议全 implemented，planned 拒绝路径不存在；
    # 门控的剩余职责 = 协议外 renderer 拒绝下发（评审 §3.1 红线不变）
    doc = {
        "schema_version": "2.0",
        "workspaces": [{"workspace_id": "main", "renderer": "hologram-board"}],
    }
    assert _v2_assignable(doc) is False  # 协议外受控拒绝，不降级


def test_v2_unknown_or_missing_renderer_rejected():
    assert _v2_assignable({
        "schema_version": "2.0",
        "workspaces": [{"workspace_id": "m", "renderer": "unsupported"}],
    }) is False
    assert _v2_assignable({
        "schema_version": "2.0",
        "workspaces": [{"workspace_id": "m"}],
    }) is False


# ---- seed 产物通过 V2 契约 ----

def test_seed_v2_products_pass_contracts():
    """seed_content._build_ui_schema_v2 的输出必须是合法 TaskUISchema V2。"""
    import seed_content

    for r in GOLD_RESOURCES_V2:
        doc = seed_content._build_ui_schema_v2(r)
        validate_ui_schema_v2(doc)  # 不抛即契约通过
        assert doc["workspaces"][0]["capabilities"], "capabilities 非空"


def test_seed_v2_mastery_rule_canonical():
    """V2 资源声明的 context_family 过词表校验并进入 mastery_rule。"""
    import seed_content

    for r in GOLD_RESOURCES_V2:
        rule = seed_content._mastery_rule_for(r)
        assert rule.get("context_family") == r["context_family"]


def test_seed_v2_answer_scalar():
    """判分契约：content.answer 必须是标量（V2 的 answer.value 与之直接比对）。"""
    for r in GOLD_RESOURCES_V2:
        assert isinstance(r["content"]["answer"], (int, float, str)), r["title"]
