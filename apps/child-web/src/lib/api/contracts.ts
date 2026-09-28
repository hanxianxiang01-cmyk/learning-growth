export type Subject = "math" | "english";

export type AbilityTrend = "up" | "stable" | "watch" | "down_review";

export type AbilityState = {
  ability_id: string;
  name?: string;
  level: number;              // 0–4
  confidence: number;         // 0–1
  fit_band?: {
    min: number;              // 1–5
    max: number;              // 1–5
  };
  evidence_count: number;
  trend?: AbilityTrend;
};

export type LearnerProfile = {
  child_id: string;
  grade: string;
  region_code?: string;
  active_abilities: AbilityState[];
  strengths: string[];
  developing: string[];
  observations: string[];
};

export type LearningSession = {
  session_id: string;
  status: "active" | string;
  plan_id: string;
};

export type TaskUiSchema = {
  kind?: "number" | "single-choice" | "formula" | "drag";
  prompt?: string;
  story?: string;
  options?: Array<{ label: string; value: string }>;
  visual?: {
    type?: "objects" | "bar-model" | "number-line" | "grid" | string;
    rows?: Array<{ label: string; count: number; symbol?: string }>;
  };
  answer_placeholder?: string;
  [key: string]: unknown;
};

export type TaskInstance = {
  task_instance_id: string;
  ability_id: string;
  difficulty: number;
  ui_schema: TaskUiSchema;
  strategy_policy: Record<string, unknown>;
  resource_version_id?: string;
  goal?: string;
  plan_id?: string;
};

export type AttemptRequest = {
  task_instance_id: string;
  attempt_no: number;
  response: Record<string, unknown>;
  client_elapsed_ms?: number;
  used_hint_levels?: number[];
};

export type DiagnosisResult = {
  code: string;
  label: string;
  confidence: number;
  evidence_scope: unknown;
};

export type NextActionCode =
  | "RETRY"
  | "HINT"
  | "TEACH"
  | "COMPLETE"
  | "NEXT_TASK";

export type NextAction = {
  type: NextActionCode;
  hint_level?: number;
  policy_id?: string;
};

export type AttemptResult = {
  attempt_id: string;
  correct: boolean;
  diagnosis?: DiagnosisResult | null;
  next_action: NextAction;
};

export type HintResponse = {
  policy_id: string;
  hint_level: number;
  action_type: "QUESTION" | "STRUCTURE_HINT" | "STEP_HINT" | "TEACH";
  text: string;
  answer_revealed: boolean;
};

/**
 * Session Result canonical frontend contract.
 *
 * Notes:
 * - Backend remains source of truth.
 * - Result page must not infer learning behavior from local attempt counts.
 * - learning_behaviors and next_recommendation drive child-visible result content.
 * - The HTTP adapter normalizes backend payload into this canonical shape.
 */
export type LearningBehavior = {
  code: string;
  label: string;
  achieved: boolean;
  evidence?: string;
};

export type AbilityChange = {
  ability_id: string;
  name?: string;
  before_level?: number;
  after_level: number;
  confidence?: number;
  trend?: AbilityTrend;
  evidence_delta?: number;
};

export type NextRecommendation = {
  type: string;
  title: string;
  description?: string;
  ability_id?: string;
  href?: string;
};

export type SessionResult = {
  session_id: string;
  child_id?: string;
  status?: string;
  duration_ms: number;
  task_count: number;
  attempt_count: number;
  hint_usage: number[];
  learning_behaviors: LearningBehavior[];
  ability_changes: AbilityChange[];
  next_recommendation?: NextRecommendation | null;
  completed_at?: string;
};

export type ApiErrorBody = {
  code?: string;
  message?: string;
  detail?: unknown;
};

export type LearningApi = {
  getProfile(childId: string): Promise<LearnerProfile>;
  getAbilities(childId: string): Promise<AbilityState[]>;
  createSession(input: {
    child_id: string;
    subject: Subject;
    requested_minutes?: number;
    plan_id?: string;
  }): Promise<LearningSession>;
  getNextTask(input: {
    child_id: string;
    session_id: string;
    subject: Subject;
    requested_minutes?: number;
    ability_id?: string;
  }): Promise<TaskInstance>;
  submitAttempt(input: AttemptRequest): Promise<AttemptResult>;
  requestHint(input: {
    attempt_id: string;
    requested_level?: number;
  }): Promise<HintResponse>;
  getSessionResult(sessionId: string): Promise<SessionResult>;
};
