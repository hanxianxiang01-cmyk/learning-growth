// FE-1429 R16 ruler 纯函数层（B5 模板第十五实例，Batch E 起手）。
// Gap R16：Semantic=length/measure/compare；Evaluator=tolerance evaluator；
// Evidence=起止点、读数；Diagnosis=**刻度读取错误** P0。
//
// 玩法：尺子上画着被测物体（铅笔跨 left..right，**故意不从 0 开始**）。
// 点刻度放两个标记夹住物体：第 1 点=起点标记，第 2 点=终点标记，
// 第 3 点起重新放（清空重来）。答案=两标记间隔（自动取差，组件填）。
//
// 分诊（evaluateMeasurement，判定顺序 EMPTY→PASS→from_zero_reading→wrong_span）：
//   PASS  span=物体长；两标记没对准物体两端（等价平移段）→ aligned=false 留痕
//         ——**解耦第七次运用**（R08/R15 形态：量对了=后端判、准没对准=结构层说）
//   FAIL  from_zero_reading  恰好从 0 起量到右端（"对齐 0 刻度"惯性错误）——
//         answer=右端值≠长度（parser 守卫 left≥1 保证此靶必判错），Diagnosis P0 精确靶
//   FAIL  wrong_span  其余（附 span 与长度差原料）

export type RulerV2Config = {
  /** 尺面总长（cm），10..30 */
  max: number;
  /** 被测物体左端（整数刻度，≥1——零起误读才可能"看着像对"） */
  left: number;
  /** 被测物体右端（≤max） */
  right: number;
};

export type RulerV2State = {
  /** 已放标记（按放置顺序；0 或 1 或 2 个） */
  marks: number[];
};

export type MeasureVerdict =
  | { status: "EMPTY"; marks: number }
  | { status: "PASS"; aligned: boolean }
  | { status: "FAIL"; error: "from_zero_reading" | "wrong_span"; span: number };

function targetLength(config: RulerV2Config): number {
  return config.right - config.left;
}

export function parseRulerConfig(raw: unknown): RulerV2Config | null {
  if (!raw || typeof raw !== "object") return null;
  const c = raw as Record<string, unknown>;
  if (typeof c.max !== "number" || !Number.isInteger(c.max) || c.max < 10 || c.max > 30) return null;
  const obj = c.object as unknown;
  if (!Array.isArray(obj) || obj.length !== 2) return null;
  const [l, r] = obj as unknown[];
  if (typeof l !== "number" || typeof r !== "number") return null;
  if (!Number.isInteger(l) || !Number.isInteger(r)) return null;
  // 守卫：物体左端 ≥1——否则 from_zero_reading 靶（0..right）与正解重合，分诊失效
  if (l < 1 || r <= l || r > c.max) return null;
  return { max: c.max, left: l, right: r };
}

export function initialRulerV2State(): RulerV2State {
  return { marks: [] };
}

/** 点刻度：未满 2 标记→追加；已满→清空重放（儿童"再点就是重来"心智）。 */
export function applyPlaceMark(
  state: RulerV2State,
  config: RulerV2Config,
  value: number
): { ok: boolean; code?: "NO_SUCH_TICK"; restarting: boolean; state: RulerV2State } {
  if (!Number.isInteger(value) || value < 0 || value > config.max) {
    return { ok: false, code: "NO_SUCH_TICK", restarting: false, state };
  }
  if (state.marks.length >= 2) {
    return { ok: true, restarting: true, state: { marks: [value] } };
  }
  return { ok: true, restarting: false, state: { marks: [...state.marks, value] } };
}

/** 清空全部标记。 */
export function applyClearMarks(state: RulerV2State): { ok: boolean; code?: "NO_MARK"; state: RulerV2State } {
  if (state.marks.length === 0) return { ok: false, code: "NO_MARK", state };
  return { ok: true, state: { marks: [] } };
}

/** 两标记间隔（绝对差，放置顺序不影响）。不足 2 个 → null。 */
export function span(state: RulerV2State): number | null {
  if (state.marks.length < 2) return null;
  return Math.abs(state.marks[1] - state.marks[0]);
}

/** 是否正好夹住物体两端（同侧或反向皆可）。 */
function isAligned(state: RulerV2State, config: RulerV2Config): boolean {
  if (state.marks.length < 2) return false;
  const lo = Math.min(...state.marks);
  const hi = Math.max(...state.marks);
  return lo === config.left && hi === config.right;
}

/** 零起误读靶：标记恰好 {0, right}——孩子把"对齐 0"当规矩，读右端刻度当长度。 */
function isFromZero(state: RulerV2State, config: RulerV2Config): boolean {
  if (state.marks.length < 2) return false;
  const lo = Math.min(...state.marks);
  const hi = Math.max(...state.marks);
  return lo === 0 && hi === config.right;
}

/** 测量评估：EMPTY(标记<2) → PASS(span=物体长；aligned 原料) →
 * from_zero_reading(0..right 精确靶) → wrong_span(其余)。
 * parser 守卫 left≥1 保证 from_zero 靶 span=right≠length 必判错、与 PASS 互斥。 */
export function evaluateMeasurement(state: RulerV2State, config: RulerV2Config): MeasureVerdict {
  if (state.marks.length < 2) return { status: "EMPTY", marks: state.marks.length };
  const s = span(state)!;
  const len = targetLength(config);
  if (s === len) return { status: "PASS", aligned: isAligned(state, config) };
  if (isFromZero(state, config)) return { status: "FAIL", error: "from_zero_reading", span: s };
  return { status: "FAIL", error: "wrong_span", span: s };
}

/** 提交答案=两标记间隔（后端标量相等判分，不动冻结链）。 */
export function rulerAnswer(state: RulerV2State): number | null {
  return span(state);
}

/** Evidence：起止点标记 + 读数原料（Gap"起止点、读数"）。 */
export function serializeRulerV2(state: RulerV2State, config: RulerV2Config) {
  const verdict = evaluateMeasurement(state, config);
  const s = span(state);
  return {
    marks: state.marks,
    span: s,
    reading: state.marks.length > 0 ? state.marks[state.marks.length - 1] : null,
    answer: s,
    object: { left: config.left, right: config.right, length: targetLength(config) },
    structure: {
      status: verdict.status,
      error: verdict.status === "FAIL" ? verdict.error : null,
      aligned: verdict.status === "PASS" ? verdict.aligned : null,
      diff_to_length: s === null ? null : s - targetLength(config),
    },
  };
}
