import type {
  BarModelVisualSchema,
  ManipulativeTaskUiSchema,
  NumberLineVisualSchema,
  ObjectCounterVisualSchema,
  TaskUiSchema,
  V2TaskUiSchema,
  WorkspaceTool
} from "./contracts";

type Dict = Record<string, unknown>;

const asDict = (value: unknown): Dict =>
  value && typeof value === "object" && !Array.isArray(value)
    ? (value as Dict)
    : {};

const asString = (value: unknown, fallback = "") =>
  typeof value === "string" ? value : fallback;

const asNumber = (value: unknown, fallback = 0) =>
  typeof value === "number" && Number.isFinite(value)
    ? value
    : typeof value === "string" && Number.isFinite(Number(value))
      ? Number(value)
      : fallback;

const defaultResponseSchema = {
  type: "structured" as const,
  answer_type: "number" as const,
  representation_required: false
};

function normalizeResponseSchema(value: unknown, representationRequired: boolean) {
  const raw = asDict(value);
  const allowed = Array.isArray(raw.allowed_representation_types)
    ? raw.allowed_representation_types.filter((v): v is "object-counter" | "bar-model" | "number-line" =>
        v === "object-counter" || v === "bar-model" || v === "number-line"
      )
    : undefined;
  return {
    type: "structured" as const,
    answer_type: raw.answer_type === "text" ? ("text" as const) : ("number" as const),
    representation_required:
      typeof raw.representation_required === "boolean"
        ? raw.representation_required
        : representationRequired,
    allowed_representation_types: allowed
  };
}

const allowedTools = new Set(["move", "align", "resize", "jump", "undo", "reset"]);
function normalizeTools(value: unknown, fallback: WorkspaceTool[]): WorkspaceTool[] {
  if (!Array.isArray(value)) return fallback;
  const tools = value.filter((tool): tool is WorkspaceTool => typeof tool === "string" && allowedTools.has(tool));
  return tools.length ? tools : fallback;
}

function normalizeObjects(visual: Dict): ObjectCounterVisualSchema {
  const source = Array.isArray(visual.groups)
    ? visual.groups
    : Array.isArray(visual.rows)
      ? visual.rows
      : [];

  return {
    type: "objects",
    groups: source.map((item, index) => {
      const row = asDict(item);
      return {
        id: asString(row.id) || `group_${index + 1}`,
        label: asString(row.label) || `第${index + 1}组`,
        count: Math.max(0, Math.floor(asNumber(row.count, 0))),
        symbol: asString(row.symbol) || "●"
      };
    })
  };
}

function normalizeBarModel(visual: Dict): BarModelVisualSchema {
  const source = Array.isArray(visual.bars)
    ? visual.bars
    : Array.isArray(visual.rows)
      ? visual.rows
      : [];

  const bars = source.map((item, index) => {
    const row = asDict(item);
    const value = row.value ?? row.count;
    return {
      id: asString(row.id) || `bar_${index + 1}`,
      label: asString(row.label) || `线段${index + 1}`,
      value: value === undefined ? undefined : asNumber(value, 0),
      min: row.min === undefined ? 0 : asNumber(row.min, 0),
      max: row.max === undefined ? undefined : asNumber(row.max, 0),
      unknown: Boolean(row.unknown)
    };
  });

  const relationship =
    visual.relationship === "part-whole" ? "part-whole" : "compare";

  return {
    type: "bar-model",
    relationship,
    bars,
    max_value:
      visual.max_value === undefined
        ? undefined
        : asNumber(visual.max_value, 0)
  };
}

function normalizeNumberLine(visual: Dict): NumberLineVisualSchema {
  const min = asNumber(visual.min, 0);
  const max = Math.max(min + 1, asNumber(visual.max, 20));
  const step = Math.max(1, asNumber(visual.step, 1));
  const start =
    visual.start === undefined ? undefined : asNumber(visual.start, min);

  return {
    type: "number-line",
    min,
    max,
    step,
    start
  };
}

function manipulative(
  prompt: string,
  answerPlaceholder: string,
  visual: ObjectCounterVisualSchema | BarModelVisualSchema | NumberLineVisualSchema,
  tools: WorkspaceTool[],
  rawTools?: unknown,
  rawResponseSchema?: unknown,
  rendererId?: string,
  interactionCapabilities?: string[]
): ManipulativeTaskUiSchema {
  return {
    schema_version: "1.0",
    kind: "manipulative",
    renderer_id: rendererId || undefined,
    interaction_capabilities: interactionCapabilities,
    renderer: rendererId
      ? { renderer_id: rendererId, version: "1.0", capability_ids: interactionCapabilities }
      : undefined,
    prompt,
    answer_placeholder: answerPlaceholder,
    visual,
    tools: normalizeTools(rawTools, tools),
    response_schema: normalizeResponseSchema(rawResponseSchema, true)
  };
}

