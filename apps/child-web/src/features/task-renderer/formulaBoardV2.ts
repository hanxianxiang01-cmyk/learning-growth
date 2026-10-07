/**
 * formula-board V2 renderer 纯函数层（FE-1420，B5 模板第七实例 / Gap R10）。
 *
 * 语义（Gap R10）：equation / relation / unknown——算式填空板。
 * config.tokens 定义算式 token 流：数字字面量 / 运算符字面量 / 空槽
 * （accept: number|operator）/ 等号；answer_slot 指认"答案槽"。
 *
 * **equation semantic evaluator**（R10 Evaluator P0）：不是字符串相等匹配，
 * 而是把填好的算式左右两边各自求值、核对等式成立性。错误二分类（Diagnosis P0
 * "运算符/数量关系错误"原料）：
 *   operator —— 存在运算符槽，且翻转它（+/− 互换）即可让等式成立（数没错、符号选错）；
 *   relation —— 等式不成立且换符号也救不回来（数量关系错）。
 * PASS = 等式成立。EMPTY = 任一槽未填（不可提交；P0-01 口径）。
 *
 * Evidence（Gap："修改顺序、替换过程"）：交互层每次 FILL/REPLACE 都留事件；
 * 本层序列化终态 filled + structure 判定。
 */

export type FormulaToken =
  | { t: "num"; v: number }
  | { t: "op"; v: "+" | "-" }
  | { t: "eq" }
  | { t: "slot"; id: string; accept: "number" | "operator" };

export type FormulaTokenInput = {
  t: string;
  v?: string | number;
  id?: string;
  accept?: string;
};

export type FormulaBoardV2Config = {
  tokens: FormulaToken[];
  answerSlot: string;
  /** 数字槽取值上限（儿童 20 以内口径）。 */
  maxNumber: number;
};

export type FormulaBoardV2State = {
  /** slot id → 填入值（number 或 "+"/"-"）。 */
  filled: Record<string, number | string>;
  /** 当前点选的槽 id（键盘/符号面板展开）；null=收起。 */
  activeSlot: string | null;
};

export type FormulaVerdict = {
  status: "EMPTY" | "FAIL" | "PASS";
  error: "operator" | "relation" | null;
};

export function parseFormulaConfig(raw: Record<string, unknown>): FormulaBoardV2Config | null {
  const rawTokens = raw.tokens;
  if (!Array.isArray(rawTokens) || rawTokens.length === 0) return null;
  const tokens: FormulaToken[] = [];
  const slotIds = new Set<string>();
  let eqCount = 0;
  for (const item of rawTokens as FormulaTokenInput[]) {
    if (item.t === "num") {
      if (typeof item.v !== "number" || !Number.isInteger(item.v)) return null;
      tokens.push({ t: "num", v: item.v });
    } else if (item.t === "op") {
      if (item.v !== "+" && item.v !== "-") return null;
      tokens.push({ t: "op", v: item.v });
    } else if (item.t === "eq") {
      eqCount += 1;
      tokens.push({ t: "eq" });
    } else if (item.t === "slot") {
      if (!item.id || slotIds.has(item.id)) return null;
      if (item.accept !== "number" && item.accept !== "operator") return null;
      slotIds.add(item.id);
      tokens.push({ t: "slot", id: item.id, accept: item.accept });
    } else {
      return null;
    }
  }
  // 恰好一个等号；槽 1~3 个；两侧各自至多一个运算符（儿童 20 以内线性算式）
  if (eqCount !== 1 || slotIds.size < 1 || slotIds.size > 3) return null;
  const answerSlot = raw.answer_slot;
  if (typeof answerSlot !== "string" || !slotIds.has(answerSlot)) return null;
  const maxNumber = Number(raw.max_number);
  return {
    tokens,
    answerSlot,
    maxNumber: Number.isInteger(maxNumber) && maxNumber >= 5 && maxNumber <= 99 ? maxNumber : 20
  };
}

export function initialFormulaV2State(): FormulaBoardV2State {
  return { filled: {}, activeSlot: null };
}

/** 点槽：打开/收起该槽的输入面板。 */
export function applyActivate(
  state: FormulaBoardV2State,
  slotId: string
): FormulaBoardV2State {
  return { ...state, activeSlot: state.activeSlot === slotId ? null : slotId };
}

/** 数字键：追加成多位数（9→9，再 5→95），超 maxNumber 拒绝；首位 0 拒。 */
export function applyNumberKey(
  state: FormulaBoardV2State,
  config: FormulaBoardV2Config,
  key: number
): { ok: true; state: FormulaBoardV2State; replaced: boolean } | { ok: false; code: "OUT_OF_RANGE" | "NO_ACTIVE_SLOT" | "NOT_NUMBER_SLOT" } {
  const slotId = state.activeSlot;
  if (!slotId) return { ok: false, code: "NO_ACTIVE_SLOT" };
  const token = config.tokens.find(t => t.t === "slot" && t.id === slotId);
  if (!token || token.t !== "slot" || token.accept !== "number") {
    return { ok: false, code: "NOT_NUMBER_SLOT" };
  }
  const current = state.filled[slotId];
  const leading = current === undefined ? "" : String(current);
  if (key === 0 && leading === "") return { ok: false, code: "OUT_OF_RANGE" };
  const next = Number(leading + String(key));
  if (next > config.maxNumber) return { ok: false, code: "OUT_OF_RANGE" };
  const replaced = current !== undefined && leading !== "";
  return { ok: true, replaced, state: { ...state, filled: { ...state.filled, [slotId]: next } } };
}

