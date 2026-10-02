export type Subject = "math" | "english";

export type AbilityTrend = "up" | "stable" | "watch" | "down_review";

export type AbilityState = {
  ability_id: string;
  name?: string;
  level: number;
  confidence: number;
  fit_band?: { min: number; max: number };
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

// ---------- V1.3 Task UI Schema ----------

export type ResponseAnswerType = "number" | "text";

export type TaskResponseSchema = {
  type: "structured";
  answer_type: ResponseAnswerType;
  representation_required: boolean;
  allowed_representation_types?: WorkspaceRepresentation["type"][];
};

export type WorkspaceTool =
  | "move"
  | "align"
  | "resize"
  | "jump"
  | "undo"
  | "reset";

export type ObjectCounterGroupSchema = {
  id: string;
  label: string;
  count: number;
  symbol?: string;
};

export type ObjectCounterVisualSchema = {
  type: "objects";
  groups: ObjectCounterGroupSchema[];
};

export type BarModelBarSchema = {
  id: string;
  label: string;
  value?: number;
  min?: number;
  max?: number;
  unknown?: boolean;
};

export type BarModelVisualSchema = {
  type: "bar-model";
  relationship: "compare" | "part-whole";
  bars: BarModelBarSchema[];
  max_value?: number;
};

export type NumberLineVisualSchema = {
  type: "number-line";
  min: number;
  max: number;
  step: number;
  start?: number;
};

export type ManipulativeVisualSchema =
  | ObjectCounterVisualSchema
  | BarModelVisualSchema
  | NumberLineVisualSchema;

export type TaskRendererRef = {
  renderer_id: string;
  version: "1.0";
  capability_ids?: string[];
};

export type NumberTaskUiSchema = {
  schema_version: "1.0";
  kind: "number";
  renderer_id?: string;
  interaction_capabilities?: string[];
  renderer?: TaskRendererRef;
  prompt: string;
  story?: string;
  answer_placeholder?: string;
  response_schema: TaskResponseSchema;
  // V2 视图扩展（FE-1405）：源 schema 版本与提交报文构造所需元数据
  source_schema_version?: "1.0" | "2.0";
  ui_revision?: string;
  response_type?: string;
  workspace_id?: string;
};

export type ManipulativeTaskUiSchema = {
  schema_version: "1.0";
  kind: "manipulative";
  renderer_id?: string;
  interaction_capabilities?: string[];
  renderer?: TaskRendererRef;
  prompt: string;
  story?: string;
  answer_placeholder?: string;
  visual: ManipulativeVisualSchema;
  tools: WorkspaceTool[];
  response_schema: TaskResponseSchema;
  source_schema_version?: "1.0" | "2.0";
  ui_revision?: string;
  response_type?: string;
  workspace_id?: string;
};

export type UnsupportedTaskUiSchema = {
  schema_version: "1.0";
  kind: "unsupported";
  renderer_id?: string;
  interaction_capabilities?: string[];
  renderer?: TaskRendererRef;
  prompt: string;
  source_kind?: string;
  response_schema: TaskResponseSchema;
};

export type TaskUiSchema = NumberTaskUiSchema | ManipulativeTaskUiSchema | UnsupportedTaskUiSchema;

// ---------- V1.3 Structured Response ----------

export type ObjectCounterItemPosition = {
  id: string;
  x: number; // 0..100 within its group lane
};

export type ObjectCounterRepresentation = {
  type: "object-counter";
  groups: Array<{
    id: string;
    label: string;
    count: number;
    items: ObjectCounterItemPosition[];
  }>;
  aligned: boolean;
};

export type BarModelRepresentation = {
  type: "bar-model";
  relationship: "compare" | "part-whole";
  bars: Array<{
    id: string;
    label: string;
    value: number;
    unknown?: boolean;
  }>;
};

export type NumberLineRepresentation = {
  type: "number-line";
  min: number;
  max: number;
  step: number;
  start: number | null;
  current: number | null;
  jumps: number[];
};

export type WorkspaceRepresentation =
  | ObjectCounterRepresentation
  | BarModelRepresentation
  | NumberLineRepresentation;

export type InteractionEventType =
  | "representation_changed"
  | "answer_changed"
  | "drag"
  | "align"
  | "resize"
  | "jump"
  | "undo"
  | "reset"
  | "highlight"
  | "focus"
  | "hint_applied";

export type InteractionEvent = {
  event_id: string;
  event_type: InteractionEventType;
  occurred_at: string;
  task_instance_id?: string;
  renderer_id?: string;
  capability_id?: string;
  target_id?: string;
  payload?: Record<string, string | number | boolean | null>;
};

export type TaskResponse = {
  schema_version: "1.0";
  answer: string;
  representation?: WorkspaceRepresentation;
  interaction_events?: InteractionEvent[];
};

// ---------- Workspace-aware Hint ----------

export type WorkspaceUiAction =
  | { type: "highlight"; targets: string[] }
  | { type: "align_groups" }
  | { type: "focus"; target: string }
  | { type: "show_bar_relation"; targets?: string[] }
  | { type: "show_number_line_start"; value?: number };

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
  response: TaskResponse;
  client_elapsed_ms?: number;
  used_hint_levels?: number[];
};

export type DiagnosisEvidence = {
  type: string;
  reference?: string;
  detail?: string;
};

export type DiagnosisResult = {
  schema_version?: "1.0";
  code: string;
  label: string;
  confidence: number;
  evidence_scope: unknown;
  evidence?: DiagnosisEvidence[];
  recommended_support?: string;
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
  ui_action?: WorkspaceUiAction | null;
};

// ---------- Session Result ----------

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
  completed_count?: number;
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
  submitAttempt(input: AttemptRequest, task?: TaskInstance): Promise<AttemptResult>;
  requestHint(input: {
    attempt_id: string;
    requested_level?: number;
  }): Promise<HintResponse>;
  getSessionResult(sessionId: string): Promise<SessionResult>;
};