// V2 资源 → 渲染视图（FE-1405 A5 链切片）：
// 把 TaskUISchema V2（workspaces/config/mode）归一为现有 V1 视图结构渲染，
// 携带 source_schema_version/ui_revision/response_type 供提交侧构造 V2 报文。
// 目前支持 implemented renderer：number-line（jump_sequence）、objects（manipulative 系）、bar-model、纯输入。
function v2ToTaskUiSchema(raw: Dict, rendererId: string): V2TaskUiSchema {
  const workspaces = Array.isArray(raw.workspaces)
    ? raw.workspaces.map(item => {
        const workspace = asDict(item);
        return {
          workspace_id: asString(workspace.workspace_id, "main"),
          renderer: asString(workspace.renderer, rendererId) as V2TaskUiSchema["workspaces"][number]["renderer"],
          renderer_version: asString(workspace.renderer_version, "1.0"),
          mode: asString(workspace.mode, "default"),
          config: asDict(workspace.config),
          initial_state: asDict(workspace.initial_state),
          capabilities: Array.isArray(workspace.capabilities)
            ? workspace.capabilities.filter((v): v is string => typeof v === "string")
            : [],
          constraints: workspace.constraints ? asDict(workspace.constraints) : undefined
        };
      })
    : [];

  const responseContract = asDict(raw.response_contract);

  return {
    schema_version: "2.0",
    ui_revision: asString(raw.ui_revision, "rev-1"),
    prompt: {
      text: asString(asDict(raw.prompt).text, "请完成这道数学任务。"),
      resource_ref: asString(asDict(raw.prompt).resource_ref) || undefined
    },
    workspaces,
    response_contract: {
      response_type: asString(responseContract.response_type, "number"),
      required_fields: Array.isArray(responseContract.required_fields)
        ? responseContract.required_fields.filter((v): v is string => typeof v === "string")
        : undefined,
      evidence_targets: Array.isArray(responseContract.evidence_targets)
        ? responseContract.evidence_targets.filter((v): v is string => typeof v === "string")
        : undefined
    },
    hint_targets: Array.isArray(raw.hint_targets)
      ? raw.hint_targets.filter((v): v is string => typeof v === "string")
      : undefined,
    accessibility: raw.accessibility ? asDict(raw.accessibility) : undefined
  };
}

export function normalizeTaskUiSchema(payload: unknown): TaskUiSchema {
  const raw = asDict(payload);

  // V2 分流（判别字段 schema_version === "2.0"）
  if (asString(raw.schema_version) === "2.0") {
    const firstRenderer = asDict(Array.isArray(raw.workspaces) ? raw.workspaces[0] : {}).renderer;
    return v2ToTaskUiSchema(raw, asString(firstRenderer, "number-input"));
  }

  const prompt = asString(raw.prompt, "请完成这道数学任务。");
  const answerPlaceholder = asString(raw.answer_placeholder, "输入答案");
  const visual = asDict(raw.visual);
  const visualType = asString(visual.type);
  const rendererRaw = asDict(raw.renderer);
  const rendererId = asString(raw.renderer_id) || asString(rendererRaw.renderer_id) || undefined;
  const interactionCapabilities = Array.isArray(raw.interaction_capabilities)
    ? raw.interaction_capabilities.filter((v): v is string => typeof v === "string")
    : Array.isArray(rendererRaw.capability_ids)
      ? rendererRaw.capability_ids.filter((v): v is string => typeof v === "string")
      : undefined;

  if (visualType === "objects") {
    return manipulative(
      prompt,
      answerPlaceholder,
      normalizeObjects(visual),
      ["move", "align", "undo", "reset"],
      raw.tools,
      raw.response_schema,
      rendererId,
      interactionCapabilities
    );
  }

  if (visualType === "bar-model") {
    return manipulative(
      prompt,
      answerPlaceholder,
      normalizeBarModel(visual),
      ["resize", "undo", "reset"],
      raw.tools,
      raw.response_schema,
      rendererId,
      interactionCapabilities
    );
  }

  if (visualType === "number-line") {
    return manipulative(
      prompt,
      answerPlaceholder,
      normalizeNumberLine(visual),
      ["jump", "undo", "reset"],
      raw.tools,
      raw.response_schema,
      rendererId,
      interactionCapabilities
    );
  }

  if (raw.kind === "number" || !raw.kind) {
    return {
      schema_version: "1.0",
      kind: "number",
      renderer_id: rendererId,
      interaction_capabilities: interactionCapabilities,
      renderer: rendererId
        ? { renderer_id: rendererId, version: "1.0", capability_ids: interactionCapabilities }
        : undefined,
      prompt,
      answer_placeholder: answerPlaceholder,
      response_schema: normalizeResponseSchema(raw.response_schema, false)
    };
  }

  return {
    schema_version: "1.0",
    kind: "unsupported",
    renderer_id: rendererId,
    interaction_capabilities: interactionCapabilities,
    renderer: rendererId
      ? { renderer_id: rendererId, version: "1.0", capability_ids: interactionCapabilities }
      : undefined,
    prompt,
    source_kind: asString(raw.kind, "unknown"),
    response_schema: normalizeResponseSchema(raw.response_schema, false)
  };
}
