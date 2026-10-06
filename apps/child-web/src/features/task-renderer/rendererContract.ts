import type { InteractionEvent, InteractionEventType, TaskResponse, V2RendererWorkspace, V2TaskUiSchema } from "@/src/lib/api/contracts";
import type { RendererProtocolId } from "./rendererRegistry";

export const RENDERER_STATES = [
  "INITIAL", "LOADING", "READY", "INTERACTING", "VALIDATING",
  "SUBMITTED", "CORRECT", "INCORRECT", "RETRY", "COMPLETED",
  "EMPTY", "ERROR", "DISABLED"
] as const;
export type RendererStateStatus = typeof RENDERER_STATES[number];

export type RendererRuntimeState<T extends Record<string, unknown> = Record<string, unknown>> = {
  status: RendererStateStatus;
  present: T;
  history: T[];
  events: RendererSemanticEvent[];
  attempt_no: number;
  correction_count: number;
  retry_count: number;
};

export type RendererSemanticEvent = InteractionEvent & {
  event_type: string;
  sequence_no?: number;
  attempt_no?: number;
  session_id?: string;
};

export type RendererEvidence = {
  evidence_id: string;
  renderer_id: RendererProtocolId;
  task_instance_id: string;
  workspace_id: string;
  attempt_no: number;
  final_state: RendererStateStatus;
  event_count: number;
  interaction_count: number;
  correction_count: number;
  retry_count: number;
  events: RendererSemanticEvent[];
  state_snapshot: Record<string, unknown>;
};

export type RendererEvaluation = {
  evaluator_id: string;
  status: "CORRECT" | "INCORRECT" | "INCOMPLETE" | "NOT_EVALUATED";
  score?: number;
  answer?: string;
  expected_answer?: string;
  error_code?: string;
  evidence_id: string;
};

export type RendererDefinition<TState extends Record<string, unknown> = Record<string, unknown>> = {
  renderer_id: RendererProtocolId;
  initial_state: TState;
  get_answer?: (state: TState) => string;
  get_status?: (state: TState, answer: string) => RendererStateStatus;
};

export function createRendererRuntimeState<T extends Record<string, unknown>>(
  initial: T,
  attemptNo = 1
): RendererRuntimeState<T> {
  return {
    status: "INITIAL",
    present: structuredClone(initial),
    history: [],
    events: [],
    attempt_no: attemptNo,
    correction_count: 0,
    retry_count: 0
  };
}

const allowedTransitions: Record<RendererStateStatus, RendererStateStatus[]> = {
  INITIAL: ["LOADING", "READY", "EMPTY", "DISABLED", "ERROR"],
  LOADING: ["READY", "EMPTY", "ERROR", "DISABLED"],
  READY: ["INTERACTING", "VALIDATING", "SUBMITTED", "EMPTY", "DISABLED", "ERROR"],
  INTERACTING: ["INTERACTING", "VALIDATING", "SUBMITTED", "READY", "EMPTY", "ERROR", "DISABLED"],
  VALIDATING: ["SUBMITTED", "CORRECT", "INCORRECT", "ERROR"],
  SUBMITTED: ["CORRECT", "INCORRECT", "RETRY", "COMPLETED", "ERROR"],
  CORRECT: ["COMPLETED", "READY", "RETRY"],
  INCORRECT: ["RETRY", "INTERACTING", "READY"],
  RETRY: ["INTERACTING", "READY", "SUBMITTED", "ERROR"],
  COMPLETED: ["READY", "DISABLED"],
  EMPTY: ["READY", "INTERACTING", "ERROR"],
  ERROR: ["READY", "RETRY", "DISABLED"],
  DISABLED: ["READY", "ERROR"]
};

export function canTransition(from: RendererStateStatus, to: RendererStateStatus) {
  return from === to || allowedTransitions[from].includes(to);
}

export function transitionRendererState(
  current: RendererStateStatus,
  next: RendererStateStatus
): RendererStateStatus {
  if (!canTransition(current, next)) {
    throw new Error(`Invalid renderer state transition: ${current} → ${next}`);
  }
  return next;
}

