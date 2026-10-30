"""FE-1466-B 过程校验单测（不依赖 DB）——契约 process_contract_frozen_v2 验收矩阵。

覆盖：四 renderer 专属规则×五态、后端独立重算（不信任客户端结论字段）、
负向归因策略（pattern/shape 允许、money/pv 门控）、未声明旧题逐比特兼容、
多 workspace 声明匹配（不取首块错位）。
"""
import pytest

from app.services.process_validate import (
    _ws_data,
    get_process_constraint,
    process_validate,
)

def ui(mode, params=None, extra_config=None, constraints=None, wsid="main"):
    cfg = {"process_constraint": {"mode": mode, "params": params or {}}}
    if extra_config:
        cfg.update(extra_config)
    return {"schema_version": "2.0", "workspaces": [
        {"workspace_id": wsid, "renderer": "x", "config": cfg,
         "constraints": constraints or {}}]}

def resp(data, wsid="main", key="workspaces"):
    return {key: [{"workspace_id": wsid, "data": data}]}


class TestNotDeclaredUnchanged:
    def test_old_item_no_constraint(self):
        assert get_process_constraint({"schema_version": "2.0",
            "workspaces": [{"config": {"blanks": 2}}]}) is None
    def test_v1_unaffected(self):
        assert get_process_constraint({"schema_version": "1.0", "kind": "number"}) is None


class TestPattern:
    U = ui("pattern_extension", constraints={"blanks": 2, "period": 2},
           extra_config={"visible": [1, 2, 1, 2], "blanks": 2})
    def test_valid_extension(self):
        r = process_validate(get_process_constraint(self.U), resp({"beads": [1, 2]}))
        assert r["status"] == "valid" and r["negative_evidence_allowed"] is True
    def test_phase_shift_contradiction(self):
        r = process_validate(get_process_constraint(self.U), resp({"beads": [2, 1]}))
        assert r["status"] == "contradiction" and r["reason_code"] == "phase_shift"
    def test_empty_beads_missing(self):
        r = process_validate(get_process_constraint(self.U), resp({"beads": []}))
        assert r["status"] == "missing"
    def test_attempt_history_not_gated(self):
        """§三特别要求：attempt_history=观察项，缺失不得拦 valid。"""
        r = process_validate(get_process_constraint(self.U), resp({"beads": [1, 2]}))
        assert r["status"] == "valid"
    def test_no_basis_unverifiable(self):
        U = ui("pattern_extension", extra_config={"visible": []})
        r = process_validate(get_process_constraint(U), resp({"beads": [1]}))
        assert r["status"] == "unverifiable"


class TestMoney:
    U = ui("payment_change", extra_config={"price": 35, "denominations": [1, 5, 10, 50]})
    def test_multi_combo_equivalence_both_valid(self):
        pv = get_process_constraint(self.U)
        for sel in ([10, 10, 10, 5], [5] * 7, [10, 10, 5, 5, 5]):
            assert process_validate(pv, resp({"selected_denominations": sel}))["status"] == "valid"
    def test_overpay_contradiction(self):
        r = process_validate(get_process_constraint(self.U), resp({"selected_denominations": [50]}))
        assert r["status"] == "contradiction" and r["reason_code"] == "total_mismatch"
    def test_negative_gated_for_money(self):
        """决策3：money 矛盾不产负向证据（标签疑点未清）。"""
        r = process_validate(get_process_constraint(self.U), resp({"selected_denominations": [50]}))
        assert r["negative_evidence_allowed"] is False
    def test_empty_missing(self):
        assert process_validate(get_process_constraint(self.U),
            resp({"selected_denominations": []}))["status"] == "missing"
    def test_client_total_ignored(self):
        """边界§一.2：客户端 total=35 谎报不改判（后端 sum(sel) 重算）。"""
        r = process_validate(get_process_constraint(self.U),
            resp({"selected_denominations": [50], "total": 35}))
        assert r["status"] == "contradiction"


class TestShape:
    U = ui("shape_drawing", constraints={"vertex_count": 4, "area": 6, "right_angles": 4},
           extra_config={"target_area": 6})
    RECT32 = [{"x": 0, "y": 0}, {"x": 3, "y": 0}, {"x": 3, "y": 2}, {"x": 0, "y": 2}]
    PARALLELO = [{"x": 0, "y": 0}, {"x": 3, "y": 0}, {"x": 4, "y": 2}, {"x": 1, "y": 2}]
    def test_rect_valid_array_form(self):
        """vertices 双形态（[[x,y]] 数组=现行 serialize 真形态）must 支持。"""
        r = process_validate(get_process_constraint(self.U),
            resp({"vertices": [[0, 0], [3, 0], [3, 2], [0, 2]]}))
        assert r["status"] == "valid"
    def test_parallelogram_area_ok_angles_bad(self):
        r = process_validate(get_process_constraint(self.U), resp({"vertices": self.PARALLELO}))
        assert r["status"] == "contradiction" and r["reason_code"] == "not_right_angles"
    def test_empty_vertices_missing(self):
        assert process_validate(get_process_constraint(self.U),
            resp({"vertices": []}))["status"] == "missing"
    def test_client_area_claim_ignored(self):
        r = process_validate(get_process_constraint(self.U),
            resp({"vertices": self.PARALLELO, "area": 6, "right_angles": 4}))
        assert r["status"] == "contradiction"   # 后端重算不采信客户端结论字段
    def test_shape_negative_allowed(self):
        r = process_validate(get_process_constraint(self.U), resp({"vertices": self.PARALLELO}))
        assert r["negative_evidence_allowed"] is True


