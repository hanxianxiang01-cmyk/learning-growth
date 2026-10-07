/**
 * place-value V2 renderer 纯函数层（FE-1419，B5 模板第六实例 / Gap R06）。
 *
 * 语义（Gap R06）：数位、位值、组成/分解——数字卡放进位值框（digit movement）。
 * - config 给目标数 target（10~999）与牌堆 pool（target 各位数字的一种排列，
 *   parser 强制 multiset 相等——孩子只能在"位置"上犯错，这正是位值混淆的靶）；
 * - 交互：选牌（pick）→ 放入空框（place）/ 与框内牌交换（swap）/ 点框收回（return）；
 * - structure evaluator：未放满=EMPTY（拦提交）；放满且每框数字=该位期望数字=PASS；
 *   放满但位置错=FAIL/place_confusion —— **R06 Diagnosis P0"位值混淆"的原料**，
 *   序列化进 Evidence 供后端诊断链（判分仍后端权威：answer=框拼出的数）。
 */

export type PlaceValueV2Config = {
  target: number;
  /** 位名（与 target 位数一致，如 ["百","十","个"]）。 */
  places: string[];
  /** 期望各框数字（高位→低位）。 */
  expected: number[];
  /** 牌堆初始顺序（确定性：E2E/回归可复现）。 */
  pool: number[];
};

export type PlaceValueV2State = {
  /** 牌堆剩余数字（按放回去的顺序追加）。 */
  pool: number[];
  /** 各框内容：null=空框。索引对齐 places。 */
  slots: Array<number | null>;
  /** 当前选中牌堆下标；null=未选。 */
  picked: number | null;
};

export type PlaceValueVerdict = {
  status: "EMPTY" | "FAIL" | "PASS";
  /** FAIL 时恒为 place_confusion（牌面 multiset 由 config 锁死，错只可能错在位）。 */
  error: "place_confusion" | null;
};

const PLACE_NAMES = ["个", "十", "百", "千"];

export function parsePlaceValueConfig(raw: Record<string, unknown>): PlaceValueV2Config | null {
  const target = Number(raw.target);
  if (!Number.isInteger(target) || target < 10 || target > 999) return null;
  const expected = String(target).split("").map(Number);
  const digits = expected.length;
  const places = PLACE_NAMES.slice(0, digits).reverse(); // 高位在前：百十个
  const poolRaw = raw.pool;
  if (!Array.isArray(poolRaw) || poolRaw.length !== digits) return null;
  const pool = poolRaw.map(Number);
  if (pool.some(d => !Number.isInteger(d) || d < 0 || d > 9)) return null;
  // 牌堆必须与目标数字 multiset 相等——题目才可解且错误只剩"位置"维度
  const sorted = (xs: number[]) => [...xs].sort().join("");
  if (sorted(pool) !== sorted(expected)) return null;
  return { target, places, expected, pool };
}

export function initialPlaceValueV2State(config: PlaceValueV2Config): PlaceValueV2State {
  return { pool: [...config.pool], slots: config.expected.map(() => null), picked: null };
}

/** 点牌堆第 i 张：选中；重复点同一张=取消选中。 */
export function applyPick(
  state: PlaceValueV2State,
  i: number
): { ok: true; state: PlaceValueV2State } | { ok: false; code: "NO_CARD" } {
  if (i < 0 || i >= state.pool.length) return { ok: false, code: "NO_CARD" };
  return { ok: true, state: { ...state, picked: state.picked === i ? null : i } };
}

/**
 * 点第 j 个框：
 * - 选中牌 + 空框 → 放入（place）；
 * - 选中牌 + 有牌框 → 框内牌回堆、选中牌进框（swap）；
 * - 未选牌 + 有牌框 → 收回（return）。
 */
export function applySlot(
  state: PlaceValueV2State,
  j: number
):
  | { ok: true; action: "place" | "swap" | "return"; state: PlaceValueV2State }
  | { ok: false; code: "NO_SELECTION" | "EMPTY_POOL" | "BAD_SLOT" } {
  if (j < 0 || j >= state.slots.length) return { ok: false, code: "BAD_SLOT" };
  const slot = state.slots[j];
  if (state.picked === null) {
    if (slot === null) return { ok: false, code: "NO_SELECTION" };
    const pool = [...state.pool, slot];
    const slots = state.slots.map((s, i) => (i === j ? null : s));
    return { ok: true, action: "return", state: { pool, slots, picked: null } };
  }
  const card = state.pool[state.picked];
  if (card === undefined) return { ok: false, code: "EMPTY_POOL" };
  const pool = state.pool.filter((_, i) => i !== state.picked);
  const slots = state.slots.map((s, i) => (i === j ? card : s));
  if (slot !== null) pool.push(slot);
  return { ok: true, action: slot === null ? "place" : "swap", state: { pool, slots, picked: null } };
}

export function placeValueAnswer(state: PlaceValueV2State, config: PlaceValueV2Config): number | null {
  if (state.slots.some(s => s === null)) return null;
  return Number(state.slots.join(""));
}

/** 结构 evaluator：EMPTY（未满）→ PASS / FAIL(place_confusion)。 */
export function evaluatePlaceValue(state: PlaceValueV2State, config: PlaceValueV2Config): PlaceValueVerdict {
  if (state.slots.some(s => s === null)) return { status: "EMPTY", error: null };
  const exact = state.slots.every((s, i) => s === config.expected[i]);
  return exact ? { status: "PASS", error: null } : { status: "FAIL", error: "place_confusion" };
}

/** Evidence 形态：框/堆终态 + 拼出的数 + 结构判定（位值混淆诊断原料）。 */
export function serializePlaceValueV2(
  state: PlaceValueV2State,
  config: PlaceValueV2Config
): Record<string, unknown> {
  const verdict = evaluatePlaceValue(state, config);
  return {
    slots: state.slots,
    pool_remaining: state.pool,
    answer: placeValueAnswer(state, config),
    target_digits: config.expected,
    structure:
      verdict.status === "EMPTY"
        ? null
        : { status: verdict.status, error: verdict.error, place_value: true }
  };
}
