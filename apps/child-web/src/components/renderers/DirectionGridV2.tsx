"use client";

/**
 * direction-grid V2 组件（FE-1427 R15，Batch D 收官）。runtime 装配对齐 SortingBoardV2。
 *
 * 5×5 地图：小标记从起点出发，点与脚下相邻的格=挪一步（对角/隔格拒绝）。
 * 走过的路（path/directions/turns）= Gap"movement sequence"。
 * 答案=终点格编码（组件自动写入，后端标量判分）。
 * 反走 = direction_reversed 原料（Diagnosis P0"方向错误"）；绕路=detour 留痕。
 */

import { useEffect, useMemo, useReducer, useRef } from "react";
import type { TaskResponse, V2TaskUiSchema } from "@/src/lib/api/contracts";
import {
  applyMoveTo,
  applyUndoStep,
  directionGridAnswer,
  evaluateRoute,
  initialDirectionV2State,
  parseDirectionConfig,
  serializeDirectionGridV2,
  type DirectionGridV2State,
  type GridCell
} from "@/src/features/task-renderer/directionGridV2";
import { buildRendererEvent, createRendererWorkspaceState, rendererWorkspaceReducer } from "@/src/features/task-renderer/rendererRuntime";

type Props = {
  taskInstanceId: string;
  schema: V2TaskUiSchema;
  response: TaskResponse;
  disabled?: boolean;
  onResponseChange: (response: TaskResponse) => void;
  onSubmit: () => void;
};

export function DirectionGridV2({
  taskInstanceId,
  schema,
  response,
  disabled,
  onResponseChange,
  onSubmit
}: Props) {
  const workspace = schema.workspaces[0];
  const config = useMemo(
    () => (workspace ? parseDirectionConfig(workspace.config as Record<string, unknown>) : null),
    [workspace]
  );
  const [runtime, dispatch] = useReducer(
    rendererWorkspaceReducer<DirectionGridV2State>,
    { steps: [] },
    createRendererWorkspaceState
  );
  const responseRef = useRef(response);
  responseRef.current = response;

  useEffect(() => {
    if (config) {
      dispatch({ type: "SET_STATE", state: initialDirectionV2State(config) });
    }
  }, [config, schema.ui_revision]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!config || !workspace || runtime.present.steps.length === 0) return;
    const answer = directionGridAnswer(runtime.present, config);
    onResponseChange({
      ...responseRef.current,
      answer: answer === null ? "" : String(answer),
      interaction_events: runtime.events,
      v2_workspaces: [
        { workspace_id: workspace.workspace_id, data: serializeDirectionGridV2(runtime.present, config) }
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
    return <div className="surface-card unsupported-task">方向网格题配置不完整。</div>;
  }

  const emit = (eventType: string, payload: Record<string, string | number | boolean | null>) =>
    buildRendererEvent(eventType, {
      task_instance_id: taskInstanceId,
      workspace_id: workspace.workspace_id,
      renderer_id: "direction-grid",
      capability_id: "navigate",
      payload
    });

  const state = runtime.present;
  const cur = state.steps.length > 0 ? state.steps[state.steps.length - 1] : config.start;
  const verdict = evaluateRoute(state, config);
  const visited = new Set(state.steps.map(s => `${s.r},${s.c}`));

  const clickCell = (r: number, c: number) => {
    if (disabled) return;
    const result = applyMoveTo(state, config, { r, c } as GridCell);
    if (!result.ok) return; // 对角/同格/越界：静默拒绝（提示条说明规则）
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit("PATH_EXTENDED", {
        from: `${cur.r},${cur.c}`,
        to: `${r},${c}`,
        step: result.state.steps.length - 1
      })
    });
  };

  const undoMove = () => {
    if (disabled) return;
    const result = applyUndoStep(state);
    if (!result.ok) return;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit("PATH_STEP_UNDONE", { remain: result.state.steps.length - 1 })
    });
  };

  const undo = () => !disabled && dispatch({ type: "UNDO", event: emit("UNDO", {}) });
  const reset = () =>
    !disabled &&
    dispatch({ type: "SET_STATE", state: initialDirectionV2State(config), event: emit("PATH_CLEARED", {}) });

  const cellRole = (r: number, c: number): string => {
    if (r === config.start.r && c === config.start.c) return "start";
    if (r === config.target.r && c === config.target.c) return "target";
    if (r === cur.r && c === cur.c) return "walker";
    return visited.has(`${r},${c}`) ? "visited" : "";
  };

  return (
    <div className="manipulative-card direction-grid-v2" data-testid="direction-grid-v2">
      <div className="manipulative-heading">
        <div>
          <strong>走一走</strong>
          <span>小人站在格子上：点旁边（上/下/左/右）的格子就走一步，走到目标格。走错可以「退一步」。</span>
        </div>
        <div className="workspace-actions">
          <button type="button" data-testid="dg-undo-move" className="dg-undo-move" disabled={disabled || state.steps.length <= 1} onClick={undoMove}>
            退一步
          </button>
          <button type="button" data-testid="dg-undo" disabled={disabled || runtime.history.length === 0} onClick={undo}>
            撤销
          </button>
          <button type="button" data-testid="dg-reset" disabled={disabled} onClick={reset}>
            重置
          </button>
        </div>
      </div>

      <div
        className="dg-grid"
        data-testid="dg-grid"
        style={{ gridTemplateColumns: `repeat(${config.cols}, 1fr)` }}
      >
        {Array.from({ length: config.rows * config.cols }, (_, i) => {
          const r = Math.floor(i / config.cols);
          const c = i % config.cols;
          const role = cellRole(r, c);
          return (
            <button
              key={i}
              type="button"
              data-testid={`dg-cell-${r}-${c}`}
              data-role={role}
              className={`dg-cell ${role}`.trim()}
              disabled={disabled}
              onClick={() => clickCell(r, c)}
            >
              {r === config.start.r && c === config.start.c ? "起" :
               r === config.target.r && c === config.target.c ? "☆" :
               r === cur.r && c === cur.c ? "●" :
               visited.has(`${r},${c}`) ? "·" : ""}
            </button>
          );
        })}
      </div>

      <div className={`dg-evaluation ${verdict.status.toLowerCase()}`} data-testid="dg-evaluation">
        {verdict.status === "EMPTY"
          ? "小人还在起点——点它旁边的格子走一步试试"
          : verdict.status === "PASS"
            ? verdict.detour
              ? `走到了！不过绕了点路：走了 ${state.steps.length - 1} 步（最短只要 ${Math.abs(config.target.r - config.start.r) + Math.abs(config.target.c - config.start.c)} 步）`
              : `走到了！${state.steps.length - 1} 步直达，路线：${state.steps.map(s => `(${s.r},${s.c})`).join("→")}`
            : verdict.error === "direction_reversed"
              ? "好像把方向走反啦——目标在起点的另一边，你走到了对称的位置"
              : `还没走到 ☆：离目标还差 ${verdict.distance_to_target} 格，看看该往哪边走`}
      </div>

      <button
        type="button"
        className="primary-button"
        data-testid="dg-submit"
        // P0-01 口径：EMPTY（还在起点没动）拦提交；PASS∪FAIL 可达后端。
        disabled={disabled || verdict.status === "EMPTY"}
        onClick={onSubmit}
      >
        提交路线
      </button>
    </div>
  );
}