class TestPlaceValue:
    U = ui("place_value_build", extra_config={"target": 352, "pool": [2, 5, 3]},
           constraints={"pool_multiset_equals_target_digits": True})
    def test_correct_slots_valid(self):
        assert process_validate(get_process_constraint(self.U),
            resp({"slots": {"h": 3, "t": 5, "o": 2}}))["status"] == "valid"
    def test_wrong_position_contradiction(self):
        r = process_validate(get_process_constraint(self.U),
            resp({"slots": {"h": 3, "t": 2, "o": 5}}))
        assert r["status"] == "contradiction" and r["reason_code"] == "digit_position_error"
    def test_pv_no_negative(self):
        r = process_validate(get_process_constraint(self.U),
            resp({"slots": {"h": 3, "t": 2, "o": 5}}))
        assert r["negative_evidence_allowed"] is False
    def test_empty_slots_missing(self):
        assert process_validate(get_process_constraint(self.U),
            resp({"slots": {}}))["status"] == "missing"
    def test_incomplete_missing(self):
        assert process_validate(get_process_constraint(self.U),
            resp({"slots": {"h": 3}}))["status"] == "missing"


class TestMultiWorkspaceNoMisread:
    def test_data_taken_from_declared_ws_not_first(self):
        U = {"schema_version": "2.0", "workspaces": [
            {"workspace_id": "w0", "config": {}},
            {"workspace_id": "w1", "config": {"process_constraint": {"mode": "payment_change"},
                "constraints": {}, }},
        ]}
        U["workspaces"][1]["config"].update({"price": 35, "denominations": [1, 5, 10, 50]})
        pc = get_process_constraint(U)
        assert pc["workspace_id"] == "w1"
        r = process_validate(pc, {"workspaces": [
            {"workspace_id": "w0", "data": {"selected_denominations": []}},
            {"workspace_id": "w1", "data": {"selected_denominations": [10, 10, 10, 5]}}]})
        assert r["status"] == "valid"   # 不被 w0 空块错位误判 missing


class TestUnverifiableChannel:
    def test_unknown_mode(self):
        r = process_validate(get_process_constraint(ui("time_travel")), resp({"x": 1}))
        assert r["status"] == "unverifiable" and r["reason_code"].startswith("unknown_mode")
    def test_no_workspace_data(self):
        r = process_validate(get_process_constraint(ui("payment_change")), {"workspaces": []})
        assert r["status"] == "unverifiable"


class TestEvidenceEligible:
    """证据资格纯函数（决策2/3 + §四验收矩阵逐格）。"""
    from app.services.turn_service import evidence_eligible as _fn  # noqa

    def _f(self, correct, pv):
        from app.services.turn_service import evidence_eligible
        return evidence_eligible(correct, pv)

    def test_grid1_answer_ok_process_valid(self):
        assert self._f(True, {"status": "valid", "negative_evidence_allowed": True}) is True
    def test_grid2_answer_ok_missing_no_evidence(self):
        assert self._f(None, {"status": "missing", "negative_evidence_allowed": True}) is False
    def test_grid3_contradiction_negative_allowed(self):
        assert self._f(False, {"status": "contradiction", "negative_evidence_allowed": True}) is True
    def test_grid3_money_contradiction_gated(self):
        assert self._f(False, {"status": "contradiction", "negative_evidence_allowed": False}) is False
    def test_grid4_wrong_answer_legacy_path_unchanged(self):
        assert self._f(False, None) is True           # 旧题答错照写负证据
        assert self._f(False, {"status": "valid"}) is True
    def test_grid5_unverifiable_no_evidence(self):
        assert self._f(None, {"status": "unverifiable"}) is False
    def test_grid6_old_item_untouched(self):
        assert self._f(True, None) is True
        assert self._f(None, None) is False          # 既有 undefined-answer 语义不变


class TestRealSerializationShapes:
    """FE-1466-C 对齐真实前端 serialize* 形态（锁测：形态失配=unverifiable 而非误判）。"""
    def test_money_counts_dict_form(self):
        U = ui("payment_change", extra_config={"price": 35, "denominations": [1, 5, 10, 50]})
        pv = get_process_constraint(U)
        assert process_validate(pv, resp({"counts": {"10": 3, "5": 1}, "total": 35}))["status"] == "valid"
        assert process_validate(pv, resp({"counts": {"5": 7}, "total": 35}))["status"] == "valid"   # 等价类
        assert process_validate(pv, resp({"counts": {"50": 1}, "total": 35}))["status"] == "contradiction"  # 谎报 total
        assert process_validate(pv, resp({"counts": {}, "total": 35}))["status"] == "missing"
    def test_pattern_beads_with_nulls(self):
        U = ui("pattern_extension", constraints={"blanks": 2, "period": 2},
               extra_config={"visible": [1, 2, 1, 2], "blanks": 2})
        assert process_validate(get_process_constraint(U),
            resp({"beads": [1, None]}))["status"] == "missing"   # 半填
    def test_pv_slots_array_form(self):
        U = ui("place_value_build", extra_config={"target": 352, "pool": [2, 5, 3]})
        pv = get_process_constraint(U)
        assert process_validate(pv, resp({"slots": [3, 5, 2]}))["status"] == "valid"
        assert process_validate(pv, resp({"slots": [3, 2, 5]}))["status"] == "contradiction"
        assert process_validate(pv, resp({"slots": [3, None, None]}))["status"] == "missing"
        assert process_validate(pv, resp({"slots": [None, None, None]}))["status"] == "missing"
    def test_shape_vertices_dict_form(self):
        U = ui("shape_drawing", constraints={"vertex_count": 4, "area": 6, "right_angles": 4})
        pts = [{"x": 0, "y": 0}, {"x": 3, "y": 0}, {"x": 3, "y": 2}, {"x": 0, "y": 2}]
        assert process_validate(get_process_constraint(U), resp({"vertices": pts}))["status"] == "valid"
