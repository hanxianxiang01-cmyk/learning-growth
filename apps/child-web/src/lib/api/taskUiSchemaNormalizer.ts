import type {
  BarModelVisualSchema,
  ManipulativeTaskUiSchema,
  NumberLineVisualSchema,
  ObjectCounterVisualSchema,
  TaskUiSchema,
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
  return {
    type: "structured" as const,
    answer_type: raw.answer_type === "text" ? ("text" as const) : ("number" as const),
    representation_required:
      typeof raw.representation_required === "boolean"
        ? raw.representation_required
        : representationRequired
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
  rawResponseSchema?: unknown
): ManipulativeTaskUiSchema {
  return {
    schema_version: "1.0",
    kind: "manipulative",
    prompt,
    answer_placeholder: answerPlaceholder,
    visual,
    tools: normalizeTools(rawTools, tools),
    response_schema: normalizeResponseSchema(rawResponseSchema, true)
  };
}

export function normalizeTaskUiSchema(payload: unknown): TaskUiSchema {
  const raw = asDict(payload);
  const prompt = asString(raw.prompt, "请完成这道数学任务。");
  const answerPlaceholder = asString(raw.answer_placeholder, "输入答案");
  const visual = asDict(raw.visual);
  const visualType = asString(visual.type);

  if (visualType === "objects") {
    return manipulative(
      prompt,
      answerPlaceholder,
      normalizeObjects(visual),
      ["move", "align", "undo", "reset"],
      raw.tools,
      raw.response_schema
    );
  }

  if (visualType === "bar-model") {
    return manipulative(
      prompt,
      answerPlaceholder,
      normalizeBarModel(visual),
      ["resize", "undo", "reset"],
      raw.tools,
      raw.response_schema
    );
  }

  if (visualType === "number-line") {
    return manipulative(
      prompt,
      answerPlaceholder,
      normalizeNumberLine(visual),
      ["jump", "undo", "reset"],
      raw.tools,
      raw.response_schema
    );
  }

  if (raw.kind === "number" || !raw.kind) {
    return {
      schema_version: "1.0",
      kind: "number",
      prompt,
      answer_placeholder: answerPlaceholder,
      response_schema: normalizeResponseSchema(raw.response_schema, false)
    };
  }

  return {
    schema_version: "1.0",
    kind: "unsupported",
    prompt,
    source_kind: asString(raw.kind, "unknown"),
    response_schema: normalizeResponseSchema(raw.response_schema, false)
  };
}
