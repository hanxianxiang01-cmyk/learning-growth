// FE-1431 R18 money-board 纯函数层（B5 模板第十七实例，Batch E 第三题）。
// Gap R18：Semantic=money/amount/change；Evaluator=monetary evaluator；
// Evidence=选择与换算过程；Diagnosis=**面值/金额关系错误** P0。
//
// 玩法：商品价格（以"角"为最小单位）摆在台面上，孩子点钱包里的钱凑出**正好**这个价。
// 钱包四档：1角 / 5角 / 1元(=10角) / 5元(=50角)。点一档=加一枚，点"取回"减。
// 答案=付出总角数（组件自动算，后端标量相等判分，不动冻结链）。
//
// 分诊（evaluatePayment：EMPTY→PASS→denomination_confusion→under/over）：
//   EMPTY  一枚没选
//   PASS   total=price；币数多于最少组合 → uses_extra=true 留痕
//          ——**解耦第八次运用**（R08/R15 形态：钱凑没凑对=后端判、换得笨不笨=结构层说）
//   FAIL   denomination_confusion  恰好 {10角×p元位, 5角×p角位}——把"5角"当"5元"用
//          （3元5角→3 枚 1 元 + 5 枚 5角 = 55 角，Diagnosis P0 精确靶）
//   FAIL   underpaid / overpaid    不足/超出（附 diff 原料）
// parser 守卫：价格个位（角）必须是 5 的非零倍数（角位=5 使混淆靶必判错且唯一可识别）；
// 混淆靶必须 ≠ 正解（自动成立：角位 5 → 多算 4×角位 角）。

export type MoneyV2Config = {
  /** 价格（角） */
  price: number;
  /** 钱包面额档（角），升序 */
  denominations: number[];
};

export type MoneyV2State = {
  /** 面额 → 已选枚数 */
  counts: Record<string, number>;
  /** 选择与换算过程：每次加/减 [denomination, delta] */
  selection_history: Array<[denomination: number, delta: 1 | -1]>;
};

export type PaymentVerdict =
  | { status: "EMPTY"; coins: number }
  | { status: "PASS"; uses_extra: boolean; min_coins: number; coins: number }
  | { status: "FAIL"; error: "denomination_confusion" | "underpaid" | "overpaid"; diff: number };

const UNIT_LABEL: Record<number, string> = { 1: "1角", 5: "5角", 10: "1元", 50: "5元" };

export function unitLabel(d: number): string {
  return UNIT_LABEL[d] ?? `${d}角`;
}

function totalOf(counts: Record<string, number>): number {
  return Object.entries(counts).reduce((sum, [d, n]) => sum + Number(d) * n, 0);
}

/** 贪心最少币数（人民币面额体系下贪心即最优：1/5/10/50 是规范币制）。 */
export function minCoins(price: number, denominations: number[]): number {
  let rest = price;
  let n = 0;
  for (const d of [...denominations].sort((a, b) => b - a)) {
    if (rest >= d) {
      const take = Math.floor(rest / d);
      n += take;
      rest -= take * d;
    }
  }
  return rest === 0 ? n : -1; // -1=组不出（词表外面额才可能）
}

export function parseMoneyConfig(raw: unknown): MoneyV2Config | null {
  if (!raw || typeof raw !== "object") return null;
  const c = raw as Record<string, unknown>;
  if (typeof c.price !== "number" || !Number.isInteger(c.price) || c.price < 5 || c.price > 200) return null;
  // 守卫：角位必须是 5 的非零倍数（=5,15,25…角）——denomination_confusion 靶存在且必判错的前提
  if (c.price % 10 === 0) return null;
  if (c.price % 5 !== 0) return null;
  if (!Array.isArray(c.denominations) || c.denominations.length < 2) return null;
  const den = c.denominations as unknown[];
  if (!den.every(d => typeof d === "number" && Number.isInteger(d) && d > 0) ||
      new Set(den).size !== den.length) return null;
  // 混淆靶可达守卫：钱包必须有 5 角和 1 元档（靶组合 {10×元位, 5×角位数字}）
  if (!(den as number[]).includes(5) || !(den as number[]).includes(10)) return null;
  // 面额必须能组成价格（防词表外怪组合）
  if (minCoins(c.price, den as number[]) === -1) return null;
  return { price: c.price, denominations: [...(den as number[])].sort((a, b) => a - b) };
}

export function initialMoneyV2State(): MoneyV2State {
  return { counts: {}, selection_history: [] };
}

