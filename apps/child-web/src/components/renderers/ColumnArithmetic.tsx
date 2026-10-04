"use client";

import { useEffect, useMemo, useReducer, useRef } from "react";
import type { InteractionEvent, TaskResponse, V2TaskUiSchema } from "@/src/lib/api/contracts";
import {
  evaluateColumnArithmetic,
  initialColumnArithmeticState,
  numericAnswer,
  placePower,
  serializeColumnArithmetic,
  setResultDigit,
  toggleCarry,
  type ColumnArithmeticConfig,
  type ColumnArithmeticState,
  type ColumnPlace
} from "@/src/features/task-renderer/columnArithmetic";
import { buildRendererEvent, createRendererWorkspaceState, rendererWorkspaceReducer } from "@/src/features/task-renderer/rendererRuntime";

type Props = {
  taskInstanceId: string;
  schema: V2TaskUiSchema;
  response: TaskResponse;
  disabled?: boolean;
  onResponseChange: (response: TaskResponse) => void;
  onSubmit: () => void;
};

const PLACE_LABEL: Record<ColumnPlace, string> = {
  ones: "个",
  tens: "十",
  hundreds: "百",
  thousands: "千"
};

function readConfig(schema: V2TaskUiSchema): ColumnArithmeticConfig | null {
  const workspace = schema.workspaces[0];
  if (!workspace || workspace.renderer !== "column-arithmetic") return null;

  const operands = Array.isArray(workspace.config.operands)
    ? workspace.config.operands.filter((value): value is number => typeof value === "number")
    : [];

  const places = Array.isArray(workspace.config.places)
    ? workspace.config.places.filter(
        (value): value is ColumnPlace =>
          value === "ones" || value === "tens" || value === "hundreds" || value === "thousands"
      )
    : (["ones", "tens", "hundreds"] as ColumnPlace[]);

  return operands.length >= 2 && places.length > 0
    ? { operands, places, operand_layout: workspace.config.operand_layout === "fixed" ? "fixed" : "right_aligned" }
    : null;
}

