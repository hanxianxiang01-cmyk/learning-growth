// FE-1403 / FE-1405：V2 Renderer → MathResponse V2 提交适配器。
// Renderer 的 Workspace state 先由 TaskRenderer 写入 TaskResponse.v2_workspaces,
// 本适配器再构造权威 MathResponse V2 envelope。
// FE-1417（交付框架包收编）：stable submission_id + Evidence/Evaluation 提交时注入。

import type { TaskInstance, TaskResponse, AttemptRequest, V2TaskUiSchema, V2RendererWorkspace, InteractionEvent } from "./contracts";
import { buildRendererEvidence, createRendererRuntimeState, type RendererSemanticEvent } from "@/src/features/task-renderer/rendererContract";
import { getRendererEvaluator } from "@/src/features/task-renderer/evaluatorRegistry";

/**
 * stable submission_id —— 必须为合法 UUID（后端 learning.py `uuid.UUID(str(...))` 校验，
 * 非 UUID 串 ValueError→404；交付原方案 `task:attempt:revision` 冒号串在此被拦——
 * 其环境无 node_modules、未跑过 E2E，故未暴露）。
 * 对派生材料做 4 轮 64 位 FNV 扩散成 32 hex → UUID 格式：同
 * (task, attempt_no, ui_revision) 恒定 → 重试/重放命中服务端幂等权威轨；
 * 不同 attempt_no/revision → 不同 submission_id（重放只发生在"同一次提交"内）。
 */
export function stableSubmissionId(taskInstanceId: string, attemptNo: number, uiRevision: string): string {
  const material = `${taskInstanceId}|${attemptNo}|${uiRevision}`;
  const hex = (seed: number) => {
    let h = seed >>> 0;
    for (let i = 0; i < material.length; i += 1) {
      h ^= material.charCodeAt(i);
      h = Math.imul(h, 0x01000193) >>> 0;
      h = (h ^ (h >>> 13)) >>> 0;
      h = Math.imul(h, 0x5bd1e995) >>> 0;
      h = (h ^ (h >>> 15)) >>> 0;
    }
    // 每个 seed 扩散 8 hex；四轮拼 32 hex（跨 seed 去相关）
    let out = h.toString(16).padStart(8, "0");
    let mix = h;
    for (let k = 1; k <= 3; k += 1) {
      mix = Math.imul(mix ^ (material.length + k * seed), 0x01000193) >>> 0;
      mix = (mix ^ (mix >>> 16)) >>> 0;
      out += mix.toString(16).padStart(8, "0");
    }
    return out;
  };
  const h = hex(0x811c9dc5);
  // 严格 8-4-4-4-12 十六进制分段——Python uuid.UUID 只认这个形状。
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20, 32)}`;
}

/** 提交时刻把 Evidence/Evaluation 注入 workspace data（attempt_no 为真实值）。 */
function enrichWorkspaceData(
  data: Record<string, unknown>,
  workspace: V2RendererWorkspace,
  taskInstanceId: string,
  attemptNo: number,
  answer: string,
  events: InteractionEvent[]
): Record<string, unknown> {
  const present = (data.state as Record<string, unknown> | undefined) ?? data;
  const runtime = createRendererRuntimeState(present, attemptNo);
  runtime.status = "SUBMITTED";
  runtime.events = events as RendererSemanticEvent[];
  const evidence = buildRendererEvidence(taskInstanceId, workspace, runtime, answer);
  const evaluation = getRendererEvaluator(workspace.renderer)({ answer, evidence, config: workspace.config });
  return { ...data, evidence, evaluation, runtime_status: runtime.status };
}

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

  const baseWorkspaces =
    response.v2_workspaces?.length
      ? response.v2_workspaces
      : schema.workspaces.map(workspace => ({
          workspace_id: workspace.workspace_id,
          data: workspace.initial_state
        }));

  // FE-1417：Evidence/Evaluation 注入（语义边界：renderer 只给 What happened，
  // 不做 mastery/diagnosis 判断；generic evaluator 的 expected 来自 task.content 下发？——
  // config 无 expected_answer 时 evaluator 返回 NOT_EVALUATED，属合法前端弱判）。
  const workspaces = baseWorkspaces.map(w => {
    const declared = schema.workspaces.find(ws => ws.workspace_id === w.workspace_id);
    if (!declared) return w;
    try {
      return {
        ...w,
        data: enrichWorkspaceData(
          w.data,
          declared,
          request.task_instance_id,
          request.attempt_no,
          response.answer,
          response.interaction_events ?? []
        )
      };
    } catch {
      return w; // 注入失败不阻塞提交（后端仍权威判分）
    }
  });

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
    // FE-1417：stable submission_id（幂等权威轨）。显式传入优先；
    // 缺省由 (task, attempt_no, ui_revision) 确定性派生，不再每次随机。
    submission_id: request.submission_id ?? stableSubmissionId(request.task_instance_id, request.attempt_no, schema.ui_revision),
    response: envelope
  };
}

function numericOrText(answer: string): number | string {
  const n = Number(answer);
  return Number.isFinite(n) && String(answer).trim() !== "" ? n : answer;
}