export function coins(state: MoneyV2State): number {
  return Object.values(state.counts).reduce((a, b) => a + b, 0);
}

export function applyAddCoin(
  state: MoneyV2State,
  config: MoneyV2Config,
  denomination: number
): { ok: boolean; code?: "NO_SUCH_DENOMINATION" | "OVER_LIMIT"; total: number; state: MoneyV2State } {
  if (!config.denominations.includes(denomination)) {
    return { ok: false, code: "NO_SUCH_DENOMINATION", total: totalOf(state.counts), state };
  }
  if (coins(state) >= 12) {
    return { ok: false, code: "OVER_LIMIT", total: totalOf(state.counts), state };
  }
  const next = { ...state.counts, [denomination]: (state.counts[denomination] ?? 0) + 1 };
  return { ok: true, total: totalOf(next), state: { counts: next, selection_history: [...state.selection_history, [denomination, 1]] } };
}

export function applyRemoveCoin(
  state: MoneyV2State,
  config: MoneyV2Config,
  denomination: number
): { ok: boolean; code?: "NO_SUCH_DENOMINATION" | "NONE_LEFT"; total: number; state: MoneyV2State } {
  if (!config.denominations.includes(denomination)) {
    return { ok: false, code: "NO_SUCH_DENOMINATION", total: totalOf(state.counts), state };
  }
  const cur = state.counts[denomination] ?? 0;
  if (cur <= 0) return { ok: false, code: "NONE_LEFT", total: totalOf(state.counts), state };
  const next: Record<string, number> = { ...state.counts, [denomination]: cur - 1 };
  if (next[denomination] === 0) delete next[denomination];
  return { ok: true, total: totalOf(next), state: { counts: next, selection_history: [...state.selection_history, [denomination, -1]] } };
}

/** 混淆靶组合：元位用 1 元币、角位"5 个 5"=5 枚 5 角（本应 1 枚）——total=元位*10+角位/5*5*... 见下。 */
function isConfusion(counts: Record<string, number>, price: number): boolean {
  const yuan = Math.floor(price / 10); // 元位数
  const jiao = price % 10; // 角位（=5）
  const keys = Object.keys(counts).map(Number).sort((a, b) => a - b);
  // 恰好 = yuan 枚 1 角? 不——混淆形态：用 yuan 枚 1 元 + jiao 枚 5 角（把 5 角当 5 元）
  const want: Record<string, number> = {};
  if (yuan > 0) want["10"] = yuan;
  want["5"] = jiao; // 5 角当 5 元 → 角位数字直接当 5 角枚数
  return JSON.stringify(keys) === JSON.stringify(Object.keys(want).map(Number).sort((a, b) => a - b)) &&
    JSON.stringify(counts) === JSON.stringify(want);
}

/** 评估：EMPTY(零枚) → PASS(total=price，多于最少币=uses_extra) →
 * denomination_confusion(混淆靶) → underpaid/overpaid(附差)。 */
export function evaluatePayment(state: MoneyV2State, config: MoneyV2Config): PaymentVerdict {
  const n = coins(state);
  if (n === 0) return { status: "EMPTY", coins: 0 };
  const total = totalOf(state.counts);
  const min = minCoins(config.price, config.denominations);
  if (total === config.price) return { status: "PASS", uses_extra: n > min, min_coins: min, coins: n };
  if (isConfusion(state.counts, config.price)) return { status: "FAIL", error: "denomination_confusion", diff: total - config.price };
  return { status: "FAIL", error: total < config.price ? "underpaid" : "overpaid", diff: total - config.price };
}

export function moneyAnswer(state: MoneyV2State): number | null {
  if (coins(state) === 0) return null;
  return totalOf(state.counts);
}

export function serializeMoneyV2(state: MoneyV2State, config: MoneyV2Config) {
  const verdict = evaluatePayment(state, config);
  const yuan = Math.floor(totalOf(state.counts) / 10);
  const jiao = totalOf(state.counts) % 10;
  return {
    counts: state.counts,
    coins: coins(state),
    total: totalOf(state.counts),
    total_text: `${yuan}元${jiao}角`,
    selection_history: state.selection_history,
    answer: moneyAnswer(state),
    price: config.price,
    structure: {
      status: verdict.status,
      error: verdict.status === "FAIL" ? verdict.error : null,
      diff: verdict.status === "FAIL" ? verdict.diff : 0,
      uses_extra: verdict.status === "PASS" ? verdict.uses_extra : null,
      min_coins: verdict.status === "PASS" ? verdict.min_coins : minCoins(config.price, config.denominations),
    },
  };
}
