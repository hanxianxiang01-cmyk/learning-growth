"use client";

/**
 * array-board V2 组件（FE-1421 R08）。runtime 装配对齐 FormulaBoardV2：
 * rendererWorkspaceReducer + buildRendererEvent。
 *
 * 加/减行列建阵列；点第 j 列可把该列及之后填满（连续填充口径同十格框）；
 * 预览阵列按 rows×cols 画格子，行列调整轨迹即事件链。
 */

import { useEffect, useMemo, useReducer, useRef } from "react";
import type { TaskResponse, V2TaskUiSchema } from "@/src/lib/api/contracts";
import {
  applyColDelta,
  applyRowDelta,
  arrayProduct,
  evaluateArray,
  initialArrayBoardV2State,
  parseArrayBoardConfig,
  serializeArrayBoardV2,
  type ArrayBoardV2Config,
  type ArrayBoardV2State
} from "@/src/features/task-renderer/arrayBoardV2";
import { buildRendererEvent, createRendererWorkspaceState, rendererWorkspaceReducer } from "@/src/features/task-renderer/rendererRuntime";

type Props = {
  taskInstanceId: string;
  schema: V2TaskUiSchema;
  response: TaskResponse;
  disabled?: boolean;
  onResponseChange: (response: TaskResponse) => void;
  onSubmit: () => void;
};

export function ArrayBoardV2({
  taskInstanceId,
  schema,
  response,
  disabled,
  onResponseChange,
  onSubmit
}: Props) {
  const workspace = schema.workspaces[0];
  const config = useMemo(
    () => (workspace ? parseArrayBoardConfig(workspace.config as Record<string, unknown>) : null),
    [workspace]
  );
  const [runtime, dispatch] = useReducer(
    rendererWorkspaceReducer<ArrayBoardV2State>,
    initialArrayBoardV2State(),
    createRendererWorkspaceState
  );
  const responseRef = useRef(response);
  responseRef.current = response;

  useEffect(() => {
    dispatch({ type: "RESET" });
  }, [schema.ui_revision]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!config || !workspace) return;
    const product = arrayProduct(runtime.present);
    onResponseChange({
      ...responseRef.current,
      answer: product === 0 ? "" : String(product),
      interaction_events: runtime.events,
      v2_workspaces: [
        { workspace_id: workspace.workspace_id, data: serializeArrayBoardV2(runtime.present, config) }
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
    return <div className="surface-card unsupported-task">阵列板题配置不完整。</div>;
  }

  const emit = (eventType: string, capability: string, payload: Record<string, string | number | boolean | null>) =>
    buildRendererEvent(eventType, {
      task_instance_id: taskInstanceId,
      workspace_id: workspace.workspace_id,
      renderer_id: "array-board",
      capability_id: capability,
      payload
    });

  const state = runtime.present;
  const verdict = evaluateArray(state, config);

  const changeRow = (delta: number) => {
    if (disabled) return;
    const result = applyRowDelta(state, delta, config);
    if (!result.ok) return;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit(delta === 1 ? "ARRAY_ROW_ADDED" : "ARRAY_ROW_REMOVED", "add_object", {
        rows: result.state.rows,
        columns: result.state.cols
      })
    });
  };

  const changeCol = (delta: number) => {
    if (disabled) return;
    const result = applyColDelta(state, delta, config);
    if (!result.ok) return;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit(delta === 1 ? "ARRAY_COL_ADDED" : "ARRAY_COL_REMOVED", "add_object", {
        rows: state.rows,
        columns: result.state.cols
      })
    });
  };

  const undo = () => !disabled && dispatch({ type: "UNDO", event: emit("UNDO", "undo", {}) });
  const reset = () => !disabled && dispatch({ type: "RESET", event: emit("RESET", "reset", {}) });

  return (
    <div className="manipulative-card array-board-v2" data-testid="array-board-v2">
      <div className="manipulative-heading">
        <div>
          <strong>排排队</strong>
          <span>用行和列排一个方阵，排好数一数一共有几个。</span>
        </div>
        <div className="workspace-actions">
          <button type="button" data-testid="ab-undo" disabled={disabled || runtime.history.length === 0} onClick={undo}>
            撤销
          </button>
          <button type="button" data-testid="ab-reset" disabled={disabled} onClick={reset}>
            重置
          </button>
        </div>
      </div>

      <div className="ab-controls">
        <div className="ab-control-row">
          <span>行（横排）</span>
          <div>
            <button type="button" data-testid="ab-row-minus" disabled={disabled || state.rows === 0} onClick={() => changeRow(-1)} aria-label="减一行">−</button>
            <strong data-testid="ab-rows">{state.rows}</strong>
            <button type="button" data-testid="ab-row-plus" disabled={disabled || state.rows >= config.maxRows} onClick={() => changeRow(1)} aria-label="加一行">＋</button>
          </div>
        </div>
        <div className="ab-control-row">
          <span>列（竖排）</span>
          <div>
            <button type="button" data-testid="ab-col-minus" disabled={disabled || state.cols === 0} onClick={() => changeCol(-1)} aria-label="减一列">−</button>
            <strong data-testid="ab-cols">{state.cols}</strong>
            <button type="button" data-testid="ab-col-plus" disabled={disabled || state.cols >= config.maxCols} onClick={() => changeCol(1)} aria-label="加一列">＋</button>
          </div>
        </div>
      </div>

      <div
        className="ab-grid"
        data-testid="ab-grid"
        style={{ gridTemplateColumns: `repeat(${Math.max(state.cols, 1)}, 34px)` }}
      >
        {Array.from({ length: state.rows * state.cols }, (_, i) => (
          <span key={i} className="ab-dot" data-testid={`ab-cell-${i}`} />
        ))}
        {state.rows * state.cols === 0 && <span className="ab-empty-hint">先加一行、再加一列</span>}
      </div>

      <div className={`ab-evaluation ${verdict.status.toLowerCase()}`} data-testid="ab-evaluation">
        {verdict.status === "EMPTY"
          ? "还没排出阵列"
          : verdict.status === "PASS"
            ? `${state.rows} 行 × ${state.cols} 列 = ${arrayProduct(state)} 个，摆对啦`
            : verdict.error === "transpose"
              ? `数是对的（${arrayProduct(state)} 个），但你把行和列说反了——横着数还是竖着数？`
              : `现在是 ${state.rows} × ${state.cols} = ${arrayProduct(state)} 个，和题目要的不一样`}
      </div>

      <button
        type="button"
        className="primary-button"
        data-testid="ab-submit"
        // P0-01 口径：EMPTY（没摆）拦提交；PASS∪FAIL 可达后端（transpose 积对=后端判对）。
        disabled={disabled || verdict.status === "EMPTY"}
        onClick={onSubmit}
      >
        提交这道题
      </button>
    </div>
  );
}
