/**
 * ten-frame V2 renderer 纯函数层（FE-1416，B5 模板第四实例 / Gap R07）。
 *
 * 语义（Gap R07）：10 以内 / 20 以内数量结构。
 * - 格子点击 → 填到该位（count=i+1）或取消该位之后（count=i）：保持"连续填充"
 *   的十格框教学纪律（不允许跳格留洞）；
 * - 补十（make-ten）：第一框填到 10 且目标 >10 时可"打包成十"——满框冻结为
 *   一个 ten 单元，计数转入第二框（20 以内结构 = n 个十 + 余数）；
 * - 答案 = total = frames.length*10 + 当前框 count；quantity evaluator 对 target。
 *
 * 提交门禁口径（P0-01 一脉相承）：EMPTY（一个都没放）不可提交；
 * PASS/FAIL（数量填了但不对）可提交——错答必须可达后端诊断链。
 */

export type TenFrameV2Config = {
  target: number;
  /** 允许的最大框数（默认 2 → 20 以内）。 */
  maxFrames: number;
};

export type TenFrameV2State = {
  /** 已打包满十的框数量（每个代表 10）。 */
  tens: number;
  /** 当前活动框已填格数 0..9（打包后归零；tens=maxFrames 时允许 10 满格展示）。 */
  count: number;
};

export function parseTenFrameConfig(raw: Record<string, unknown>): TenFrameV2Config | null {
  const target = Number(raw.target_count ?? raw.target);
  if (!Number.isInteger(target) || target < 1 || target > 20) return null;
  const maxFrames = Number(raw.max_frames);
  return { target, maxFrames: Number.isInteger(maxFrames) && maxFrames >= 1 ? maxFrames : 2 };
}

export function initialTenFrameV2State(): TenFrameV2State {
  return { tens: 0, count: 0 };
}

export function totalOf(state: TenFrameV2State): number {
  return state.tens * 10 + state.count;
}

/** 点击第 i 格（0..9）：已填到 i 则取消至 i 格；否则填到 i+1 格。满框不可再点格（只能打包或回退）。 */
export function applyCell(
  state: TenFrameV2State,
  i: number,
  config: TenFrameV2Config
): { ok: true; state: TenFrameV2State } | { ok: false; code: "FROZEN_FRAME" | "OUT_OF_RANGE" } {
  if (i < 0 || i > 9) return { ok: false, code: "OUT_OF_RANGE" };
  if (state.count === 10) return { ok: false, code: "FROZEN_FRAME" };
  const nextCount = state.count > i ? i : i + 1;
  if (state.tens === config.maxFrames && nextCount > 10) return { ok: false, code: "OUT_OF_RANGE" };
  return { ok: true, state: { ...state, count: nextCount } };
}

/** 补十打包：当前框满 10 且还有框位且目标>10 → tens+1、count 归零。 */
export function applyMakeTen(
  state: TenFrameV2State,
  config: TenFrameV2Config
): { ok: true; state: TenFrameV2State } | { ok: false; code: "NOT_FULL" | "NO_ROOM" } {
  if (state.count !== 10) return { ok: false, code: "NOT_FULL" };
  if (state.tens >= config.maxFrames) return { ok: false, code: "NO_ROOM" };
  return { ok: true, state: { tens: state.tens + 1, count: 0 } };
}

/** 拆十回退：把最后一个满框还原为活动框（undo 语义之外的显式教学动作）。 */
export function applyBreakTen(
  state: TenFrameV2State
): { ok: true; state: TenFrameV2State } | { ok: false; code: "NOT_FULL" } {
  if (state.tens === 0) return { ok: false, code: "NOT_FULL" };
  return { ok: true, state: { tens: state.tens - 1, count: 10 } };
}

export type QuantityVerdict = "PASS" | "FAIL" | "EMPTY";

/** quantity evaluator（对 target）：EMPTY 不可提交；PASS/FAIL 可提交。 */
export function evaluateQuantity(state: TenFrameV2State, target: number): QuantityVerdict {
  const total = totalOf(state);
  if (total === 0) return "EMPTY";
  return total === target ? "PASS" : "FAIL";
}

/** Evidence 形态：结构（tens + 活动框）+ 总数。补十过程留痕在 events（MAKE_TEN_COMPLETED）。 */
export function serializeTenFrameV2(state: TenFrameV2State): Record<string, unknown> {
  return { tens: state.tens, current_frame_count: state.count, total: totalOf(state) };
}
