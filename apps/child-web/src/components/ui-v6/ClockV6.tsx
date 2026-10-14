"use client";

import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";
import type { KeyboardEvent, PointerEvent } from "react";
import type { TaskResponse, V2TaskUiSchema } from "@/src/lib/api/contracts";
import { applySetHour, applySetMinute, clockAnswer, initialClockV2State, parseClockConfig, serializeClockV2, type ClockV2Config, type ClockV2State } from "@/src/features/task-renderer/clockV2";
import { buildRendererEvent, createRendererWorkspaceState, rendererWorkspaceReducer } from "@/src/features/task-renderer/rendererRuntime";
import { clockDragStarted, clockKeyValue, clockValueFromPoint, type ClockHand } from "@/src/features/ui-v6/clockInput";
import { ChildIcon } from "./ChildIcon";

export type ClockV6Props = {
  taskInstanceId: string;
  schema: V2TaskUiSchema;
  response: TaskResponse;
  disabled?: boolean;
  onResponseChange: (response: TaskResponse) => void;
  onSubmit: () => void;
};

type Drag = {
  pointerId: number;
  hand: ClockHand;
  target: SVGCircleElement;
  startX: number;
  startY: number;
  moved: boolean;
  value: number;
};

export function ClockV6(props: ClockV6Props) {
  const workspace = props.schema.workspaces[0];
  const config = useMemo(() => workspace ? parseClockConfig(workspace.config) : null, [workspace]);
  if (!config || !workspace) return <div className="surface-card unsupported-task" role="alert">这道钟面题暂时没有准备好，请返回任务后再试。</div>;
  // Only a new task/revision resets the board. Hint/retry/viewport/skin do not remount it.
  return <ClockReady key={`${props.taskInstanceId}:${props.schema.ui_revision}`} {...props} config={config} />;
}

