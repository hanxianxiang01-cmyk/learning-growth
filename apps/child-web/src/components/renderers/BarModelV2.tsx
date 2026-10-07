"use client";

/**
 * bar-model V2 组件（FE-1418 R02）。runtime 装配对齐 TenFrameV2：
 * rendererWorkspaceReducer（undo/history 内建）+ buildRendererEvent（UPPER_SNAKE）。
 *
 * 三根条：已知条可编辑（摆错了 evaluator 报 modeling——读题错误也是学习信号），
 * 答案条被碰过才算"有答案"（EMPTY 门禁）。结构错误分类（modeling/relation/calc）
 * 由纯函数层产出、序列化进 Evidence，后端权威判分不受前端弱判影响。
 */

import { useEffect, useMemo, useReducer, useRef } from "react";
import type { TaskResponse, V2TaskUiSchema } from "@/src/lib/api/contracts";
import {
  applyBarDelta,
  barModelAnswer,
  evaluateBarModel,
  initialBarModelV2State,
  parseBarModelConfig,
  serializeBarModelV2,
  type BarId,
  type BarModelV2Config,
  type BarModelV2State
} from "@/src/features/task-renderer/barModelV2";
import { buildRendererEvent, createRendererWorkspaceState, rendererWorkspaceReducer } from "@/src/features/task-renderer/rendererRuntime";

type Props = {
  taskInstanceId: string;
  schema: V2TaskUiSchema;
  response: TaskResponse;
  disabled?: boolean;
  onResponseChange: (response: TaskResponse) => void;
  onSubmit: () => void;
};

const BAR_LABELS: Record<BarId, (config: BarModelV2Config) => string> = {
  a: config => (config.mode === "comparison" ? "大条（多的一方）" : config.known.a !== undefined ? "部分一" : "部分一（未知）"),
  b: config => (config.mode === "comparison" ? "小条（少的一方）" : config.known.b !== undefined ? "部分二" : "部分二（未知）"),
  c: config => (config.mode === "comparison" ? "差（多几？）" : config.known.c !== undefined ? "整体（一共）" : "整体（一共多少？）")
};

export function BarModelV2({
  taskInstanceId,
  schema,
  response,
  disabled,
  onResponseChange,
  onSubmit
}: Props) {
  const workspace = schema.workspaces[0];
  const config = useMemo(
    () => (workspace ? parseBarModelConfig(workspace.config as Record<string, unknown>) : null),
    [workspace]
  );
  const [runtime, dispatch] = useReducer(
    rendererWorkspaceReducer<BarModelV2State>,
    initialBarModelV2State(),
    createRendererWorkspaceState
  );
  const responseRef = useRef(response);
  responseRef.current = response;

  useEffect(() => {
    dispatch({ type: "RESET" });
  }, [schema.ui_revision]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!config || !workspace) return;
    const answer = barModelAnswer(runtime.present, config);
    onResponseChange({
      ...responseRef.current,
      answer: answer === null ? "" : String(answer),
      interaction_events: runtime.events,
      v2_workspaces: [
        { workspace_id: workspace.workspace_id, data: serializeBarModelV2(runtime.present, config) }
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
    return <div className="surface-card unsupported-task">条形模型题配置不完整。</div>;
  }

  const emit = (eventType: string, capability: string, payload: Record<string, string | number | boolean | null>) =>
    buildRendererEvent(eventType, {
      task_instance_id: taskInstanceId,
      workspace_id: workspace.workspace_id,
      renderer_id: "bar-model",
      capability_id: capability,
      payload
    });

  const state = runtime.present;
  const verdict = evaluateBarModel(state, config);

  const changeBar = (bar: BarId, delta: number) => {
    if (disabled) return;
    const result = applyBarDelta(state, bar, delta, config);
    if (!result.ok) return;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit(
        delta === 1 ? "BAR_BLOCK_ADDED" : "BAR_BLOCK_REMOVED",
        delta === 1 ? "add_object" : "remove_object",
        { bar, blocks: result.state.bars[bar] }
      )
    });
  };

  const undo = () => !disabled && dispatch({ type: "UNDO", event: emit("UNDO", "undo", {}) });
  const reset = () => !disabled && dispatch({ type: "RESET", event: emit("RESET", "reset", {}) });

  const renderBar = (bar: BarId) => {
    const value = state.bars[bar];
    const isAnswer = bar === config.answerBar;
    return (
      <div className={`bm-bar-row ${isAnswer ? "answer" : "known"}`} key={bar} data-testid={`bm-row-${bar}`}>
        <span className="bm-bar-label">{BAR_LABELS[bar](config)}</span>
        <div className="bm-bar-track">
          <div className="bm-bar-blocks" data-testid={`bm-bar-${bar}`}>
            {Array.from({ length: value }, (_, i) => (
              <span key={i} className="bm-block" />
            ))}
          </div>
        </div>
        <div className="bm-bar-controls">
          <button
            type="button"
            data-testid={`bm-minus-${bar}`}
            disabled={disabled || value === 0}
            onClick={() => changeBar(bar, -1)}
            aria-label={`${BAR_LABELS[bar](config)} 减一格`}
          >
            −
          </button>
          <strong data-testid={`bm-count-${bar}`}>{value}</strong>
          <button
            type="button"
            data-testid={`bm-plus-${bar}`}
            disabled={disabled || value >= config.maxBlocks}
            onClick={() => changeBar(bar, 1)}
            aria-label={`${BAR_LABELS[bar](config)} 加一格`}
          >
            ＋
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="manipulative-card bar-model-v2" data-testid="bar-model-v2">
      <div className="manipulative-heading">
        <div>
          <strong>画条形图</strong>
          <span>按题目把方格一根一根摆出来，想清楚了就提交。</span>
        </div>
        <div className="workspace-actions">
          <button type="button" data-testid="bm-undo" disabled={disabled || runtime.history.length === 0} onClick={undo}>
            撤销
          </button>
          <button type="button" data-testid="bm-reset" disabled={disabled} onClick={reset}>
            重置
          </button>
        </div>
      </div>

      <div className="bm-bars" data-testid="bm-bars">
        {(["a", "b", "c"] as BarId[]).map(renderBar)}
      </div>

      <div className={`bm-evaluation ${verdict.status.toLowerCase()}`} data-testid="bm-evaluation">
        {verdict.status === "EMPTY"
          ? "还没摆出答案条"
          : verdict.status === "PASS"
            ? "条形图摆对了"
            : verdict.error === "modeling"
              ? "有些条和题目说的不一样，再读一遍题"
              : verdict.error === "relation"
                ? "条的长短关系不对——想想谁应该比谁长"
                : "图形摆对了，数字再检查检查"}
      </div>

      <button
        type="button"
        className="primary-button"
        data-testid="bm-submit"
        // P0-01 口径：EMPTY（答案条未碰）拦提交；PASS∪FAIL 可达后端。
        disabled={disabled || verdict.status === "EMPTY"}
        onClick={onSubmit}
      >
        提交这道题
      </button>
    </div>
  );
}
