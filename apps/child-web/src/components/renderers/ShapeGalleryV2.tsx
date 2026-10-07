"use client";

/**
 * shape-gallery V2 组件（FE-1424 R12）。runtime 装配对齐 EstimationCanvasV2。
 *
 * 图形墙选形两步（点图形=拿起/放下，点家=放进）+ 家里可退回。
 * 五类事件 SHAPE_SELECTED/DESELECTED/PLACED/HOME_REJECTED/RETURNED =
 * Gap Evidence"选择与分类轨迹"（home 序列 + 轨迹事件双通道）。
 * attribute_confusion 拒入时给"属性识别错误"即时提示（Diagnosis P0 前端反馈）。
 */

import { useEffect, useMemo, useReducer, useRef } from "react";
import type { TaskResponse, V2TaskUiSchema } from "@/src/lib/api/contracts";
import {
  applyPlaceHome,
  applyReturnHome,
  applySelect,
  evaluateShapeGallery,
  initialShapeGalleryV2State,
  parseShapeGalleryConfig,
  serializeShapeGalleryV2,
  shapeGalleryAnswer,
  SHAPE_KIND_LABELS,
  targetShapeIds,
  type ShapeGalleryV2State
} from "@/src/features/task-renderer/shapeGalleryV2";
import { buildRendererEvent, createRendererWorkspaceState, rendererWorkspaceReducer } from "@/src/features/task-renderer/rendererRuntime";

type Props = {
  taskInstanceId: string;
  schema: V2TaskUiSchema;
  response: TaskResponse;
  disabled?: boolean;
  onResponseChange: (response: TaskResponse) => void;
  onSubmit: () => void;
};

const SHAPE_EMOJI: Record<string, string> = {
  square: "■",
  rectangle: "▬",
  circle: "●",
  triangle: "▲",
};

