// FE-1430 R17 clock 纯函数层（B5 模板第十六实例，Batch E 第二题）。
// Gap R17：Semantic=hour/minute/time relation；Evaluator=time evaluator；
// Evidence=指针调整过程；Diagnosis=**时针/分针关系错误** P0。
//
// 玩法：钟面上先选针（时针=点数字 1..12，分针=点"整点/半点"），把时间拨到目标。
// 整时/半点口径（二年级）：m∈{0,30}，h∈1..12。
// 答案=总分钟数 h*60+m（如 6:00→360；后端标量相等判分，不动冻结链）。
//
// 分诊（evaluateClock：EMPTY→PASS→hand_swap→wrong_time）：
//   EMPTY  零调整（一步没拨）
//   PASS   到达 target
//   FAIL   hand_swap  读数恰好"拿错针"：把分针指着的数字当时针读
//          ——互换态 swapOf(target)={h: target.m/5（m=0 时=12）, m: target.m}
//          （例：目标 6:00 长针指 12 → 误读"12点"→拨成 (12,0)，answer=720≠360
//           判错+关系错误精确分诊，Diagnosis P0 落地）
//   FAIL   wrong_time  其余（附分钟差原料）
// parser 守卫：swap 态必须是合法组合且 ≠ target（否则 hand_swap 名存实亡/退化）。

export type ClockTime = { h: number; m: number };

export type ClockV2Config = {
  start: ClockTime;
  target: ClockTime;
};

export type ClockV2State = ClockTime & {
  /** 指针调整过程（Gap Evidence）：每次成功拨针 [hand, from, to] */
  adjust_history: Array<[hand: "hour" | "minute", from: number, to: number]>;
};

export type ClockVerdict =
  | { status: "EMPTY" }
  | { status: "PASS" }
  | { status: "FAIL"; error: "hand_swap" | "wrong_time"; delta_minutes: number };

function validCombo(h: number, m: number): boolean {
  return Number.isInteger(h) && h >= 1 && h <= 12 && (m === 0 || m === 30);
}

function minutes(t: ClockTime): number {
  return t.h * 60 + t.m;
}

/** 拿错针读数：分针指着的数字（30 分→"6"、0 分→"12"）被当成时针。 */
export function swapOf(target: ClockTime): ClockTime {
  return { h: target.m === 0 ? 12 : target.m / 5, m: target.m };
}

function readTime(v: unknown): ClockTime | null {
  if (!Array.isArray(v) || v.length !== 2) return null;
  const [h, m] = v as unknown[];
  if (typeof h !== "number" || typeof m !== "number") return null;
  if (!validCombo(h, m)) return null;
  return { h, m };
}

export function parseClockConfig(raw: unknown): ClockV2Config | null {
  if (!raw || typeof raw !== "object") return null;
  const c = raw as Record<string, unknown>;
  const start = readTime(c.start);
  const target = readTime(c.target);
  if (!start || !target) return null;
  if (start.h === target.h && start.m === target.m) return null; // 题已做完
  // 守卫：互换靶必须合法且 ≠ target（(12,0)/(6,30) 类目标 swap 退化重合——拒）
  const sw = swapOf(target);
  if (!validCombo(sw.h, sw.m)) return null;
  if (sw.h === target.h && sw.m === target.m) return null;
  return { start, target };
}

export function initialClockV2State(config: ClockV2Config): ClockV2State {
  return { h: config.start.h, m: config.start.m, adjust_history: [] };
}

/** 拨时针：点数字 1..12（非法位 NO_SUCH_POSITION；m=30 时 h=12 合法=12:30）。 */
export function applySetHour(
  state: ClockV2State,
  value: number
): { ok: boolean; code?: "NO_SUCH_POSITION" | "INVALID_COMBO"; unchanged: boolean; state: ClockV2State } {
  if (!Number.isInteger(value) || value < 1 || value > 12) {
    return { ok: false, code: "NO_SUCH_POSITION", unchanged: false, state };
  }
  if (!validCombo(value, state.m)) return { ok: false, code: "INVALID_COMBO", unchanged: false, state };
  if (state.h === value) return { ok: true, unchanged: true, state };
  return { ok: true, unchanged: false, state: { h: value, m: state.m, adjust_history: [...state.adjust_history, ["hour", state.h, value]] } };
}

/** 拨分针：整点(0)/半点(30) 两档。 */
export function applySetMinute(
  state: ClockV2State,
  value: number
): { ok: boolean; code?: "NO_SUCH_POSITION"; unchanged: boolean; state: ClockV2State } {
  if (value !== 0 && value !== 30) {
    return { ok: false, code: "NO_SUCH_POSITION", unchanged: false, state };
  }
  if (state.m === value) return { ok: true, unchanged: true, state };
  return { ok: true, unchanged: false, state: { h: state.h, m: value, adjust_history: [...state.adjust_history, ["minute", state.m, value]] } };
}

/** 评估：EMPTY(零调整) → PASS → hand_swap → wrong_time。 */
export function evaluateClock(state: ClockV2State, config: ClockV2Config): ClockVerdict {
  if (state.adjust_history.length === 0) return { status: "EMPTY" };
  const t = config.target;
  const delta = minutes(state) - minutes(t);
  if (state.h === t.h && state.m === t.m) return { status: "PASS" };
  const sw = swapOf(t);
  if (state.h === sw.h && state.m === sw.m) return { status: "FAIL", error: "hand_swap", delta_minutes: delta };
  return { status: "FAIL", error: "wrong_time", delta_minutes: delta };
}

export function clockAnswer(state: ClockV2State): number | null {
  if (state.adjust_history.length === 0) return null;
  return minutes(state);
}

export function serializeClockV2(state: ClockV2State, config: ClockV2Config) {
  const verdict = evaluateClock(state, config);
  return {
    h: state.h,
    m: state.m,
    time_text: `${state.h}:${String(state.m).padStart(2, "0")}`,
    adjust_history: state.adjust_history,
    answer: clockAnswer(state),
    structure: {
      status: verdict.status,
      error: verdict.status === "FAIL" ? verdict.error : null,
      delta_minutes: verdict.status === "FAIL" ? verdict.delta_minutes : 0,
    },
  };
}
