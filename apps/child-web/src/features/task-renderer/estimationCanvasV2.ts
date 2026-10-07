// FE-1423 R11 estimation-canvas 纯函数层（B5 模板第十实例，Batch C 收官）。
// Gap R11：Semantic=estimate/range/reason；Evaluator=tolerance/reasoning；
// Diagnosis=估算策略错误；Evidence=估算值、调整过程。
//
// 判分口径（与 R08 transpose 解耦同款）：金题锚定「近似数」语义——答案唯一
// （最接近的整十），后端 _judge float 相等判对判错；**前端 tolerance evaluator
// 的 too_high/too_low 分类是诊断原料走 Evidence**，不越权判分。
// reason 落点：估算理由三选一 chip，未选不可提交（"先想再估"教学纪律）。

export type EstimationReasonId = "group_by_ten" | "use_reference" | "quick_guess";

export const ESTIMATION_REASONS: ReadonlyArray<{ id: EstimationReasonId; label: string }> = [
  { id: "group_by_ten", label: "十个十个数" },
  { id: "use_reference", label: "跟参照比一比" },
  { id: "quick_guess", label: "先估个大概" },
];

export type EstimationCanvasV2Config = {
  /** 参照量（如"这一小杯是 10 颗"），画布展示用 */
  reference: number;
  /** 滑条上限 */
  max: number;
  /** 唯一答案（近似数，如 38→40） */
  expected: number;
  /** 真实量（仅诊断 too_high/too_low 与 close 判断用，绝不下发进 answer） */
  actual: number;
  /** 判"接近"的容差（诊断原料粒度，默认 max 的 10%） */
  tolerance: number;
};

export type EstimationCanvasV2State = {
  /** null=滑条从未触碰（EMPTY 态之一） */
  estimate: number | null;
  /** null=理由未选（EMPTY 态之二） */
  reason: EstimationReasonId | null;
  /** 调整过程 Evidence：每次落定的 [值]，含首次 */
  adjust_history: number[];
};

export type EstimationVerdict =
  | { status: "EMPTY"; missing: "estimate" | "reason" }
  | { status: "PASS" }
  | { status: "FAIL"; error: "too_high" | "too_low"; close: boolean };

export function parseEstimationConfig(raw: unknown): EstimationCanvasV2Config | null {
  if (!raw || typeof raw !== "object") return null;
  const c = raw as Record<string, unknown>;
  const reference = c.reference;
  const max = c.max;
  const expected = c.expected;
  const actual = c.actual;
  if (
    typeof reference !== "number" || !Number.isInteger(reference) || reference < 1 ||
    typeof max !== "number" || !Number.isInteger(max) || max < 2 || max > 100 ||
    typeof expected !== "number" || !Number.isInteger(expected) ||
    typeof actual !== "number" || !Number.isInteger(actual)
  ) return null;
  // 值域守卫：全部落 1~max，答案与真实量在滑条可达范围内
  if (reference > max || expected > max || actual > max) return null;
  if (expected < 10 || actual < 11) return null; // 近似到"整十"至少 10；actual 非整十且 ≥11
  // 近似数语义自洽：expected 必须是 actual 四舍五入到最近十的结果
  if (Math.round(actual / 10) * 10 !== expected) return null;
  // expected=10 的倍数（整十近似）；actual 非整十（否则估算没有意义）
  if (expected % 10 !== 0 || actual % 10 === 0) return null;
  const tolerance = typeof c.tolerance === "number" && c.tolerance >= 1 ? c.tolerance : Math.max(1, Math.round(max * 0.1));
  return { reference, max, expected, actual, tolerance };
}

export function initialEstimationV2State(): EstimationCanvasV2State {
  return { estimate: null, reason: null, adjust_history: [] };
}

/** 滑条移动：只在值变化时记史（range input 每像素都触发，落定=与上一个不同）。 */
export function applyEstimate(
  state: EstimationCanvasV2State,
  config: EstimationCanvasV2Config,
  value: number,
): { ok: boolean; code?: "OUT_OF_RANGE"; state: EstimationCanvasV2State } {
  if (!Number.isFinite(value) || value < 0 || value > config.max) {
    return { ok: false, code: "OUT_OF_RANGE", state };
  }
  const v = Math.round(value);
  if (state.estimate === v) return { ok: true, state }; // 未变化不入史
  return {
    ok: true,
    state: { ...state, estimate: v, adjust_history: [...state.adjust_history, v] },
  };
}

export function applyReason(
  state: EstimationCanvasV2State,
  reason: EstimationReasonId,
): { ok: boolean; code?: "UNKNOWN_REASON"; replaced: boolean; noop: boolean; state: EstimationCanvasV2State } {
  if (!ESTIMATION_REASONS.some(r => r.id === reason)) {
    return { ok: false, code: "UNKNOWN_REASON", replaced: false, noop: false, state };
  }
  if (state.reason === reason) {
    return { ok: true, replaced: false, noop: true, state }; // 重复点选=无操作不记事件
  }
  return { ok: true, replaced: state.reason !== null, noop: false, state: { ...state, reason } };
}

/** 五态评估（Gap R11 Acceptance=五状态）：
 * EMPTY(estimate) → EMPTY(reason) → PASS → FAIL(too_high/too_low + close 粒度)。
 * 方向（too_high/too_low）= 相对情境真值 actual（"估得偏高/偏低"的事实判断）；
 * close 粒度 = 相对答案 expected（教学反馈"差一点点 vs 差很多"以目标为准）。 */
export function evaluateEstimation(
  state: EstimationCanvasV2State,
  config: EstimationCanvasV2Config,
): EstimationVerdict {
  if (state.estimate === null) return { status: "EMPTY", missing: "estimate" };
  if (state.reason === null) return { status: "EMPTY", missing: "reason" };
  const e = state.estimate;
  if (e === config.expected) return { status: "PASS" };
  const dir = e - config.actual;
  return {
    status: "FAIL",
    error: dir > 0 ? "too_high" : "too_low",
    close: Math.abs(e - config.expected) <= config.tolerance,
  };
}

/** 提交答案=滑条值（后端与 expected 严格相等判分）。 */
export function estimationAnswer(state: EstimationCanvasV2State): number | null {
  return state.estimate;
}

/** Evidence 序列化：估算值、调整过程、理由、五态结构原料。 */
export function serializeEstimationCanvasV2(
  state: EstimationCanvasV2State,
  config: EstimationCanvasV2Config,
) {
  const verdict = evaluateEstimation(state, config);
  return {
    estimate: state.estimate,
    reason: state.reason,
    adjust_history: state.adjust_history,
    reference: config.reference,
    answer: estimationAnswer(state),
    structure: {
      status: verdict.status,
      error: verdict.status === "FAIL" ? verdict.error : null,
      close: verdict.status === "FAIL" ? verdict.close : null,
    },
  };
}