export function ColumnArithmetic({
  taskInstanceId,
  schema,
  response,
  disabled,
  onResponseChange,
  onSubmit
}: Props) {
  const config = useMemo(() => readConfig(schema), [schema]);
  const workspace = schema.workspaces[0];
  const initial = useMemo(
    () =>
      config
        ? initialColumnArithmeticState(
            config,
            workspace?.initial_state as Partial<ColumnArithmeticState> | undefined
          )
        : { result_digits: [], carries: [] },
    [config, workspace]
  );
  const [runtime, dispatch] = useReducer(
    rendererWorkspaceReducer<ColumnArithmeticState>,
    initial,
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
      answer: numericAnswer(runtime.present)?.toString() ?? "",
      interaction_events: runtime.events,
      v2_workspaces: [
        {
          workspace_id: workspace.workspace_id,
          data: serializeColumnArithmetic(runtime.present) as unknown as Record<string, unknown>
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
    return <div className="surface-card unsupported-task">竖式题配置不完整，暂时无法开始。</div>;
  }

  const emit = (
    eventType: string,
    capability: string,
    payload: Record<string, string | number | boolean | null>
  ) => {
    const event = buildRendererEvent(eventType, {
      task_instance_id: taskInstanceId,
      workspace_id: workspace.workspace_id,
      renderer_id: "column-arithmetic",
      capability_id: capability,
      payload
    });
    return event;
  };

  const setDigit = (place: ColumnPlace, raw: string) => {
    if (disabled) return;
    const value = raw === "" ? null : Number(raw);
    if (value !== null && (!Number.isInteger(value) || value < 0 || value > 9)) return;
    const next = setResultDigit(runtime.present, place, value);
    const event = emit("DIGIT_ENTERED", "input_digit", { place, value });
    dispatch({ type: "SET_STATE", state: next, event });
  };

  const setCarry = (place: ColumnPlace) => {
    if (disabled) return;
    const next = toggleCarry(runtime.present, place);
    const value = next.carries.find(item => item.from_place === place)?.value ?? 0;
    const event = emit(value ? "CARRY_CREATED" : "CARRY_REMOVED", "place_carry", {
      from_place: place,
      to_place: next.carries.find(item => item.from_place === place)?.to_place ?? "",
      value
    });
    dispatch({ type: "SET_STATE", state: next, event });
  };

  const reset = () => {
    if (disabled) return;
    const event = emit("RESET", "reset", {});
    dispatch({ type: "RESET", event });
  };

  const undo = () => {
    if (disabled) return;
    const event = emit("UNDO", "undo", {});
    dispatch({ type: "UNDO", event });
  };

  const evaluation = evaluateColumnArithmetic(config, runtime.present);
  const columns = [...config.places].reverse();

  return (
    <div className="manipulative-card column-arithmetic" data-testid="column-arithmetic">
      <div className="manipulative-heading">
        <div>
          <strong>竖式计算</strong>
          <span>按个位、十位、百位依次计算，先填写结果，再检查进位。</span>
        </div>
        <div className="workspace-actions">
          <button type="button" disabled={disabled} onClick={undo}>撤销</button>
          <button type="button" disabled={disabled} onClick={reset}>重置</button>
        </div>
      </div>

      <div className="column-arithmetic-board">
        {config.operands.map((operand, index) => (
          <div className="column-number-row" key={`operand-${index}`}>
            <span className="column-row-label">{index === 0 ? "算式" : ""}</span>
            <div className="column-number">
              {columns.map(place => (
                <span key={place}>{Math.floor(Math.abs(operand) / placePower(place)) % 10}</span>
              ))}
            </div>
          </div>
        ))}

        <div className="column-operation-row">
          <span className="column-row-label">结果</span>
          <div className="column-number result-row">
            {columns.map(place => {
              const digit = runtime.present.result_digits.find(item => item.place === place)?.value;
              return (
                <label key={place} className="column-cell">
                  <span className="sr-only">{PLACE_LABEL[place]}位结果</span>
                  <input
                    aria-label={`${PLACE_LABEL[place]}位结果`}
                    inputMode="numeric"
                    maxLength={1}
                    value={digit ?? ""}
                    disabled={disabled}
                    onChange={event => setDigit(place, event.target.value.replace(/\D/g, ""))}
                  />
                </label>
              );
            })}
          </div>
        </div>

        <div className="carry-row">
          <span className="column-row-label">进位</span>
          <div className="column-number">
            {columns.map(place => {
              const carry = runtime.present.carries.find(item => item.to_place === place);
              if (!carry) return <span key={place} className="carry-cell empty">·</span>;
              return (
                <button
                  key={place}
                  type="button"
                  className={`carry-cell ${carry.value ? "is-on" : ""}`}
                  disabled={disabled}
                  aria-label={`${PLACE_LABEL[carry.from_place]}位进位到${PLACE_LABEL[carry.to_place]}位`}
                  onClick={() => setCarry(carry.from_place)}
                >
                  {carry.value}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <div className={`column-evaluation ${evaluation.status.toLowerCase()}`}>
        <strong>
          {evaluation.status === "PASS"
            ? "完成"
            : evaluation.status === "PARTIAL"
              ? "继续检查"
              : evaluation.status === "INVALID"
                ? "请检查输入"
                : "再检查一次"}
        </strong>
        <span>
          {evaluation.status === "PASS"
            ? `结果 ${evaluation.expected_answer}，进位也正确。`
            : "每一位都可以单独修改，进位按钮点一下即可切换。"}
        </span>
      </div>

      <button
        className="primary-button"
        type="button"
        // FE-1403-P0-01（联调方案 §3）：提交资格只由「是否有可提交答案」决定，
        // 不由 evaluator 对错决定。PASS/FAIL 均已填满结果位 → 可提交；
        // PARTIAL（含 EMPTY，结果位未满）与 INVALID（非法输入）→ 不可提交。
        // 错误答案必须能到达后端，否则 Diagnosis / Retry / Evidence 链无法验证。
        disabled={disabled || (evaluation.status !== "PASS" && evaluation.status !== "FAIL")}
        onClick={onSubmit}
      >
        提交这道题
      </button>
    </div>
  );
}
