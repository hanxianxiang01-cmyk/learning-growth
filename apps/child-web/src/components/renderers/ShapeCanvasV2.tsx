"use client";

/**
 * shape-canvas V2 组件（FE-1425 R13）。runtime 装配对齐 ShapeGalleryV2。
 *
 * 点阵板依序点顶点（draw=POINT_ADDED、delete=撤点/清空），自动闭合预览。
 * geometry evaluator 三分类（vertex_count/not_right_angle/wrong_size）各有靶；
 * 面积答案=shoelace，平行四边形面积恰好=目标 → 判对+not_right_angle 原料
 * （解耦第四次运用）。
 */

import { useEffect, useMemo, useReducer, useRef } from "react";
import type { TaskResponse, V2TaskUiSchema } from "@/src/lib/api/contracts";
import {
  applyAddPoint,
  applyRemoveLast,
  evaluateShapeCanvas,
  initialShapeCanvasV2State,
  parseShapeCanvasConfig,
  polygonArea,
  serializeShapeCanvasV2,
  shapeCanvasAnswer,
  type ShapeCanvasV2State
} from "@/src/features/task-renderer/shapeCanvasV2";
import { buildRendererEvent, createRendererWorkspaceState, rendererWorkspaceReducer } from "@/src/features/task-renderer/rendererRuntime";

type Props = {
  taskInstanceId: string;
  schema: V2TaskUiSchema;
  response: TaskResponse;
  disabled?: boolean;
  onResponseChange: (response: TaskResponse) => void;
  onSubmit: () => void;
};

const CELL = 56;
const PAD = 24;

