// FE-1427 R15 direction-grid 纯函数层（B5 模板第十四实例，Batch D 收官）。
// Gap R15：Semantic=position/direction/route/movement；Evaluator=route evaluator；
// Evidence=移动序列；Diagnosis=**方向/位置关系错误** P0。
//
// 玩法：小标记站在起点格，按题面走到目标格——点与脚下**相邻**（上下左右一步）
// 的格子就挪过去（点对角/隔格拒绝）。走过的路一格一格记下来（steps）。
// 答案=终点格编码 row*cols+col（组件自动填，后端标量相等判分，不动冻结链）。
//
// 分诊（route evaluator，判定顺序 EMPTY → PASS → reversed → wrong_position）：
//   PASS  end=target；路线长于最短路 → detour=true 原料留痕（解耦第六次运用，
//         到没走到=后端判、走得绕不绕=Evidence 说——R08 形态）
//   FAIL  direction_reversed  终点=位移反转 (2·sr−tr, 2·sc−tc)——"完全往反方向走"
//         （Diagnosis P0"方向错误"精确靶；parser 守卫反转点必须仍在盘内，否则靶不可达）
//   FAIL  wrong_position      其余未到终点（附距目标曼哈顿距离原料）

export type GridCell = { r: number; c: number };

export type DirectionGridV2Config = {
  rows: number;
  cols: number;
  start: GridCell;
  target: GridCell;
};

export type DirectionGridV2State = {
  /** 走过的格序列（含起点），最后一步=脚下 */
  steps: GridCell[];
};

export type RouteVerdict =
  | { status: "EMPTY" }
  | { status: "PASS"; detour: boolean }
  | { status: "FAIL"; error: "direction_reversed" | "wrong_position"; distance_to_target: number };

function cellKey(cell: GridCell): string {
  return `${cell.r},${cell.c}`;
}

export function parseDirectionConfig(raw: unknown): DirectionGridV2Config | null {
  if (!raw || typeof raw !== "object") return null;
  const c = raw as Record<string, unknown>;
  if (typeof c.rows !== "number" || !Number.isInteger(c.rows) || c.rows < 3 || c.rows > 6) return null;
  if (typeof c.cols !== "number" || !Number.isInteger(c.cols) || c.cols < 3 || c.cols > 6) return null;
  const rows = c.rows as number;
  const cols = c.cols as number;
  const read = (v: unknown): GridCell | null => {
    let r: unknown;
    let col: unknown;
    if (Array.isArray(v) && v.length === 2) {
      [r, col] = v as unknown[];
    } else if (v && typeof v === "object") {
      // 亦接受 {r,c} 对象形态（金题 seed 即此式；两种形态同一值域守卫）
      const o = v as Record<string, unknown>;
      r = o.r;
      col = o.c;
    } else {
      return null;
    }
    if (typeof r !== "number" || typeof col !== "number") return null;
    if (!Number.isInteger(r) || !Number.isInteger(col)) return null;
    if (r < 0 || r >= rows || col < 0 || col >= cols) return null;
    return { r, c: col };
  };
  const start = read(c.start);
  const target = read(c.target);
  if (!start || !target) return null;
  if (cellKey(start) === cellKey(target)) return null; // 起点=终点：题已做完
  const dr = target.r - start.r;
  const dc = target.c - start.c;
  // 守卫：行列位移都非零（纯直线路线没有"转向"教学点，且反走靶退化为回头路）
  if (dr === 0 || dc === 0) return null;
  // 守卫：位移反转点 (sr-dr, sc-dc) 仍在盘内——否则 direction_reversed 靶永远打不中，
  // 分诊名存实亡（对齐 R14"三参考序互斥守卫"精神：每个 FAIL 态必须有可达靶）
  if (start.r - dr < 0 || start.r - dr >= c.rows) return null;
  if (start.c - dc < 0 || start.c - dc >= c.cols) return null;
  return { rows: c.rows, cols: c.cols, start, target };
}

export function initialDirectionV2State(config: DirectionGridV2Config): DirectionGridV2State {
  return { steps: [{ ...config.start }] };
}

export function currentCell(state: DirectionGridV2State): GridCell {
  return state.steps[state.steps.length - 1];
}

function isAdjacent(a: GridCell, b: GridCell): boolean {
  return Math.abs(a.r - b.r) + Math.abs(a.c - b.c) === 1;
}

