"use client";

/**
 * money-board V2 组件（FE-1431 R18，Batch E 第三题）。runtime 装配对齐 ClockV2。
 *
 * 台面上是商品价格；钱包四档（1角/5角/1元/5元）点一次加一枚，"取回"减一枚。
 * 答案=付出总角数（组件自动填，后端标量判分）。
 * 把 5 角当 5 元用（角位数字×5角币）→ denomination_confusion（Diagnosis P0 面值/金额关系）。
 * 凑对但币多于最少组合 → 判对 + uses_extra 留痕（解耦第八次运用）。
 */

import { useEffect, useMemo, useReducer, useRef } from "react";
import type { TaskResponse, V2TaskUiSchema } from "@/src/lib/api/contracts";
import {
  applyAddCoin,
  applyRemoveCoin,
  coins,
  evaluatePayment,
  initialMoneyV2State,
  moneyAnswer,
  parseMoneyConfig,
  serializeMoneyV2,
  unitLabel,
  type MoneyV2State
} from "@/src/features/task-renderer/moneyBoardV2";
import { buildRendererEvent, createRendererWorkspaceState, rendererWorkspaceReducer } from "@/src/features/task-renderer/rendererRuntime";

type Props = {
  taskInstanceId: string;
  schema: V2TaskUiSchema;
  response: TaskResponse;
  disabled?: boolean;
  onResponseChange: (response: TaskResponse) => void;
  onSubmit: () => void;
};

export function MoneyBoardV2({
  taskInstanceId,
  schema,
  response,
  disabled,
  onResponseChange,
  onSubmit
}: Props) {
  const workspace = schema.workspaces[0];
  const config = useMemo(
    () => (workspace ? parseMoneyConfig(workspace.config as Record<string, unknown>) : null),
    [workspace]
  );
  const [runtime, dispatch] = useReducer(
    rendererWorkspaceReducer<MoneyV2State>,
    { counts: {}, selection_history: [] },
    createRendererWorkspaceState
  );
  const responseRef = useRef(response);
  responseRef.current = response;

  useEffect(() => {
    dispatch({ type: "SET_STATE", state: initialMoneyV2State() });
  }, [config, schema.ui_revision]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!config || !workspace) return;
    const answer = moneyAnswer(runtime.present);
    onResponseChange({
      ...responseRef.current,
      answer: answer === null ? "" : String(answer),
      interaction_events: runtime.events,
      v2_workspaces: [
        { workspace_id: workspace.workspace_id, data: serializeMoneyV2(runtime.present, config) }
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
    return <div className="surface-card unsupported-task">付钱题配置不完整。</div>;
  }

  const emit = (eventType: string, payload: Record<string, string | number | boolean | null>) =>
    buildRendererEvent(eventType, {
      task_instance_id: taskInstanceId,
      workspace_id: workspace.workspace_id,
      renderer_id: "money-board",
      capability_id: "compose_groups",
      payload
    });

  const state = runtime.present;
  const verdict = evaluatePayment(state, config);
  const yuan = Math.floor((verdict.status !== "EMPTY" ? Object.entries(state.counts).reduce((a, [d, n]) => a + Number(d) * n, 0) : 0));
  const totalText = `${Math.floor(yuan / 10)}元${yuan % 10}角`;

  const addCoin = (d: number) => {
    if (disabled) return;
    const result = applyAddCoin(state, config, d);
    if (!result.ok) return;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit("MONEY_COIN_ADDED", { denomination: d, label: unitLabel(d), count: (result.state.counts[d] ?? 0), total: result.total })
    });
  };

  const removeCoin = (d: number) => {
    if (disabled) return;
    const result = applyRemoveCoin(state, config, d);
    if (!result.ok) return;
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit("MONEY_COIN_REMOVED", { denomination: d, label: unitLabel(d), count: result.state.counts[d] ?? 0, total: result.total })
    });
  };

  const undo = () => !disabled && dispatch({ type: "UNDO", event: emit("UNDO", {}) });
  const reset = () =>
    !disabled &&
    dispatch({ type: "SET_STATE", state: initialMoneyV2State(), event: emit("MONEY_RESET", {}) });

  return (
    <div className="manipulative-card money-board-v2" data-testid="money-board-v2">
      <div className="manipulative-heading">
        <div>
          <strong>付钱</strong>
          <span>点钱包里的一档=拿出一枚放到台面上；点「取回」放回去。凑出**正好**商品的价格。</span>
        </div>
        <div className="workspace-actions">
          <button type="button" data-testid="mb-undo" disabled={disabled || runtime.history.length === 0} onClick={undo}>
            撤销
          </button>
          <button type="button" data-testid="mb-reset" disabled={disabled} onClick={reset}>
            重置
          </button>
        </div>
      </div>

      <div className="mb-price" data-testid="mb-price">
        商品价：{Math.floor(config.price / 10)}元{config.price % 10}角
      </div>

      <div className="mb-wallet" data-testid="mb-wallet">
        {config.denominations.map(d => (
          <div key={d} className="mb-unit" data-testid={`mb-unit-${d}`}>
            <button
              type="button"
              data-testid={`mb-add-${d}`}
              className="mb-coin"
              disabled={disabled}
              onClick={() => addCoin(d)}
            >
              {unitLabel(d)}
            </button>
            <div className="mb-on-table" data-testid={`mb-count-${d}`}>
              {Array.from({ length: state.counts[d] ?? 0 }, (_, i) => (
                <span key={i} className="mb-chip">{unitLabel(d)}</span>
              ))}
              {(state.counts[d] ?? 0) === 0 ? <span className="mb-muted">—</span> : null}
            </div>
            <button
              type="button"
              data-testid={`mb-remove-${d}`}
              className="mb-return"
              disabled={disabled || (state.counts[d] ?? 0) === 0}
              onClick={() => removeCoin(d)}
            >
              取回
            </button>
          </div>
        ))}
      </div>

      <div className={`mb-evaluation ${verdict.status.toLowerCase()}`} data-testid="mb-evaluation">
        {verdict.status === "EMPTY"
          ? "一枚钱还没拿出来——先数一数商品价格里有几个 1 元"
          : verdict.status === "PASS"
            ? verdict.uses_extra
              ? `凑对了 ${totalText}！不过用了 ${coins(state)} 枚，最少 ${verdict.min_coins} 枚就能搞定（5 角×3 可以换成 1 元＋5 角）`
              : `正好 ${totalText}，${coins(state)} 枚搞定`
            : verdict.error === "denomination_confusion"
              ? `现在是 ${totalText}——你是不是把「5角」当成「5元」数啦？角和元不一样大`
              : verdict.error === "underpaid"
                ? `${totalText}，还差 ${-verdict.diff} 角（差 ${Math.ceil(-verdict.diff / 10)} 个 1 元的位置想想怎么补）`
                : `${totalText}，超出 ${verdict.diff} 角了，取回几张`}
      </div>

      <button
        type="button"
        className="primary-button"
        data-testid="mb-submit"
        // P0-01 口径：EMPTY（一枚没拿）拦提交；PASS∪FAIL 可达后端。
        disabled={disabled || verdict.status === "EMPTY"}
        onClick={onSubmit}
      >
        提交付钱
      </button>
    </div>
  );
}
