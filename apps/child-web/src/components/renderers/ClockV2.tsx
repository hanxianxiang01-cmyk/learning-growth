"use client";

/**
 * clock V2 组件（FE-1430 R17）。runtime 装配对齐 RulerV2。
 *
 * 钟面 12 个数字=时针落位（点数字拨短针）；下方两档=分针（整点/半点拨长针）。
 * 指针 SVG 实时指向 (h, m)。adjust_history=Gap"指针调整过程"。
 * 答案=总分钟数（组件自动填，后端标量判分）。
 * 拿分针数字当时针读 → hand_swap（Diagnosis P0"时针/分针关系错误"）。
 */

import { useEffect, useMemo, useReducer, useRef } from "react";
import type { TaskResponse, V2TaskUiSchema } from "@/src/lib/api/contracts";
import {
  applySetHour,
  applySetMinute,
  clockAnswer,
  evaluateClock,
  initialClockV2State,
  parseClockConfig,
  serializeClockV2,
  type ClockV2State
} from "@/src/features/task-renderer/clockV2";
import { buildRendererEvent, createRendererWorkspaceState, rendererWorkspaceReducer } from "@/src/features/task-renderer/rendererRuntime";

type Props = {
  taskInstanceId: string;
  schema: V2TaskUiSchema;
  response: TaskResponse;
  disabled?: boolean;
  onResponseChange: (response: TaskResponse) => void;
  onSubmit: () => void;
};

/** 表盘角：数字 n 在 (n/12)*360°，12 在正上。 */
function faceAngle(value: number, mod: number): number {
  return ((value % mod) / mod) * 360;
}

