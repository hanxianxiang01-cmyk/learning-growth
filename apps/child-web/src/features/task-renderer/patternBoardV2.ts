// FE-1436 R19 pattern-board 纯函数层（B5 模板第十八实例，Batch E 收官题）。
// Gap R19：Semantic=sequence/rule/prediction；Evaluator=pattern evaluator；
// Evidence=尝试顺序、修改过程；Diagnosis=**规律识别错误** P0。
//
// 玩法：礼物包装纸花边按规律排：黄蓝黄 ……（可见 3 个），后面缺 2 个。
// 点颜色按钮=往第一个空格填一颗；再点同一颗=替换（修改留痕）；点空格=清空。
// 答案=空格 token 拼接整数（32=蓝黄? 否——[3,2]→"32"；后端标量判分，不动冻结链）。
//
// 分诊（evaluatePattern：EMPTY→PASS→phase_shift→rule_ignored→wrong_sequence）：
//   EMPTY  空格没填满
//   PASS   恰=周期延续（32）；改过=changed_once 留痕（Gap"尝试顺序、修改过程"）
//   FAIL   phase_shift  恰好 [2,3]——周期读对但**起步相位错**（从上一颗重新数）
//   FAIL   rule_ignored 全填=末颗颜色（延续惯性：一直涂黄的）——"没找规律"精确靶
//   FAIL   wrong_sequence 其余（附逐位原料）
// parser 守卫：可见段必须周期≥2（全同无规律可考）、周期≤3；
// 相位靶 ≠ 正解（单位非回文）；rule_ignored 靶 ≠ 正解（周期≥2 自动成立）。

export type PatternV2Config = {
  /** 可见 token 序列（1..palette 的整数） */
  visible: number[];
  /** 空格数（2..3） */
  blanks: number;
  /** 调色板（升序） */
  palette: number[];
  /** 推断出的最小周期（parser 计算，组件展示"规律提示条"用） */
  period: number;
};

export type PatternV2State = {
  /** 空格现值（长度=blanks，null=空） */
  beads: (number | null)[];
  /** 尝试顺序、修改过程：每次 [slot, from, to]（to=null 即清空） */
  attempt_history: Array<[slot: number, from: number | null, to: number | null]>;
};

export type PatternVerdict =
  | { status: "EMPTY"; filled: number }
  | { status: "PASS"; changed_once: boolean }
  | {
      status: "FAIL";
      error: "phase_shift" | "rule_ignored" | "wrong_sequence";
      expected: number[];
      actual: number[];
    };

/** 最小周期：最小的 p≥2 使 visible 以 p 周期展开（p=1 全同不算规律）。 */
export function inferPeriod(visible: number[]): number | null {
  const n = visible.length;
  for (let p = 2; p <= Math.min(3, n - 1); p++) {
    if (n % p !== 0 && n < 2 * p) continue;
    const unit = visible.slice(0, p);
    let ok = true;
    for (let i = p; i < n; i++) {
      if (visible[i] !== unit[i % p]) {
        ok = false;
        break;
      }
    }
    if (ok) return p;
  }
  return null;
}

export function parsePatternConfig(raw: unknown): PatternV2Config | null {
  if (!raw || typeof raw !== "object") return null;
  const c = raw as Record<string, unknown>;
  if (!Array.isArray(c.visible) || c.visible.length < 3 || c.visible.length > 6) return null;
  const visible = c.visible as unknown[];
  if (!visible.every(v => typeof v === "number" && Number.isInteger(v) && v >= 1 && v <= 5)) return null;
  if (typeof c.blanks !== "number" || !Number.isInteger(c.blanks) || c.blanks < 2 || c.blanks > 3) return null;
  if (!Array.isArray(c.palette) || c.palette.length < 2 || c.palette.length > 4) return null;
  const palette = c.palette as unknown[];
  if (!palette.every(v => typeof v === "number" && Number.isInteger(v) && v >= 1 && v <= 5) ||
      new Set(palette).size !== palette.length) return null;
  const vis = visible as number[];
  const pal = [...palette] as number[];
  // 守卫：调色板 ⊇ 可见 token（否则填不出正解）
  if (!vis.every(v => pal.includes(v))) return null;
  const period = inferPeriod(vis);
  if (period === null) return null; // 无周期/全同（p=1 被排除）/周期>3 不可考
  const blanks = c.blanks as number;
  const expected = Array.from({ length: blanks }, (_, i) => vis[(vis.length + i) % period]);
  const lastVisible = vis[vis.length - 1];
  // 守卫：相位偏移靶 = 期望整体后移一位（unit 非回文才可能）——必须 ≠ 正解
  const shifted = Array.from({ length: blanks }, (_, i) => vis[(vis.length + i + 1) % period]);
  if (JSON.stringify(shifted) === JSON.stringify(expected)) return null;
  // 守卫：惯性靶（全填末颗）≠ 正解（周期≥2 时自动成立，显式双保险）
  if (expected.every(v => v === lastVisible)) return null;
  return { visible: vis, blanks, palette: pal.sort((a, b) => a - b), period };
}

export function expectedBeads(config: PatternV2Config): number[] {
  return Array.from(
    { length: config.blanks },
    (_, i) => config.visible[(config.visible.length + i) % config.period]
  );
}

