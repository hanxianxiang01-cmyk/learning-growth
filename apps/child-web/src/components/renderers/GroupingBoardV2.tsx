"use client";

/**
 * grouping-board V2 组件（FE-1422 R09）。runtime 装配对齐 ArrayBoardV2。
 *
 * 平均分物三步：建组（圈人）→ 逐组发糖（点组 +1）→ 收回（组内 −1）。
 * 空组可解散（拆组）；池子发完才形成可提交的答案（EMPTY 口径）。
 * 分组过程事件链 GROUP_CREATED/REMOVED + ITEM_ADDED/REMOVED = Gap Evidence。
 */

import { useEffect, useMemo, useReducer, useRef } from "react";
import type { TaskResponse, V2TaskUiSchema } from "@/src/lib/api/contracts";
import {
  applyAddGroup,
  applyAddItem,
  applyRemoveGroup,
  applyRemoveItem,
  evaluateGrouping,
  groupingAnswer,
  initialGroupingV2State,
  parseGroupingConfig,
  serializeGroupingBoardV2,
  type GroupingBoardV2State
} from "@/src/features/task-renderer/groupingBoardV2";
import { buildRendererEvent, createRendererWorkspaceState, rendererWorkspaceReducer } from "@/src/features/task-renderer/rendererRuntime";

type Props = {
  taskInstanceId: string;
  schema: V2TaskUiSchema;
  response: TaskResponse;
  disabled?: boolean;
  onResponseChange: (response: TaskResponse) => void;
  onSubmit: () => void;
};

