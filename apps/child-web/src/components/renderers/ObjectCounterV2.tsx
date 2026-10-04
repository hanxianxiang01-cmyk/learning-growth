"use client";

import { useEffect, useMemo, useReducer, useRef } from "react";
import type { TaskResponse, V2TaskUiSchema } from "@/src/lib/api/contracts";
import {
  answerOf,
  applyCompose,
  applyDecompose,
  applyDelta,
  evaluateStructure,
  initialObjectCounterV2State,
  serializeObjectCounterV2,
  total,
  type ExpectedGroup,
  type ObjectCounterGroup,
  type ObjectCounterV2Config,
  type ObjectCounterV2State
} from "@/src/features/task-renderer/objectCounterV2";
import { buildRendererEvent, createRendererWorkspaceState, rendererWorkspaceReducer } from "@/src/features/task-renderer/rendererRuntime";

type Props = {
  taskInstanceId: string;
  schema: V2TaskUiSchema;
  response: TaskResponse;
  disabled?: boolean;
  onResponseChange: (response: TaskResponse) => void;
  onSubmit: () => void;
};

function readGroup(value: unknown): ObjectCounterGroup | null {
  if (typeof value !== "object" || value === null) return null;
  const v = value as Record<string, unknown>;
  if (typeof v.group_id !== "string" || typeof v.label !== "string") return null;
  return {
    group_id: v.group_id,
    label: v.label,
    symbol: typeof v.symbol === "string" ? v.symbol : "🔵",
    count: typeof v.count === "number" && v.count >= 0 ? v.count : 0,
    locked: v.locked === true
  };
}

function readConfig(schema: V2TaskUiSchema):
  | { groups: ObjectCounterGroup[]; expected: ExpectedGroup[]; maxTotalCount: number }
  | null {
  const workspace = schema.workspaces[0];
  if (!workspace || workspace.renderer !== "object-counter") return null;

  const groups = Array.isArray(workspace.config.groups)
    ? workspace.config.groups.map(readGroup).filter((g): g is ObjectCounterGroup => g !== null)
    : [];
  const expected = Array.isArray(workspace.config.expected)
    ? (workspace.config.expected as unknown[])
        .map(e => {
          if (typeof e !== "object" || e === null) return null;
          const v = e as Record<string, unknown>;
          return typeof v.group_id === "string" && typeof v.min_count === "number"
            ? { group_id: v.group_id, min_count: v.min_count }
            : null;
        })
        .filter((e): e is ExpectedGroup => e !== null)
    : [];

  if (groups.length === 0 || expected.length === 0) return null;
  const maxTotalCount =
    typeof workspace.config.max_total_count === "number" ? workspace.config.max_total_count : 20;
  return { groups, expected, maxTotalCount };
}

