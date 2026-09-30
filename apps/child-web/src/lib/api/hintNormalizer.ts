import type { HintResponse, WorkspaceUiAction } from "./contracts";

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

function normalizeUiAction(value: unknown): WorkspaceUiAction | null {
  const row = asDict(value);
  const type = asString(row.type);
  if (type === "highlight" && Array.isArray(row.targets)) {
    return { type, targets: row.targets.filter((v): v is string => typeof v === "string") };
  }
  if (type === "align_groups") return { type };
  if (type === "focus" && typeof row.target === "string") return { type, target: row.target };
  if (type === "show_bar_relation") {
    return {
      type,
      targets: Array.isArray(row.targets)
        ? row.targets.filter((v): v is string => typeof v === "string")
        : undefined
    };
  }
  if (type === "show_number_line_start") {
    return {
      type,
      value: row.value === undefined ? undefined : asNumber(row.value, 0)
    };
  }
  return null;
}

export function normalizeHintResponse(payload: unknown): HintResponse {
  const raw = asDict(payload);
  const level = Math.max(1, Math.min(4, asNumber(raw.hint_level ?? raw.level, 1)));
  const rawAction = asString(raw.action_type ?? raw.action);
  const allowed = ["QUESTION", "STRUCTURE_HINT", "STEP_HINT", "TEACH"] as const;
  const action_type = allowed.includes(rawAction as typeof allowed[number])
    ? (rawAction as typeof allowed[number])
    : level === 1 ? "QUESTION" : level === 4 ? "TEACH" : "STEP_HINT";

  return {
    policy_id: asString(raw.policy_id ?? raw.policy, "unknown-policy"),
    hint_level: level,
    action_type,
    text: asString(raw.text ?? raw.message, "先想一想，可以换一种表示方法。"),
    answer_revealed: Boolean(raw.answer_revealed),
    ui_action: normalizeUiAction(raw.ui_action)
  };
}
