/**
 * number-line V2 renderer 纯函数层（FE-1408）。
 *
 * 与 columnArithmetic.ts 同层同风格：state / 动作函数 / serialize 全部纯函数，
 * React 组件（NumberLineV2.tsx）只做装配。数据结构对齐 FE-1405 A5 链
 * E2E 已验证的提交形态：workspaces[0].data.jumps = [{jump_id, from, to}]。
 */

export type NumberLineJump = {
  jump_id: string;
  from: number;
  to: number;
};

export type NumberLineV2State = {
  start: number | null;
  current: number | null;
  jumps: NumberLineJump[];
};

export type NumberLineV2Config = {
  min: number;
  max: number;
  tickStep: number;
  startValue: number | null;
};

export function initialNumberLineV2State(config: NumberLineV2Config): NumberLineV2State {
  return {
    start: config.startValue,
    current: config.startValue,
    jumps: []
  };
}

/** 从刻度值 v 起跳（v 必须是合法刻度且 v ≠ current）。 */
export function applyJump(
  state: NumberLineV2State,
  v: number,
  jumpIdFactory: () => string
): NumberLineV2State {
  if (state.current === null || v === state.current) return state;
  const jump: NumberLineJump = { jump_id: jumpIdFactory(), from: state.current, to: v };
  return {
    ...state,
    current: v,
    jumps: [...state.jumps, jump]
  };
}

/** 终点即答案；未跳步时不给答案（不让孩子用起点 20 空提交碰运气）。 */
export function endpointAnswer(state: NumberLineV2State): number | null {
  if (state.jumps.length === 0) return null;
  return state.current;
}

/** 序列化为 V2 workspace data（对齐 FE-1405 E2E 形态）。 */
export function serializeNumberLineV2(state: NumberLineV2State): Record<string, unknown> {
  return {
    start: state.start,
    end: state.current,
    jumps: state.jumps.map(j => ({ jump_id: j.jump_id, from: j.from, to: j.to }))
  };
}
