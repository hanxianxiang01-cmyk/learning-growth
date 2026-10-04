"use client";

/**
 * number-input V2 renderer（FE-1415 R04）——SEM-1413 / Gap R04。
 *
 * 语义最简：数字输入 → 提交。它是 submission_id 幂等契约（FE-1410）与
 * MathResponse V2 envelope 的专项验证入口。
 * 提交门禁口径（B5/P0-01 一脉相承）：EMPTY（未填/非法/越界）不可提交；
 * 已填合法数字即可提交——对错由后端权威判定，错误答案必须可达 Diagnosis 链。
 */

import { useEffect, useMemo, useRef, useState } from "react";
import type { InteractionEvent, TaskResponse, V2TaskUiSchema } from "@/src/lib/api/contracts";
import { buildRendererEvent } from "@/src/features/task-renderer/rendererRuntime";

type Props = {
  taskInstanceId: string;
  schema: V2TaskUiSchema;
  response: TaskResponse;
  disabled?: boolean;
  onResponseChange: (response: TaskResponse) => void;
  onSubmit: () => void;
};

export type NumberInputV2Config = {
  min: number | null;
  max: number | null;
  integerOnly: boolean;
};

/** config 解析（纯函数）：min/max/integer_only 字段级守卫；缺省=不设限。 */
export function parseNumberInputConfig(raw: Record<string, unknown>): NumberInputV2Config {
  const min = typeof raw.min === "number" ? raw.min : null;
  const max = typeof raw.max === "number" ? raw.max : null;
  return { min, max, integerOnly: raw.integer_only === true };
}

/** 输入文本 → 答案值（纯函数）：非法/越界/非整数（要求时）→ null（EMPTY 态）。 */
export function parseAnswer(text: string, config: NumberInputV2Config): number | null {
  const trimmed = text.trim();
  if (trimmed === "" || trimmed === "-" || trimmed === ".") return null;
  const value = Number(trimmed);
  if (!Number.isFinite(value)) return null;
  if (config.integerOnly && !Number.isInteger(value)) return null;
  if (config.min !== null && value < config.min) return null;
  if (config.max !== null && value > config.max) return null;
  return value;
}

/** workspace data 序列化（Evidence 形态：最终答案 + 输入历史尾部 20 条）。 */
export function serializeNumberInputV2(
  answer: number | null,
  history: Array<{ text: string; at: string }>
): Record<string, unknown> {
  return { answer, input_history: history.slice(-20) };
}

export function NumberInputV2({
  taskInstanceId,
  schema,
  response,
  disabled,
  onResponseChange,
  onSubmit
}: Props) {
  const workspace = schema.workspaces[0];
  const config = useMemo(
    () => parseNumberInputConfig((workspace?.config ?? {}) as Record<string, unknown>),
    [workspace]
  );
  const [text, setText] = useState("");
  const [events, setEvents] = useState<InteractionEvent[]>([]);
  const historyRef = useRef<Array<{ text: string; at: string }>>([]);
  const responseRef = useRef(response);
  responseRef.current = response;

  // 下一题（ui_revision 变化）→ 组件级清态
  const lastRevision = useRef(schema.ui_revision);
  useEffect(() => {
    if (lastRevision.current !== schema.ui_revision) {
      lastRevision.current = schema.ui_revision;
      setText("");
      setEvents([]);
      historyRef.current = [];
    }
  }, [schema.ui_revision]);

  const answer = parseAnswer(text, config);

  // 状态 → response 单向同步（对齐 NumberLineV2 的 effect 纪律；
  // FE-1411 教训：依赖全部是稳定值——answer(原始值)/events/state 引用）
  useEffect(() => {
    if (!workspace) return;
    onResponseChange({
      ...responseRef.current,
      answer: answer === null ? "" : String(answer),
      interaction_events: events,
      v2_workspaces: [
        {
          workspace_id: workspace.workspace_id,
          data: serializeNumberInputV2(answer, historyRef.current)
        }
      ],
      v2_response_type: schema.response_contract.response_type,
      v2_ui_revision: schema.ui_revision
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [answer, events, workspace, schema.ui_revision, schema.response_contract.response_type]);

  if (!workspace || workspace.renderer !== "number-input") {
    return <div className="surface-card unsupported-task">数字输入题配置不完整。</div>;
  }

  const onChange = (next: string) => {
    if (disabled) return;
    const cleaned = config.integerOnly
      ? next.replace(/[^\d-]/g, "")
      : next.replace(/[^\d.\-]/g, "");
    setText(cleaned);
    historyRef.current = [
      ...historyRef.current,
      { text: cleaned, at: new Date().toISOString() }
    ];
    setEvents(prev =>
      [
        ...prev,
        buildRendererEvent("NUMBER_INPUT_CHANGED", {
          task_instance_id: taskInstanceId,
          workspace_id: workspace.workspace_id,
          renderer_id: "number-input",
          capability_id: "answer_input",
          payload: { text: cleaned }
        })
      ].slice(-100)
    );
  };

  return (
    <div className="manipulative-card number-input-v2" data-testid="number-input-v2">
      <div className="manipulative-heading">
        <div>
          <strong>写出答案</strong>
          <span>想好了就把数字写在框里，然后提交。</span>
        </div>
      </div>
      <label className="ni-field">
        <span className="sr-only">我的答案</span>
        <input
          data-testid="ni-input"
          inputMode={config.integerOnly ? "numeric" : "decimal"}
          value={text}
          disabled={disabled}
          placeholder={
            config.min !== null && config.max !== null
              ? `${config.min} ~ ${config.max}`
              : "输入数字"
          }
          onChange={event => onChange(event.target.value)}
        />
      </label>
      <div
        className={`ni-evaluation ${answer === null ? "empty" : "ready"}`}
        data-testid="ni-evaluation"
      >
        {answer === null ? "还没写好答案" : `你的答案：${answer}`}
      </div>
      <button
        type="button"
        className="primary-button"
        data-testid="ni-submit"
        // 门禁只看"有没有可提交答案"，不看对错（P0-01 口径）。
        disabled={disabled || answer === null}
        onClick={onSubmit}
      >
        提交这道题
      </button>
    </div>
  );
}
