"use client";

/**
 * pattern-board V2 组件（FE-1436 R19，Batch E 收官）。runtime 装配对齐 MoneyBoardV2。
 *
 * 花边规律：可见串 + 2 个空格。点调色板=往第一个空格填一颗珠子；
 * 点已填的珠子再点颜色=改这颗（修改留痕）；点珠子本身=抠掉。
 * 答案=空格 token 拼接整数（12；后端标量判分）。
 * 相位错=phase_shift / 无脑延续末颗=rule_ignored（Diagnosis P0"规律识别错误"）；
 * 改过才凑对=changed_once 留痕（Gap"尝试顺序、修改过程"）。
 */

import { useEffect, useMemo, useReducer, useRef } from "react";
import type { TaskResponse, V2TaskUiSchema } from "@/src/lib/api/contracts";
import {
  applyClearAt,
  applyPlaceToken,
  applyReplaceAt,
  evaluatePattern,
  initBlanks,
  parsePatternConfig,
  patternAnswer,
  serializePatternV2,
  type PatternV2State
} from "@/src/features/task-renderer/patternBoardV2";
import { buildRendererEvent, createRendererWorkspaceState, rendererWorkspaceReducer } from "@/src/features/task-renderer/rendererRuntime";

type Props = {
  taskInstanceId: string;
  schema: V2TaskUiSchema;
  response: TaskResponse;
  disabled?: boolean;
  onResponseChange: (response: TaskResponse) => void;
  onSubmit: () => void;
};

/** token → 颜色（1..5）。 */
const TOKEN_COLOR: Record<number, { bg: string; label: string }> = {
  1: { bg: "#e0a800", label: "黄" },
  2: { bg: "#3b6fb5", label: "蓝" },
  3: { bg: "#d64545", label: "红" },
  4: { bg: "#2f9e63", label: "绿" },
  5: { bg: "#7a5aa8", label: "紫" },
};

