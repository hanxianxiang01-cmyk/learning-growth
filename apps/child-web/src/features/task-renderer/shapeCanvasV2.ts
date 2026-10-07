// FE-1425 R13 shape-canvas 纯函数层（B5 模板第十二实例，Batch D 第二题）。
// Gap R13：Semantic=draw/compose/transform；Evaluator=geometry evaluator；
// Evidence=绘制轨迹；Diagnosis=几何属性错误 P0。
//
// 玩法：点阵板依序点顶点 → 首尾自动闭合成多边形。金题=画面积为 target_area
// 的长方形。答案=面积（shoelace，整数）——**解耦第四次运用**：平行四边形
// 面积恰好相等时后端判对，not_right_angle 几何属性原料走 Evidence。
// （交互口径：draw=点顶点、delete=撤点/清空；move/rotate 以点序重建替代——
// 儿童可靠性口径不依赖拖拽，差异记录在底表。）

export type GridPoint = { x: number; y: number };

export type ShapeCanvasV2Config = {
  /** 点阵边长（grid×grid，坐标 0..grid-1） */
  grid: number;
  /** 目标面积（唯一可判对的答案值） */
  targetArea: number;
  /** 本 Gate 支持的目标形状（词表守卫，暂只 rectangle） */
  targetShape: "rectangle";
};

export type ShapeCanvasV2State = {
  /** 绘制轨迹：顶点点击顺序 */
  vertices: GridPoint[];
};

export type GeometryVerdict =
  | { status: "EMPTY" }
  | { status: "PASS" }
  | { status: "FAIL"; error: "vertex_count" | "not_right_angle" | "wrong_size" };

const MAX_VERTICES = 8;

export function parseShapeCanvasConfig(raw: unknown): ShapeCanvasV2Config | null {
  if (!raw || typeof raw !== "object") return null;
  const c = raw as Record<string, unknown>;
  if (typeof c.grid !== "number" || !Number.isInteger(c.grid) || c.grid < 4 || c.grid > 6) return null;
  if (typeof c.target_area !== "number" || !Number.isInteger(c.target_area) || c.target_area < 2 || c.target_area > 20) return null;
  if (c.target_shape !== "rectangle") return null;
  // 面积必须在点阵上可达（最长边 ≤ grid-1 的组合）：2..((grid-1)^2) 内的合数或可分解值
  const maxArea = (c.grid - 1) * (c.grid - 1);
  if (c.target_area > maxArea) return null;
  return { grid: c.grid, targetArea: c.target_area, targetShape: "rectangle" };
}

export function initialShapeCanvasV2State(): ShapeCanvasV2State {
  return { vertices: [] };
}

function samePoint(a: GridPoint, b: GridPoint): boolean {
  return a.x === b.x && a.y === b.y;
}

export function applyAddPoint(
  state: ShapeCanvasV2State,
  config: ShapeCanvasV2Config,
  x: number,
  y: number,
): { ok: boolean; code?: "OUT_OF_RANGE" | "DUPLICATE_POINT" | "MAX_VERTICES"; state: ShapeCanvasV2State } {
  if (!Number.isInteger(x) || !Number.isInteger(y) || x < 0 || y < 0 || x >= config.grid || y >= config.grid) {
    return { ok: false, code: "OUT_OF_RANGE", state };
  }
  const p = { x, y };
  // 闭合点（重复第一个顶点）视为主动收口 → 拒绝重复（自动闭合已存在）
  if (state.vertices.some(v => samePoint(v, p))) return { ok: false, code: "DUPLICATE_POINT", state };
  if (state.vertices.length >= MAX_VERTICES) return { ok: false, code: "MAX_VERTICES", state };
  return { ok: true, state: { vertices: [...state.vertices, p] } };
}

export function applyRemoveLast(state: ShapeCanvasV2State): { ok: boolean; code?: "NO_VERTEX"; state: ShapeCanvasV2State } {
  if (state.vertices.length === 0) return { ok: false, code: "NO_VERTEX", state };
  return { ok: true, state: { vertices: state.vertices.slice(0, -1) } };
}

/** 有向面积×2（shoelace，整数运算免浮点误差）。 */
export function doubledSignedArea(vertices: GridPoint[]): number {
  let sum = 0;
  for (let i = 0; i < vertices.length; i += 1) {
    const a = vertices[i];
    const b = vertices[(i + 1) % vertices.length];
    sum += a.x * b.y - b.x * a.y;
  }
  return sum;
}

/** 面积（绝对值；三角形起才有意义，<3 点视为 0）。 */
export function polygonArea(vertices: GridPoint[]): number {
  if (vertices.length < 3) return 0;
  return Math.abs(doubledSignedArea(vertices)) / 2;
}

/** 各内角是否直角：相邻两边向量点积 ==0（对全部顶点）。返回直角个数。 */
export function countRightAngles(vertices: GridPoint[]): number {
  const n = vertices.length;
  if (n !== 4) return 0;
  let right = 0;
  for (let i = 0; i < n; i += 1) {
    const prev = vertices[(i + n - 1) % n];
    const cur = vertices[i];
    const next = vertices[(i + 1) % n];
    const v1 = { x: prev.x - cur.x, y: prev.y - cur.y };
    const v2 = { x: next.x - cur.x, y: next.y - cur.y };
    if (v1.x * v2.x + v1.y * v2.y === 0) right += 1;
  }
  return right;
}

/** 几何评估：EMPTY(<3 点未成图) → vertex_count(≠4) → not_right_angle(四边形但角不直角)
 * → wrong_size(是长方形但面积不对) → PASS。属性错（形状）优先于尺寸错。 */
export function evaluateShapeCanvas(
  state: ShapeCanvasV2State,
  config: ShapeCanvasV2Config,
): GeometryVerdict {
  const v = state.vertices;
  if (v.length < 3) return { status: "EMPTY" };
  if (v.length !== 4) return { status: "FAIL", error: "vertex_count" };
  if (countRightAngles(v) !== 4) return { status: "FAIL", error: "not_right_angle" };
  if (polygonArea(v) !== config.targetArea) return { status: "FAIL", error: "wrong_size" };
  return { status: "PASS" };
}

/** 提交答案=面积（后端与 expected 标量相等判分）。 */
export function shapeCanvasAnswer(state: ShapeCanvasV2State): number | null {
  if (state.vertices.length < 3) return null;
  return polygonArea(state.vertices);
}

/** Evidence：绘制轨迹（顶点序）+ 几何属性原料。 */
export function serializeShapeCanvasV2(
  state: ShapeCanvasV2State,
  config: ShapeCanvasV2Config,
) {
  const verdict = evaluateShapeCanvas(state, config);
  const v = state.vertices;
  return {
    vertices: v,
    vertex_count: v.length,
    area: v.length >= 3 ? polygonArea(v) : null,
    right_angles: countRightAngles(v),
    answer: shapeCanvasAnswer(state),
    structure: {
      status: verdict.status,
      error: verdict.status === "FAIL" ? verdict.error : null,
      target_shape: config.targetShape,
      target_area: config.targetArea,
    },
  };
}