/** 点格移动：仅接受与脚下相邻的格。拒绝码给组件层做提示（事件不入库）。 */
export function applyMoveTo(
  state: DirectionGridV2State,
  config: DirectionGridV2Config,
  cell: GridCell
): { ok: boolean; code?: "SAME_CELL" | "NON_ADJACENT" | "NO_SUCH_CELL"; state: DirectionGridV2State } {
  if (cell.r < 0 || cell.r >= config.rows || cell.c < 0 || cell.c >= config.cols) {
    return { ok: false, code: "NO_SUCH_CELL", state };
  }
  const cur = currentCell(state);
  if (cellKey(cell) === cellKey(cur)) return { ok: false, code: "SAME_CELL", state };
  if (!isAdjacent(cur, cell)) return { ok: false, code: "NON_ADJACENT", state };
  return { ok: true, state: { steps: [...state.steps, { ...cell }] } };
}

/** 退最后一步（起点不可退光——steps 至少保留起点）。 */
export function applyUndoStep(state: DirectionGridV2State): { ok: boolean; code?: "AT_START"; state: DirectionGridV2State } {
  if (state.steps.length <= 1) return { ok: false, code: "AT_START", state };
  return { ok: true, state: { steps: state.steps.slice(0, -1) } };
}

/** 位移反转终点：走反方向应落到的格子。 */
function reversedEnd(config: DirectionGridV2Config): GridCell {
  const dr = config.target.r - config.start.r;
  const dc = config.target.c - config.start.c;
  return { r: config.start.r - dr, c: config.start.c - dc };
}

/** 路线评估：EMPTY(一步没挪) → PASS(end=target，长于最短路=detour) →
 * direction_reversed(恰好=反走终点) → wrong_position(其余)。
 * parser 守卫保证 reversed 终点≠target（位移非零）且可达（在盘内）。 */
export function evaluateRoute(state: DirectionGridV2State, config: DirectionGridV2Config): RouteVerdict {
  if (state.steps.length <= 1) return { status: "EMPTY" };
  const end = currentCell(state);
  const manhattan = (a: GridCell, b: GridCell) => Math.abs(a.r - b.r) + Math.abs(a.c - b.c);
  if (cellKey(end) === cellKey(config.target)) {
    const shortest = manhattan(config.start, config.target);
    return { status: "PASS", detour: state.steps.length - 1 > shortest };
  }
  if (cellKey(end) === cellKey(reversedEnd(config))) {
    return { status: "FAIL", error: "direction_reversed", distance_to_target: manhattan(end, config.target) };
  }
  return { status: "FAIL", error: "wrong_position", distance_to_target: manhattan(end, config.target) };
}

/** 提交答案=终点格编码（行主序，0 起）。组件自动写入 response.answer。 */
export function directionGridAnswer(state: DirectionGridV2State, config: DirectionGridV2Config): number | null {
  if (state.steps.length <= 1) return null;
  const end = currentCell(state);
  return end.r * config.cols + end.c;
}

/** Evidence：移动序列（Gap"movement sequence"）+ 方向串 + 转向数 + 分诊原料。 */
export function serializeDirectionGridV2(state: DirectionGridV2State, config: DirectionGridV2Config) {
  const verdict = evaluateRoute(state, config);
  const dirs = state.steps.slice(1).map((cell, i) => {
    const prev = state.steps[i];
    if (cell.r < prev.r) return "up";
    if (cell.r > prev.r) return "down";
    if (cell.c < prev.c) return "left";
    return "right";
  });
  const turns = dirs.reduce((n, d, i) => (i > 0 && dirs[i - 1] !== d ? n + 1 : n), 0);
  const end = currentCell(state);
  return {
    path: state.steps.map(cellKey),
    directions: dirs,
    move_count: dirs.length,
    turns,
    current: { r: end.r, c: end.c },
    target: { r: config.target.r, c: config.target.c },
    answer: directionGridAnswer(state, config),
    structure: {
      status: verdict.status,
      error: verdict.status === "FAIL" ? verdict.error : null,
      detour: verdict.status === "PASS" ? verdict.detour : null,
      distance_to_target: verdict.status === "FAIL" ? verdict.distance_to_target : 0,
      reached: cellKey(end) === cellKey(config.target),
    },
  };
}
