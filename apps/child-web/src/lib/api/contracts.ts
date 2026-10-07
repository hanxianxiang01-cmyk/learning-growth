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

export type V2RendererWorkspace = {
  workspace_id: string;
  renderer: import("@/src/features/task-renderer/rendererRegistry").RendererProtocolId;
  renderer_version: string;
  mode: string;
  config: Record<string, unknown>;
  initial_state: Record<string, unknown>;
  capabilities: string[];
  constraints?: Record<string, unknown>;
};

export type V2TaskUiSchema = {
  schema_version: "2.0";
  ui_revision: string;
  prompt: {
    text: string;
    resource_ref?: string;
  };
  workspaces: V2RendererWorkspace[];
  response_contract: {
    response_type: string;
    required_fields?: string[];
    evidence_targets?: string[];
  };
  hint_targets?: string[];
  accessibility?: Record<string, unknown>;
};

export type TaskUiSchema = V2TaskUiSchema | NumberTaskUiSchema | ManipulativeTaskUiSchema | UnsupportedTaskUiSchema;

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

/**
 * 交互事件枚举（FE-1417 收编交付框架包）：
 * 小写值为 V1 时代遗留（Representation 路径），UPPER_SNAKE 为 V2 语义事件
 * （docs/frontend/26 §3 / rendererContract）。渲染器状态名（READY/INTERACTING/…）
 * 不属于事件，其事实源是 rendererContract.RENDERER_STATES。
 */
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
  | "hint_applied"
  // V2 语义事件（专件已闭 Gate：B5/A5/R01/R04/R07）
  | "DIGIT_ENTERED"
  | "CARRY_CREATED"
  | "CARRY_REMOVED"
  | "STEP_SUBMITTED"
  | "JUMP_CREATED"
  | "MARKER_PLACED"
  | "COUNT_ADDED"
  | "COUNT_REMOVED"
  | "GROUP_COMPOSED"
  | "GROUP_DECOMPOSED"
  | "NUMBER_INPUT_CHANGED"
  | "MAKE_TEN_COMPLETED"
  | "TEN_BROKEN"
  | "BAR_BLOCK_ADDED"
  | "BAR_BLOCK_REMOVED"
  | "DIGIT_PICKED"
  | "DIGIT_UNPICKED"
  | "DIGIT_PLACED"
  | "DIGIT_SWAPPED"
  | "DIGIT_RETURNED"
  | "SLOT_ACTIVATED"
  | "NUMBER_FILLED"
  | "NUMBER_REPLACED"
  | "OPERATOR_FILLED"
  | "OPERATOR_REPLACED"
  | "SLOT_CLEARED"
  | "ARRAY_ROW_ADDED"
  | "ARRAY_ROW_REMOVED"
  | "ARRAY_COL_ADDED"
  | "ARRAY_COL_REMOVED"
  | "ITEM_ADDED"
  | "ITEM_REMOVED"
  | "SUBMITTED"
  | "UNDO"
  | "RESET"
  // V2 语义事件（基座 18 组件，V2RendererLibrary 实际发射）
  | "OPTION_SELECTED"
  | "OPTION_DESELECTED"
  | "VALUE_CHANGED"
  | "COUNTER_ADDED"
  | "COUNTER_REMOVED"
  | "ROW_CHANGED"
  | "COLUMN_CHANGED"
  | "GROUP_CHANGED"
  | "GROUP_CREATED"
  | "GROUP_REMOVED"
  | "FORMULA_CHANGED"
  | "ESTIMATE_CHANGED"
  | "SHAPE_SELECTED"
  | "SHAPE_CHANGED"
  | "ORDER_CHANGED"
  | "DIRECTION_CHANGED"
  | "MEASUREMENT_CHANGED"
  | "TIME_CHANGED"
  | "MONEY_ADDED"
  | "CELL_EDITED"
  | "DATA_POINT_SELECTED"
  | "BLANK_FILLED"
  | "DIGIT_CHANGED";

export type InteractionEvent = {
  event_id: string;
  event_type: InteractionEventType;
  occurred_at: string;
  task_instance_id?: string;
  renderer_id?: string;
  capability_id?: string;
  target_id?: string;
  payload?: Record<string, string | number | boolean | null>;
  /** V2 事件元数据（FE-1417，rendererContract.createSemanticEvent 填充）。 */
  session_id?: string;
  attempt_no?: number;
  sequence_no?: number;
};

export type V2WorkspaceResponseData = Record<string, unknown>;

export type TaskResponse = {
  schema_version: "1.0";
  answer: string;
  representation?: WorkspaceRepresentation;
  interaction_events?: InteractionEvent[];
  /**
   * Internal frontend transport fields for V2 renderer state.
   * v2AttemptAdapter consumes these fields; they are never sent as V1 fields.
   */
  v2_workspaces?: Array<{
    workspace_id: string;
    data: V2WorkspaceResponseData;
  }>;
  v2_response_type?: string;
  v2_ui_revision?: string;
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
  /** FE-1417：V2 幂等键（stable，缺省由 adapter 派生 task:attempt:revision）。 */
  submission_id?: string;
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
