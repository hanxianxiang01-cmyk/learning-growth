import type {
  AbilityChange,
  AbilityTrend,
  LearningBehavior,
  NextRecommendation,
  SessionResult
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
    : typeof value === "string" && value.trim() !== "" && Number.isFinite(Number(value))
      ? Number(value)
      : fallback;

const asBoolean = (value: unknown, fallback = false) =>
  typeof value === "boolean" ? value : fallback;

function normalizeDurationMs(raw: Dict) {
  if (typeof raw.duration_ms === "number") return Math.max(0, raw.duration_ms);
  if (typeof raw.duration_seconds === "number") return Math.max(0, raw.duration_seconds * 1000);
  if (typeof raw.duration === "number") {
    // Canonical preference: backend should use duration_ms.
    // For an unqualified duration, treat values under one day as seconds.
    return raw.duration < 86_400 ? raw.duration * 1000 : raw.duration;
  }
  return 0;
}

function normalizeHintUsage(value: unknown): number[] {
  if (Array.isArray(value)) {
    return value
      .map(v => asNumber(v, 0))
      .filter(v => v >= 1 && v <= 4);
  }
  const count = asNumber(value, 0);
  if (count <= 0) return [];
  return Array.from({ length: Math.min(count, 4) }, (_, i) => i + 1);
}

function normalizeLearningBehaviors(value: unknown): LearningBehavior[] {
  if (!Array.isArray(value)) return [];

  return value.map((entry, index) => {
    if (typeof entry === "string") {
      return {
        code: `BEHAVIOR_${index + 1}`,
        label: entry,
        achieved: true
      };
    }

    const row = asDict(entry);
    return {
      code:
        asString(row.code) ||
        asString(row.behavior_code) ||
        `BEHAVIOR_${index + 1}`,
      label:
        asString(row.label) ||
        asString(row.name) ||
        asString(row.description) ||
        "学习行为",
      achieved:
        typeof row.achieved === "boolean"
          ? row.achieved
          : typeof row.done === "boolean"
            ? row.done
            : asBoolean(row.met, true),
      evidence:
        asString(row.evidence) ||
        asString(row.note) ||
        undefined
    };
  });
}

function normalizeAbilityChanges(value: unknown): AbilityChange[] {
  if (!Array.isArray(value)) return [];

  return value.map((entry, index) => {
    const row = asDict(entry);
    const trend = asString(row.trend) as AbilityTrend;

    return {
      ability_id:
        asString(row.ability_id) ||
        asString(row.id) ||
        `ABILITY_${index + 1}`,
      name: asString(row.name) || asString(row.ability_name) || undefined,
      before_level:
        row.before_level === undefined
          ? undefined
          : asNumber(row.before_level, 0),
      after_level: asNumber(
        row.after_level ?? row.level ?? row.mastery_level,
        0
      ),
      confidence:
        row.confidence === undefined
          ? undefined
          : asNumber(row.confidence, 0),
      trend:
        ["up", "stable", "watch", "down_review"].includes(trend)
          ? trend
          : undefined,
      evidence_delta:
        row.evidence_delta === undefined
          ? undefined
          : asNumber(row.evidence_delta, 0)
    };
  });
}

function normalizeNextRecommendation(value: unknown): NextRecommendation | null {
  if (!value) return null;

  if (typeof value === "string") {
    return {
      type: "NEXT",
      title: value
    };
  }

  const row = asDict(value);
  const title =
    asString(row.title) ||
    asString(row.label) ||
    asString(row.recommendation);

  if (!title) return null;

  return {
    type:
      asString(row.type) ||
      asString(row.action) ||
      "NEXT",
    title,
    description:
      asString(row.description) ||
      asString(row.reason) ||
      undefined,
    ability_id:
      asString(row.ability_id) ||
      undefined,
    href:
      asString(row.href) ||
      undefined
  };
}

/**
 * Normalizes backend Session Result payload to the V1.2 canonical UI contract.
 *
 * Once the authoritative OpenAPI includes SessionResult, this adapter should be
 * tightened to that schema rather than growing more aliases.
 */
export function normalizeSessionResult(
  payload: unknown,
  sessionId: string
): SessionResult {
  const raw = asDict(payload);

  return {
    session_id:
      asString(raw.session_id) ||
      asString(raw.id) ||
      sessionId,
    child_id:
      asString(raw.child_id) ||
      undefined,
    status:
      asString(raw.status) ||
      undefined,
    duration_ms: normalizeDurationMs(raw),
    task_count: asNumber(raw.task_count ?? raw.tasks_completed, 0),
    completed_count:
      raw.completed_count === undefined
        ? undefined
        : asNumber(
            raw.completed_count ??
              raw.completed_tasks ??
              raw.correct_count,
            0
          ),
    attempt_count: asNumber(raw.attempt_count ?? raw.total_attempts, 0),
    hint_usage: normalizeHintUsage(raw.hint_usage ?? raw.hints_used),
    learning_behaviors: normalizeLearningBehaviors(raw.learning_behaviors),
    ability_changes: normalizeAbilityChanges(raw.ability_changes),
    next_recommendation: normalizeNextRecommendation(raw.next_recommendation),
    completed_at:
      asString(raw.completed_at) ||
      undefined
  };
}
