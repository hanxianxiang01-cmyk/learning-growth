"use client";

import { useChildUi } from "@/src/theme/ChildSkinProvider";
import { A5LivePanel } from "@/src/features/task-renderer/interaction/kernel/A5LivePanel";
import { RendererFrame } from "@/src/components/ui-v6/RendererFrame";


import { useEffect, useId, useMemo, useReducer, useRef } from "react";
import type { TaskResponse, V2TaskUiSchema } from "@/src/lib/api/contracts";
import {
  applyJump,
  endpointAnswer,
  initialNumberLineV2State,
  serializeNumberLineV2,
  type NumberLineV2Config,
  type NumberLineV2State
} from "@/src/features/task-renderer/numberLineV2";
import {
  buildRendererEvent,
  createRendererWorkspaceState,
  rendererWorkspaceReducer
} from "@/src/features/task-renderer/rendererRuntime";

type Props = {
  /** MIK A5: task-pinned opt-in, legacy and V6 default unchanged. */
  naturalEnabled?: boolean;
  taskInstanceId: string;
  schema: V2TaskUiSchema;
  response: TaskResponse;
  disabled?: boolean;
  onResponseChange: (response: TaskResponse) => void;
  onSubmit: () => void;
};

/** jump_id 工厂：uuid 优先，降级序号（同一工作区内唯一即可）。 */
function makeJumpIdFactory() {
  let seq = 0;
  return () =>
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `jump-${++seq}`;
}

function readConfig(schema: V2TaskUiSchema): NumberLineV2Config | null {
  const workspace = schema.workspaces[0];
  if (!workspace || workspace.renderer !== "number-line") return null;

  const scale = workspace.config.scale as
    | { min?: unknown; max?: unknown; tick_step?: unknown }
    | undefined;
  const min = typeof scale?.min === "number" ? scale.min : null;
  const max = typeof scale?.max === "number" ? scale.max : null;
  const tickStep = typeof scale?.tick_step === "number" && scale.tick_step > 0 ? scale.tick_step : null;
  if (min === null || max === null || tickStep === null || max < min) return null;

  const startMarker = workspace.config.start_marker as { value?: unknown } | undefined;
  const startValue =
    typeof startMarker?.value === "number" && startMarker.value >= min && startMarker.value <= max
      ? startMarker.value
      : null;

  return { min, max, tickStep, startValue };
}

