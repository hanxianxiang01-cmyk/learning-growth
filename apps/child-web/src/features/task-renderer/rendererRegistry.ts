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
  | "step_submit";

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
  vertical_gate?: "A5" | "B5" | "D5" | "E4" | "F6";
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
    ["answer_input", "drag", "align", "undo", "reset", "highlight", "focus"],
    { visual_type: "objects", phase: 1 }
  ),
  "bar-model": implemented(
    "bar-model", "BarModel", "v1.3_reuse", "manipulative",
    ["answer_input", "resize", "undo", "reset", "highlight", "focus"],
    { visual_type: "bar-model", phase: 1 }
  ),
  "number-line": implemented(
    "number-line", "NumberLine", "v1.3_reuse", "manipulative",
    ["answer_input", "jump", "undo", "reset", "highlight", "focus"],
    { visual_type: "number-line", phase: 1, vertical_gate: "A5" }
  ),
  "number-input": implemented(
    "number-input", "NumberInput", "base_ui", "number",
    ["answer_input"], { phase: 1 }
  ),

  "choice-grid": planned("choice-grid", "ChoiceGrid", 4, ["answer_input"]),
  "place-value": planned("place-value", "PlaceValue", 1, ["answer_input", "highlight", "focus"]),
  "ten-frame": planned("ten-frame", "TenFrame", 1, ["drag", "answer_input", "undo", "reset"]),
  "column-arithmetic": implementedV2(
    "column-arithmetic", "ColumnArithmetic", 1,
    ["input_digit", "place_carry", "edit_carry", "step_submit", "undo", "reset"],
    { vertical_gate: "B5" }
  ),
  "array-board": planned("array-board", "ArrayBoard", 1, ["drag", "resize", "answer_input", "undo", "reset"]),
  "grouping-board": planned("grouping-board", "GroupingBoard", 1, ["drag", "answer_input", "undo", "reset"]),
  "formula-board": planned("formula-board", "FormulaBoard", 1, ["answer_input", "highlight", "focus"]),
  "estimation-canvas": planned("estimation-canvas", "EstimationCanvas", 1, ["drag", "answer_input", "undo", "reset"]),
  "shape-gallery": planned("shape-gallery", "ShapeGallery", 3, ["highlight", "focus"]),
  "shape-canvas": planned(
    "shape-canvas", "ShapeCanvas", 3,
    ["drag", "resize", "undo", "reset", "highlight", "focus"],
    { vertical_gate: "D5" }
  ),
  "sorting-board": planned("sorting-board", "SortingBoard", 2, ["drag", "undo", "reset"]),
  "direction-grid": planned("direction-grid", "DirectionGrid", 4, ["drag", "answer_input", "undo", "reset"]),
  "ruler": planned(
    "ruler", "Ruler", 4,
    ["drag", "answer_input", "undo", "reset"],
    { vertical_gate: "E4" }
  ),
  "clock": planned("clock", "Clock", 4, ["drag", "answer_input", "undo", "reset"]),
  "timeline": planned("timeline", "Timeline", 4, ["drag", "answer_input", "undo", "reset"]),
  "money-board": planned("money-board", "MoneyBoard", 4, ["drag", "answer_input", "undo", "reset"]),
  "data-table": planned(
    "data-table", "DataTable", 2,
    ["answer_input", "highlight", "focus", "undo", "reset"],
    { vertical_gate: "F6" }
  ),
  "pictograph": planned("pictograph", "Pictograph", 2, ["answer_input", "highlight", "focus"]),
  "pattern-board": planned("pattern-board", "PatternBoard", 2, ["drag", "answer_input", "undo", "reset"]),

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