export function ShapeCanvasV2({
  taskInstanceId,
  schema,
  response,
  disabled,
  onResponseChange,
  onSubmit
}: Props) {
  const workspace = schema.workspaces[0];
  const config = useMemo(
    () => (workspace ? parseShapeCanvasConfig(workspace.config as Record<string, unknown>) : null),
    [workspace]
  );
  const [runtime, dispatch] = useReducer(
    rendererWorkspaceReducer<ShapeCanvasV2State>,
    { vertices: [] },
    createRendererWorkspaceState
  );
  const responseRef = useRef(response);
  responseRef.current = response;

  useEffect(() => {
    if (config) dispatch({ type: "SET_STATE", state: initialShapeCanvasV2State() });
  }, [config, schema.ui_revision]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!config || !workspace) return;
    const answer = shapeCanvasAnswer(runtime.present);
    onResponseChange({
      ...responseRef.current,
      answer: answer === null ? "" : String(answer),
      interaction_events: runtime.events,
      v2_workspaces: [
        { workspace_id: workspace.workspace_id, data: serializeShapeCanvasV2(runtime.present, config) }
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
    return <div className="surface-card unsupported-task">图形画布题配置不完整。</div>;
  }

  const emit = (eventType: string, payload: Record<string, string | number | boolean | null>) =>
    buildRendererEvent(eventType, {
      task_instance_id: taskInstanceId,
      workspace_id: workspace.workspace_id,
      renderer_id: "shape-canvas",
      capability_id: "draw",
      payload
    });

  const state = runtime.present;
  const verdict = evaluateShapeCanvas(state, config);
  const v = state.vertices;

  const clickPoint = (x: number, y: number) => {
    if (disabled) return;
    const result = applyAddPoint(state, config, x, y);
    if (!result.ok) {
      if (result.code === "DUPLICATE_POINT" || result.code === "MAX_VERTICES") {
        dispatch({
          type: "SET_STATE",
          state,
          event: emit("SHAPE_POINT_REJECTED", { x, y, code: result.code })
        });
      }
      return;
    }
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit("SHAPE_POINT_ADDED", { x, y, order: result.state.vertices.length })
    });
  };

  const removeLast = () => {
    if (disabled) return;
    const result = applyRemoveLast(state);
    if (!result.ok) return;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit("SHAPE_POINT_DELETED", { count: result.state.vertices.length })
    });
  };

  const undo = () => !disabled && dispatch({ type: "UNDO", event: emit("UNDO", {}) });
  const reset = () =>
    !disabled && config &&
    dispatch({ type: "SET_STATE", state: initialShapeCanvasV2State(), event: emit("RESET", {}) });

  const span = (config.grid - 1) * CELL;
  const side = span + PAD * 2;
  const px = (p: { x: number; y: number }) => ({ cx: PAD + p.x * CELL, cy: PAD + p.y * CELL });
  const polyPoints = v.map(p => `${PAD + p.x * CELL},${PAD + p.y * CELL}`).join(" ");
  const area = v.length >= 3 ? polygonArea(v) : null;

  return (
    <div className="manipulative-card shape-canvas-v2" data-testid="shape-canvas-v2">
      <div className="manipulative-heading">
        <div>
          <strong>钉子板画图</strong>
          <span>按顺序点钉子上色，画出面积为 {config.targetArea} 的长方形；点「撤一个点」删除最后一个点。</span>
        </div>
        <div className="workspace-actions">
          <button type="button" data-testid="sc-remove" disabled={disabled || v.length === 0} onClick={removeLast}>
            撤一个点
          </button>
          <button type="button" data-testid="sc-undo" disabled={disabled || runtime.history.length === 0} onClick={undo}>
            撤销
          </button>
          <button type="button" data-testid="sc-reset" disabled={disabled} onClick={reset}>
            清空
          </button>
        </div>
      </div>

      <svg
        data-testid="sc-board"
        width={side}
        height={side}
        className="sc-board"
        role="img"
        aria-label="点阵画图板"
      >
        {Array.from({ length: config.grid - 1 }, (_, i) => (
          <line key={`h${i}`} className="sc-line" x1={PAD} y1={PAD + i * CELL} x2={PAD + span} y2={PAD + i * CELL} />
        ))}
        {Array.from({ length: config.grid - 1 }, (_, i) => (
          <line key={`v${i}`} className="sc-line" x1={PAD + i * CELL} y1={PAD} x2={PAD + i * CELL} y2={PAD + span} />
        ))}
        {v.length >= 3 && (
          <polygon data-testid="sc-polygon" points={polyPoints} className="sc-polygon" />
        )}
        {v.map((p, i) => (
          <g key={`vp-${i}`}>
            <circle {...px(p)} r={11} className="sc-vertex" data-testid={`sc-vertex-${i}`} />
            <text {...px(p)} className="sc-vertex-index" dy={5} textAnchor="middle">{i + 1}</text>
          </g>
        ))}
        {Array.from({ length: config.grid }, (_, gy) =>
          Array.from({ length: config.grid }, (_, gx) => {
            const taken = v.some(p => p.x === gx && p.y === gy);
            return (
              <circle
                key={`p-${gx}-${gy}`}
                cx={PAD + gx * CELL}
                cy={PAD + gy * CELL}
                r={taken ? 10 : 7}
                className={taken ? "sc-peg taken" : "sc-peg"}
                data-testid={`sc-peg-${gx}-${gy}`}
                onClick={() => clickPoint(gx, gy)}
              />
            );
          })
        )}
      </svg>

      <div className="sc-meta" data-testid="sc-meta">
        已点 <strong data-testid="sc-vertex-count">{v.length}</strong> 个顶点
        {area !== null && <> · 面积 <strong data-testid="sc-area">{area}</strong></>}
      </div>

      <div className={`sc-evaluation ${verdict.status.toLowerCase()}`} data-testid="sc-evaluation">
        {verdict.status === "EMPTY"
          ? "至少点 3 个点才围得出图形"
          : verdict.status === "PASS"
            ? `面积 ${area}，长方形画好啦`
            : verdict.error === "vertex_count"
              ? "围是围起来了，但长方形要 4 个顶点——你现在点了 " + v.length + " 个"
              : verdict.error === "not_right_angle"
                ? "四条边歪歪扭扭的——长方形每个角都要方方正正（直角）"
                : `角是直的，但面积是 ${area}，题目要 ${config.targetArea}`}
      </div>

      <button
        type="button"
        className="primary-button"
        data-testid="sc-submit"
        // P0-01 口径：EMPTY（<3 点）拦提交；PASS∪FAIL 可达后端。
        disabled={disabled || verdict.status === "EMPTY"}
        onClick={onSubmit}
      >
        提交这幅图
      </button>
    </div>
  );
}