export function PatternBoardV2({
  taskInstanceId,
  schema,
  response,
  disabled,
  onResponseChange,
  onSubmit
}: Props) {
  const workspace = schema.workspaces[0];
  const config = useMemo(
    () => (workspace ? parsePatternConfig(workspace.config as Record<string, unknown>) : null),
    [workspace]
  );
  const [runtime, dispatch] = useReducer(
    rendererWorkspaceReducer<PatternV2State>,
    // 哨兵（beads 空数组=config 未装载，同 R15 steps/R17 m=-1）
    { beads: [], attempt_history: [] },
    createRendererWorkspaceState
  );
  const responseRef = useRef(response);
  responseRef.current = response;

  useEffect(() => {
    if (config) dispatch({ type: "SET_STATE", state: initBlanks(config) });
  }, [config, schema.ui_revision]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!config || !workspace || runtime.present.beads.length === 0) return;
    const answer = patternAnswer(runtime.present, config);
    onResponseChange({
      ...responseRef.current,
      answer: answer === null ? "" : String(answer),
      interaction_events: runtime.events,
      v2_workspaces: [
        { workspace_id: workspace.workspace_id, data: serializePatternV2(runtime.present, config) }
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
    return <div className="surface-card unsupported-task">规律板题配置不完整。</div>;
  }

  const emit = (eventType: string, payload: Record<string, string | number | boolean | null>) =>
    buildRendererEvent(eventType, {
      task_instance_id: taskInstanceId,
      workspace_id: workspace.workspace_id,
      renderer_id: "pattern-board",
      capability_id: "extend_pattern",
      payload
    });

  const state = runtime.present;
  const verdict = evaluatePattern(state, config);

  const pickToken = (token: number) => {
    if (disabled) return;
    const active = activeSlot();
    if (active === -1) return;
    if (state.beads[active] === null) {
      const result = applyPlaceToken(state, config, token);
      if (!result.ok) return;
      dispatch({
        type: "SET_STATE",
        state: result.state,
        event: emit("PATTERN_BEAD_PLACED", { slot: active, token, color: TOKEN_COLOR[token]?.label ?? token })
      });
    } else {
      const result = applyReplaceAt(state, config, active, token);
      if (!result.ok) return;
      dispatch({
        type: "SET_STATE",
        state: result.state,
        event: emit("PATTERN_BEAD_REPLACED", { slot: active, from: state.beads[active], token })
      });
    }
  };

  const clearBead = (slot: number) => {
    if (disabled) return;
    const result = applyClearAt(state, slot);
    if (!result.ok) return;
    setActiveSlot(-1);
    dispatch({
      type: "SET_STATE",
      state: result.state,
      event: emit("PATTERN_BEAD_REMOVED", { slot, from: state.beads[slot] })
    });
  };

  // 当前操作槽位：点选中的已填珠（改/抠目标），否则第一个空格
  const [activeSlotIdx, setActiveSlot] = useReducer((_: number, i: number) => i, -1);
  const activeSlot = () =>
    activeSlotIdx >= 0 && state.beads[activeSlotIdx] !== null
      ? activeSlotIdx
      : state.beads.findIndex(b => b === null);

  const undo = () => !disabled && dispatch({ type: "UNDO", event: emit("UNDO", {}) });
  const reset = () =>
    !disabled &&
    dispatch({ type: "SET_STATE", state: initBlanks(config), event: emit("PATTERN_RESET", {}) });

  const beadsView = [...config.visible.map(v => ({ token: v, fixed: true, slot: -1 })),
    ...state.beads.map((b, i) => ({ token: b, fixed: false, slot: config.visible.length + i }))];

  const clickBead = (beadIdx: number) => {
    if (disabled || state.beads[beadIdx] === null) return;
    if (activeSlotIdx === beadIdx) {
      // 再点已选中那颗=抠掉
      clearBead(beadIdx);
      return;
    }
    setActiveSlot(beadIdx);
  };

  return (
    <div className="manipulative-card pattern-board-v2" data-testid="pattern-board-v2">
      <div className="manipulative-heading">
        <div>
          <strong>找规律接着摆</strong>
          <span>花边按什么规律排的？先数一数，再把后面 2 个空格补上。点颜色=放进空格；点珠子=抠掉。</span>
        </div>
        <div className="workspace-actions">
          <button type="button" data-testid="pb-undo" disabled={disabled || runtime.history.length === 0} onClick={undo}>
            撤销
          </button>
          <button type="button" data-testid="pb-reset" disabled={disabled} onClick={reset}>
            重置
          </button>
        </div>
      </div>

      <div className="pb-strip" data-testid="pb-strip">
        {beadsView.map((b, i) => {
          const blank = b.token === null;
          const active = !b.fixed && !blank && b.slot - config.visible.length === activeSlot() && state.beads[b.slot - config.visible.length] !== null;
          return (
            <button
              key={b.fixed ? `v${i}` : `b${i}`}
              type="button"
              data-testid={b.fixed ? undefined : `pb-blank-${i - config.visible.length}`}
              className={`pb-bead ${b.fixed ? "fixed" : ""} ${blank ? "blank" : ""} ${active ? "active" : ""}`.trim()}
              style={!blank ? { background: TOKEN_COLOR[b.token as number]?.bg } : undefined}
              disabled={disabled || b.fixed || blank}
              onClick={() => !blank && !b.fixed && clickBead(b.slot - config.visible.length)}
            >
              {blank ? "" : ""}
            </button>
          );
        })}
      </div>

      <div className="pb-palette" data-testid="pb-palette">
        {config.palette.map(t => (
          <button
            key={t}
            type="button"
            data-testid={`pb-token-${t}`}
            className="pb-token"
            style={{ background: TOKEN_COLOR[t]?.bg }}
            disabled={disabled}
            onClick={() => pickToken(t)}
          >
            {TOKEN_COLOR[t]?.label ?? t}
          </button>
        ))}
      </div>

      <div className={`pb-evaluation ${verdict.status.toLowerCase()}`} data-testid="pb-evaluation">
        {verdict.status === "EMPTY"
          ? `还差 ${config.blanks - verdict.filled} 颗没摆上`
          : verdict.status === "PASS"
            ? verdict.changed_once
              ? "摆对了！改过一次也算数——试错就是把规律找对的过程"
              : `摆对了！前面是「${config.visible.map(v => TOKEN_COLOR[v]?.label).join("、")}」这样轮流排的，后面接着这个规律就对啦`
            : verdict.error === "phase_shift"
              ? "规律好像找对了，但你**从上一颗重新数**了——接着最后那颗往后数才对"
              : verdict.error === "rule_ignored"
                ? "全摆成一种颜色啦——先看看前面是怎么**轮流**的"
                : "顺序对不上规律，再数一遍前面几颗"}
      </div>

      <button
        type="button"
        className="primary-button"
        data-testid="pb-submit"
        // P0-01 口径：EMPTY（没填满空格）拦提交；PASS∪FAIL 可达后端。
        disabled={disabled || verdict.status === "EMPTY"}
        onClick={onSubmit}
      >
        提交规律
      </button>
    </div>
  );
}
