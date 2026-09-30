import type { AttemptResult, DiagnosisResult, NextActionCode } from "./contracts";

type Dict = Record<string, unknown>;

function asDict(value: unknown): Dict {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Dict)
    : {};
}

function asString(value: unknown, fallback = "") {
  return typeof value === "string" ? value : fallback;
}

function asNumber(value: unknown, fallback = 0) {
  return typeof value === "number" && Number.isFinite(value)
    ? value
    : typeof value === "string" && Number.isFinite(Number(value))
      ? Number(value)
      : fallback;
}

function normalizeDiagnosis(value: unknown): DiagnosisResult | null {
  if (!value) return null;
  const row = asDict(value);
  const evidence = Array.isArray(row.evidence)
    ? row.evidence.map(item => {
        const entry = asDict(item);
        return {
          type: asString(entry.type, "unknown"),
          reference: asString(entry.reference) || undefined,
          detail: asString(entry.detail) || undefined
        };
      })
    : undefined;

  return {
    schema_version: "1.0",
    code: asString(row.code, "UNKNOWN"),
    label: asString(row.label) || asString(row.name) || "暂时没有更多说明",
    confidence: Math.max(0, Math.min(1, asNumber(row.confidence, 0))),
    evidence_scope: row.evidence_scope ?? row.scope ?? null,
    evidence,
    recommended_support:
      asString(row.recommended_support) || asString(row.support) || undefined
  };
}

export function normalizeAttemptResult(payload: unknown): AttemptResult {
  const raw = asDict(payload);
  const action = asDict(raw.next_action ?? raw.nextAction);
  const supported: NextActionCode[] = [
    "RETRY",
    "HINT",
    "TEACH",
    "COMPLETE",
    "NEXT_TASK"
  ];
  const rawType = asString(action.type, asString(action.action, "RETRY")).toUpperCase();

  return {
    attempt_id: asString(raw.attempt_id ?? raw.id, `attempt-${Date.now()}`),
    correct: Boolean(raw.correct),
    diagnosis: normalizeDiagnosis(raw.diagnosis),
    next_action: {
      type: supported.includes(rawType as NextActionCode)
        ? (rawType as NextActionCode)
        : "RETRY",
      hint_level:
        action.hint_level === undefined && action.level === undefined
          ? undefined
          : Math.max(1, Math.min(4, asNumber(action.hint_level ?? action.level, 1))),
      policy_id: asString(action.policy_id ?? action.policy) || undefined
    }
  };
}