function ClockReady({ taskInstanceId, schema, response, disabled = false, onResponseChange, onSubmit, config }: ClockV6Props & { config: ClockV2Config }) {
  const workspace = schema.workspaces[0];
  const [runtime, dispatch] = useReducer(rendererWorkspaceReducer<ClockV2State>, initialClockV2State(config), createRendererWorkspaceState);
  const [activeHand, setActiveHand] = useState<ClockHand>("hour");
  const [preview, setPreview] = useState<{ hand: ClockHand; value: number } | null>(null);
  const [dragging, setDragging] = useState(false);
  const drag = useRef<Drag | null>(null);
  const svg = useRef<SVGSVGElement>(null);
  const responseRef = useRef(response);
  responseRef.current = response;
  const state = runtime.present;
  const event = (type: string, payload: Record<string, string | number | boolean | null>) => buildRendererEvent(type, {
    task_instance_id: taskInstanceId, workspace_id: workspace.workspace_id,
    renderer_id: "clock", capability_id: "set_time", payload
  });

  useEffect(() => {
    const answer = clockAnswer(runtime.present);
    onResponseChange({
      ...responseRef.current, answer: answer === null ? "" : String(answer),
      interaction_events: runtime.events,
      v2_workspaces: [{ workspace_id: workspace.workspace_id, data: serializeClockV2(runtime.present, config) }],
      v2_response_type: schema.response_contract.response_type, v2_ui_revision: schema.ui_revision
    });
  }, [runtime.present, runtime.events, config, workspace.workspace_id, schema.response_contract.response_type, schema.ui_revision, onResponseChange]);

  const cancel = useCallback(() => {
    const current = drag.current;
    drag.current = null;
    if (current) {
      try { current.target.releasePointerCapture(current.pointerId); } catch { /* capture may already be released */ }
    }
    setPreview(null);
    setDragging(false);
  }, []);
  useEffect(() => { if (disabled) cancel(); }, [disabled, cancel]);
  useEffect(() => {
    window.addEventListener("blur", cancel);
    return () => { window.removeEventListener("blur", cancel); };
  }, [cancel]);

  const commit = (hand: ClockHand, value: number) => {
    if (disabled) return;
    const result = hand === "hour" ? applySetHour(state, value) : applySetMinute(state, value);
    if (!result.ok || result.unchanged) return;
    dispatch({ type: "SET_STATE", state: result.state, event: event(hand === "hour" ? "CLOCK_HOUR_SET" : "CLOCK_MINUTE_SET", { from: hand === "hour" ? state.h : state.m, to: value }) });
  };
  const setByControl = (hand: ClockHand, value: number) => {
    if (drag.current || disabled) return;
    setActiveHand(hand);
    commit(hand, value);
  };
  const begin = (e: PointerEvent<SVGCircleElement>, hand: ClockHand) => {
    if (disabled || drag.current || e.button !== 0 || !e.isPrimary) return;
    e.preventDefault();
    setActiveHand(hand);
    e.currentTarget.focus();
    drag.current = { pointerId: e.pointerId, hand, target: e.currentTarget, startX: e.clientX, startY: e.clientY, moved: false, value: hand === "hour" ? state.h : state.m };
    e.currentTarget.setPointerCapture(e.pointerId);
    setDragging(true);
  };
  const move = (e: PointerEvent<SVGCircleElement>) => {
    const current = drag.current;
    if (!current || e.pointerId !== current.pointerId || disabled) return;
    if (!current.moved && !clockDragStarted(current.startX, current.startY, e.clientX, e.clientY)) return;
    const matrix = svg.current?.getScreenCTM();
    if (!matrix) return;
    e.preventDefault();
    const point = new DOMPoint(e.clientX, e.clientY).matrixTransform(matrix.inverse());
    const value = clockValueFromPoint(current.hand, point.x, point.y, state.m);
    if (value === null) return;
    current.moved = true;
    current.value = value;
    setPreview({ hand: current.hand, value });
  };
  const end = (e: PointerEvent<SVGCircleElement>) => {
    const current = drag.current;
    if (!current || current.pointerId !== e.pointerId) return;
    const shouldCommit = e.type === "pointerup" && current.moved && !disabled;
    cancel();
    // A completed gesture is one existing SET event / one history entry, not a new event family.
    if (shouldCommit) commit(current.hand, current.value);
  };
  const key = (e: KeyboardEvent<SVGCircleElement>, hand: ClockHand) => {
    if (e.key === "Escape" && drag.current) { e.preventDefault(); cancel(); return; }
    if (disabled || drag.current) return;
    const value = clockKeyValue(hand, hand === "hour" ? state.h : state.m, e.key);
    if (value === null) return;
    e.preventDefault();
    setActiveHand(hand);
    commit(hand, value);
  };

  const display = { h: preview?.hand === "hour" ? preview.value : state.h, m: preview?.hand === "minute" ? preview.value : state.m };
  const pos = (degrees: number, length: number) => ({ x: 180 + Math.sin(degrees * Math.PI / 180) * length, y: 180 - Math.cos(degrees * Math.PI / 180) * length });
  const hours = display.h % 12 * 30 + display.m * .5, minutes = display.m * 6;
  const hourTip = pos(hours, 54), minuteTip = pos(minutes, 86);
  const ready = state.adjust_history.length > 0;
  const time = `${display.h}:${String(display.m).padStart(2, "0")}`;

  return <section className="v6-clock manipulative-card" data-testid="clock-v2" data-v6-renderer="clock" aria-label="拨钟面">
    <div className="v6-clock-heading"><div><h2>拨一拨</h2><p id="v6-clock-help">拖动针尖，或点数字调短针。长针可以选整点、半点。</p></div>
      <div className="workspace-actions">
        <button type="button" data-testid="ck-undo" disabled={disabled || dragging || runtime.history.length === 0} onClick={() => dispatch({ type: "UNDO", event: event("UNDO", {}) })}><ChildIcon name="undo" />撤销</button>
        <button type="button" data-testid="ck-reset" disabled={disabled || dragging} onClick={() => dispatch({ type: "RESET", event: event("RESET", {}) })}><ChildIcon name="reset" />重置</button>
      </div>
    </div>
    <div className="v6-clock-body">
      <svg ref={svg} className="v6-clock-face" data-testid="ck-face" viewBox="0 0 360 360" role="group" aria-label={`当前钟面${time}`} aria-describedby="v6-clock-help">
        <circle cx="180" cy="180" r="120" className="v6-clock-rim" />
        {Array.from({ length: 60 }, (_, i) => { const a = pos(i * 6, i % 5 ? 110 : 104), b = pos(i * 6, 116); return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} className="v6-clock-tick" strokeWidth={i % 5 ? 1 : 2} pointerEvents="none" />; })}
        {Array.from({ length: 12 }, (_, i) => { const n = i + 1, p = pos(n * 30, 149); return <g key={n} role="button" tabIndex={disabled ? -1 : 0} aria-disabled={disabled} aria-label={`把短针拨到${n}点`} aria-pressed={display.h === n} className={`v6-clock-number ${display.h === n ? "picked" : ""}`} data-testid={`ck-hour-${n}`} onClick={() => setByControl("hour", n)} onKeyDown={e => { if (["Enter", " "].includes(e.key)) { e.preventDefault(); setByControl("hour", n); } }}>
          <circle cx={p.x} cy={p.y} r="29" /><text x={p.x} y={p.y} dy=".35em" textAnchor="middle" pointerEvents="none">{n}</text>
        </g>; })}
        <line x1="180" y1="180" x2={hourTip.x} y2={hourTip.y} className="v6-clock-hour" data-testid="ck-hour-hand" pointerEvents="none" />
        <line x1="180" y1="180" x2={minuteTip.x} y2={minuteTip.y} className="v6-clock-minute" data-testid="ck-minute-hand" pointerEvents="none" />
        {(["hour", "minute"] as const).map(hand => { const tip = hand === "hour" ? hourTip : minuteTip; return <circle key={hand} cx={tip.x} cy={tip.y} r="29" className={`v6-clock-handle ${activeHand === hand ? "active" : ""}`} role="slider" tabIndex={disabled ? -1 : 0} aria-disabled={disabled} aria-orientation="horizontal" aria-label={hand === "hour" ? "短针，方向键调整小时" : "长针，方向键切换整点和半点"} aria-valuemin={hand === "hour" ? 1 : 0} aria-valuemax={hand === "hour" ? 12 : 30} aria-valuenow={hand === "hour" ? display.h : display.m} aria-valuetext={hand === "hour" ? `${display.h}点` : display.m === 0 ? "整点" : "半点"} data-testid={`ck-${hand}-handle`} onFocus={() => setActiveHand(hand)} onPointerDown={e => begin(e, hand)} onPointerMove={move} onPointerUp={end} onPointerCancel={end} onLostPointerCapture={() => { if (drag.current?.hand === hand) cancel(); }} onKeyDown={e => key(e, hand)} />; })}
        <circle cx="180" cy="180" r="7" className="v6-clock-center" pointerEvents="none" />
      </svg>
      <div className="v6-clock-controls">
        <output className="v6-clock-readout" data-testid="ck-time" aria-live="polite" aria-atomic="true">{time}</output>
        <span className="v6-clock-label">当前钟面</span>
        <div className="v6-hand-choice" aria-label="选择要调整的针">{(["hour", "minute"] as const).map(hand => <button key={hand} type="button" disabled={disabled || dragging} aria-pressed={activeHand === hand} onClick={() => setActiveHand(hand)}>{hand === "hour" ? "调短针" : "调长针"}</button>)}</div>
        <div className="v6-hour-stepper"><button type="button" aria-label="小时减一" disabled={disabled || dragging || state.h === 1} onClick={() => setByControl("hour", state.h - 1)}>−</button><span>{display.h} 点</span><button type="button" aria-label="小时加一" disabled={disabled || dragging || state.h === 12} onClick={() => setByControl("hour", state.h + 1)}>＋</button></div>
        <div className="ck-minute-row" data-testid="ck-minute-row">{([0, 30] as const).map(m => <button key={m} type="button" data-testid={`ck-minute-${m}`} className={display.m === m ? "picked" : ""} aria-pressed={display.m === m} disabled={disabled || dragging} onClick={() => setByControl("minute", m)}>{m === 0 ? "整点" : "半点"}</button>)}</div>
      </div>
    </div>
    <div className="v6-clock-footer">
      <p id="v6-clock-completeness" data-testid="ck-evaluation" aria-live="polite">{dragging ? "松开针尖，完成这一步。" : ready ? `当前时间 ${time}，想好了就提交。` : "钟面还在原位，先拨一拨。"}</p>
      <button type="button" className="primary-button" data-testid="ck-submit" aria-describedby="v6-clock-completeness" disabled={disabled || dragging || !ready} onClick={onSubmit}>提交答案<ChildIcon name="check" /></button>
    </div>
  </section>;
}
