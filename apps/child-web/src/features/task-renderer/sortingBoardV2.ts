// FE-1426 R14 sorting-board 纯函数层（B5 模板第十三实例，Batch D 第三题）。
// Gap R14：Semantic=compare/classify/order；Evaluator=order evaluator；
// Evidence=排序过程；Diagnosis=**比较维度错误** P0。
//
// 玩法：数字卡按题面维度（数值从小到大）排好；点两张卡=交换位置（两步点选，
// 不依赖 drag）。答案=数值顺序拼接整数（后端 float 相等判分，不动冻结链）。
// 卡面视觉字号与数值**故意不一致**（干扰维度）——按"看起来大小"排 →
// dimension_confusion 原料；全降序 → reversed 原料；两者与正序三态互斥各有靶。

export type SortItem = {
  id: string;
  /** 题面维度：数值 */
  value: number;
  /** 干扰维度：卡面视觉档位（1=最小号字 … n=最大号字），与 value 序故意错开 */
  visual_rank: number;
};

export type SortingBoardV2Config = {
  items: SortItem[];
  /** 题面目标方向（本 Gate 词表守卫只开升序） */
  direction: "asc";
  /** 初始乱序（id 序列）——parser 守卫 ≠ 正解序 */
  initialOrder: string[];
};

export type SortingBoardV2State = {
  order: string[];
  /** 点选交换：第一步选中的卡 id（null=没拿） */
  selected: string | null;
  /** 排序过程 Evidence：每次成功交换 [i,j] */
  swaps: Array<[number, number]>;
};

export type SortVerdict =
  | { status: "EMPTY" }
  | { status: "PASS" }
  | { status: "FAIL"; error: "reversed" | "dimension_confusion" | "disordered" };

export function parseSortingConfig(raw: unknown): SortingBoardV2Config | null {
  if (!raw || typeof raw !== "object") return null;
  const c = raw as Record<string, unknown>;
  if (!Array.isArray(c.items) || c.items.length < 3 || c.items.length > 6) return null;
  const items: SortItem[] = [];
  const ids = new Set<string>();
  const values = new Set<number>();
  const ranks = new Set<number>();
  for (const s of c.items) {
    if (!s || typeof s !== "object") return null;
    const it = s as Record<string, unknown>;
    if (typeof it.id !== "string" || !it.id || ids.has(it.id)) return null;
    if (typeof it.value !== "number" || !Number.isInteger(it.value) || it.value < 1 || it.value > 9 || values.has(it.value)) return null; // 单值一位数：拼接答案无歧义（12|3 vs 1|23）
    if (typeof it.visual_rank !== "number" || !Number.isInteger(it.visual_rank) || ranks.has(it.visual_rank)) return null;
    items.push({ id: it.id, value: it.value, visual_rank: it.visual_rank });
    ids.add(it.id);
    values.add(it.value);
    ranks.add(it.visual_rank);
  }
  // visual_rank 必须是 1..n 的排列（档位语义完整）
  const rankList = [...ranks];
  if (Math.min(...rankList) !== 1 || Math.max(...rankList) !== items.length) return null;
  if (c.direction !== "asc") return null;
  if (!Array.isArray(c.initial_order) || c.initial_order.length !== items.length) return null;
  const init = c.initial_order as unknown[];
  if (!init.every(x => typeof x === "string" && ids.has(x as string)) || new Set(init).size !== init.length) return null;
  // 守卫：初始序≠数值正序（否则题已做完）；正解由 value 排序派生
  const target = orderByIds(items, [...items].sort((a, b) => a.value - b.value).map(i => i.id));
  if (JSON.stringify(init) === JSON.stringify(target)) return null;
  // 干扰维度守卫：视觉序（visual_rank 大→小=字大的在前）既非正序也非降序——
  // 否则 dimension 与 reversed 态重叠，分诊失效
  const byVisual = [...items].sort((a, b) => b.visual_rank - a.visual_rank).map(i => i.id);
  const desc = [...items].sort((a, b) => b.value - a.value).map(i => i.id);
  if (JSON.stringify(byVisual) === JSON.stringify(target) || JSON.stringify(byVisual) === JSON.stringify(desc)) return null;
  return { items, direction: "asc", initialOrder: init as string[] };
}

function orderByIds(items: SortItem[], ids: string[]): string[] {
  const map = new Map(items.map(i => [i.id, i] as const));
  return ids.map(id => map.get(id)!.id);
}

export function targetOrder(config: SortingBoardV2Config): string[] {
  return [...config.items].sort((a, b) => a.value - b.value).map(i => i.id);
}

