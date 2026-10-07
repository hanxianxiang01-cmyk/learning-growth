"use client";

/**
 * place-value V2 组件（FE-1419 R06）。runtime 装配对齐 TenFrameV2/BarModelV2：
 * rendererWorkspaceReducer（undo/history 内建）+ buildRendererEvent（UPPER_SNAKE）。
 *
 * 牌堆点选 → 位值框放入/交换/收回。错误分类"位值混淆"（place_confusion）
 * 由纯函数层产出、序列化进 Evidence；EMPTY（没放满）拦提交，放满即可提交
 * （位置对错后端权威判——P0-01 口径）。
 */

import { useEffect, useMemo, useReducer, useRef } from "react";
import type { TaskResponse, V2TaskUiSchema } from "@/src/lib/api/contracts";
import {
  applyPick,
  applySlot,
  evaluatePlaceValue,
  initialPlaceValueV2State,
  parsePlaceValueConfig,
  placeValueAnswer,
  serializePlaceValueV2,
  type PlaceValueV2Config,
  type PlaceValueV2State
} from "@/src/features/task-renderer/placeValueV2";
import { buildRendererEvent, createRendererWorkspaceState, rendererWorkspaceReducer } from "@/src/features/task-renderer/rendererRuntime";

type Props = {
  taskInstanceId: string;
  schema: V2TaskUiSchema;
  response: TaskResponse;
  disabled?: boolean;
  onResponseChange: (response: TaskResponse) => void;
  onSubmit: () => void;
};

export function PlaceValueV2({
  taskInstanceId,
  schema,
  response,
  disabled,
  onResponseChange,
  onSubmit
}: Props) {
  const workspace = schema.workspaces[0];
  const config = useMemo(
    () => (workspace ? parsePlaceValueConfig(workspace.config as Record<string, unknown>) : null),
    [workspace]
  );
  const [runtime, dispatch] = useReducer(
    rendererWorkspaceReducer<PlaceValueV2State>,
    config ? initialPlaceValueV2State(config) : { pool: [], slots: [], picked: null },
    createRendererWorkspaceState
  );
  const responseRef = useRef(response);
  responseRef.current = response;

  useEffect(() => {
    dispatch({ type: "RESET" });
  }, [schema.ui_revision]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!config || !workspace) return;
    const answer = placeValueAnswer(runtime.present, config);
    onResponseChange({
      ...responseRef.current,
      answer: answer === null ? "" : String(answer),
      interaction_events: runtime.events,
      v2_workspaces: [
        { workspace_id: workspace.workspace_id, data: serializePlaceValueV2(runtime.present, config) }
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
    return <div className="surface-card unsupported-task">位值板题配置不完整。</div>;
  }

  const emit = (eventType: string, payload: Record<string, string | number | boolean | null>) =>
    buildRendererEvent(eventType, {
      task_instance_id: taskInstanceId,
      workspace_id: workspace.workspace_id,
      renderer_id: "place-value",
      capability_id: "select",
      payload
    });

  const state = runtime.present;
  const verdict = evaluatePlaceValue(state, config);

  const pickCard = (i: number) => {
    if (disabled) return;
    const result = applyPick(state, i);
    if (!result.ok) return;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit(result.state.picked === i ? "DIGIT_PICKED" : "DIGIT_UNPICKED", {
        digit: state.pool[i],
        index: i
      })
    });
  };

  const tapSlot = (j: number) => {
    if (disabled) return;
    const result = applySlot(state, j);
    if (!result.ok) return;
    const digit = state.picked !== null ? state.pool[state.picked] : state.slots[j];
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit(
        result.action === "place" ? "DIGIT_PLACED" : result.action === "swap" ? "DIGIT_SWAPPED" : "DIGIT_RETURNED",
        { place: config.places[j], digit: digit ?? 0, slot: j }
      )
    });
  };

  const undo = () => !disabled && dispatch({ type: "UNDO", event: emit("UNDO", {}) });
  const reset = () => !disabled && dispatch({ type: "RESET", event: emit("RESET", {}) });

  return (
    <div className="manipulative-card place-value-v2" data-testid="place-value-v2">
      <div className="manipulative-heading">
        <div>
          <strong>位值板</strong>
          <span>点一张数字卡，再点对应的位值框放进去。放满三个框就能提交。</span>
        </div>
        <div className="workspace-actions">
          <button
            type="button"
            data-testid="pv-undo"
            disabled={disabled || runtime.history.length === 0}
            onClick={undo}
          >
            撤销
          </button>
          <button type="button" data-testid="pv-reset" disabled={disabled} onClick={reset}>
            重置
          </button>
        </div>
      </div>

      <div className="pv-slots" data-testid="pv-slots">
        {config.places.map((place, j) => {
          const value = state.slots[j];
          return (
            <button
              type="button"
              key={place}
              data-testid={`pv-slot-${j}`}
              className={`pv-slot ${value !== null ? "filled" : ""}`}
              disabled={disabled}
              onClick={() => tapSlot(j)}
            >
              <span className="pv-place-name">{place}</span>
              <span className="pv-digit" data-testid={`pv-slot-digit-${j}`}>
                {value ?? " "}
              </span>
            </button>
          );
        })}
      </div>

      <div className="pv-pool" data-testid="pv-pool">
        {state.pool.map((digit, i) => (
          <button
            type="button"
            key={`${digit}-${i}`}
            data-testid={`pv-tile-${digit}`}
            className={`pv-tile ${state.picked === i ? "picked" : ""}`}
            disabled={disabled}
            onClick={() => pickCard(i)}
          >
            {digit}
          </button>
        ))}
        {state.pool.length === 0 && <span className="pv-pool-empty">牌都放好啦</span>}
      </div>

      <div className={`pv-evaluation ${verdict.status.toLowerCase()}`} data-testid="pv-evaluation">
        {verdict.status === "EMPTY"
          ? "还有框没放上数字"
          : verdict.status === "PASS"
            ? `位值放对了：${placeValueAnswer(state, config)}`
            : "数字都在，但有几张站错了位置——想想哪个才是百位"}
      </div>

      <button
        type="button"
        className="primary-button"
        data-testid="pv-submit"
        // P0-01 口径：EMPTY（没放满）拦提交；PASS∪FAIL 可达后端。
        disabled={disabled || verdict.status === "EMPTY"}
        onClick={onSubmit}
      >
        提交这道题
      </button>
    </div>
  );
}
