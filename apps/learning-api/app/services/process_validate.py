"""Q07 Process Evidence Integrity（FE-1466-B）：四类 V2 Renderer 过程校验。

架构裁决（process_contract_frozen_v2.json，PR#112 冻结）：
- **复用 FE-1455 显式声明机制**：仅 workspace.config 声明 `process_constraint`
  的资源版本启用校验；未声明（含现行 225 题全部旧版）判分逐比特不变。
  不新增第二套 Judge——本模块只产出过程状态，终值判分仍走既有 _judge。
- **后端独立计算（边界§一.2）**：只信原始操作数据（beads/
  selected_denominations/vertices/slots）+资源冻结约束重算；客户端提交的
  total/area/right_angles/valid/structure 结论字段一律不作证据输入，
  仅当"客户端声明≠后端重算"时作 contradiction 佐证。
- 五态（§三.3）：valid / missing / contradiction / unverifiable / not_required。
- 负向归因按 renderer 策略（决策3）：pattern/shape 允许；money/place-value
  暂不写（能力标签疑点未清）——由规则表 negative_evidence 决定。
"""
from __future__ import annotations

from typing import Any

STATUS = ("valid", "missing", "contradiction", "unverifiable", "not_required")


def get_process_constraint(ui_schema: Any) -> dict | None:
    """读首个声明 process_constraint 的 workspace；未声明→None（旧题零扰动）。"""
    if not isinstance(ui_schema, dict) or ui_schema.get("schema_version") != "2.0":
        return None
    for ws in ui_schema.get("workspaces") or []:
        if not isinstance(ws, dict):
            continue
        cfg = ws.get("config") if isinstance(ws.get("config"), dict) else {}
        pc = cfg.get("process_constraint")
        if isinstance(pc, dict) and pc.get("mode"):
            return {"mode": pc["mode"], "params": pc.get("params") or {},
                    "config": cfg, "constraints": ws.get("constraints") or {},
                    "workspace_id": ws.get("workspace_id")}
    return None


def _ws_data(response: dict | None, workspace_id: Any = None) -> dict | None:
    """从出网/内部两形态 envelope 取目标 workspace data。

    多 workspace 题按声明的 workspace_id 匹配（不取首块——声明与数据错位
    会把另一块合法数据误当本约束证据）；单块/无 id 题回落首块（同
    jump_process 支持面）。结构不认识→None（unverifiable）。
    """
    if not isinstance(response, dict):
        return None
    for key in ("workspaces", "v2_workspaces"):
        blocks = [ws for ws in (response.get(key) or []) if isinstance(ws, dict)]
        if not blocks:
            continue
        if workspace_id is not None:
            # 声明了目标 id：只认匹配块；匹配块缺失/无 data → None
            # （unverifiable，不拿别块数据错位充证据）
            for ws in blocks:
                if ws.get("workspace_id") == workspace_id:
                    return ws.get("data") if isinstance(ws.get("data"), dict) else None
            continue
        first = blocks[0].get("data")
        if isinstance(first, dict):
            return first
    return None


def _as_pairs(vertices: Any) -> list[tuple] | None:
    """顶点双形态归一：[{x,y}] 或 [[x,y]]。结构不认识→None（unverifiable）。"""
    if not isinstance(vertices, list):
        return None
    out = []
    for v in vertices:
        if isinstance(v, dict) and "x" in v and "y" in v:
            out.append((v["x"], v["y"]))
        elif isinstance(v, (list, tuple)) and len(v) == 2:
            out.append((v[0], v[1]))
        else:
            return None
    return out


def _shoelace_area(pts: list[tuple]) -> float:
    n = len(pts)
    s = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1]
            for i in range(n))
    return abs(s) / 2.0


def _right_angle_count(pts: list[tuple]) -> int:
    n = len(pts)
    cnt = 0
    for i in range(n):
        ax, ay = pts[i][0] - pts[(i - 1) % n][0], pts[i][1] - pts[(i - 1) % n][1]
        bx, by = pts[(i + 1) % n][0] - pts[i][0], pts[(i + 1) % n][1] - pts[i][1]
        if ax * bx + ay * by == 0 and (ax or ay) and (bx or by):
            cnt += 1
    return cnt


# ---------- renderer 专属规则：返回 (status, reason_code) ----------

