import type { TaskUiSchema, V2TaskUiSchema } from "@/src/lib/api/contracts";

// Renderer 协议事实源：docs/frontend/28_RENDERER_REGISTRY_CONTRACT.md
// 23 个协议 renderer + 前端专用 unsupported 哨兵。
// planned renderer 可以注册，但不得被 Task Router / Renderer Runtime 当作可渲染实现。

export type RendererProtocolId =
  | "object-counter"
  | "bar-model"
  | "number-line"
  | "number-input"
  | "choice-grid"
  | "place-value"
  | "ten-frame"
  | "column-arithmetic"
  | "array-board"
  | "grouping-board"
  | "formula-board"
  | "estimation-canvas"
  | "shape-gallery"
  | "shape-canvas"
  | "sorting-board"
  | "direction-grid"
  | "ruler"
  | "clock"
  | "timeline"
  | "money-board"
  | "data-table"
  | "pictograph"
  | "pattern-board";

export type RendererId = RendererProtocolId | "unsupported";

export type RendererStatus = "implemented" | "planned";

/**
 * V1.4 Release Scope（FE-1417，交付方 docs/frontend/32 口径）：
 * 协议 Registry 仍保留 23 个 ID（冻结枚举不缩——28 号契约治理），
 * 但发布验收 / QA 看板只计算这 19 个。被剔除的 4 个（choice-grid /
 * data-table / pictograph / timeline）组件保留运行，Gate 顺延。
 */
export const V2_RELEASE_RENDERER_IDS = [
  "object-counter", "bar-model", "number-line", "number-input",
  "column-arithmetic", "place-value", "ten-frame", "array-board",
  "grouping-board", "formula-board", "estimation-canvas", "shape-gallery",
  "shape-canvas", "sorting-board", "direction-grid", "ruler", "clock",
  "money-board", "pattern-board"
] as const satisfies readonly RendererProtocolId[];

export type V2ReleaseRendererId = typeof V2_RELEASE_RENDERER_IDS[number];

export function isV2ReleaseRenderer(id: RendererId): id is V2ReleaseRendererId {
  return (V2_RELEASE_RENDERER_IDS as readonly string[]).includes(id);
}

export type InteractionCapability =
  | "answer_input"
  | "drag"
  | "align"
  | "resize"
  | "jump"
  | "undo"
  | "reset"
  | "highlight"
  | "focus"
  | "input_digit"
  | "place_carry"
  | "edit_carry"
  | "step_submit"
  | "add_object"
  | "remove_object"
  | "compose_groups"
  | "decompose_group"
  | "fill"
  | "grouping"
  | "select"
  | "draw"
  | "rotate"
  | "sort"
  | "set_time"
  | "set_value"
  | "select_symbol";

/**
 * FE-1414：能力注册名单（唯一事实源）。
 * 组件 capabilities ⊆ 名单；seed 校验（seed_content.py）与 getInteractionCapabilities
 * 均引用此名单，杜绝"能力被静默过滤、组件行为失去契约依据"的漂移。
 */
export const KNOWN_CAPABILITY_IDS: readonly string[] = [
  "answer_input", "drag", "align", "resize", "jump", "undo", "reset",
  "highlight", "focus", "input_digit", "place_carry", "edit_carry", "step_submit",
  "add_object", "remove_object", "compose_groups", "decompose_group",
  "fill", "grouping", "select", "draw", "rotate", "sort", "set_time", "set_value", "select_symbol",
];

export type RendererDescriptor = {
  renderer_id: RendererId;
  renderer_name: string;
  renderer_version: "1.0";
  source: "v1.3_reuse" | "base_ui" | "v1.4_new" | "runtime";
  status: RendererStatus;
  schema_version: "1.0" | "2.0";
  supported_kind: "number" | "manipulative" | "unsupported" | "v2";
  visual_type?: "objects" | "bar-model" | "number-line";
  interaction_capabilities: InteractionCapability[];
  input_contract: string;
  state_contract: string;
  interaction_contract: string;
  response_contract: string;
  evidence_capability: boolean;
  diagnosis_capability: boolean;
  serialize_contract: string;
  theme_contract: "shared-semantic-tokens";
  phase: 1 | 2 | 3 | 4;
  vertical_gate?: "A5" | "B5" | "D5" | "E4" | "F6" | "R01" | "R02" | "R04" | "R06" | "R07" | "R10";
};

