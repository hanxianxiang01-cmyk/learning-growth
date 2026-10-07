/**
 * grouping-board V2 renderer 纯函数层（FE-1422，B5 模板第九实例 / Gap R09）。
 *
 * 语义（Gap R09）：grouping / equal groups / remainder——**平均分物**：
 * items 个东西要发到 targetGroups 个组里，每组一样多。与基座"自动均分"根本不同：
 * 孩子主动建组（group）、逐组发物（add）、收物（remove）、拆空组（split/解散）。
 *
 * group structure evaluator（R09 Evaluator P0），错误二分类各有靶（Diagnosis P0
 * "分组数量/每组数量错误"原料）：
 *   count   —— 组数 ≠ 目标组数（要分给 3 人却分了 2/4 堆）；
 *   unequal —— 组数对但各组不一样多（没理解"平均分"）；
 *   PASS    —— 组数对 + 各组相等 + 物品全发完（答案=每组个数）。
 * EMPTY：池子里还有没发出去的糖（分完才是一个成立的"答案"；P0-01 拦截提交）。
 *
 * 除法场景 transpose 不适用（4人分3个≠3人分4个——题意由 targetGroups 钉死），
 * 故分类只此两支。remainder 变式（12 分 5 组不尽）本 Gate 金题不配，parser
 * 已放行 items%target!=0 的 config 形态——组数对+发完但必不均 → 恒 unequal，
 * 数学上自洽（12 无法均分成 5 组，孩子怎么摆都暴露概念缺口，属内容线后续）。
 *
 * Evidence（Gap："分组过程"）：GROUP_CREATED/REMOVED + ITEM_ADDED/REMOVED 事件链。
 */

export type GroupingBoardV2Config = {
  items: number;
  targetGroups: number;
  maxGroups: number;
};

export type GroupingBoardV2State = {
  /** 每组已发到的个数（数组长度=当前组数）。 */
  groups: number[];
  /** 池子里还没发出去的物品数。 */
  pool: number;
};

export type GroupingVerdict = {
  status: "EMPTY" | "FAIL" | "PASS";
  error: "count" | "unequal" | null;
};

export function parseGroupingConfig(raw: Record<string, unknown>): GroupingBoardV2Config | null {
  const items = Number(raw.items);
  const targetGroups = Number(raw.target_groups);
  if (
    !Number.isInteger(items) || !Number.isInteger(targetGroups) ||
    items < 2 || items > 20 || targetGroups < 2 || targetGroups > items
  ) {
    return null;
  }
  const maxGroups = Number(raw.max_groups);
  return {
    items,
    targetGroups,
    maxGroups: Number.isInteger(maxGroups) && maxGroups >= targetGroups && maxGroups <= items ? maxGroups : items
  };
}

export function initialGroupingV2State(config: GroupingBoardV2Config): GroupingBoardV2State {
  return { groups: [], pool: config.items };
}

/** 新建一组（需池里有物可分？否——空组合法，孩子可以先圈人再发糖）。 */
export function applyAddGroup(
  state: GroupingBoardV2State,
  config: GroupingBoardV2Config
): { ok: true; state: GroupingBoardV2State } | { ok: false; code: "MAX_GROUPS" } {
  if (state.groups.length >= config.maxGroups) return { ok: false, code: "MAX_GROUPS" };
  return { ok: true, state: { ...state, groups: [...state.groups, 0] } };
}

/** 解散一个组（仅空组可拆——有糖的组拆了糖要先收回，防丢物）。 */
export function applyRemoveGroup(
  state: GroupingBoardV2State,
  j: number
): { ok: true; state: GroupingBoardV2State } | { ok: false; code: "NOT_EMPTY_GROUP" | "NO_SUCH_GROUP" } {
  const size = state.groups[j];
  if (size === undefined) return { ok: false, code: "NO_SUCH_GROUP" };
  if (size > 0) return { ok: false, code: "NOT_EMPTY_GROUP" };
  return { ok: true, state: { ...state, groups: state.groups.filter((_, i) => i !== j) } };
}

/** 给第 j 组发一个（池空拒绝）。 */
export function applyAddItem(
  state: GroupingBoardV2State,
  j: number
): { ok: true; state: GroupingBoardV2State } | { ok: false; code: "POOL_EMPTY" | "NO_SUCH_GROUP" } {
  if (state.groups[j] === undefined) return { ok: false, code: "NO_SUCH_GROUP" };
  if (state.pool === 0) return { ok: false, code: "POOL_EMPTY" };
  const groups = state.groups.map((g, i) => (i === j ? g + 1 : g));
  return { ok: true, state: { groups, pool: state.pool - 1 } };
}

/** 从第 j 组收回一个到池子。 */
export function applyRemoveItem(
  state: GroupingBoardV2State,
  j: number
): { ok: true; state: GroupingBoardV2State } | { ok: false; code: "GROUP_EMPTY" | "NO_SUCH_GROUP" } {
  const size = state.groups[j];
  if (size === undefined) return { ok: false, code: "NO_SUCH_GROUP" };
  if (size === 0) return { ok: false, code: "GROUP_EMPTY" };
  const groups = state.groups.map((g, i) => (i === j ? g - 1 : g));
  return { ok: true, state: { groups, pool: state.pool + 1 } };
}

/**
 * group structure evaluator：EMPTY（没发完/一组没建）→ count（组数错）→
 * unequal（每组数量不等）→ PASS。
 */
export function evaluateGrouping(
  state: GroupingBoardV2State,
  config: GroupingBoardV2Config
): GroupingVerdict {
  if (state.groups.length === 0 || state.pool > 0) return { status: "EMPTY", error: null };
  if (state.groups.length !== config.targetGroups) return { status: "FAIL", error: "count" };
  const first = state.groups[0];
  if (state.groups.some(g => g !== first)) return { status: "FAIL", error: "unequal" };
  return { status: "PASS", error: null };
}

/** 答案=每组个数（仅在发完时有意义；EMPTY 提交被组件拦截）。 */
export function groupingAnswer(state: GroupingBoardV2State): number | null {
  if (state.groups.length === 0 || state.pool > 0) return null;
  return state.groups[0];
}

/** Evidence：各组大小+池余+答案+结构判定（count/unequal 原料）。 */
export function serializeGroupingBoardV2(
  state: GroupingBoardV2State,
  config: GroupingBoardV2Config
): Record<string, unknown> {
  const verdict = evaluateGrouping(state, config);
  return {
    groups: [...state.groups],
    pool_remaining: state.pool,
    answer: groupingAnswer(state),
    target_groups: config.targetGroups,
    items: config.items,
    structure:
      verdict.status === "EMPTY"
        ? null
        : { status: verdict.status, error: verdict.error, equal_groups: true }
  };
}
