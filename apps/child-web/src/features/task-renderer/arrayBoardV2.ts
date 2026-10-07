/**
 * array-board V2 renderer 纯函数层（FE-1421，B5 模板第八实例 / Gap R08，Batch C 起手）。
 *
 * 语义（Gap R08）：rows × columns / repeated addition——用行列建阵列表征乘法。
 * 动作只有四个：加/减行、加/减列（row/column editing）；答案=行×列的积。
 *
 * **product/structure 解耦是本 Gate 的数学点**：
 * - 摆成 4×3（目标是 3×4）：积仍是 12——乘法交换律，答案"对"；
 *   但 structure evaluator 报 **transpose**（行列概念互换）留痕进 Evidence。
 *   诊断链由此能区分"理解交换律但行列语义混"与"真不会"——Gap R08
 *   Diagnosis P0"行列概念错误"的原料；判分仍后端权威（answer=积）。
 * - count：行列至少一个数不对且不构成转置（行数/列数概念错）。
 * - EMPTY：没摆（rows=0 或 cols=0，初始态）不可提交（P0-01 口径）。
 *
 * Evidence（Gap："行列调整轨迹"）：ARRAY_ROW/COL_ADDED/REMOVED 事件序列即轨迹。
 */

export type ArrayBoardV2Config = {
  targetRows: number;
  targetCols: number;
  maxRows: number;
  maxCols: number;
};

export type ArrayBoardV2State = {
  rows: number;
  cols: number;
};

export type ArrayVerdict = {
  status: "EMPTY" | "FAIL" | "PASS";
  /** transpose=行列互换（交换律下积仍对）；count=行列数错；PASS/EMPTY=null。 */
  error: "transpose" | "count" | null;
};

export function parseArrayBoardConfig(raw: Record<string, unknown>): ArrayBoardV2Config | null {
  const targetRows = Number(raw.target_rows);
  const targetCols = Number(raw.target_cols);
  if (
    !Number.isInteger(targetRows) || !Number.isInteger(targetCols) ||
    targetRows < 1 || targetCols < 1 || targetRows > 9 || targetCols > 9
  ) {
    return null;
  }
  const maxRows = Number(raw.max_rows);
  const maxCols = Number(raw.max_cols);
  return {
    targetRows,
    targetCols,
    maxRows: Number.isInteger(maxRows) && maxRows >= targetRows && maxRows <= 12 ? maxRows : 9,
    maxCols: Number.isInteger(maxCols) && maxCols >= targetCols && maxCols <= 12 ? maxCols : 9
  };
}

export function initialArrayBoardV2State(): ArrayBoardV2State {
  return { rows: 0, cols: 0 };
}

export function arrayProduct(state: ArrayBoardV2State): number {
  return state.rows * state.cols;
}

/** 加/减行（0..max 钳制，越界拒绝码）。 */
export function applyRowDelta(
  state: ArrayBoardV2State,
  delta: number,
  config: ArrayBoardV2Config
): { ok: true; state: ArrayBoardV2State } | { ok: false; code: "OUT_OF_RANGE" | "BAD_DELTA" } {
  if (delta !== 1 && delta !== -1) return { ok: false, code: "BAD_DELTA" };
  const next = state.rows + delta;
  if (next < 0 || next > config.maxRows) return { ok: false, code: "OUT_OF_RANGE" };
  return { ok: true, state: { ...state, rows: next } };
}

/** 加/减列。 */
export function applyColDelta(
  state: ArrayBoardV2State,
  delta: number,
  config: ArrayBoardV2Config
): { ok: true; state: ArrayBoardV2State } | { ok: false; code: "OUT_OF_RANGE" | "BAD_DELTA" } {
  if (delta !== 1 && delta !== -1) return { ok: false, code: "BAD_DELTA" };
  const next = state.cols + delta;
  if (next < 0 || next > config.maxCols) return { ok: false, code: "OUT_OF_RANGE" };
  return { ok: true, state: { ...state, cols: next } };
}

/**
 * row/column/product evaluator（R08 Evaluator P0）：
 * EMPTY（没摆）→ 全对=PASS → 转置（且真转置：target 非方阵）=transpose → 否则 count。
 */
export function evaluateArray(state: ArrayBoardV2State, config: ArrayBoardV2Config): ArrayVerdict {
  if (state.rows === 0 || state.cols === 0) return { status: "EMPTY", error: null };
  if (state.rows === config.targetRows && state.cols === config.targetCols) {
    return { status: "PASS", error: null };
  }
  // 方阵（targetRows==targetCols）时"转置"就是正确摆法，上面已 PASS——这里必是非方阵
  if (state.rows === config.targetCols && state.cols === config.targetRows) {
    return { status: "FAIL", error: "transpose" };
  }
  return { status: "FAIL", error: "count" };
}

/** Evidence：行列终态 + 积（答案）+ 结构判定（transpose/count 原料）。 */
export function serializeArrayBoardV2(
  state: ArrayBoardV2State,
  config: ArrayBoardV2Config
): Record<string, unknown> {
  const verdict = evaluateArray(state, config);
  return {
    rows: state.rows,
    columns: state.cols,
    product: arrayProduct(state),
    answer: arrayProduct(state),
    target_structure: { rows: config.targetRows, columns: config.targetCols },
    structure:
      verdict.status === "EMPTY"
        ? null
        : { status: verdict.status, error: verdict.error, array: true }
  };
}
