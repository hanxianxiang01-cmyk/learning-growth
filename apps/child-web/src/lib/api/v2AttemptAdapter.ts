// FE-1403 / FE-1405：V2 Renderer → MathResponse V2 提交适配器。
// Renderer 的 Workspace state 先由 TaskRenderer 写入 TaskResponse.v2_workspaces，
// 本适配器再构造权威 MathResponse V2 envelope。

import type { TaskInstance, TaskResponse, AttemptRequest, V2TaskUiSchema } from "./contracts";

type V2EnvelopeResponse = {
  schema_version: "2.0";
  ui_revision: string;
  type: string;
  workspaces: Array<{ workspace_id: string; data: Record<string, unknown> }>;
  answer: { value: number | string };
  interaction_events?: unknown[];
};

function isV2TaskUiSchema(task?: TaskInstance): task is TaskInstance & { ui_schema: V2TaskUiSchema } {
  return task?.ui_schema.schema_version === "2.0";
}

/** V2 资源：把内部 TaskResponse 转为 MathResponseSchema V2。 */
export function buildAttemptPayload(task: TaskInstance | undefined, request: AttemptRequest): unknown {
  if (!isV2TaskUiSchema(task)) {
    return request;
  }

  const response = request.response;
  const schema = task.ui_schema;

  const workspaces =
    response.v2_workspaces?.length
      ? response.v2_workspaces
      : schema.workspaces.map(workspace => ({
          workspace_id: workspace.workspace_id,
          data: workspace.initial_state
        }));

  const envelope: V2EnvelopeResponse = {
    schema_version: "2.0",
    ui_revision: response.v2_ui_revision ?? schema.ui_revision,
    type: response.v2_response_type ?? schema.response_contract.response_type,
    workspaces,
    answer: { value: numericOrText(response.answer) }
  };

  if (Array.isArray(response.interaction_events)) {
    envelope.interaction_events = response.interaction_events;
  }

  return {
    task_instance_id: request.task_instance_id,
    attempt_no: request.attempt_no,
    submission_id: crypto.randomUUID(),
    response: envelope
  };
}

function numericOrText(answer: string): number | string {
  const n = Number(answer);
  return Number.isFinite(n) && String(answer).trim() !== "" ? n : answer;
}
