"use client";

/**
 * formula-board V2 组件（FE-1420 R10）。runtime 装配对齐 PlaceValueV2/TenFrameV2：
 * rendererWorkspaceReducer + buildRendererEvent。
 *
 * 算式 token 流：数字/符号/等号直接展示，空槽点选后弹对应输入面板
 * （数字槽=数字键盘+清空；符号槽=+/− 大按钮）。填改过程每步留事件
 * （SLOT_ACTIVATED/NUMBER_FILLED/OPERATOR_FILLED/SLOT_CLEARED），
 * "修改顺序、替换过程"即 Gap R10 Evidence 条目。
 */

import { useEffect, useMemo, useReducer, useRef } from "react";
import type { TaskResponse, V2TaskUiSchema } from "@/src/lib/api/contracts";
import {
  applyActivate,
  applyClear,
  applyNumberKey,
  applyOperatorKey,
  evaluateFormula,
  formulaAnswer,
  initialFormulaV2State,
  parseFormulaConfig,
  serializeFormulaBoardV2,
  type FormulaBoardV2State
} from "@/src/features/task-renderer/formulaBoardV2";
import { buildRendererEvent, createRendererWorkspaceState, rendererWorkspaceReducer } from "@/src/features/task-renderer/rendererRuntime";

type Props = {
  taskInstanceId: string;
  schema: V2TaskUiSchema;
  response: TaskResponse;
  disabled?: boolean;
  onResponseChange: (response: TaskResponse) => void;
  onSubmit: () => void;
};