export function GroupingBoardV2({
  taskInstanceId,
  schema,
  response,
  disabled,
  onResponseChange,
  onSubmit
}: Props) {
  const workspace = schema.workspaces[0];
  const config = useMemo(
    () => (workspace ? parseGroupingConfig(workspace.config as Record<string, unknown>) : null),
    [workspace]
  );
  const [runtime, dispatch] = useReducer(
    rendererWorkspaceReducer<GroupingBoardV2State>,
    { groups: [], pool: 0 },
    createRendererWorkspaceState
  );
  const responseRef = useRef(response);
  responseRef.current = response;

  // config/revision 变化 → 以 items 重灌池子
  useEffect(() => {
    if (config) dispatch({ type: "SET_STATE", state: initialGroupingV2State(config) });
  }, [config, schema.ui_revision]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!config || !workspace) return;
    const answer = groupingAnswer(runtime.present);
    onResponseChange({
      ...responseRef.current,
      answer: answer === null ? "" : String(answer),
      interaction_events: runtime.events,
      v2_workspaces: [
        { workspace_id: workspace.workspace_id, data: serializeGroupingBoardV2(runtime.present, config) }
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
    return <div className="surface-card unsupported-task">分组板题配置不完整。</div>;
  }

  const emit = (eventType: string, payload: Record<string, string | number | boolean | null>) =>
    buildRendererEvent(eventType, {
      task_instance_id: taskInstanceId,
      workspace_id: workspace.workspace_id,
      renderer_id: "grouping-board",
      capability_id: "grouping",
      payload
    });

  const state = runtime.present;
  const verdict = evaluateGrouping(state, config);

  const addGroup = () => {
    if (disabled) return;
    const result = applyAddGroup(state, config);
    if (!result.ok) return;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit("GROUP_CREATED", { groups: result.state.groups.length })
    });
  };

  const removeGroup = (j: number) => {
    if (disabled) return;
    const result = applyRemoveGroup(state, j);
    if (!result.ok) return;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit("GROUP_REMOVED", { group: j, groups: result.state.groups.length })
    });
  };

  const giveItem = (j: number) => {
    if (disabled) return;
    const result = applyAddItem(state, j);
    if (!result.ok) return;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit("ITEM_ADDED", { group: j, count: result.state.groups[j], pool: result.state.pool })
    });
  };

  const takeItem = (j: number) => {
    if (disabled) return;
    const result = applyRemoveItem(state, j);
    if (!result.ok) return;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit("ITEM_REMOVED", { group: j, count: result.state.groups[j], pool: result.state.pool })
    });
  };

  const undo = () => !disabled && dispatch({ type: "UNDO", event: emit("UNDO", {}) });
  const reset = () =>
    !disabled && config &&
    dispatch({ type: "SET_STATE", state: initialGroupingV2State(config), event: emit("RESET", {}) });

  return (
    <div className="manipulative-card grouping-board-v2" data-testid="grouping-board-v2">
      <div className="manipulative-heading">
        <div>
          <strong>分一分</strong>
          <span>先圈出{config.targetGroups}个组，再把糖一颗一颗发进去，每组要一样多。</span>
        </div>
        <div className="workspace-actions">
          <button type="button" data-testid="gb-undo" disabled={disabled || runtime.history.length === 0} onClick={undo}>
            撤销
          </button>
          <button type="button" data-testid="gb-reset" disabled={disabled} onClick={reset}>
            重置
          </button>
        </div>
      </div>

      <div className="gb-pool" data-testid="gb-pool">
        <span className="gb-pool-label">还没分：</span>
        <div className="gb-pool-items">
          {Array.from({ length: state.pool }, (_, i) => (
            <span key={i} className="gb-candy" />
          ))}
        </div>
        <strong data-testid="gb-pool-count">{state.pool}</strong>
      </div>

      <div className="gb-groups" data-testid="gb-groups">
        {state.groups.map((size, j) => (
          <div className="gb-group" key={j} data-testid={`gb-group-${j}`}>
            <span className="gb-group-name">第{j + 1}组</span>
            <div className="gb-group-items">
              {Array.from({ length: size }, (_, i) => (
                <span key={i} className="gb-candy in-group" data-testid={`gb-candy-${j}-${i}`} />
              ))}
            </div>
            <div className="gb-group-actions">
              <button
                type="button"
                data-testid={`gb-take-${j}`}
                disabled={disabled || size === 0}
                onClick={() => takeItem(j)}
                aria-label="收回一颗"
              >
                −
              </button>
              <strong data-testid={`gb-group-count-${j}`}>{size}</strong>
              <button
                type="button"
                data-testid={`gb-give-${j}`}
                disabled={disabled || state.pool === 0}
                onClick={() => giveItem(j)}
                aria-label="发一颗"
              >
                ＋
              </button>
              <button
                type="button"
                data-testid={`gb-dismiss-${j}`}
                className="gb-dismiss"
                disabled={disabled || size > 0}
                onClick={() => removeGroup(j)}
                aria-label="解散这组"
              >
                解散
              </button>
            </div>
          </div>
        ))}
        {state.groups.length < config.maxGroups && (
          <button type="button" className="gb-new-group" data-testid="gb-add-group" disabled={disabled} onClick={addGroup}>
            ＋圈一个组
          </button>
        )}
      </div>

      <div className={`gb-evaluation ${verdict.status.toLowerCase()}`} data-testid="gb-evaluation">
        {verdict.status === "EMPTY"
          ? state.groups.length === 0
            ? "先圈一个组吧"
            : `还有 ${state.pool} 颗没分出去`
          : verdict.status === "PASS"
            ? `每组分 ${groupingAnswer(state)} 颗，分好啦`
            : verdict.error === "count"
              ? `题目要分给 ${config.targetGroups} 个组，你现在分了 ${state.groups.length} 组`
              : "组数对了，但有的组多有的组少——平均才公平哦"}
      </div>

      <button
        type="button"
        className="primary-button"
        data-testid="gb-submit"
        // P0-01 口径：EMPTY（没发完/没建组）拦提交；PASS∪FAIL 可达后端。
        disabled={disabled || verdict.status === "EMPTY"}
        onClick={onSubmit}
      >
        提交这道题
      </button>
    </div>
  );
}