export function ClockV2({
  taskInstanceId,
  schema,
  response,
  disabled,
  onResponseChange,
  onSubmit
}: Props) {
  const workspace = schema.workspaces[0];
  const config = useMemo(
    () => (workspace ? parseClockConfig(workspace.config as Record<string, unknown>) : null),
    [workspace]
  );
  const [runtime, dispatch] = useReducer(
    rendererWorkspaceReducer<ClockV2State>,
    // 哨兵初始态（m=-1 非法组合=config 未装载/未初始化）——避免用假时间写 envelope（R15 steps 空数组同款）
    { h: 12, m: -1, adjust_history: [] },
    createRendererWorkspaceState
  );
  const responseRef = useRef(response);
  responseRef.current = response;

  useEffect(() => {
    if (config) dispatch({ type: "SET_STATE", state: initialClockV2State(config) });
  }, [config, schema.ui_revision]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!config || !workspace || runtime.present.m < 0) return;
    const answer = clockAnswer(runtime.present);
    onResponseChange({
      ...responseRef.current,
      answer: answer === null ? "" : String(answer),
      interaction_events: runtime.events,
      v2_workspaces: [
        { workspace_id: workspace.workspace_id, data: serializeClockV2(runtime.present, config) }
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
    return <div className="surface-card unsupported-task">时钟题配置不完整。</div>;
  }

  const emit = (eventType: string, payload: Record<string, string | number | boolean | null>) =>
    buildRendererEvent(eventType, {
      task_instance_id: taskInstanceId,
      workspace_id: workspace.workspace_id,
      renderer_id: "clock",
      capability_id: "set_time",
      payload
    });

  const state = runtime.present;
  const verdict = evaluateClock(state, config);

  const clickNumber = (n: number) => {
    if (disabled) return;
    const result = applySetHour(state, n);
    if (!result.ok || result.unchanged) return;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit("CLOCK_HOUR_SET", { from: state.h, to: n })
    });
  };

  const clickMinute = (v: number) => {
    if (disabled) return;
    const result = applySetMinute(state, v);
    if (!result.ok || result.unchanged) return;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit("CLOCK_MINUTE_SET", { from: state.m, to: v })
    });
  };

  const undo = () => !disabled && dispatch({ type: "UNDO", event: emit("UNDO", {}) });
  const reset = () =>
    !disabled &&
    dispatch({ type: "SET_STATE", state: initialClockV2State(config), event: emit("RESET", {}) });

  const hourDeg = faceAngle(state.h % 12 === 0 ? 0 : state.h, 12) + (state.m / 30) * 15;
  const minuteDeg = faceAngle(state.m / 5, 12);

  return (
    <div className="manipulative-card clock-v2" data-testid="clock-v2">
      <div className="manipulative-heading">
        <div>
          <strong>拨一拨</strong>
          <span>短针是时针：点数字拨过去；长针是分针：点下面「整点 / 半点」两档。把钟面拨到题目要的时间。</span>
        </div>
        <div className="workspace-actions">
          <button type="button" data-testid="ck-undo" disabled={disabled || runtime.history.length === 0} onClick={undo}>
            撤销
          </button>
          <button type="button" data-testid="ck-reset" disabled={disabled} onClick={reset}>
            重置
          </button>
        </div>
      </div>

      <div className="ck-face-wrap">
        <svg viewBox="0 0 200 200" className="ck-face" data-testid="ck-face" aria-label="钟面">
          <circle cx="100" cy="100" r="96" className="ck-rim" />
          {Array.from({ length: 12 }, (_, i) => {
            const n = i + 1;
            const rad = ((n % 12) / 12) * 2 * Math.PI - Math.PI / 2;
            const x = 100 + Math.cos(rad) * 78;
            const y = 100 + Math.sin(rad) * 78;
            return (
              <g key={n} className={state.h === n ? "ck-num-hit picked" : "ck-num-hit"} onClick={() => clickNumber(n)} data-testid={`ck-hour-${n}`}>
                <circle cx={x} cy={y} r="14" className={state.h === n ? "ck-num picked" : "ck-num"} />
                <text x={x} y={y + 5} textAnchor="middle" className="ck-num-text">{n}</text>
              </g>
            );
          })}
          <line x1="100" y1="100" x2="100" y2="55" className="ck-hour-hand"
            transform={`rotate(${hourDeg} 100 100)`} data-testid="ck-hour-hand" />
          <line x1="100" y1="100" x2="100" y2="32" className="ck-minute-hand"
            transform={`rotate(${minuteDeg} 100 100)`} data-testid="ck-minute-hand" />
          <circle cx="100" cy="100" r="5" className="ck-center" />
        </svg>
        <div className="ck-minute-row" data-testid="ck-minute-row">
          <button type="button" data-testid="ck-minute-0" className={state.m === 0 ? "ck-minute picked" : "ck-minute"} disabled={disabled} onClick={() => clickMinute(0)}>整点（长针指 12）</button>
          <button type="button" data-testid="ck-minute-30" className={state.m === 30 ? "ck-minute picked" : "ck-minute"} disabled={disabled} onClick={() => clickMinute(30)}>半点（长针指 6）</button>
        </div>
      </div>

      <div className={`ck-evaluation ${verdict.status.toLowerCase()}`} data-testid="ck-evaluation">
        {verdict.status === "EMPTY"
          ? "钟面还在原位——先想清楚题目要几点，再拨针"
          : verdict.status === "PASS"
            ? `拨好了：${state.h}:${String(state.m).padStart(2, "0")}`
            : verdict.error === "hand_swap"
              ? "你是不是看着**长针**指的数字读钟啦？短针才是时针，长针只管整点/半点"
              : `现在是 ${state.h}:${String(state.m).padStart(2, "0")}，和题目还差 ${Math.abs(verdict.delta_minutes)} 分钟，再看看`}
      </div>

      <button
        type="button"
        className="primary-button"
        data-testid="ck-submit"
        // P0-01 口径：EMPTY（一步没拨）拦提交；PASS∪FAIL 可达后端。
        disabled={disabled || verdict.status === "EMPTY"}
        onClick={onSubmit}
      >
        提交时间
      </button>
    </div>
  );
}
