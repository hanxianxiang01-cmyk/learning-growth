"""FE-1455 NumberLine 跳步过程校验（后端层，docs/qa/FE1455_JUMP_PROCESS_VALIDATION.md）。

裁决红线：
- **旧题兼容**：仅当 workspace.config 显式声明 `jump_constraint` 才启用逐跳校验；
  未声明（含无 config/非 number-line renderer）→ 判分行为逐比特不变。
- **终点正确但过程错误 → 不得判对**：步长/方向/次数任一不符 → correct=False，
  诊断分诊码=constraint 违规类型（rule_ignored / direction_reversed / count_mismatch），
  Mastery 侧因 correct=False 自然不生成有效掌握证据（_scorable 既有守卫）。

约束字段（jump_constraint，全部可选，声明了才校验该维度）：
  jump_size: int            每跳步长（绝对值）
  direction: "right"|"left" 跳步方向
  expected_jumps: int       跳步次数
"""
from __future__ import annotations

from typing import Any

VALID_DIRECTIONS = {"right", "left"}


def extract_jump_trajectory(response: dict | None) -> list[dict] | None:
    """从提交 envelope 取数轴跳步轨迹。

    两种形态都要支持：
    - V2 提交适配器出网 envelope：`workspaces[].data{jumps:[{jump_id,from,to}]}`
      （v2AttemptAdapter.buildAttemptPayload）
    - 内部/测试直接构造：`v2_workspaces[].data…`（serializeNumberLineV2 原形态）
    取不到（V1 提交/非数轴）→ None = 无轨迹可校验。
    """
    if not isinstance(response, dict):
        return None
    for key in ("workspaces", "v2_workspaces"):
        for ws in response.get(key) or []:
            if not isinstance(ws, dict):
                continue
            data = ws.get("data")
            if isinstance(data, dict) and isinstance(data.get("jumps"), list):
                return [j for j in data["jumps"] if isinstance(j, dict)]
    return None


def get_jump_constraint(ui_schema: dict | None) -> dict | None:
    """从题目 ui_schema 读 jump_constraint；未声明 → None（旧题零扰动）。"""
    if not isinstance(ui_schema, dict):
        return None
    for ws in ui_schema.get("workspaces") or []:
        if not isinstance(ws, dict):
            continue
        if ws.get("renderer") != "number-line":
            continue
        cfg = ws.get("config")
        if isinstance(cfg, dict):
            jc = cfg.get("jump_constraint")
            if isinstance(jc, dict) and jc:
                return jc
    return None


def validate_jump_process(jumps: list[dict] | None, constraint: dict) -> tuple[bool, str | None]:
    """逐跳核对：步长/方向/次数。返回 (process_ok, violation_code)。

    violation_code ∈ {None, "no_trajectory", "count_mismatch",
                      "size_mismatch", "direction_reversed", "malformed_jump"}
    """
    if jumps is None:
        return False, "no_trajectory"
    expected_n = constraint.get("expected_jumps")
    if isinstance(expected_n, int) and len(jumps) != expected_n:
        return False, "count_mismatch"
    exp_size = constraint.get("jump_size")
    exp_dir = constraint.get("direction")
    if exp_dir not in VALID_DIRECTIONS and exp_size is None:
        return True, None  # 约束空壳：无可校验维度（视为通过，防误伤）
    for j in jumps:
        frm, to = j.get("from"), j.get("to")
        if not isinstance(frm, (int, float)) or not isinstance(to, (int, float)):
            return False, "malformed_jump"
        delta = to - frm
        if exp_dir in VALID_DIRECTIONS:
            if exp_dir == "right" and delta <= 0:
                return False, "direction_reversed"
            if exp_dir == "left" and delta >= 0:
                return False, "direction_reversed"
        if isinstance(exp_size, (int, float)) and abs(delta) != exp_size:
            return False, "size_mismatch"
    return True, None