function reversedOrder(config: SortingBoardV2Config): string[] {
  return [...config.items].sort((a, b) => b.value - a.value).map(i => i.id);
}

function visualOrder(config: SortingBoardV2Config): string[] {
  return [...config.items].sort((a, b) => b.visual_rank - a.visual_rank).map(i => i.id);
}

export function initialSortingV2State(config: SortingBoardV2Config): SortingBoardV2State {
  return { order: [...config.initialOrder], selected: null, swaps: [] };
}

export function applySelectCard(
  state: SortingBoardV2State,
  config: SortingBoardV2Config,
  id: string,
): { ok: boolean; code?: "NO_SUCH_ITEM"; deselected: boolean; state: SortingBoardV2State } {
  if (!config.items.some(i => i.id === id)) return { ok: false, code: "NO_SUCH_ITEM", deselected: false, state };
  if (state.selected === id) return { ok: true, deselected: true, state: { ...state, selected: null } };
  return { ok: true, deselected: false, state: { ...state, selected: id } };
}

/** 点第二张卡=交换两位置（选中保留清除）。同位/无选中由组件层先行分流。 */
export function applySwap(
  state: SortingBoardV2State,
  config: SortingBoardV2Config,
  id: string,
): { ok: boolean; code?: "NO_SELECTION" | "NO_SUCH_ITEM" | "SAME_CARD"; from?: number; to?: number; state: SortingBoardV2State } {
  if (state.selected === null) return { ok: false, code: "NO_SELECTION", state };
  if (!config.items.some(i => i.id === id)) return { ok: false, code: "NO_SUCH_ITEM", state };
  const from = state.order.indexOf(state.selected);
  const to = state.order.indexOf(id);
  if (from < 0 || to < 0) return { ok: false, code: "NO_SUCH_ITEM", state };
  if (from === to) return { ok: false, code: "SAME_CARD", state };
  const order = [...state.order];
  [order[from], order[to]] = [order[to], order[from]];
  return { ok: true, from, to, state: { order, selected: null, swaps: [...state.swaps, [from, to]] } };
}

export function applyUndoSwap(state: SortingBoardV2State): { ok: boolean; code?: "NO_SWAP"; state: SortingBoardV2State } {
  if (state.swaps.length === 0) return { ok: false, code: "NO_SWAP", state };
  const [f, t] = state.swaps[state.swaps.length - 1];
  const order = [...state.order];
  [order[f], order[t]] = [order[t], order[f]];
  return { ok: true, state: { order, selected: null, swaps: state.swaps.slice(0, -1) } };
}

/** 排序评估：EMPTY(零交换=还没动手比) → PASS(数值正序) →
 * reversed(整体降序) → dimension_confusion(恰好=视觉字号序) → disordered(其余)。
 * 三 FAIL 态互斥（parser 守卫保证 dimension/reversed/正序三者不同）。 */
export function evaluateSorting(state: SortingBoardV2State, config: SortingBoardV2Config): SortVerdict {
  if (state.swaps.length === 0) return { status: "EMPTY" };
  const cur = JSON.stringify(state.order);
  if (cur === JSON.stringify(targetOrder(config))) return { status: "PASS" };
  if (cur === JSON.stringify(reversedOrder(config))) return { status: "FAIL", error: "reversed" };
  if (cur === JSON.stringify(visualOrder(config))) return { status: "FAIL", error: "dimension_confusion" };
  return { status: "FAIL", error: "disordered" };
}

export function orderValues(state: SortingBoardV2State, config: SortingBoardV2Config): number[] {
  const map = new Map(config.items.map(i => [i.id, i.value] as const));
  return state.order.map(id => map.get(id)!);
}

/** 提交答案=数值顺序拼接整数（如 [1,2,4,7]→1247）。后端标量相等判分。 */
export function sortingAnswer(state: SortingBoardV2State, config: SortingBoardV2Config): number | null {
  if (state.swaps.length === 0) return null;
  return Number(orderValues(state, config).join(""));
}

/** Evidence：排序过程（交换序列）+ 维度命中原料。 */
export function serializeSortingBoardV2(state: SortingBoardV2State, config: SortingBoardV2Config) {
  const verdict = evaluateSorting(state, config);
  return {
    order: state.order,
    order_values: orderValues(state, config),
    swaps: state.swaps,
    swap_count: state.swaps.length,
    answer: sortingAnswer(state, config),
    structure: {
      status: verdict.status,
      error: verdict.status === "FAIL" ? verdict.error : null,
      ordering: true,
    },
  };
}
