import type { TaskUiSchema } from "@/src/lib/api/contracts";

export type RendererId =
  | "number-input"
  | "object-counter"
  | "bar-model"
  | "number-line"
  | "unsupported";

export type InteractionCapability =
  | "answer_input"
  | "drag"
  | "align"
  | "resize"
  | "jump"
  | "undo"
  | "reset"
  | "highlight"
  | "focus";

export type RendererDescriptor = {
  renderer_id: RendererId;
  schema_version: "1.0";
  supported_kind: TaskUiSchema["kind"];
  visual_type?: "objects" | "bar-model" | "number-line";
  interaction_capabilities: InteractionCapability[];
};

export const RENDERER_REGISTRY: Record<RendererId, RendererDescriptor> = {
  "number-input": {
    renderer_id: "number-input",
    schema_version: "1.0",
    supported_kind: "number",
    interaction_capabilities: ["answer_input"]
  },
  "object-counter": {
    renderer_id: "object-counter",
    schema_version: "1.0",
    supported_kind: "manipulative",
    visual_type: "objects",
    interaction_capabilities: ["answer_input", "drag", "align", "undo", "reset", "highlight", "focus"]
  },
  "bar-model": {
    renderer_id: "bar-model",
    schema_version: "1.0",
    supported_kind: "manipulative",
    visual_type: "bar-model",
    interaction_capabilities: ["answer_input", "resize", "undo", "reset", "highlight", "focus"]
  },
  "number-line": {
    renderer_id: "number-line",
    schema_version: "1.0",
    supported_kind: "manipulative",
    visual_type: "number-line",
    interaction_capabilities: ["answer_input", "jump", "undo", "reset", "highlight", "focus"]
  },
  unsupported: {
    renderer_id: "unsupported",
    schema_version: "1.0",
    supported_kind: "unsupported",
    interaction_capabilities: []
  }
};

export function resolveRendererId(schema: TaskUiSchema): RendererId {
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

export function getInteractionCapabilities(schema: TaskUiSchema): InteractionCapability[] {
  if (Array.isArray(schema.interaction_capabilities)) {
    return schema.interaction_capabilities.filter((value): value is InteractionCapability =>
      Object.values(RENDERER_REGISTRY).some(item => item.interaction_capabilities.includes(value as InteractionCapability))
    );
  }
  return getRendererDescriptor(schema).interaction_capabilities;
}

export function getRendererDescriptor(schema: TaskUiSchema) {
  return RENDERER_REGISTRY[resolveRendererId(schema)];
}
