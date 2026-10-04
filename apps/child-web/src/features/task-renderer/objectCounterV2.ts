/**
 * object-counter V2 renderer 纯函数层（FE-1414，B5 模板第二个 Vertical Gate）。
 *
 * 与 columnArithmetic.ts / numberLineV2.ts 同层同风格：state / 动作函数 /
 * serialize / 结构判定全部纯函数，React 组件（ObjectCounterV2.tsx）只做装配。
 *
 * 语义（docs/frontend/31 SEM-1410 / Gap R01）：
 * - count：答案 = Σ groups[i].count（唯一来源）
 * - add / remove：指定组增减（COUNT_ADDED / COUNT_REMOVED）；locked 组（题目给定）不可增减
 * - compose：source 并入 target（GROUP_COMPOSED）；source 清零并记录 composed_into/composed_count
 * - decompose：拆 k 个为新组（GROUP_DECOMPOSED），新组继承 symbol
 * - compare：语义附着在增减事件 payload（with_group_id），不新增状态
 *
 * 提交门禁口径（对齐 B5/P0-01：错误答案必须能到后端）：
 * PASS/FAIL → 可提交；PARTIAL/EMPTY → 不可。
 */

export type ObjectCounterGroup = {
  group_id: string;
  label: string;
  count: number;
  symbol: string;
  locked?: boolean;
  /** compose 记录：本组已并入哪个组、并入了多少。 */
  composed_into?: string;
  composed_count?: number;
};

export type ObjectCounterV2State = {
  groups: ObjectCounterGroup[];
};

export type ObjectCounterV2Config = {
  maxTotalCount: number;
};

export type MoveCode =
  | "UNKNOWN_GROUP"
  | "OVER_LIMIT"
  | "EMPTY_GROUP"
  | "SAME_GROUP"
  | "LOCKED_GROUP"
  | "DUPLICATE_GROUP";

export type MoveResult =
  | { ok: true; state: ObjectCounterV2State }
  | { ok: false; code: MoveCode };

export function initialObjectCounterV2State(groups: ObjectCounterGroup[]): ObjectCounterV2State {
  return { groups: groups.map(g => ({ ...g })) };
}

export function total(state: ObjectCounterV2State): number {
  return state.groups.reduce((sum, g) => sum + g.count, 0);
}

/** 答案 = 物体总数；总数 0（空状态）不给答案。 */
export function answerOf(state: ObjectCounterV2State): number | null {
  const n = total(state);
  return n === 0 ? null : n;
}

function findGroup(state: ObjectCounterV2State, groupId: string): ObjectCounterGroup | undefined {
  return state.groups.find(g => g.group_id === groupId);
}

/** add/remove：±delta 指定组；locked 拒绝；remove 不穿 0；总数不超 max。 */
export function applyDelta(
  state: ObjectCounterV2State,
  groupId: string,
  delta: number,
  config: ObjectCounterV2Config
): MoveResult {
  const target = findGroup(state, groupId);
  if (!target) return { ok: false, code: "UNKNOWN_GROUP" };
  if (target.locked) return { ok: false, code: "LOCKED_GROUP" };
  if (target.count + delta < 0) return { ok: false, code: "EMPTY_GROUP" };
  if (total(state) + delta > config.maxTotalCount) return { ok: false, code: "OVER_LIMIT" };
  return {
    ok: true,
    state: {
      groups: state.groups.map(g =>
        g.group_id === groupId ? { ...g, count: g.count + delta } : g
      )
    }
  };
}

/** compose：source 并入 target。locked source 拒绝（题目给定不能被合走）；
 *  locked target 允许（"放进盒子里"正是合起来的动作）。 */
export function applyCompose(
  state: ObjectCounterV2State,
  sourceId: string,
  targetId: string
): MoveResult {
  if (sourceId === targetId) return { ok: false, code: "SAME_GROUP" };
  const source = findGroup(state, sourceId);
  const target = findGroup(state, targetId);
  if (!source || !target) return { ok: false, code: "UNKNOWN_GROUP" };
  if (source.locked) return { ok: false, code: "LOCKED_GROUP" };
  if (source.count === 0) return { ok: false, code: "EMPTY_GROUP" };
  return {
    ok: true,
    state: {
      groups: state.groups.map(g => {
        if (g.group_id === targetId) return { ...g, count: g.count + source.count };
        if (g.group_id === sourceId) {
          return {
            ...g,
            count: 0,
            composed_into: targetId,
            composed_count: (g.composed_count ?? 0) + source.count
          };
        }
        return g;
      })
    }
  };
}

/** decompose：从 groupId 拆 k 个到紧随其后的新组（symbol 继承）。locked 源拒绝。 */
export function applyDecompose(
  state: ObjectCounterV2State,
  groupId: string,
  k: number,
  newGroup: ObjectCounterGroup
): MoveResult {
  const source = findGroup(state, groupId);
  if (!source) return { ok: false, code: "UNKNOWN_GROUP" };
  if (source.locked) return { ok: false, code: "LOCKED_GROUP" };
  if (k <= 0) return { ok: false, code: "EMPTY_GROUP" };
  if (source.count < k) return { ok: false, code: "OVER_LIMIT" };
  if (state.groups.some(g => g.group_id === newGroup.group_id)) {
    return { ok: false, code: "DUPLICATE_GROUP" };
  }
  const idx = state.groups.findIndex(g => g.group_id === groupId);
  const next = state.groups.map(g =>
    g.group_id === groupId ? { ...g, count: g.count - k } : g
  );
  next.splice(idx + 1, 0, { ...newGroup, count: k });
  return { ok: true, state: { groups: next } };
}

/** 序列化为 V2 workspace data（Evidence 形态：组结构 + 总数 + 合并记录）。 */
export function serializeObjectCounterV2(state: ObjectCounterV2State): Record<string, unknown> {
  return {
    groups: state.groups.map(g => ({
      group_id: g.group_id,
      label: g.label,
      count: g.count,
      ...(g.composed_into ? { composed_into: g.composed_into, composed_count: g.composed_count } : {})
    })),
    total: total(state)
  };
}

/**
 * 结构判定（前端即时反馈 Evaluator）。
 * expected 组"有效达成"= count 达标，或先自建后 compose 走（composed_count 计入）。
 * - EMPTY：一个物体都没有
 * - PASS：每个 expected 组有效达成（count + composed_count ≥ min_count）
 * - FAIL：每个 expected 组都有参与（有物体或被合走），但至少一组数量不足
 * - PARTIAL：存在 expected 组完全空置未参与
 */
export type ExpectedGroup = { group_id: string; min_count: number };

function effectiveCount(state: ObjectCounterV2State, groupId: string): number {
  const g = findGroup(state, groupId);
  if (!g) return 0;
  return g.count + (g.composed_count ?? 0);
}

export function evaluateStructure(
  state: ObjectCounterV2State,
  expected: ExpectedGroup[]
): "PASS" | "FAIL" | "PARTIAL" | "EMPTY" {
  if (total(state) === 0 && state.groups.every(g => (g.composed_count ?? 0) === 0)) {
    return "EMPTY";
  }
  const engaged = expected.every(e => effectiveCount(state, e.group_id) >= 1);
  if (!engaged) return "PARTIAL";
  const meets = expected.every(e => effectiveCount(state, e.group_id) >= e.min_count);
  return meets ? "PASS" : "FAIL";
}
