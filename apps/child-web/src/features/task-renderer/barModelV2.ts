/**
 * bar-model V2 renderer 纯函数层（FE-1418，B5 模板第五实例 / Gap R02）。
 *
 * 语义（Gap R02）：条形模型两种可提交关系——
 * - part_whole：部分 a、部分 b、整体 c（c = a + b）；
 * - comparison：大条 a、小条 b、差条 c（c = a - b，config 保证 a>b）。
 * 每题 config 声明两根"读题已知条"（known）+ 一根"答案条"（answer_bar）。
 *
 * **模型结构 evaluator 是本 Gate 的核心卖点**（R02 P0：Diagnosis=结构错误分类证据）。
 * 判分不只核答案数字，而是三根条一起核，错误分三类留痕（各自 E2E 可达）：
 *   modeling —— 已知条没照题摆（读题/建模范畴错误）；
 *   relation —— 模型结构本身不成立：整体比部分还短 / 差条不比大条短（没理解条形关系）；
 *   calc     —— 结构成立但数不对（模型搭对、算错）。
 * 后端诊断链由此拿到"结构错误分类"原料（R02 Diagnosis P0 条目）。
 *
 * 提交门禁（P0-01 口径）：EMPTY=答案条没碰过不可提交；其余可提交，对错后端权威判。
 */

export type BarModelMode = "part_whole" | "comparison";
export type BarId = "a" | "b" | "c";

export type BarModelV2Config = {
  mode: BarModelMode;
  /** 读题已知条期望值——恰好两根，各 ≥1（parser 保证，否则题目不可解/结构恒坏）。 */
  known: Record<"a" | "b" | "c", number> extends never ? never : Partial<Record<BarId, number>>;
  answerBar: BarId;
  maxBlocks: number;
};

export type BarModelV2State = {
  bars: Record<BarId, number>;
  /** 答案条是否被碰过（EMPTY 判定的唯一依据）。 */
  answerTouched: boolean;
};

export type BarModelError = "modeling" | "relation" | "calc" | null;
export type BarModelVerdict = { status: "EMPTY" | "FAIL" | "PASS"; error: BarModelError };

const BARS: BarId[] = ["a", "b", "c"];

/** config 解析（纯函数）：非法结构返回 null（组件出配置不完整卡，不瞎渲染）。 */
export function parseBarModelConfig(raw: Record<string, unknown>): BarModelV2Config | null {
  const mode = raw.mode === "part_whole" || raw.mode === "comparison" ? raw.mode : null;
  if (!mode) return null;
  if (raw.answer_bar !== "a" && raw.answer_bar !== "b" && raw.answer_bar !== "c") return null;
  const answerBar = raw.answer_bar as BarId;
  const knownRaw = raw.known;
  if (typeof knownRaw !== "object" || knownRaw === null) return null;
  const known: Partial<Record<BarId, number>> = {};
  let count = 0;
  for (const id of BARS) {
    const v = (knownRaw as Record<string, unknown>)[id];
    if (v === undefined) continue;
    if (typeof v !== "number" || !Number.isInteger(v) || v < 1) return null;
    known[id] = v;
    count += 1;
  }
  // 恰好两根已知条：答案条唯一未知，题目才可解
  if (count !== 2 || known[answerBar] !== undefined) return null;

  const a = known.a ?? 0;
  const b = known.b ?? 0;
  const c = known.c ?? 0;
  // 答案可解性守卫：comparison 的差不能为负/为 0；part_whole 的答案恒可解
  let solved: number;
  if (mode === "part_whole") {
    solved = answerBar === "c" ? a + b : answerBar === "a" ? c - b : c - a;
    if (solved < 1) return null;
  } else {
    solved = answerBar === "c" ? a - b : answerBar === "a" ? b + c : a - c;
    if (solved < 1) return null;
  }

  const maxBlocksRaw = Number(raw.max_blocks);
  const maxBlocks =
    Number.isInteger(maxBlocksRaw) && maxBlocksRaw >= solved + 1 && maxBlocksRaw <= 30
      ? maxBlocksRaw
      : Math.max(20, solved + 5);
  return { mode, known, answerBar, maxBlocks };
}

export function initialBarModelV2State(): BarModelV2State {
  return { bars: { a: 0, b: 0, c: 0 }, answerTouched: false };
}

/** 单条增/减方块：0..max 钳制；越界拒绝码。 */
export function applyBarDelta(
  state: BarModelV2State,
  bar: BarId,
  delta: number,
  config: BarModelV2Config
): { ok: true; state: BarModelV2State } | { ok: false; code: "OUT_OF_RANGE" | "BAD_DELTA" } {
  if (delta !== 1 && delta !== -1) return { ok: false, code: "BAD_DELTA" };
  const next = state.bars[bar] + delta;
  if (next < 0 || next > config.maxBlocks) return { ok: false, code: "OUT_OF_RANGE" };
  const bars = { ...state.bars, [bar]: next };
  return {
    ok: true,
    state: { bars, answerTouched: bar === config.answerBar ? true : state.answerTouched }
  };
}

/** 从两根已知条解出答案条期望值（parser 已保证可解且 ≥1）。 */
export function solveExpected(config: BarModelV2Config): number {
  const a = config.known.a ?? 0;
  const b = config.known.b ?? 0;
  const c = config.known.c ?? 0;
  if (config.mode === "part_whole") {
    if (config.answerBar === "c") return a + b;
    return config.answerBar === "a" ? c - b : c - a;
  }
  if (config.answerBar === "c") return a - b;
  return config.answerBar === "a" ? b + c : a - c;
}

/**
 * 模型结构 evaluator（三根条整体核对）。错误三分类各自可达：
 * 1) modeling：已知条 ≠ 题面值；
 * 2) relation：结构不成立——part_whole 的整体条不比两根部分条长 /
 *    comparison 的差条不比大条短（摆出数学上不存在的模型）；
 * 3) calc：结构成立但答案 ≠ 期望值。
 */
export function evaluateBarModel(state: BarModelV2State, config: BarModelV2Config): BarModelVerdict {
  if (!state.answerTouched) return { status: "EMPTY", error: null };

  for (const id of BARS) {
    const expectedKnown = config.known[id];
    if (expectedKnown !== undefined && state.bars[id] !== expectedKnown) {
      return { status: "FAIL", error: "modeling" };
    }
  }

  const { a, b, c } = state.bars;
  // 结构规则：part_whole 的整体条 c 必须严格长于两根部分；
  // comparison 的差条 c 必须严格短于大条 a 且 a>b（摆出数学上不存在的模型=relation 错）
  const structureBroken =
    config.mode === "part_whole" ? !(c > a && c > b) : !(c < a && a > b);
  if (structureBroken) return { status: "FAIL", error: "relation" };

  const expected = solveExpected(config);
  if (state.bars[config.answerBar] !== expected) return { status: "FAIL", error: "calc" };
  return { status: "PASS", error: null };
}

/** Evidence 形态：三根条 + 答案 + 结构判定（诊断原料随 envelope 入库）。 */
export function serializeBarModelV2(
  state: BarModelV2State,
  config: BarModelV2Config
): Record<string, unknown> {
  const verdict = evaluateBarModel(state, config);
  return {
    bars: { ...state.bars },
    answer_bar: config.answerBar,
    answer: state.answerTouched ? state.bars[config.answerBar] : null,
    structure:
      verdict.status === "EMPTY"
        ? null
        : { status: verdict.status, error: verdict.error, relation: config.mode }
  };
}

export function barModelAnswer(state: BarModelV2State, config: BarModelV2Config): number | null {
  return state.answerTouched ? state.bars[config.answerBar] : null;
}