export function NumberLineV2({
  taskInstanceId,
  schema,
  response,
  disabled,
  onResponseChange,
  onSubmit,
  naturalEnabled
}: Props) {
  const { uiVersion } = useChildUi();
  const arrowId = `v6-jump-${useId().replace(/:/g, "")}`;
  const config = useMemo(() => readConfig(schema), [schema]);
  const workspace = schema.workspaces[0];
  const jumpId = useMemo(() => makeJumpIdFactory(), []);
  const [runtime, dispatch] = useReducer(
    rendererWorkspaceReducer<NumberLineV2State>,
    config ? initialNumberLineV2State(config) : { start: null, current: null, jumps: [] },
    createRendererWorkspaceState
  );
  const responseRef = useRef(response);
  responseRef.current = response;

  useEffect(() => {
    dispatch({ type: "RESET" });
  }, [schema.ui_revision]);

  useEffect(() => {
    if (!workspace) return;
    onResponseChange({
      ...responseRef.current,
      answer: endpointAnswer(runtime.present)?.toString() ?? "",
      interaction_events: runtime.events,
      v2_workspaces: [
        {
          workspace_id: workspace.workspace_id,
          data: serializeNumberLineV2(runtime.present)
        }
      ],
      v2_response_type: schema.response_contract.response_type,
      v2_ui_revision: schema.ui_revision
    });
  }, [
    runtime.present,
    runtime.events,
    workspace,
    onResponseChange,
    schema.response_contract.response_type,
    schema.ui_revision
  ]);

  if (!config || !workspace) {
    return <div className="surface-card unsupported-task" role="alert">{uiVersion === "v6" ? "这道题暂时没准备好，请返回任务页再试一次。" : "数轴题配置不完整，暂时无法开始。"}</div>;
  }

  const values: number[] = [];
  for (let v = config.min; v <= config.max && values.length < 31; v += config.tickStep) {
    values.push(v);
  }

  const jump = (v: number) => {
    if (disabled) return;
    if (runtime.present.current === null || v === runtime.present.current) return;
    const event = buildRendererEvent("JUMP_CREATED", {
      task_instance_id: taskInstanceId,
      workspace_id: workspace.workspace_id,
      renderer_id: "number-line",
      capability_id: "jump",
      payload: { from: runtime.present.current, to: v }
    });
    dispatch({ type: "SET_STATE", state: applyJump(runtime.present, v, jumpId), event });
  };

  const undo = () => {
    if (disabled) return;
    dispatch({
      type: "UNDO",
      event: buildRendererEvent("UNDO", {
        task_instance_id: taskInstanceId,
        workspace_id: workspace.workspace_id,
        renderer_id: "number-line",
        capability_id: "undo"
      })
    });
  };

  const reset = () => {
    if (disabled) return;
    dispatch({
      type: "RESET",
      event: buildRendererEvent("RESET", {
        task_instance_id: taskInstanceId,
        workspace_id: workspace.workspace_id,
        renderer_id: "number-line",
        capability_id: "reset"
      })
    });
  };

  const v6TickCount = Math.floor((config.max - config.min) / config.tickStep) + 1;
  if (uiVersion === "v6" && (!Number.isFinite(v6TickCount) || v6TickCount > 2000)) {
    return <section className="surface-card" role="alert">这道题的数轴暂时无法显示，请返回任务页重新开始。</section>;
  }
  const v6LineValues = uiVersion === "v6" ? Array.from({ length: v6TickCount }, (_, i) => Number((config.min + i * config.tickStep).toFixed(10))) : [];
  if (uiVersion === "v6") {
    return <RendererFrame rendererId="number-line" title="在数轴上跳一跳" instruction="从起点出发，点一个数字完成一次跳步。数轴可以左右滑动。"
      actions={<div className="workspace-actions">
          <button type="button" disabled={disabled || runtime.history.length === 0} onClick={undo}>
            撤销
          </button>
          <button type="button" disabled={disabled} onClick={reset}>
            重置
          </button>
        </div>}
      testId="number-line-v2" className="manipulative-card number-line"
      submitTestId="number-line-v2-submit" submitDisabled={disabled || endpointAnswer(runtime.present) === null} locked={disabled} onSubmit={onSubmit} summary={`现在到 ${runtime.present.current ?? "起点待定"}`}>
      {naturalEnabled && <A5LivePanel
        rendererId="number-line"
        state={state} config={config}
        taskInstanceId={taskInstanceId} uiRevision={schema.ui_revision}
        disabled={disabled}
        handlers={{
          "applyJump": a => jump(a.toTick as number)
        }}
      />}
      <div className="v6-number-line-scroll"><div className="v6-number-line-track" style={{width: Math.max(104, v6LineValues.length * 52)}}>
       <svg className="v6-jump-arcs" viewBox={`0 0 ${Math.max(104, v6LineValues.length * 52)} 100`} aria-hidden="true">
         <defs><marker id={arrowId} markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="userSpaceOnUse"><polygon points="0,0 8,4 0,8" fill="var(--v6-theme)" /></marker></defs>
         {runtime.present.jumps.map((j,i)=>{const x1=26+(j.from-config.min)/config.tickStep*52;const x2=26+(j.to-config.min)/config.tickStep*52;return <path key={j.jump_id} markerEnd={`url(#${arrowId})`} d={`M${x1} 87 Q${(x1+x2)/2} ${Math.max(5,75-Math.abs(x2-x1)/3)} ${x2} 87`} />;})}
       </svg>
       <div className="number-line-axis" />
       <div className="number-line-ticks">{v6LineValues.map(value=><button key={value} type="button" disabled={disabled}
         data-testid={`v6-line-tick-${value}`} aria-label={`跳到 ${value}`} aria-pressed={runtime.present.current===value}
         className={`number-tick ${runtime.present.start===value?"is-start":""} ${runtime.present.current===value?"is-current":""}`}
         onClick={()=>jump(value)}><span className="tick-mark"/><span>{value}</span></button>)}</div>
     </div></div>
<div className="jump-history">
        {runtime.present.start === null ? (
          <span>请先选择起点</span>
        ) : runtime.present.jumps.length === 0 ? (
          <span>起点：{runtime.present.start}，点一个数字完成跳步</span>
        ) : (
          <>
            <strong>起点 {runtime.present.start}</strong>
            {runtime.present.jumps.map(j => (
              <span className="jump-chip" key={j.jump_id}>
                {j.to - j.from > 0 ? `+${j.to - j.from}` : j.to - j.from}
              </span>
            ))}
            <strong>到 {runtime.present.current}</strong>
          </>
        )}
      </div>
    </RendererFrame>;
  }

  return (
    <div className="manipulative-card number-line" data-testid="number-line-v2">
      <div className="manipulative-heading">
        <div>
          <strong>数轴跳一跳</strong>
          <span>从起点开始，点一个数字完成一次跳步，跳到终点后提交。</span>
        </div>
        <div className="workspace-actions">
          <button type="button" disabled={disabled || runtime.history.length === 0} onClick={undo}>
            撤销
          </button>
          <button type="button" disabled={disabled} onClick={reset}>
            重置
          </button>
        </div>
      </div>

      <div className="number-line-board">
        <div className="number-line-axis" />
        <div className="number-line-ticks">
          {values.map(value => {
            const isStart = runtime.present.start === value;
            const isCurrent = runtime.present.current === value;
            return (
              <button
                key={value}
                type="button"
                disabled={disabled}
                className={`number-tick ${isStart ? "is-start" : ""} ${isCurrent ? "is-current" : ""}`}
                onClick={() => jump(value)}
              >
                <span className="tick-mark" />
                <span>{value}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="jump-history">
        {runtime.present.start === null ? (
          <span>请先选择起点</span>
        ) : runtime.present.jumps.length === 0 ? (
          <span>起点：{runtime.present.start}，点一个数字完成跳步</span>
        ) : (
          <>
            <strong>起点 {runtime.present.start}</strong>
            {runtime.present.jumps.map(j => (
              <span className="jump-chip" key={j.jump_id}>
                {j.to - j.from > 0 ? `+${j.to - j.from}` : j.to - j.from}
              </span>
            ))}
            <strong>到 {runtime.present.current}</strong>
          </>
        )}
      </div>

      <button
        type="button"
        className="primary-button"
        data-testid="number-line-v2-submit"
        disabled={disabled || endpointAnswer(runtime.present) === null}
        onClick={onSubmit}
      >
        提交答案
      </button>
    </div>
  );
}
