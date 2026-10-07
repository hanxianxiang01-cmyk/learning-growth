// FE-1424 R12 shape-gallery 纯函数层（B5 模板第十一实例，Batch D 起手）。
// Gap R12：Semantic=shape recognition/classification；Evaluator=classification；
// Diagnosis=属性识别错误 P0；Evidence=选择与分类轨迹。
//
// 图形墙选形 → 放进"正方形的家"。答案=家里图形数（可数对但摆错——
// R08 解耦同款：后端按 count 判，attribute_confusion 走 Evidence 诊断原料）。

export type ShapeKind = "square" | "rectangle" | "circle" | "triangle";

export const SHAPE_KIND_LABELS: Record<ShapeKind, string> = {
  square: "正方形",
  rectangle: "长方形",
  circle: "圆形",
  triangle: "三角形",
};

export type GalleryShape = {
  id: string;
  name: string;
  kind: ShapeKind;
  color: string;
};

export type ShapeGalleryV2Config = {
  shapes: GalleryShape[];
  /** 目标"家"的图形种类（教学指令=把这种图形放进去） */
  targetKind: ShapeKind;
};

export type ShapeGalleryV2State = {
  /** 墙上当前选中的图形 id（null=没拿） */
  selected: string | null;
  /** 家里的图形 id 序列（放入顺序=分类轨迹） */
  home: string[];
};

export type ShapeVerdict =
  | { status: "EMPTY" }
  | { status: "PASS" }
  | { status: "FAIL"; error: "attribute_confusion" | "missed" };

const KIND_SET: readonly string[] = ["square", "rectangle", "circle", "triangle"];

export function parseShapeGalleryConfig(raw: unknown): ShapeGalleryV2Config | null {
  if (!raw || typeof raw !== "object") return null;
  const c = raw as Record<string, unknown>;
  if (!Array.isArray(c.shapes) || c.shapes.length < 4 || c.shapes.length > 10) return null;
  const shapes: GalleryShape[] = [];
  const seen = new Set<string>();
  for (const s of c.shapes) {
    if (!s || typeof s !== "object") return null;
    const item = s as Record<string, unknown>;
    if (
      typeof item.id !== "string" || !item.id || seen.has(item.id) ||
      typeof item.name !== "string" || !item.name ||
      typeof item.color !== "string" ||
      typeof item.kind !== "string" || !KIND_SET.includes(item.kind)
    ) return null;
    seen.add(item.id);
    shapes.push({ id: item.id, name: item.name, kind: item.kind as ShapeKind, color: item.color });
  }
  if (typeof c.target_kind !== "string" || !KIND_SET.includes(c.target_kind)) return null;
  const targetKind = c.target_kind as ShapeKind;
  // 目标类必须有成员、且墙上必须有非目标类（否则分类不成立、答案退化为全拿）
  const targetCount = shapes.filter(s => s.kind === targetKind).length;
  if (targetCount < 1 || targetCount === shapes.length) return null;
  return { shapes, targetKind };
}

export function initialShapeGalleryV2State(): ShapeGalleryV2State {
  return { selected: null, home: [] };
}

export function targetShapeIds(config: ShapeGalleryV2Config): string[] {
  return config.shapes.filter(s => s.kind === config.targetKind).map(s => s.id);
}

function findShape(config: ShapeGalleryV2Config, id: string): GalleryShape | undefined {
  return config.shapes.find(s => s.id === id);
}

export function applySelect(
  state: ShapeGalleryV2State,
  config: ShapeGalleryV2Config,
  id: string,
): { ok: boolean; code?: "NO_SUCH_SHAPE" | "IN_HOME"; deselected: boolean; state: ShapeGalleryV2State } {
  const shape = findShape(config, id);
  if (!shape) return { ok: false, code: "NO_SUCH_SHAPE", deselected: false, state };
  if (state.home.includes(id)) return { ok: false, code: "IN_HOME", deselected: false, state };
  // 点已选中=放下（toggle）
  if (state.selected === id) return { ok: true, deselected: true, state: { ...state, selected: null } };
  return { ok: true, deselected: false, state: { ...state, selected: id } };
}

export function applyPlaceHome(
  state: ShapeGalleryV2State,
  config: ShapeGalleryV2Config,
): { ok: boolean; code?: "NO_SELECTION" | "ALREADY_IN_HOME"; state: ShapeGalleryV2State } {
  if (state.selected === null) return { ok: false, code: "NO_SELECTION", state };
  if (state.home.includes(state.selected)) return { ok: false, code: "ALREADY_IN_HOME", state };
  return {
    ok: true,
    state: { selected: null, home: [...state.home, state.selected] },
  };
}

export function applyReturnHome(
  state: ShapeGalleryV2State,
  id: string,
): { ok: boolean; code?: "NOT_IN_HOME"; state: ShapeGalleryV2State } {
  if (!state.home.includes(id)) return { ok: false, code: "NOT_IN_HOME", state };
  return { ok: true, state: { ...state, home: state.home.filter(h => h !== id) } };
}

/** 分类评估：EMPTY(家空) → attribute_confusion(有非目标成员，优先) →
 * missed(成员全对但漏放) → PASS。属性错先于漏放=Diagnosis P0"属性识别错误"权重。 */
export function evaluateShapeGallery(
  state: ShapeGalleryV2State,
  config: ShapeGalleryV2Config,
): ShapeVerdict {
  if (state.home.length === 0) return { status: "EMPTY" };
  const wanted = new Set(targetShapeIds(config));
  const hasWrong = state.home.some(id => !wanted.has(id));
  if (hasWrong) return { status: "FAIL", error: "attribute_confusion" };
  if (state.home.length < wanted.size) return { status: "FAIL", error: "missed" };
  return { status: "PASS" };
}

/** 提交答案=家里图形个数（后端与 expected count 相等判分）。 */
export function shapeGalleryAnswer(state: ShapeGalleryV2State): number | null {
  return state.home.length === 0 ? null : state.home.length;
}

/** Evidence：home 序列=分类轨迹，home_kinds 记录每个成员真实种类（原料）。 */
export function serializeShapeGalleryV2(
  state: ShapeGalleryV2State,
  config: ShapeGalleryV2Config,
) {
  const kindOf = new Map(config.shapes.map(s => [s.id, s.kind] as const));
  const verdict = evaluateShapeGallery(state, config);
  return {
    selected: state.selected,
    home: state.home,
    home_kinds: state.home.map(id => kindOf.get(id) ?? "unknown"),
    answer: shapeGalleryAnswer(state),
    structure: {
      status: verdict.status,
      error: verdict.status === "FAIL" ? verdict.error : null,
      classification: true,
    },
  };
}