export function FormulaBoardV2({
  taskInstanceId,
  schema,
  response,
  disabled,
  onResponseChange,
  onSubmit
}: Props) {
  const workspace = schema.workspaces[0];
  const config = useMemo(
    () => (workspace ? parseFormulaConfig(workspace.config as Record<string, unknown>) : null),
    [workspace]
  );
  const [runtime, dispatch] = useReducer(
    rendererWorkspaceReducer<FormulaBoardV2State>,
    initialFormulaV2State(),
    createRendererWorkspaceState
  );
  const responseRef = useRef(response);
  responseRef.current = response;

  useEffect(() => {
    dispatch({ type: "RESET" });
  }, [schema.ui_revision]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!config || !workspace) return;
    const answer = formulaAnswer(runtime.present, config);
    onResponseChange({
      ...responseRef.current,
      answer: answer === null ? "" : String(answer),
      interaction_events: runtime.events,
      v2_workspaces: [
        { workspace_id: workspace.workspace_id, data: serializeFormulaBoardV2(runtime.present, config) }
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
    return <div className="surface-card unsupported-task">算式板题配置不完整。</div>;
  }

  const emit = (eventType: string, payload: Record<string, string | number | boolean | null>) =>
    buildRendererEvent(eventType, {
      task_instance_id: taskInstanceId,
      workspace_id: workspace.workspace_id,
      renderer_id: "formula-board",
      capability_id: "answer_input",
      payload
    });

  const state = runtime.present;
  const verdict = evaluateFormula(state, config);
  const activeSlotToken = state.activeSlot
    ? config.tokens.find(t => t.t === "slot" && t.id === state.activeSlot)
    : undefined;
  const activeToken = activeSlotToken && activeSlotToken.t === "slot" ? activeSlotToken : null;

  const activate = (slotId: string) => {
    if (disabled) return;
    dispatch({
      type: "SET_STATE",
      state: applyActivate(state, slotId),
      event: emit("SLOT_ACTIVATED", { slot: slotId })
    });
  };

  const pressNumber = (key: number) => {
    if (disabled) return;
    const result = applyNumberKey(state, config, key);
    if (!result.ok) return;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit(result.replaced ? "NUMBER_REPLACED" : "NUMBER_FILLED", {
        slot: state.activeSlot ?? "",
        value: (result.state.filled as Record<string, number>)[state.activeSlot as string],
        key
      })
    });
  };

  const pressOperator = (op: "+" | "-") => {
    if (disabled) return;
    const result = applyOperatorKey(state, config, op);
    if (!result.ok) return;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit(result.replaced ? "OPERATOR_REPLACED" : "OPERATOR_FILLED", {
        slot: state.activeSlot ?? "",
        value: op
      })
    });
  };

  const clearSlot = () => {
    if (disabled) return;
    const result = applyClear(state);
    if (!result.ok) return;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit("SLOT_CLEARED", { slot: state.activeSlot ?? "" })
    });
  };

  const undo = () => !disabled && dispatch({ type: "UNDO", event: emit("UNDO", {}) });
  const reset = () => !disabled && dispatch({ type: "RESET", event: emit("RESET", {}) });

  return (
    <div className="manipulative-card formula-board-v2" data-testid="formula-board-v2">
      <div className="manipulative-heading">
        <div>
          <strong>算式板</strong>
          <span>点亮空圈，用下面的数字键或符号键把算式补齐。</span>
        </div>
        <div className="workspace-actions">
          <button
            type="button"
            data-testid="fb-undo"
            disabled={disabled || runtime.history.length === 0}
            onClick={undo}
          >
            撤销
          </button>
          <button type="button" data-testid="fb-reset" disabled={disabled} onClick={reset}>
            重置
          </button>
        </div>
      </div>

      <div className="fb-formula" data-testid="fb-formula">
        {config.tokens.map((token, i) => {
          if (token.t === "num") return <span key={i} className="fb-num" data-testid={`fb-num-${token.v}`}>{token.v}</span>;
          if (token.t === "op") return <span key={i} className="fb-op">{token.v}</span>;
          if (token.t === "eq") return <span key={i} className="fb-eq">=</span>;
          const filledValue = state.filled[token.id];
          return (
            <button
              type="button"
              key={i}
              data-testid={`fb-slot-${token.id}`}
              className={`fb-slot ${filledValue !== undefined ? "filled" : ""} ${state.activeSlot === token.id ? "active" : ""}`}
              disabled={disabled}
              onClick={() => activate(token.id)}
            >
              {filledValue ?? "○"}
            </button>
          );
        })}
      </div>

      {activeToken && (
        <div className="fb-keypad" data-testid="fb-keypad">
          {activeToken.accept === "operator" ? (
            <>
              <button type="button" data-testid="fb-op-plus" className="fb-key op" disabled={disabled} onClick={() => pressOperator("+")}>＋</button>
              <button type="button" data-testid="fb-op-minus" className="fb-key op" disabled={disabled} onClick={() => pressOperator("-")}>－</button>
            </>
          ) : (
            <>
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 0].map(key => (
                <button
                  type="button"
                  key={key}
                  data-testid={`fb-key-${key}`}
                  className="fb-key"
                  disabled={disabled}
                  onClick={() => pressNumber(key)}
                >
                  {key}
                </button>
              ))}
            </>
          )}
          <button type="button" data-testid="fb-clear" className="fb-key clear" disabled={disabled} onClick={clearSlot}>
            清空
          </button>
        </div>
      )}

      <div className={`fb-evaluation ${verdict.status.toLowerCase()}`} data-testid="fb-evaluation">
        {verdict.status === "EMPTY"
          ? "还有空圈没填上"
          : verdict.status === "PASS"
            ? "等式成立啦"
            : verdict.error === "operator"
              ? "数字都对，符号选错了——换成另一个符号试试"
              : "两边的数不相等——想想谁该和谁在一边"}
      </div>

      <button
        type="button"
        className="primary-button"
        data-testid="fb-submit"
        // P0-01 口径：EMPTY（有空圈）拦提交；PASS∪FAIL 可达后端。
        disabled={disabled || verdict.status === "EMPTY"}
        onClick={onSubmit}
      >
        提交这道题
      </button>
    </div>
  );
}