export function initialPatternV2State(): PatternV2State {
  return { beads: [], attempt_history: [] };
}

/** 初始化空格（组件装载后调用一次——不算"尝试"）。 */
export function initBlanks(config: PatternV2Config): PatternV2State {
  return { beads: Array.from({ length: config.blanks }, () => null), attempt_history: [] };
}

/** 点颜色=填第一个空格；若该位已有值且点不同颜色=替换（修改留痕）。 */
export function applyPlaceToken(
  state: PatternV2State,
  config: PatternV2Config,
  token: number
): { ok: boolean; code?: "NO_SUCH_TOKEN" | "NO_EMPTY_SLOT"; replaced: boolean; state: PatternV2State } {
  if (!config.palette.includes(token)) {
    return { ok: false, code: "NO_SUCH_TOKEN", replaced: false, state };
  }
  const slot = state.beads.findIndex(b => b === null);
  if (slot === -1) {
    return { ok: false, code: "NO_EMPTY_SLOT", replaced: false, state };
  }
  const from = state.beads[slot];
  const beads = [...state.beads];
  beads[slot] = token;
  return {
    ok: true,
    replaced: from !== null,
    state: { beads, attempt_history: [...state.attempt_history, [slot, from, token]] },
  };
}

/** 替换指定空格（点已填的珠子再点颜色=改这颗）。 */
export function applyReplaceAt(
  state: PatternV2State,
  config: PatternV2Config,
  slot: number,
  token: number
): { ok: boolean; code?: "NO_SUCH_TOKEN" | "NO_SUCH_SLOT" | "SAME_TOKEN"; state: PatternV2State } {
  if (!config.palette.includes(token)) return { ok: false, code: "NO_SUCH_TOKEN", state };
  if (slot < 0 || slot >= state.beads.length) return { ok: false, code: "NO_SUCH_SLOT", state };
  if (state.beads[slot] === token) return { ok: false, code: "SAME_TOKEN", state };
  const beads = [...state.beads];
  const from = beads[slot];
  beads[slot] = token;
  return { ok: true, state: { beads, attempt_history: [...state.attempt_history, [slot, from, token]] } };
}

/** 点空格=清空该位。 */
export function applyClearAt(
  state: PatternV2State,
  slot: number
): { ok: boolean; code?: "NO_SUCH_SLOT" | "ALREADY_EMPTY"; state: PatternV2State } {
  if (slot < 0 || slot >= state.beads.length) return { ok: false, code: "NO_SUCH_SLOT", state };
  if (state.beads[slot] === null) return { ok: false, code: "ALREADY_EMPTY", state };
  const beads = [...state.beads];
  const from = beads[slot];
  beads[slot] = null;
  return { ok: true, state: { beads, attempt_history: [...state.attempt_history, [slot, from, null]] } };
}

function filledCount(state: PatternV2State): number {
  return state.beads.filter(b => b !== null).length;
}

/** 评估：EMPTY(没填满) → PASS(=期望；attempt>blanks 即改过→changed_once) →
 * phase_shift(=后移一位) → rule_ignored(全=末颗) → wrong_sequence。 */
export function evaluatePattern(state: PatternV2State, config: PatternV2Config): PatternVerdict {
  const expected = expectedBeads(config);
  const beads = state.beads;
  if (beads.some(b => b === null) || beads.length !== config.blanks) {
    return { status: "EMPTY", filled: filledCount(state) };
  }
  const actual = beads as number[];
  const equals = (a: number[], b: number[]) => JSON.stringify(a) === JSON.stringify(b);
  if (equals(actual, expected)) {
    return { status: "PASS", changed_once: state.attempt_history.length > config.blanks };
  }
  const shifted = Array.from(
    { length: config.blanks },
    (_, i) => config.visible[(config.visible.length + i + 1) % config.period]
  );
  if (equals(actual, shifted)) return { status: "FAIL", error: "phase_shift", expected, actual };
  const lastVisible = config.visible[config.visible.length - 1];
  if (actual.every(v => v === lastVisible)) {
    return { status: "FAIL", error: "rule_ignored", expected, actual };
  }
  return { status: "FAIL", error: "wrong_sequence", expected, actual };
}

/** 提交答案=空格 token 拼接整数（token 限 1..5 一位数无歧义）。 */
export function patternAnswer(state: PatternV2State, config: PatternV2Config): number | null {
  if (state.beads.some(b => b === null) || state.beads.length !== config.blanks) return null;
  return Number((state.beads as number[]).join(""));
}

export function serializePatternV2(state: PatternV2State, config: PatternV2Config) {
  const verdict = evaluatePattern(state, config);
  return {
    visible: config.visible,
    beads: state.beads,
    pattern_text: [...config.visible, ...state.beads.map(b => b ?? "?")].join(" "),
    period: config.period,
    attempt_history: state.attempt_history,
    answer: patternAnswer(state, config),
    structure: {
      status: verdict.status,
      error: verdict.status === "FAIL" ? verdict.error : null,
      changed_once: verdict.status === "PASS" ? verdict.changed_once : null,
      expected: verdict.status === "FAIL" ? verdict.expected : null,
    },
  };
}