def _rule_pattern(data: dict, cfg: dict, cons: dict) -> tuple[str, str | None]:
    beads = data.get("beads")
    if not isinstance(beads, list):
        return ("unverifiable", "beads_absent")
    if not beads:
        return ("missing", "no_beads_placed")
    visible = cfg.get("visible") or []
    blanks = cons.get("blanks", cfg.get("blanks", 0))
    period = cons.get("period", 2)
    if not visible or not blanks:
        return ("unverifiable", "pattern_basis_missing")
    expected = [visible[i % period] for i in range(len(visible), len(visible) + blanks)]
    if beads != expected:
        return ("contradiction", "phase_shift" if sorted(beads) == sorted(expected) else "rule_ignored")
    return ("valid", None)   # attempt_history=observation_only，不设门槛（§三）


def _rule_money(data: dict, cfg: dict, cons: dict) -> tuple[str, str | None]:
    sel = data.get("selected_denominations")
    if not isinstance(sel, list):
        return ("unverifiable", "denominations_absent")
    if not sel:
        return ("missing", "no_coins_selected")
    price = cfg.get("price")
    if not isinstance(price, (int, float)):
        return ("unverifiable", "price_missing")
    if any(d not in (cfg.get("denominations") or []) for d in sel):
        return ("contradiction", "illegal_denomination")
    if sum(sel) != price:
        return ("contradiction", "total_mismatch")   # 超付/欠付
    # 多组合等价类一律认可（[10,10,10,5]==[5]*7==35，§三特别要求）
    return ("valid", None)


def _rule_shape(data: dict, cfg: dict, cons: dict) -> tuple[str, str | None]:
    pts = _as_pairs(data.get("vertices"))
    if pts is None:
        return ("unverifiable", "vertices_shape_unknown")
    if not pts:
        return ("missing", "no_vertices_placed")
    if len(pts) != cons.get("vertex_count", 4):
        return ("contradiction", "vertex_count_mismatch")
    area = cons.get("area", cfg.get("target_area"))
    # 后端独立重算面积/直角（边界§一.2；平行四边形=面积对直角违规）
    if _shoelace_area(pts) != area:
        return ("contradiction", "area_mismatch")
    if _right_angle_count(pts) != cons.get("right_angles", 4):
        return ("contradiction", "not_right_angles")
    return ("valid", None)


def _rule_place_value(data: dict, cfg: dict, cons: dict) -> tuple[str, str | None]:
    slots = data.get("slots")
    if not isinstance(slots, dict):
        return ("unverifiable", "slots_shape_unknown")
    if not any(slots.get(k) is not None for k in ("h", "t", "o")):
        return ("missing", "no_cards_placed")
    target = cfg.get("target")
    if not isinstance(target, int):
        return ("unverifiable", "target_missing")
    h, t, o = slots.get("h"), slots.get("t"), slots.get("o")
    if None in (h, t, o):
        return ("missing", "slots_incomplete")
    if sorted((h, t, o)) != sorted(int(d) for d in str(target)):
        # 卡池多重集不符（pool_multiset_equals_target_digits）
        return ("contradiction", "denomination_confusion")
    if h * 100 + t * 10 + o != target:
        return ("contradiction", "digit_position_error")  # 卡位与数位结构不一致
    return ("valid", None)


RULES: dict[str, tuple] = {   # mode → (rule, negative_evidence_allowed per 决策3)
    "pattern_extension": (_rule_pattern, True),
    "payment_change": (_rule_money, False),
    "shape_drawing": (_rule_shape, True),
    "place_value_build": (_rule_place_value, False),
}


def process_validate(pc: dict, response: dict | None) -> dict:
    """统一过程验证入口。返回 {status, reason_code, negative_evidence_allowed, mode}。"""
    mode = pc["mode"]
    if mode not in RULES:
        return {"status": "unverifiable", "reason_code": f"unknown_mode:{mode}",
                "negative_evidence_allowed": False, "mode": mode}
    rule, neg_ok = RULES[mode]
    data = _ws_data(response, pc.get("workspace_id"))
    if data is None:
        return {"status": "unverifiable", "reason_code": "no_workspace_data",
                "negative_evidence_allowed": False, "mode": mode}
    try:
        status, reason = rule(data, pc["config"], pc["constraints"])
    except Exception:
        # 结构异常=系统无法核验，不是孩子的错（§三 unverifiable 语义）
        return {"status": "unverifiable", "reason_code": "rule_exception",
                "negative_evidence_allowed": False, "mode": mode}
    return {"status": status, "reason_code": reason,
            "negative_evidence_allowed": bool(neg_ok), "mode": mode}