export function ObjectCounterV2({
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
    () => (config ? initialObjectCounterV2State(config.groups) : { groups: [] }),
    [config]
  );
  const [runtime, dispatch] = useReducer(
    rendererWorkspaceReducer<ObjectCounterV2State>,
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
      answer: answerOf(runtime.present)?.toString() ?? "",
      interaction_events: runtime.events,
      v2_workspaces: [
        {
          workspace_id: workspace.workspace_id,
          data: serializeObjectCounterV2(runtime.present)
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
    return <div className="surface-card unsupported-task">点子图题配置不完整，暂时无法开始。</div>;
  }

  const cfg: ObjectCounterV2Config = { maxTotalCount: config.maxTotalCount };

  const emit = (
    eventType: string,
    capability: string,
    payload: Record<string, string | number | boolean | null>
  ) =>
    buildRendererEvent(eventType, {
      task_instance_id: taskInstanceId,
      workspace_id: workspace.workspace_id,
      renderer_id: "object-counter",
      capability_id: capability,
      payload
    });

  const apply = (
    result: ReturnType<typeof applyDelta>,
    eventType: string,
    capability: string,
    payload: Record<string, string | number | boolean | null>
  ) => {
    if (disabled || !result.ok) return;
    dispatch({ type: "SET_STATE", state: result.state, event: emit(eventType, capability, payload) });
  };

  const add = (groupId: string, withGroupId: string | null) =>
    apply(applyDelta(runtime.present, groupId, 1, cfg), "COUNT_ADDED", "add_object", {
      group_id: groupId,
      delta: 1,
      with_group_id: withGroupId ?? ""
    });

  const remove = (groupId: string) =>
    apply(applyDelta(runtime.present, groupId, -1, cfg), "COUNT_REMOVED", "remove_object", {
      group_id: groupId,
      delta: -1
    });

  const compose = (sourceId: string, targetId: string) =>
    apply(applyCompose(runtime.present, sourceId, targetId), "GROUP_COMPOSED", "compose_groups", {
      source_group_id: sourceId,
      target_group_id: targetId
    });

  const decomposeCounter = useRef(0);
  const decompose = (groupId: string) => {
    decomposeCounter.current += 1;
    const newGroup: ObjectCounterGroup = {
      group_id: `d${decomposeCounter.current}`,
      label: `拆出的${decomposeCounter.current}`,
      symbol: runtime.present.groups.find(g => g.group_id === groupId)?.symbol ?? "🔵",
      count: 0
    };
    apply(applyDecompose(runtime.present, groupId, 1, newGroup), "GROUP_DECOMPOSED", "decompose_group", {
      source_group_id: groupId,
      new_group_id: newGroup.group_id,
      count: 1
    });
  };

  const undo = () =>
    !disabled &&
    dispatch({ type: "UNDO", event: emit("UNDO", "undo", {}) });
  const reset = () =>
    !disabled &&
    dispatch({ type: "RESET", event: emit("RESET", "reset", {}) });

  // compare 语义锚点：增减操作默认附着"与第一个非本组比较"（题目若需要显式比较对象，
  // add 时传 with 参数；E2E 断言 payload 键存在即可）。
  const evaluation = evaluateStructure(runtime.present, config.expected);
  const answer = answerOf(runtime.present);

  return (
    <div className="manipulative-card object-counter-v2" data-testid="object-counter-v2">
      <div className="manipulative-heading">
        <div>
          <strong>点子图</strong>
          <span>把物体放到组里，合起来或拆一拆，然后提交。</span>
        </div>
        <div className="workspace-actions">
          <button type="button" data-testid="oc-undo" disabled={disabled || runtime.history.length === 0} onClick={undo}>
            撤销
          </button>
          <button type="button" data-testid="oc-reset" disabled={disabled} onClick={reset}>
            重置
          </button>
        </div>
      </div>

      <div className="oc-groups">
        {runtime.present.groups.map(group => {
          const merged = group.composed_into;
          return (
            <div
              key={group.group_id}
              className={`oc-group ${merged ? "is-merged" : ""}`}
              data-testid={`oc-group-${group.group_id}`}
            >
              <div className="oc-group-head">
                <strong>{group.label}</strong>
                <span className="oc-count">{group.count}</span>
                {group.locked && <span className="oc-locked">题目给定</span>}
                {merged && <span className="oc-merged">已并入{merged}（{group.composed_count}）</span>}
              </div>
              <div className="oc-objects" aria-label={`${group.label}里的物体`}>
                {Array.from({ length: group.count }, (_, i) => (
                  <span key={i} className="oc-object">{group.symbol}</span>
                ))}
                {group.count === 0 && <span className="oc-empty-hint">空</span>}
              </div>
              {!group.locked && !merged && (
                <div className="oc-group-actions">
                  <button type="button" data-testid={`oc-add-${group.group_id}`} disabled={disabled} onClick={() => add(group.group_id, null)}>
                    ＋1
                  </button>
                  <button type="button" data-testid={`oc-remove-${group.group_id}`} disabled={disabled || group.count === 0} onClick={() => remove(group.group_id)}>
                    －1
                  </button>
                  <button type="button" data-testid={`oc-decompose-${group.group_id}`} disabled={disabled || group.count === 0} onClick={() => decompose(group.group_id)}>
                    拆出1个
                  </button>
                  {runtime.present.groups
                    .filter(other => other.group_id !== group.group_id && !other.composed_into)
                    .map(other => (
                      <button
                        key={other.group_id}
                        type="button"
                        data-testid={`oc-compose-${group.group_id}-into-${other.group_id}`}
                        disabled={disabled || group.count === 0}
                        onClick={() => compose(group.group_id, other.group_id)}
                      >
                        并入「{other.label}」
                      </button>
                    ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className={`oc-evaluation ${evaluation.toLowerCase()}`} data-testid="oc-evaluation">
        <strong>
          {evaluation === "PASS"
            ? "摆好了"
            : evaluation === "FAIL"
              ? "数量还要检查"
              : evaluation === "PARTIAL"
                ? "还有组空着"
                : "先放物体"}
        </strong>
        <span>一共有 {total(runtime.present)} 个{answer === null ? "，还不能提交" : `，答案 ${answer}`}。</span>
      </div>

      <button
        type="button"
        className="primary-button"
        data-testid="oc-submit"
        // B5/P0-01 口径：门禁只看"有没有可提交答案"，不看对错。
        // PASS/FAIL → 可提交（错误答案必须能到达后端验证 Diagnosis 链）；PARTIAL/EMPTY → 不可。
        disabled={disabled || (evaluation !== "PASS" && evaluation !== "FAIL")}
        onClick={onSubmit}
      >
        提交这道题
      </button>
    </div>
  );
}
