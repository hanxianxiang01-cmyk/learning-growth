"""V2 契约校验器（FE-1404，packages/contracts 的可执行入口）。

校验分三层：
1. JSON Schema 结构层（task-ui-schema-v2 / math-response-v2）；
2. 协议层：renderer ∈ FE-1403 冻结枚举（renderer_protocol 单一事实源，schema enum 同步自它）；
3. 语义层：workspace_id 任务内唯一；V2 资源下发还要求 is_implemented()（planned 拒绝）。

用法：
    from contracts.validate import validate_ui_schema_v2, validate_response_v2
"""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from app.content.renderer_protocol import RENDERER_PROTOCOL_IDS, is_implemented, validate_renderer_id

CONTRACTS_DIR = Path(__file__).resolve().parents[1]

_UI_SCHEMA = json.loads((CONTRACTS_DIR / "schemas" / "task-ui-schema-v2.schema.json").read_text(encoding="utf-8"))
_RESPONSE_SCHEMA = json.loads((CONTRACTS_DIR / "schemas" / "math-response-v2.schema.json").read_text(encoding="utf-8"))


class ContractValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def _schema_errors(instance: dict, schema: dict) -> list[str]:
    v = Draft202012Validator(schema)
    return [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}" for e in v.iter_errors(instance)]


def validate_ui_schema_v2(doc: dict) -> None:
    """校验 TaskUISchema V2 文档；不合法抛 ContractValidationError。"""
    errors = _schema_errors(doc, _UI_SCHEMA)

    # 协议双保险：schema enum 可能与 renderer_protocol 漂移，以代码枚举为准
    for ws in doc.get("workspaces", []):
        rid = ws.get("renderer")
        if isinstance(rid, str):
            try:
                validate_renderer_id(rid)
            except ValueError as e:
                errors.append(f"workspace[{ws.get('workspace_id')}]: {e}")
            else:
                if rid not in RENDERER_PROTOCOL_IDS:
                    errors.append(f"workspace[{ws.get('workspace_id')}]: {rid} 不在冻结枚举")

    # 语义层：workspace_id 任务内唯一（§3.1）
    ids = [ws.get("workspace_id") for ws in doc.get("workspaces", []) if isinstance(ws, dict)]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        errors.append(f"duplicate workspace_id: {sorted(dup)}")

    if errors:
        raise ContractValidationError(sorted(set(errors)))


def validate_response_v2(doc: dict) -> None:
    """校验 Attempt 外层 + MathResponse V2；客户端自评字段必然被 additionalProperties 拒绝。"""
    errors = _schema_errors(doc, _RESPONSE_SCHEMA)

    # 语义层：workspaces 引用的 workspace_id 不重复（提交侧同样校验，防伪造）
    ws_ids = [w.get("workspace_id") for w in doc.get("response", {}).get("workspaces", [])]
    dup = {i for i in ws_ids if ws_ids.count(i) > 1}
    if dup:
        errors.append(f"duplicate submitted workspace_id: {sorted(dup)}")

    # 事件顺序：sequence 唯一
    seqs = [e.get("sequence") for e in doc.get("response", {}).get("interaction_events", [])]
    if len(seqs) != len(set(seqs)):
        errors.append("interaction_events sequence not unique")

    if errors:
        raise ContractValidationError(sorted(set(errors)))


def check_assignable(doc: dict) -> list[str]:
    """下发前检查：返回不可下发原因。

    FE-1409 后 23 协议全部 implemented（前端可渲染、不降级）；
    本函数职责收敛为「协议面守卫」：协议外/哨兵 renderer 受控拒绝，不降级。
    （planned 拒绝路径自 FE-1409 起不存在，保留判定逻辑以防未来新增 planned 项。）
    """
    reasons: list[str] = []
    for ws in doc.get("workspaces", []):
        rid = ws.get("renderer")
        if rid and not is_implemented(rid):
            reasons.append(f"renderer '{rid}' 不在协议面或未实现，不得下发")
    return reasons
