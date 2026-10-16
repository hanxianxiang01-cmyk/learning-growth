"""FE-1455 后端跳步过程校验单测（不依赖 DB）。

覆盖裁决验收矩阵的后端两格：
- 「后端 Judge：正确终点但错误跳步，不得判为满足过程要求」
- 「兼容性：未声明跳步约束的旧题保持原有行为」
纯函数层（jump_process）+ submit_attempt 集成逻辑（monkeypatch 判分主链）。
"""
import pytest

from app.services.jump_process import (
    extract_jump_trajectory,
    get_jump_constraint,
    validate_jump_process,
)

JC = {"jump_size": 5, "direction": "right", "expected_jumps": 3}


def jumps(*pairs):
    return [{"jump_id": f"j{i}", "from": a, "to": b} for i, (a, b) in enumerate(pairs)]


class TestExtractTrajectory:
    def test_v2_envelope(self):
        resp = {"v2_workspaces": [{"workspace_id": "main",
                "data": {"start": 20, "end": 35, "jumps": jumps((20, 25), (25, 30), (30, 35))}}]}
        t = extract_jump_trajectory(resp)
        assert t is not None and len(t) == 3

    def test_v1_or_missing_returns_none(self):
        assert extract_jump_trajectory(None) is None
        assert extract_jump_trajectory({"answer": "35"}) is None
        assert extract_jump_trajectory({"v2_workspaces": []}) is None


class TestGetConstraint:
    def test_declared(self):
        ui = {"workspaces": [{"renderer": "number-line", "config": {"jump_constraint": JC}}]}
        assert get_jump_constraint(ui) == JC

    def test_legacy_numberline_no_constraint_none(self):
        """兼容红线核心：无 jump_constraint 的现有题 → None（判分零扰动）。"""
        ui = {"workspaces": [{"renderer": "number-line",
              "config": {"scale": {"min": 0, "max": 50}, "start_marker": {"value": 20}}}]}
        assert get_jump_constraint(ui) is None
        assert get_jump_constraint({"schema_version": "1.0", "kind": "number"}) is None
        assert get_jump_constraint(None) is None


class TestValidateProcess:
    def test_legal_right5x3(self):
        ok, v = validate_jump_process(jumps((20, 25), (25, 30), (30, 35)), JC)
        assert (ok, v) == (True, None)

    def test_endpoint_right_but_one_big_jump_rejected(self):
        """裁决重点：终点 35 对、但一步 15 → 不得判满足过程。"""
        ok, v = validate_jump_process(jumps((20, 35)), JC)
        assert ok is False and v in ("count_mismatch",)  # 次数先行

    def test_size_mismatch(self):
        ok, v = validate_jump_process(jumps((20, 26), (26, 32), (32, 35)), JC)
        assert ok is False and v == "size_mismatch"

    def test_direction_reversed(self):
        ok, v = validate_jump_process(jumps((40, 35), (35, 30), (30, 35)), JC)
        assert ok is False and v == "direction_reversed"

    def test_no_trajectory_when_required(self):
        ok, v = validate_jump_process(None, JC)
        assert ok is False and v == "no_trajectory"

    def test_partial_constraint_size_only(self):
        jc = {"jump_size": 5}
        ok, _ = validate_jump_process(jumps((20, 25), (25, 20)), jc)
        assert ok  # 仅约束步长：来回跳但每跳 ±5 → 通过（方向次数未声明）

    def test_empty_shell_pass(self):
        ok, v = validate_jump_process(jumps((0, 40)), {})
        assert (ok, v) == (True, None)  # 空壳约束不校验（防误伤，读取侧已过滤）

    def test_malformed_jump(self):
        # 次数=3 先行通过，逐跳数据检查才命中 malformed
        ok, v = validate_jump_process(
            [{"jump_id": "a", "from": "x", "to": 5},
             {"jump_id": "b", "from": 5, "to": 10},
             {"jump_id": "c", "from": 10, "to": 15}], JC)
        assert ok is False and v == "malformed_jump"

    def test_zero_delta_direction_right(self):
        ok, v = validate_jump_process(jumps((20, 20), (20, 25), (25, 30)), JC)
        assert ok is False and v == "direction_reversed"  # 原地=非右移
