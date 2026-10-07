"use client";

/**
 * sorting-board V2 组件（FE-1426 R14）。runtime 装配对齐 ShapeGalleryV2。
 *
 * 两步点选交换（点第一张=拿起，点第二张=换位；再点自己=放下）。
 * 卡面字号按 visual_rank（干扰维度，与数值故意错开）——按字号排 →
 * dimension_confusion 原料（Diagnosis P0"比较维度错误"）。
 * SORT_CARD_SELECTED/SWAPPED/UNDOED + swaps 序列 = Gap"排序过程"。
 */

import { useEffect, useMemo, useReducer, useRef } from "react";
import type { TaskResponse, V2TaskUiSchema } from "@/src/lib/api/contracts";
import {
  applySelectCard,
  applySwap,
  applyUndoSwap,
  evaluateSorting,
  initialSortingV2State,
  parseSortingConfig,
  serializeSortingBoardV2,
  sortingAnswer,
  type SortingBoardV2State
} from "@/src/features/task-renderer/sortingBoardV2";
import { buildRendererEvent, createRendererWorkspaceState, rendererWorkspaceReducer } from "@/src/features/task-renderer/rendererRuntime";

type Props = {
  taskInstanceId: string;
  schema: V2TaskUiSchema;
  response: TaskResponse;
  disabled?: boolean;
  onResponseChange: (response: TaskResponse) => void;
  onSubmit: () => void;
};

/** visual_rank 1..4 → 字号档位（干扰维度显性化）。 */
const RANK_FONT: Record<number, number> = { 1: 15, 2: 20, 3: 27, 4: 36 };

export function SortingBoardV2({
  taskInstanceId,
  schema,
  response,
  disabled,
  onResponseChange,
  onSubmit
}: Props) {
  const workspace = schema.workspaces[0];
  const config = useMemo(
    () => (workspace ? parseSortingConfig(workspace.config as Record<string, unknown>) : null),
    [workspace]
  );
  const [runtime, dispatch] = useReducer(
    rendererWorkspaceReducer<SortingBoardV2State>,
    { order: [], selected: null, swaps: [] },
    createRendererWorkspaceState
  );
  const responseRef = useRef(response);
  responseRef.current = response;

  useEffect(() => {
    if (config) dispatch({ type: "SET_STATE", state: initialSortingV2State(config) });
  }, [config, schema.ui_revision]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!config || !workspace) return;
    const answer = sortingAnswer(runtime.present, config);
    onResponseChange({
      ...responseRef.current,
      answer: answer === null ? "" : String(answer),
      interaction_events: runtime.events,
      v2_workspaces: [
        { workspace_id: workspace.workspace_id, data: serializeSortingBoardV2(runtime.present, config) }
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
    return <div className="surface-card unsupported-task">排序板题配置不完整。</div>;
  }

  const emit = (eventType: string, payload: Record<string, string | number | boolean | null>) =>
    buildRendererEvent(eventType, {
      task_instance_id: taskInstanceId,
      workspace_id: workspace.workspace_id,
      renderer_id: "sorting-board",
      capability_id: "sort",
      payload
    });

  const state = runtime.present;
  const verdict = evaluateSorting(state, config);
  const itemOf = (id: string) => config.items.find(i => i.id === id)!;

  const clickCard = (id: string) => {
    if (disabled) return;
    if (state.selected !== null && state.selected !== id) {
      const result = applySwap(state, config, id);
      if (!result.ok) return;
      dispatch({
        type: "SET_STATE",
        state: result.state,
        event: emit("SORT_CARD_SWAPPED", { from: result.from!, to: result.to!, swap: result.state.swaps.length })
      });
      return;
    }
    const result = applySelectCard(state, config, id);
    if (!result.ok) return;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit(result.deselected ? "SORT_CARD_UNPICKED" : "SORT_CARD_SELECTED", {
        card: id,
        value: itemOf(id).value
      })
    });
  };

  const undoSwap = () => {
    if (disabled) return;
    const result = applyUndoSwap(state);
    if (!result.ok) return;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit("SORT_UNDOED", { swap: result.state.swaps.length + 1, remain: result.state.swaps.length })
    });
  };

  const undo = () => !disabled && dispatch({ type: "UNDO", event: emit("UNDO", {}) });
  const reset = () =>
    !disabled && config &&
    dispatch({ type: "SET_STATE", state: initialSortingV2State(config), event: emit("RESET", {}) });

  return (
    <div className="manipulative-card sorting-board-v2" data-testid="sorting-board-v2">
      <div className="manipulative-heading">
        <div>
          <strong>排排队</strong>
          <span>按数字**从小到大**排：先点一张卡拿起来，再点另一张——两张就交换位置。（卡片字大小是画的，数字大小才是真的哦）</span>
        </div>
        <div className="workspace-actions">
          <button type="button" data-testid="sb-undo-swap" className="sb-undo-swap" disabled={disabled || state.swaps.length === 0} onClick={undoSwap}>
            退回上次交换
          </button>
          <button type="button" data-testid="sb-undo" disabled={disabled || runtime.history.length === 0} onClick={undo}>
            撤销
          </button>
          <button type="button" data-testid="sb-reset" disabled={disabled} onClick={reset}>
            重置
          </button>
        </div>
      </div>

      <div className="sb-cards" data-testid="sb-cards">
        {state.order.map((id, i) => {
          const item = itemOf(id);
          return (
            <button
              key={id}
              type="button"
              data-testid={`sb-card-${i}`}
              data-value={item.value}
              className={state.selected === id ? "sb-card picked" : "sb-card"}
              disabled={disabled}
              onClick={() => clickCard(id)}
              style={{ fontSize: `${RANK_FONT[item.visual_rank] ?? 18}px` }}
            >
              {item.value}
            </button>
          );
        })}
      </div>

      <div className={`sb-evaluation ${verdict.status.toLowerCase()}`} data-testid="sb-evaluation">
        {verdict.status === "EMPTY"
          ? "先点两张卡交换，把它们排好"
          : verdict.status === "PASS"
            ? `从小到大排好了：${state.order.map(id => itemOf(id).value).join(" < ")}，交换了 ${state.swaps.length} 次`
            : verdict.error === "reversed"
              ? "排得很整齐——但方向反啦，题目要**从小到大**"
              : verdict.error === "dimension_confusion"
                ? "你是按字的大小排的吧？数字大小不看字多大，看它是几"
                : `顺序还差一点：${state.order.map(id => itemOf(id).value).join("、")}，检查一下谁最小`}
      </div>

      <button
        type="button"
        className="primary-button"
        data-testid="sb-submit"
        // P0-01 口径：EMPTY（一次都没交换）拦提交；PASS∪FAIL 可达后端。
        disabled={disabled || verdict.status === "EMPTY"}
        onClick={onSubmit}
      >
        提交排序
      </button>
    </div>
  );
}
