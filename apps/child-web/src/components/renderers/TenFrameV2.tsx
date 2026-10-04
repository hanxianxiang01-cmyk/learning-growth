"use client";

/**
 * ten-frame V2 组件（FE-1416 R07）。runtime 装配对齐 NumberLineV2/ColumnArithmetic：
 * rendererWorkspaceReducer（undo/history 内建）+ buildRendererEvent（UPPER_SNAKE）。
 */

import { useEffect, useMemo, useReducer, useRef } from "react";
import type { TaskResponse, V2TaskUiSchema } from "@/src/lib/api/contracts";
import {
  applyBreakTen,
  applyCell,
  applyMakeTen,
  evaluateQuantity,
  initialTenFrameV2State,
  parseTenFrameConfig,
  serializeTenFrameV2,
  totalOf,
  type TenFrameV2Config,
  type TenFrameV2State
} from "@/src/features/task-renderer/tenFrameV2";
import { buildRendererEvent, createRendererWorkspaceState, rendererWorkspaceReducer } from "@/src/features/task-renderer/rendererRuntime";

type Props = {
  taskInstanceId: string;
  schema: V2TaskUiSchema;
  response: TaskResponse;
  disabled?: boolean;
  onResponseChange: (response: TaskResponse) => void;
  onSubmit: () => void;
};

export function TenFrameV2({
  taskInstanceId,
  schema,
  response,
  disabled,
  onResponseChange,
  onSubmit
}: Props) {
  const workspace = schema.workspaces[0];
  const config = useMemo(
    () => (workspace ? parseTenFrameConfig(workspace.config as Record<string, unknown>) : null),
    [workspace]
  );
  const [runtime, dispatch] = useReducer(
    rendererWorkspaceReducer<TenFrameV2State>,
    initialTenFrameV2State(),
    createRendererWorkspaceState
  );
  const responseRef = useRef(response);
  responseRef.current = response;

  useEffect(() => {
    dispatch({ type: "RESET" });
  }, [schema.ui_revision]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!workspace) return;
    onResponseChange({
      ...responseRef.current,
      answer: totalOf(runtime.present) === 0 ? "" : String(totalOf(runtime.present)),
      interaction_events: runtime.events,
      v2_workspaces: [
        { workspace_id: workspace.workspace_id, data: serializeTenFrameV2(runtime.present) }
      ],
      v2_response_type: schema.response_contract.response_type,
      v2_ui_revision: schema.ui_revision
    });
  }, [
    runtime.present,
    runtime.events,
    workspace,
    onResponseChange,
    schema.response_contract.response_type,
    schema.ui_revision
  ]);

  if (!config || !workspace) {
    return <div className="surface-card unsupported-task">十格框题配置不完整，暂时无法开始。</div>;
  }

  const emit = (eventType: string, capability: string, payload: Record<string, string | number | boolean | null>) =>
    buildRendererEvent(eventType, {
      task_instance_id: taskInstanceId,
      workspace_id: workspace.workspace_id,
      renderer_id: "ten-frame",
      capability_id: capability,
      payload
    });

  const state = runtime.present;
  const verdict = evaluateQuantity(state, config.target);

  const tapCell = (i: number) => {
    if (disabled) return;
    const result = applyCell(state, i, config);
    if (!result.ok) return;
    const filling = result.state.count > state.count;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit(filling ? "COUNTER_ADDED" : "COUNTER_REMOVED", filling ? "fill" : "fill", {
        index: i,
        count: result.state.count,
        tens: result.state.tens
      })
    });
  };

  const makeTen = () => {
    if (disabled) return;
    const result = applyMakeTen(state, config);
    if (!result.ok) return;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit("MAKE_TEN_COMPLETED", "grouping", { tens: result.state.tens, total: totalOf(result.state) })
    });
  };

  const breakTen = () => {
    if (disabled) return;
    const result = applyBreakTen(state);
    if (!result.ok) return;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit("TEN_BROKEN", "grouping", { tens: result.state.tens, total: totalOf(result.state) })
    });
  };

  const undo = () => !disabled && dispatch({ type: "UNDO", event: emit("UNDO", "undo", {}) });
  const reset = () => !disabled && dispatch({ type: "RESET", event: emit("RESET", "reset", {}) });

  const currentFrameCells = Array.from({ length: 10 }, (_, i) => i);

  return (
    <div className="manipulative-card ten-frame-v2" data-testid="ten-frame-v2">
      <div className="manipulative-heading">
        <div>
          <strong>十格框</strong>
          <span>点格子放圆片，满了十个可以打包成一袋，摆到目标数量后提交。</span>
        </div>
        <div className="workspace-actions">
          <button type="button" data-testid="tf-undo" disabled={disabled || runtime.history.length === 0} onClick={undo}>
            撤销
          </button>
          <button type="button" data-testid="tf-reset" disabled={disabled} onClick={reset}>
            重置
          </button>
        </div>
      </div>

      {state.tens > 0 && (
        <div className="tf-tens" data-testid="tf-tens">
          {Array.from({ length: state.tens }, (_, i) => (
            <span key={i} className="tf-bundle">十×1</span>
          ))}
        </div>
      )}

      <div className="tf-frame" data-testid="tf-current-frame">
        {currentFrameCells.map(i => {
          const filled = i < state.count; // count===10 时 i<10 恒真=满框
          return (
            <button
              key={i}
              type="button"
              data-testid={`tf-cell-${i}`}
              className={`tf-cell ${filled ? "filled" : ""}`}
              disabled={disabled || state.count === 10}
              aria-label={`第${i + 1}格`}
              onClick={() => tapCell(i)}
            >
              {filled ? "●" : "○"}
            </button>
          );
        })}
      </div>

      <div className="tf-actions">
        <button
          type="button"
          data-testid="tf-make-ten"
          className="secondary-button"
          disabled={disabled || state.count !== 10 || state.tens >= config.maxFrames}
          onClick={makeTen}
        >
          打包成十
        </button>
        <button
          type="button"
          data-testid="tf-break-ten"
          className="secondary-button"
          disabled={disabled || state.tens === 0}
          onClick={breakTen}
        >
          拆开一袋
        </button>
        <span data-testid="tf-total">现在一共 {totalOf(state)} 个（目标 {config.target}）</span>
      </div>

      <div className={`tf-evaluation ${verdict.toLowerCase()}`} data-testid="tf-evaluation">
        {verdict === "PASS" ? "摆好了" : verdict === "FAIL" ? "数量还要检查" : "先放圆片"}
      </div>

      <button
        type="button"
        className="primary-button"
        data-testid="tf-submit"
        // P0-01 口径：EMPTY 拦提交；PASS∪FAIL 可达后端。
        disabled={disabled || verdict === "EMPTY"}
        onClick={onSubmit}
      >
        提交这道题
      </button>
    </div>
  );
}