const implemented = (
  renderer_id: RendererId,
  renderer_name: string,
  source: RendererDescriptor["source"],
  supported_kind: RendererDescriptor["supported_kind"],
  interaction_capabilities: InteractionCapability[],
  extra: Partial<RendererDescriptor> = {}
): RendererDescriptor => ({
  renderer_id,
  renderer_name,
  renderer_version: "1.0",
  source,
  status: "implemented",
  schema_version: renderer_id === "number-input" ? "1.0" : "1.0",
  supported_kind,
  interaction_capabilities,
  input_contract: "TaskUISchema",
  state_contract: "WorkspaceState",
  interaction_contract: "Action + Reducer",
  response_contract: "ResponseSchema",
  evidence_capability: true,
  diagnosis_capability: true,
  serialize_contract: "RendererState → ResponseSchema",
  theme_contract: "shared-semantic-tokens",
  phase: 1,
  ...extra
});

const implementedV2 = (
  renderer_id: RendererProtocolId,
  renderer_name: string,
  phase: RendererDescriptor["phase"],
  interaction_capabilities: InteractionCapability[],
  extra: Partial<RendererDescriptor> = {}
): RendererDescriptor => ({
  renderer_id,
  renderer_name,
  renderer_version: "1.0",
  source: "v1.4_new",
  status: "implemented",
  schema_version: "2.0",
  supported_kind: "v2",
  interaction_capabilities,
  input_contract: "TaskUISchema V2 + mode-specific config",
  state_contract: "Renderer-specific WorkspaceState",
  interaction_contract: "Action + Reducer",
  response_contract: "MathResponse V2 workspace.data",
  evidence_capability: true,
  diagnosis_capability: true,
  serialize_contract: "RendererState → MathResponse V2 workspace.data",
  theme_contract: "shared-semantic-tokens",
  phase,
  ...extra
});

const planned = (
  renderer_id: RendererProtocolId,
  renderer_name: string,
  phase: RendererDescriptor["phase"],
  interaction_capabilities: InteractionCapability[],
  extra: Partial<RendererDescriptor> = {}
): RendererDescriptor => ({
  renderer_id,
  renderer_name,
  renderer_version: "1.0",
  source: "v1.4_new",
  status: "planned",
  schema_version: "2.0",
  supported_kind: "v2",
  interaction_capabilities,
  input_contract: "TaskUISchema V2 + mode-specific config",
  state_contract: "Renderer-specific WorkspaceState",
  interaction_contract: "Action + Reducer",
  response_contract: "MathResponse V2 workspace.data",
  evidence_capability: true,
  diagnosis_capability: true,
  serialize_contract: "RendererState → MathResponse V2 workspace.data",
  theme_contract: "shared-semantic-tokens",
  phase,
  ...extra
});

