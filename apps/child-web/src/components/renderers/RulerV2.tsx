"use client";

/**
 * ruler V2 组件（FE-1429 R16，Batch E 起手）。runtime 装配对齐 DirectionGridV2。
 *
 * 尺面上画着被测物体（跨 left..right，故意不从 0 开始）——点刻度放两个标记
 * 夹住它：第 1 点=左标记、第 2 点=右标记、第 3 点起清空重放。
 * 答案=两标记间隔（组件自动填，后端标量判分）。
 * 零起误读 {0, right} → from_zero_reading（Diagnosis P0"刻度读取错误"精确靶）；
 * 平移段 span 对但没夹住物体 → 判对 + aligned=false 留痕（解耦第七次运用）。
 */

import { useEffect, useMemo, useReducer, useRef } from "react";
import type { TaskResponse, V2TaskUiSchema } from "@/src/lib/api/contracts";
import {
  applyClearMarks,
  applyPlaceMark,
  evaluateMeasurement,
  initialRulerV2State,
  parseRulerConfig,
  rulerAnswer,
  serializeRulerV2,
  type RulerV2State
} from "@/src/features/task-renderer/rulerV2";
import { buildRendererEvent, createRendererWorkspaceState, rendererWorkspaceReducer } from "@/src/features/task-renderer/rendererRuntime";

type Props = {
  taskInstanceId: string;
  schema: V2TaskUiSchema;
  response: TaskResponse;
  disabled?: boolean;
  onResponseChange: (response: TaskResponse) => void;
  onSubmit: () => void;
};

export function RulerV2({
  taskInstanceId,
  schema,
  response,
  disabled,
  onResponseChange,
  onSubmit
}: Props) {
  const workspace = schema.workspaces[0];
  const config = useMemo(
    () => (workspace ? parseRulerConfig(workspace.config as Record<string, unknown>) : null),
    [workspace]
  );
  const [runtime, dispatch] = useReducer(
    rendererWorkspaceReducer<RulerV2State>,
    { marks: [] },
    createRendererWorkspaceState
  );
  const responseRef = useRef(response);
  responseRef.current = response;

  useEffect(() => {
    dispatch({ type: "SET_STATE", state: initialRulerV2State() });
  }, [config, schema.ui_revision]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!config || !workspace) return;
    const answer = rulerAnswer(runtime.present);
    onResponseChange({
      ...responseRef.current,
      answer: answer === null ? "" : String(answer),
      interaction_events: runtime.events,
      v2_workspaces: [
        { workspace_id: workspace.workspace_id, data: serializeRulerV2(runtime.present, config) }
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
    return <div className="surface-card unsupported-task">量尺题配置不完整。</div>;
  }

  const emit = (eventType: string, payload: Record<string, string | number | boolean | null>) =>
    buildRendererEvent(eventType, {
      task_instance_id: taskInstanceId,
      workspace_id: workspace.workspace_id,
      renderer_id: "ruler",
      capability_id: "measure",
      payload
    });

  const state = runtime.present;
  const verdict = evaluateMeasurement(state, config);
  const markAt = (v: number) => (state.marks.includes(v) ? "marked" : "");

  const clickTick = (v: number) => {
    if (disabled) return;
    const result = applyPlaceMark(state, config, v);
    if (!result.ok) return;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit("RULER_MARK_SET", {
        value: v,
        index: result.state.marks.length,
        restarting: result.restarting
      })
    });
  };

  const clearMarks = () => {
    if (disabled) return;
    const result = applyClearMarks(state);
    if (!result.ok) return;
    dispatch({ type: "SET_STATE", state: result.state, event: emit("RULER_MARKS_CLEARED", {}) });
  };

  const undo = () => !disabled && dispatch({ type: "UNDO", event: emit("UNDO", {}) });
  const reset = () =>
    !disabled &&
    dispatch({ type: "SET_STATE", state: initialRulerV2State(), event: emit("RULER_MARKS_CLEARED", {}) });

  const ticks = Array.from({ length: config.max + 1 }, (_, i) => i);
  const pct = (v: number) => `${(v / config.max) * 100}%`;

  return (
    <div className="manipulative-card ruler-v2" data-testid="ruler-v2">
      <div className="manipulative-heading">
        <div>
          <strong>量一量</strong>
          <span>铅笔躺在尺子上：先点它**左头**对的刻度，再点**右头**对的刻度——两个红色标记之间的距离就是长度。</span>
        </div>
        <div className="workspace-actions">
          <button type="button" data-testid="rl-clear" className="rl-clear" disabled={disabled || state.marks.length === 0} onClick={clearMarks}>
            清标记
          </button>
          <button type="button" data-testid="rl-undo" disabled={disabled || runtime.history.length === 0} onClick={undo}>
            撤销
          </button>
          <button type="button" data-testid="rl-reset" disabled={disabled} onClick={reset}>
            重置
          </button>
        </div>
      </div>

      <div className="rl-ruler" data-testid="rl-ruler">
        <div
          className="rl-object"
          data-testid="rl-object"
          data-left={config.left}
          data-right={config.right}
          style={{ left: pct(config.left), width: pct(config.right - config.left) }}
        >
          ✏️
        </div>
        <div className="rl-ticks" data-testid="rl-ticks">
          {ticks.map(v => (
            <button
              key={v}
              type="button"
              data-testid={`rl-tick-${v}`}
              data-value={v}
              className={`rl-tick ${v % 5 === 0 ? "major" : "minor"} ${markAt(v)}`}
              disabled={disabled}
              onClick={() => clickTick(v)}
            >
              {v % 5 === 0 ? <span className="rl-num">{v}</span> : null}
            </button>
          ))}
        </div>
      </div>

      <div className={`rl-evaluation ${verdict.status.toLowerCase()}`} data-testid="rl-evaluation">
        {verdict.status === "EMPTY"
          ? state.marks.length === 0
            ? "先点铅笔左头对着的刻度，放第一个标记"
            : "第一个标记放好了——再点右头对着的刻度"
          : verdict.status === "PASS"
            ? verdict.aligned
              ? `夹住了！${Math.abs(state.marks[1] - state.marks[0])} 格，正好是铅笔的长度`
              : `间隔量对了（${Math.abs(state.marks[1] - state.marks[0])}），不过标记没夹在铅笔两头哦`
            : verdict.error === "from_zero_reading"
              ? "你把左标记放在 0 上啦——铅笔不是从 0 开始的，要夹住它的两头"
              : `两个标记差 ${Math.abs(verdict.span)} 格，和铅笔长度对不上，重新夹一夹`}
      </div>

      <button
        type="button"
        className="primary-button"
        data-testid="rl-submit"
        // P0-01 口径：EMPTY（标记不足 2 个）拦提交；PASS∪FAIL 可达后端。
        disabled={disabled || verdict.status === "EMPTY"}
        onClick={onSubmit}
      >
        提交测量
      </button>
    </div>
  );
}
