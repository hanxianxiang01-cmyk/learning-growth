"use client";

/**
 * estimation-canvas V2 组件（FE-1423 R11）。runtime 装配对齐 GroupingBoardV2。
 *
 * 估算三步：拖滑条定估算值 → 选估算理由 chip → 提交。
 * 五态评估：EMPTY(estimate)→EMPTY(reason)→PASS→FAIL(too_high/too_low)——
 * FAIL 可提交（P0-01 口径），too_high/too_low/close 是诊断原料走 Evidence。
 * 调整过程 adjust_history + ESTIMATE_CHANGED/REASON_SELECTED 事件链 = Gap Evidence。
 */

import { useEffect, useMemo, useReducer, useRef } from "react";
import type { TaskResponse, V2TaskUiSchema } from "@/src/lib/api/contracts";
import {
  applyEstimate,
  applyReason,
  estimationAnswer,
  evaluateEstimation,
  ESTIMATION_REASONS,
  initialEstimationV2State,
  parseEstimationConfig,
  serializeEstimationCanvasV2,
  type EstimationCanvasV2State,
  type EstimationReasonId
} from "@/src/features/task-renderer/estimationCanvasV2";
import { buildRendererEvent, createRendererWorkspaceState, rendererWorkspaceReducer } from "@/src/features/task-renderer/rendererRuntime";

type Props = {
  taskInstanceId: string;
  schema: V2TaskUiSchema;
  response: TaskResponse;
  disabled?: boolean;
  onResponseChange: (response: TaskResponse) => void;
  onSubmit: () => void;
};

export function EstimationCanvasV2({
  taskInstanceId,
  schema,
  response,
  disabled,
  onResponseChange,
  onSubmit
}: Props) {
  const workspace = schema.workspaces[0];
  const config = useMemo(
    () => (workspace ? parseEstimationConfig(workspace.config as Record<string, unknown>) : null),
    [workspace]
  );
  const [runtime, dispatch] = useReducer(
    rendererWorkspaceReducer<EstimationCanvasV2State>,
    { estimate: null, reason: null, adjust_history: [] },
    createRendererWorkspaceState
  );
  const responseRef = useRef(response);
  responseRef.current = response;

  // config/revision 变化 → 清态重灌
  useEffect(() => {
    if (config) dispatch({ type: "SET_STATE", state: initialEstimationV2State() });
  }, [config, schema.ui_revision]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!config || !workspace) return;
    const answer = estimationAnswer(runtime.present);
    onResponseChange({
      ...responseRef.current,
      answer: answer === null ? "" : String(answer),
      interaction_events: runtime.events,
      v2_workspaces: [
        { workspace_id: workspace.workspace_id, data: serializeEstimationCanvasV2(runtime.present, config) }
      ],
      v2_response_type: schema.response_contract.response_type,
      v2_ui_revision: schema.ui_revision
    });
  }, [
    runtime.present,
    runtime.events,
    config,
    workspace,
    onResponseChange,
    schema.response_contract.response_type,
    schema.ui_revision
  ]);

  if (!config || !workspace) {
    return <div className="surface-card unsupported-task">估算画布题配置不完整。</div>;
  }

  const emit = (eventType: string, payload: Record<string, string | number | boolean | null>) =>
    buildRendererEvent(eventType, {
      task_instance_id: taskInstanceId,
      workspace_id: workspace.workspace_id,
      renderer_id: "estimation-canvas",
      capability_id: "answer_input",
      payload
    });

  const state = runtime.present;
  const verdict = evaluateEstimation(state, config);

  const moveEstimate = (raw: number) => {
    if (disabled) return;
    const result = applyEstimate(state, config, raw);
    if (!result.ok || result.state === state) return; // 未变化不记史不 emit
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit("ESTIMATE_CHANGED", {
        estimate: result.state.estimate,
        step: result.state.adjust_history.length
      })
    });
  };

  const pickReason = (reason: EstimationReasonId) => {
    if (disabled) return;
    const result = applyReason(state, reason);
    if (!result.ok || result.noop) return; // 重复点选=无操作不记事件
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit(result.replaced ? "REASON_REPLACED" : "REASON_SELECTED", { reason })
    });
  };

  const undo = () => !disabled && dispatch({ type: "UNDO", event: emit("UNDO", {}) });
  const reset = () =>
    !disabled && config &&
    dispatch({ type: "SET_STATE", state: initialEstimationV2State(), event: emit("RESET", {}) });

  return (
    <div className="manipulative-card estimation-canvas-v2" data-testid="estimation-canvas-v2">
      <div className="manipulative-heading">
        <div>
          <strong>估一估</strong>
          <span>拖动滑条给出你的估算，再选一选你是怎么想的。</span>
        </div>
        <div className="workspace-actions">
          <button type="button" data-testid="ec-undo" disabled={disabled || runtime.history.length === 0} onClick={undo}>
            撤销
          </button>
          <button type="button" data-testid="ec-reset" disabled={disabled} onClick={reset}>
            重置
          </button>
        </div>
      </div>

      <div className="ec-reference" data-testid="ec-reference">
        参照：这么多是 <strong data-testid="ec-reference-count">{config.reference}</strong> 本
      </div>

      <input
        type="range"
        min={0}
        max={config.max}
        step={1}
        value={state.estimate ?? 0}
        disabled={disabled}
        data-testid="ec-slider"
        aria-label="估算滑条"
        onChange={e => moveEstimate(Number(e.target.value))}
      />
      <div className="ec-estimate-value" data-testid="ec-estimate-value">
        {state.estimate === null ? "还没拖动" : state.estimate}
      </div>

      <div className="ec-reasons" data-testid="ec-reasons">
        {ESTIMATION_REASONS.map(r => (
          <button
            key={r.id}
            type="button"
            data-testid={`ec-reason-${r.id}`}
            className={state.reason === r.id ? "ec-reason chosen" : "ec-reason"}
            disabled={disabled}
            onClick={() => pickReason(r.id)}
          >
            {r.label}
          </button>
        ))}
      </div>

      <div className={`ec-evaluation ${verdict.status.toLowerCase()}`} data-testid="ec-evaluation">
        {verdict.status === "EMPTY"
          ? verdict.missing === "estimate"
            ? "先拖动滑条估一个数"
            : "再选一选你是怎么估的"
          : verdict.status === "PASS"
            ? `估到 ${state.estimate}，接近整十估得准`
            : verdict.error === "too_high"
              ? verdict.close
                ? "方向偏高了，差一点点——往回拖一拖"
                : "估得太高啦，往小了调"
              : verdict.close
                ? "方向偏低了，差一点点——再多拖一点"
                : "估得太低了，往大了调"}
      </div>

      <button
        type="button"
        className="primary-button"
        data-testid="ec-submit"
        // P0-01 口径：EMPTY（未拖/未选理由）拦提交；PASS∪FAIL 可达后端。
        disabled={disabled || verdict.status === "EMPTY"}
        onClick={onSubmit}
      >
        提交估算
      </button>
    </div>
  );
}