export function createSemanticEvent(
  taskInstanceId: string,
  rendererId: RendererProtocolId,
  eventType: string,
  payload: Record<string, unknown> = {},
  detail: { attempt_no?: number; session_id?: string; workspace_id?: string; capability_id?: string; sequence_no?: number } = {}
): RendererSemanticEvent {
  const safePayload = Object.fromEntries(
    Object.entries(payload).filter(([, value]) =>
      value === null || ["string", "number", "boolean"].includes(typeof value)
    )
  ) as Record<string, string | number | boolean | null>;

  return {
    event_id: typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `evt-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    // FE-1417：事件名由调用方（语义事件契约）保证合法；此处收窄类型。
    // 交付原版参数是 string，未跑 tsc 未暴露。
    event_type: eventType as InteractionEventType,
    occurred_at: new Date().toISOString(),
    task_instance_id: taskInstanceId,
    renderer_id: rendererId,
    capability_id: detail.capability_id,
    target_id: detail.workspace_id,
    payload: safePayload,
    attempt_no: detail.attempt_no,
    session_id: detail.session_id,
    sequence_no: detail.sequence_no
  };
}

export function buildRendererEvidence(
  taskInstanceId: string,
  workspace: V2RendererWorkspace,
  runtime: Pick<RendererRuntimeState, "status" | "events" | "attempt_no" | "correction_count" | "retry_count" | "present">,
  answer: string
): RendererEvidence {
  const events = runtime.events;
  return {
    evidence_id: `ev-${workspace.renderer}-${taskInstanceId}-${runtime.attempt_no}`,
    renderer_id: workspace.renderer,
    task_instance_id: taskInstanceId,
    workspace_id: workspace.workspace_id,
    attempt_no: runtime.attempt_no,
    final_state: runtime.status,
    event_count: events.length,
    interaction_count: events.filter(e => !["RESET", "UNDO"].includes(e.event_type)).length,
    correction_count: runtime.correction_count,
    retry_count: runtime.retry_count,
    events,
    state_snapshot: { ...runtime.present, answer }
  };
}

export function evaluateRendererAnswer(
  evaluatorId: string,
  answer: string,
  evidence: RendererEvidence,
  expectedAnswer?: unknown
): RendererEvaluation {
  const expected = expectedAnswer === undefined || expectedAnswer === null ? undefined : String(expectedAnswer);
  if (!answer.trim()) {
    return { evaluator_id: evaluatorId, status: "INCOMPLETE", answer, expected_answer: expected, evidence_id: evidence.evidence_id };
  }
  if (expected === undefined) {
    return { evaluator_id: evaluatorId, status: "NOT_EVALUATED", answer, evidence_id: evidence.evidence_id };
  }
  const correct = answer.trim() === expected.trim();
  return {
    evaluator_id: evaluatorId,
    status: correct ? "CORRECT" : "INCORRECT",
    score: correct ? 1 : 0,
    answer,
    expected_answer: expected,
    error_code: correct ? undefined : "ANSWER_MISMATCH",
    evidence_id: evidence.evidence_id
  };
}

export function assertTaskUiSchemaV2(schema: V2TaskUiSchema) {
  if (schema.schema_version !== "2.0") throw new Error("Renderer runtime requires TaskUISchema V2");
  if (!schema.ui_revision) throw new Error("TaskUISchema V2 requires ui_revision");
  if (!schema.workspaces.length) throw new Error("TaskUISchema V2 requires at least one workspace");
  for (const workspace of schema.workspaces) {
    if (!workspace.workspace_id || !workspace.renderer) throw new Error("Workspace requires workspace_id and renderer");
    if (!workspace.renderer_version) throw new Error(`Workspace ${workspace.workspace_id} requires renderer_version`);
    if (!Array.isArray(workspace.capabilities)) throw new Error(`Workspace ${workspace.workspace_id} requires capabilities[]`);
  }
}

export function appendRendererEvidence(response: TaskResponse, evidence: RendererEvidence) {
  const workspace = response.v2_workspaces?.find(w => w.workspace_id === evidence.workspace_id);
  if (!workspace) return response;
  const data = {
    ...workspace.data,
    evidence,
    evidence_targets: evidence.events.map(event => event.event_type)
  };
  return {
    ...response,
    v2_workspaces: response.v2_workspaces?.map(w =>
      w.workspace_id === evidence.workspace_id ? { ...w, data } : w
    )
  };
}
