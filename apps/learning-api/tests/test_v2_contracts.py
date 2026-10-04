"""FE-1404 V2 契约可执行校验测试（TaskUISchema V2 + MathResponse V2 + 样例集）。

样例与 schema 在 packages/contracts/（前后端共享契约包）；本测试把它纳入 CI 门禁。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "packages" / "contracts"))

from contracts.validate import (  # noqa: E402
    ContractValidationError,
    check_assignable,
    validate_response_v2,
    validate_ui_schema_v2,
)

SAMPLES = REPO_ROOT / "packages" / "contracts" / "samples"


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


# ---- UI Schema：五条纵向链样例（本 PR 交付 B5/A5/D5/E4/F6 五条全量）----

def test_ui_schema_five_chains_valid():
    for chain in ["b5", "a5", "d5", "e4", "f6"]:
        doc = _load(SAMPLES / "ui_schema" / f"{chain}_valid.json")
        validate_ui_schema_v2(doc)  # 不抛即过


def test_ui_schema_illegal_renderer_alias_rejected():
    p = SAMPLES / "ui_schema" / "illegal_renderer_alias.json"
    try:
        validate_ui_schema_v2(_load(p))
        assert False, "PascalCase 别名应被拒绝"
    except ContractValidationError as e:
        assert "UNKNOWN_RENDERER_ID" in str(e)


def test_ui_schema_duplicate_workspace_id_rejected():
    doc = _load(SAMPLES / "ui_schema" / "b5_valid.json")
    doc["workspaces"].append(dict(doc["workspaces"][0]))  # 复制 → workspace_id 重复
    try:
        validate_ui_schema_v2(doc)
        assert False, "重复 workspace_id 应被拒绝"
    except ContractValidationError as e:
        assert "duplicate workspace_id" in str(e)


def test_ui_schema_missing_required_rejected():
    doc = _load(SAMPLES / "ui_schema" / "b5_valid.json")
    del doc["ui_revision"]
    try:
        validate_ui_schema_v2(doc)
        assert False, "缺 ui_revision 应被拒绝"
    except ContractValidationError:
        pass


# ---- Response ----

def test_response_valid():
    doc = _load(SAMPLES / "response" / "e4_valid.json")
    validate_response_v2(doc)
    full = _load(REPO_ROOT / "packages" / "contracts" / "examples" / "b5-column-arithmetic-attempt.json")
    validate_response_v2(full)  # 带 interaction_events 的全量样例


def test_response_client_selfgraded_rejected():
    """客户端自评字段（correct/evidence_role）必须被 additionalProperties 拒绝——架构不变量。"""
    doc = _load(SAMPLES / "response" / "illegal_client_selfgraded.json")
    try:
        validate_response_v2(doc)
        assert False, "客户端不得提交 correct/evidence_role"
    except ContractValidationError as e:
        assert "Additional properties" in str(e) or "correct" in str(e)


def test_response_sequence_duplicate_rejected():
    doc = _load(REPO_ROOT / "packages" / "contracts" / "examples" / "b5-column-arithmetic-attempt.json")
    doc["response"]["interaction_events"][1]["sequence"] = 0  # 与第一条重号
    try:
        validate_response_v2(doc)
        assert False, "sequence 重复应被拒绝"
    except ContractValidationError as e:
        assert "sequence" in str(e)


# ---- 下发分层：协议面 + 可下发 ----

def test_assignable_after_full_implementation():
    """FE-1409：五链样例全部可下发（23 协议 implemented）；协议外 renderer 仍拒绝。"""
    doc = _load(SAMPLES / "ui_schema" / "b5_valid.json")
    assert check_assignable(doc) == []

    doc_e4 = _load(SAMPLES / "ui_schema" / "e4_valid.json")
    assert check_assignable(doc_e4) == []  # ruler 已 implemented

    doc_bad = {
        "schema_version": "2.0",
        "workspaces": [{"workspace_id": "main", "renderer": "hologram-board"}],
    }
    reasons = check_assignable(doc_bad)
    assert reasons and "hologram-board" in reasons[0]  # 协议外 → 受控拒绝


def test_schema_enum_synced_with_protocol():
    """schema 的 renderer enum 必须与 FE-1403 代码枚举完全一致（防双源漂移）。"""
    schema = json.loads(
        (REPO_ROOT / "packages" / "contracts" / "schemas" / "task-ui-schema-v2.schema.json").read_text(encoding="utf-8")
    )
    enum_ids = set(schema["$defs"]["renderer_id"]["enum"])
    from app.content.renderer_protocol import RENDERER_PROTOCOL_IDS
    assert enum_ids == set(RENDERER_PROTOCOL_IDS)