export function ShapeGalleryV2({
  taskInstanceId,
  schema,
  response,
  disabled,
  onResponseChange,
  onSubmit
}: Props) {
  const workspace = schema.workspaces[0];
  const config = useMemo(
    () => (workspace ? parseShapeGalleryConfig(workspace.config as Record<string, unknown>) : null),
    [workspace]
  );
  const [runtime, dispatch] = useReducer(
    rendererWorkspaceReducer<ShapeGalleryV2State>,
    { selected: null, home: [] },
    createRendererWorkspaceState
  );
  const responseRef = useRef(response);
  responseRef.current = response;

  useEffect(() => {
    if (config) dispatch({ type: "SET_STATE", state: initialShapeGalleryV2State() });
  }, [config, schema.ui_revision]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!config || !workspace) return;
    const answer = shapeGalleryAnswer(runtime.present);
    onResponseChange({
      ...responseRef.current,
      answer: answer === null ? "" : String(answer),
      interaction_events: runtime.events,
      v2_workspaces: [
        { workspace_id: workspace.workspace_id, data: serializeShapeGalleryV2(runtime.present, config) }
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
    return <div className="surface-card unsupported-task">图形画廊题配置不完整。</div>;
  }

  const emit = (eventType: string, payload: Record<string, string | number | boolean | null>) =>
    buildRendererEvent(eventType, {
      task_instance_id: taskInstanceId,
      workspace_id: workspace.workspace_id,
      renderer_id: "shape-gallery",
      capability_id: "select",
      payload
    });

  const state = runtime.present;
  const verdict = evaluateShapeGallery(state, config);
  const selectedShape = state.selected ? config.shapes.find(s => s.id === state.selected) : null;
  const targetTotal = targetShapeIds(config).length;

  const clickShape = (id: string) => {
    if (disabled) return;
    const result = applySelect(state, config, id);
    if (!result.ok) {
      if (result.code === "IN_HOME") {
        dispatch({ type: "SET_STATE", state, event: emit("SHAPE_HOME_REJECTED", { shape: id, reason: "IN_HOME" }) });
      }
      return;
    }
    const shape = config.shapes.find(s => s.id === id)!;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit(result.deselected ? "SHAPE_DESELECTED" : "SHAPE_SELECTED", {
        shape: id,
        kind: shape.kind
      })
    });
  };

  const placeHome = () => {
    if (disabled) return;
    const result = applyPlaceHome(state, config);
    if (!result.ok) return;
    const id = state.selected!;
    const shape = config.shapes.find(s => s.id === id)!;
    const isTarget = shape.kind === config.targetKind;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit("SHAPE_PLACED", { shape: id, kind: shape.kind, target: isTarget })
    });
  };

  const returnShape = (id: string) => {
    if (disabled) return;
    const result = applyReturnHome(state, id);
    if (!result.ok) return;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit("SHAPE_RETURNED", { shape: id })
    });
  };

  const undo = () => !disabled && dispatch({ type: "UNDO", event: emit("UNDO", {}) });
  const reset = () =>
    !disabled && config &&
    dispatch({ type: "SET_STATE", state: initialShapeGalleryV2State(), event: emit("RESET", {}) });

  const kindOfHome = (id: string) => config.shapes.find(s => s.id === id)?.kind ?? "unknown";

  return (
    <div className="manipulative-card shape-gallery-v2" data-testid="shape-gallery-v2">
      <div className="manipulative-heading">
        <div>
          <strong>图形找家</strong>
          <span>点一个图形拿起来，再点下面的"{SHAPE_KIND_LABELS[config.targetKind]}的家"放进去。</span>
        </div>
        <div className="workspace-actions">
          <button type="button" data-testid="sg-undo" disabled={disabled || runtime.history.length === 0} onClick={undo}>
            撤销
          </button>
          <button type="button" data-testid="sg-reset" disabled={disabled} onClick={reset}>
            重置
          </button>
        </div>
      </div>

      <div className="sg-wall" data-testid="sg-wall">
        {config.shapes.map(s => {
          const inHome = state.home.includes(s.id);
          return (
            <button
              key={s.id}
              type="button"
              data-testid={`sg-shape-${s.id}`}
              className={
                inHome
                  ? "sg-shape in-home"
                  : state.selected === s.id
                    ? "sg-shape picked"
                    : "sg-shape"
              }
              disabled={disabled || inHome}
              onClick={() => clickShape(s.id)}
              style={{ color: s.color }}
            >
              <span className="sg-shape-glyph">{SHAPE_EMOJI[s.kind]}</span>
              <span className="sg-shape-name">{s.name}</span>
            </button>
          );
        })}
      </div>

      <div className={`sg-home ${selectedShape ? "waiting" : ""}`} data-testid="sg-home" onClick={placeHome}>
        <span className="sg-home-label">{SHAPE_KIND_LABELS[config.targetKind]}的家</span>
        <div className="sg-home-items" data-testid="sg-home-items">
          {state.home.map(id => (
            <button
              key={id}
              type="button"
              data-testid={`sg-home-${id}`}
              className="sg-home-item"
              disabled={disabled}
              onClick={e => {
                e.stopPropagation();
                returnShape(id);
              }}
            >
              {SHAPE_EMOJI[kindOfHome(id)]}
            </button>
          ))}
          {state.home.length === 0 && <span className="sg-home-empty">还空着</span>}
        </div>
        <strong data-testid="sg-home-count">{state.home.length}</strong>
      </div>

      <div className={`sg-evaluation ${verdict.status.toLowerCase()}`} data-testid="sg-evaluation">
        {verdict.status === "EMPTY"
          ? selectedShape
            ? `手里拿着「${selectedShape.name}」，点下面的家放进去`
            : "先从墙上点一个图形"
          : verdict.status === "PASS"
            ? `找到全部 ${targetTotal} 个${SHAPE_KIND_LABELS[config.targetKind]}，真棒`
            : verdict.error === "attribute_confusion"
              ? `家里混进了不是${SHAPE_KIND_LABELS[config.targetKind]}的朋友——仔细看看它的边和角`
              : "都放对了，但还有朋友在外面没回家"}
      </div>

      <button
        type="button"
        className="primary-button"
        data-testid="sg-submit"
        // P0-01 口径：EMPTY（家空）拦提交；PASS∪FAIL 可达后端。
        disabled={disabled || verdict.status === "EMPTY"}
        onClick={onSubmit}
      >
        提交这道题
      </button>
    </div>
  );
}