export const RENDERER_REGISTRY: Record<RendererId, RendererDescriptor> = {
  "object-counter": implemented(
    "object-counter", "ObjectCounter", "v1.3_reuse", "manipulative",
    ["answer_input", "drag", "align", "undo", "reset", "highlight", "focus",
      "add_object", "remove_object", "compose_groups", "decompose_group"],
    { visual_type: "objects", phase: 1, vertical_gate: "R01" }
  ),
  "bar-model": implemented(
    "bar-model", "BarModel", "v1.3_reuse", "manipulative",
    ["answer_input", "resize", "undo", "reset", "highlight", "focus", "add_object", "remove_object"],
    { visual_type: "bar-model", phase: 1, vertical_gate: "R02" }
  ),
  "number-line": implemented(
    "number-line", "NumberLine", "v1.3_reuse", "manipulative",
    ["answer_input", "jump", "undo", "reset", "highlight", "focus"],
    { visual_type: "number-line", phase: 1, vertical_gate: "A5" }
  ),
  "number-input": implemented(
    "number-input", "NumberInput", "base_ui", "number",
    ["answer_input"], { phase: 1, vertical_gate: "R04" }
  ),

  "choice-grid": implementedV2("choice-grid", "ChoiceGrid", 1, ["answer_input", "reset"], { vertical_gate: undefined }),
  "place-value": implementedV2("place-value", "PlaceValue", 1, ["answer_input", "highlight", "focus", "reset", "undo", "select"], { vertical_gate: "R06" }),
  "ten-frame": implementedV2("ten-frame", "TenFrame", 1, ["fill", "grouping", "drag", "answer_input", "undo", "reset"], { vertical_gate: "R07" }),
  "column-arithmetic": implementedV2(
    "column-arithmetic", "ColumnArithmetic", 1,
    ["input_digit", "place_carry", "edit_carry", "step_submit", "undo", "reset"],
    { vertical_gate: "B5" }
  ),
  "array-board": implementedV2("array-board", "ArrayBoard", 1, ["drag", "resize", "answer_input", "undo", "reset"]),
  "grouping-board": implementedV2("grouping-board", "GroupingBoard", 1, ["drag", "answer_input", "undo", "reset"]),
  "formula-board": implementedV2("formula-board", "FormulaBoard", 1, ["answer_input", "highlight", "focus", "reset", "undo"], { vertical_gate: "R10" }),
  "estimation-canvas": implementedV2("estimation-canvas", "EstimationCanvas", 1, ["drag", "answer_input", "undo", "reset"]),
  "shape-gallery": implementedV2("shape-gallery", "ShapeGallery", 3, ["highlight", "focus", "answer_input", "reset"]),
  "shape-canvas": implementedV2(
    "shape-canvas", "ShapeCanvas", 3,
    ["drag", "resize", "undo", "reset", "highlight", "focus"],
    { vertical_gate: "D5" }
  ),
  "sorting-board": implementedV2("sorting-board", "SortingBoard", 2, ["drag", "undo", "reset"]),
  "direction-grid": implementedV2("direction-grid", "DirectionGrid", 4, ["drag", "answer_input", "undo", "reset"]),
  "ruler": implementedV2(
    "ruler", "Ruler", 4,
    ["drag", "answer_input", "undo", "reset"],
    { vertical_gate: "E4" }
  ),
  "clock": implementedV2("clock", "Clock", 4, ["drag", "answer_input", "undo", "reset"]),
  "timeline": implementedV2("timeline", "Timeline", 4, ["drag", "answer_input", "undo", "reset"]),
  "money-board": implementedV2("money-board", "MoneyBoard", 4, ["drag", "answer_input", "undo", "reset"]),
  "data-table": implementedV2(
    "data-table", "DataTable", 2,
    ["answer_input", "highlight", "focus", "undo", "reset"],
    { vertical_gate: "F6" }
  ),
  "pictograph": implementedV2("pictograph", "Pictograph", 2, ["answer_input", "highlight", "focus", "reset"]),
  "pattern-board": implementedV2("pattern-board", "PatternBoard", 2, ["drag", "answer_input", "undo", "reset"]),

  unsupported: {
    renderer_id: "unsupported",
    renderer_name: "Unsupported",
    renderer_version: "1.0",
    source: "runtime",
    status: "implemented",
    schema_version: "1.0",
    supported_kind: "unsupported",
    interaction_capabilities: [],
    input_contract: "none",
    state_contract: "none",
    interaction_contract: "safe fallback",
    response_contract: "none",
    evidence_capability: false,
    diagnosis_capability: false,
    serialize_contract: "none",
    theme_contract: "shared-semantic-tokens",
    phase: 1
  }
};

export const IMPLEMENTED_RENDERERS = Object.values(RENDERER_REGISTRY)
  .filter(item => item.status === "implemented" && item.renderer_id !== "unsupported")
  .map(item => item.renderer_id as RendererProtocolId);

export function isImplementedRenderer(rendererId: RendererId): rendererId is RendererProtocolId {
  return rendererId !== "unsupported" && RENDERER_REGISTRY[rendererId].status === "implemented";
}

export function resolveRendererId(schema: TaskUiSchema | V2TaskUiSchema): RendererId {
  if (schema.schema_version === "2.0") {
    return schema.workspaces[0]?.renderer ?? "unsupported";
  }

  const declared = schema.renderer_id;
  if (declared) {
    return declared in RENDERER_REGISTRY
      ? (declared as RendererId)
      : "unsupported";
  }

  if (schema.kind === "number") return "number-input";
  if (schema.kind === "unsupported") return "unsupported";

  switch (schema.visual.type) {
    case "objects":
      return "object-counter";
    case "bar-model":
      return "bar-model";
    case "number-line":
      return "number-line";
    default:
      return "unsupported";
  }
}

export function getRendererDescriptorById(rendererId: RendererId): RendererDescriptor {
  return RENDERER_REGISTRY[rendererId];
}

export function getInteractionCapabilities(schema: TaskUiSchema | V2TaskUiSchema): InteractionCapability[] {
  if (schema.schema_version === "2.0") {
    const workspace = schema.workspaces[0];
    if (!workspace) return [];
    const descriptor = RENDERER_REGISTRY[workspace.renderer];
    return workspace.capabilities.filter(value =>
      descriptor?.interaction_capabilities.includes(value as InteractionCapability)
    ) as InteractionCapability[];
  }

  if (Array.isArray(schema.interaction_capabilities)) {
    return schema.interaction_capabilities.filter((value): value is InteractionCapability =>
      Object.values(RENDERER_REGISTRY).some(item =>
        item.interaction_capabilities.includes(value as InteractionCapability)
      )
    );
  }
  return getRendererDescriptor(schema).interaction_capabilities;
}

export function getRendererDescriptor(schema: TaskUiSchema | V2TaskUiSchema): RendererDescriptor {
  return RENDERER_REGISTRY[resolveRendererId(schema)];
}