/** 符号键（+/-）：填入运算符槽。 */
export function applyOperatorKey(
  state: FormulaBoardV2State,
  config: FormulaBoardV2Config,
  op: "+" | "-"
): { ok: true; state: FormulaBoardV2State; replaced: boolean } | { ok: false; code: "NO_ACTIVE_SLOT" | "NOT_OPERATOR_SLOT" } {
  const slotId = state.activeSlot;
  if (!slotId) return { ok: false, code: "NO_ACTIVE_SLOT" };
  const token = config.tokens.find(t => t.t === "slot" && t.id === slotId);
  if (!token || token.t !== "slot" || token.accept !== "operator") {
    return { ok: false, code: "NOT_OPERATOR_SLOT" };
  }
  const replaced = state.filled[slotId] !== undefined && state.filled[slotId] !== op;
  return { ok: true, replaced, state: { ...state, filled: { ...state.filled, [slotId]: op } } };
}

/** 清空当前激活槽（修改/替换前撤回）。 */
export function applyClear(
  state: FormulaBoardV2State
): { ok: true; state: FormulaBoardV2State } | { ok: false; code: "NO_ACTIVE_SLOT" } {
  const slotId = state.activeSlot;
  if (!slotId) return { ok: false, code: "NO_ACTIVE_SLOT" };
  const filled = { ...state.filled };
  delete filled[slotId];
  return { ok: true, state: { ...state, filled } };
}

/** 用 filled 值替换槽后，把 token 流拆成左右两段的"可求值序列"；缺槽=null。 */
function evaluateSide(
  side: FormulaToken[],
  filled: Record<string, number | string>
): number | null {
  const seq: Array<number | "+" | "-"> = [];
  for (const token of side) {
    if (token.t === "num") seq.push(token.v);
    else if (token.t === "op") seq.push(token.v);
    else if (token.t === "slot") {
      const value = filled[token.id];
      if (value === undefined) return null;
      seq.push(value as number | "+" | "-");
    }
  }
  // 合法形态：n | n op n（一个等号两侧各至多一个二元运算）
  if (seq.length === 1 && typeof seq[0] === "number") return seq[0];
  if (seq.length === 3 && typeof seq[0] === "number" && typeof seq[2] === "number") {
    const op = seq[1];
    if (op === "+") return seq[0] + seq[2];
    if (op === "-") return seq[0] - seq[2];
  }
  return null; // 形态非法（如 op op n）→ 视为不可求值
}

function sidesOf(config: FormulaBoardV2Config): [FormulaToken[], FormulaToken[]] | null {
  const eqIndex = config.tokens.findIndex(t => t.t === "eq");
  if (eqIndex < 0) return null;
  return [config.tokens.slice(0, eqIndex), config.tokens.slice(eqIndex + 1)];
}

/**
 * equation semantic evaluator：
 * EMPTY（任一槽未填或形态非法）→ 等式成立=PASS；
 * FAIL 分类：翻转任一运算符槽可救=operator；否则=relation。
 */
export function evaluateFormula(
  state: FormulaBoardV2State,
  config: FormulaBoardV2Config
): FormulaVerdict {
  const slots = config.tokens.filter(t => t.t === "slot");
  if (slots.some(s => s.t === "slot" && state.filled[s.id] === undefined)) {
    return { status: "EMPTY", error: null };
  }
  const sides = sidesOf(config);
  if (!sides) return { status: "EMPTY", error: null };
  const left = evaluateSide(sides[0], state.filled);
  const right = evaluateSide(sides[1], state.filled);
  if (left === null || right === null) return { status: "EMPTY", error: null };
  if (left === right) return { status: "PASS", error: null };

  // operator 判定：逐个翻转运算符槽（+/-互换），任一使等式成立 → operator
  const opSlots = config.tokens.filter(t => t.t === "slot" && t.accept === "operator");
  for (const opSlot of opSlots) {
    if (opSlot.t !== "slot") continue;
    const flipped = { ...state.filled };
    flipped[opSlot.id] = flipped[opSlot.id] === "+" ? "-" : "+";
    if (evaluateSide(sides[0], flipped) === evaluateSide(sides[1], flipped)) {
      return { status: "FAIL", error: "operator" };
    }
  }
  return { status: "FAIL", error: "relation" };
}

/** 答案槽值（数字或符号字符串）；未填=null。 */
export function formulaAnswer(
  state: FormulaBoardV2State,
  config: FormulaBoardV2Config
): number | string | null {
  return state.filled[config.answerSlot] ?? null;
}

/** Evidence：终态 filled + 答案 + structure 判定（operator/relation 原料）。 */
export function serializeFormulaBoardV2(
  state: FormulaBoardV2State,
  config: FormulaBoardV2Config
): Record<string, unknown> {
  const verdict = evaluateFormula(state, config);
  return {
    filled: { ...state.filled },
    answer: formulaAnswer(state, config),
    structure:
      verdict.status === "EMPTY"
        ? null
        : { status: verdict.status, error: verdict.error, equation: true }
  };
}
