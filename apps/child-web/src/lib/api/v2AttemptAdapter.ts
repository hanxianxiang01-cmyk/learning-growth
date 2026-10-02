// FE-1405：V2 提交适配器。
// 视图层（渲染）继续用 V1 结构；V2 资源提交时按 MathResponseSchema V2 构造报文：
//   { schema_version:"2.0", ui_revision, type, workspaces:[{workspace_id,data}], answer, interaction_events? }
// V1 资源原样透传（向后兼容）。

import type { TaskInstance, TaskResponse, AttemptRequest } from "./contracts";

type V2EnvelopeResponse = {
  schema_version: "2.0";
  ui_revision: string;
  type: string;
  workspaces: Array<{ workspace_id: string; data: Record<string, unknown> }>;
  answer: { value: number | string };
  interaction_events?: unknown[];
};

/** V2 资源：把内部 TaskResponse（V1 形态）转为 V2 提交信封。 */
export function buildAttemptPayload(task: TaskInstance | undefined, request: AttemptRequest): unknown {
  const ui = task?.ui_schema as (TaskInstance["ui_schema"] & {
    source_schema_version?: string;
    ui_revision?: string;
    response_type?: string;
    workspace_id?: string;
  }) | undefined;

  if (!ui || ui.source_schema_version !== "2.0") {
    return request; // V1 原样透传
  }

  const response = request.response as TaskResponse & Record<string, unknown>;
  const envelope: V2EnvelopeResponse = {
    schema_version: "2.0",
    ui_revision: ui.ui_revision ?? "rev-1",
    type: ui.response_type ?? "number_line",
    workspaces: [
      {
        workspace_id: ui.workspace_id ?? "main",
        // 表征即工作区数据（V2：workspace 承载过程，answer 承载结果）
        data: (response.representation
          ? { ...response.representation, type: undefined }
          : {}) as Record<string, unknown>
      }
    ],
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
