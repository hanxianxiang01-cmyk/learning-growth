"use client";

import { useMemo, useState } from "react";
import { ChildSkinProvider } from "@/src/theme/ChildSkinProvider";
import { TaskRenderer, createEmptyTaskResponse } from "@/src/features/task-renderer";
import { getRendererDescriptor, resolveRendererId, RENDERER_REGISTRY, V2_RELEASE_RENDERER_IDS } from "@/src/features/task-renderer/rendererRegistry";
import type { TaskInstance, TaskResponse, TaskResponseSchema, WorkspaceUiAction } from "@/src/lib/api/contracts";

const responseSchema: TaskResponseSchema = {
  type: "structured",
  answer_type: "number",
  representation_required: true,
  allowed_representation_types: ["object-counter", "bar-model", "number-line"]
};

const fixtures: TaskInstance[] = [
  {
    task_instance_id: "v14-objects",
    ability_id: "ability_fixture_rel",
    difficulty: 2,
    goal: "数量关系 · Object Counter",
    strategy_policy: {},
    ui_schema: {
      schema_version: "1.0",
      kind: "manipulative",
      renderer_id: "object-counter",
      interaction_capabilities: ["answer_input", "drag", "align", "undo", "reset", "highlight", "focus"],
      prompt: "8个苹果比5个苹果多几个？",
      answer_placeholder: "输入答案",
      visual: {
        type: "objects",
        groups: [
          { id: "a", label: "第一组", count: 8, symbol: "🍎" },
          { id: "b", label: "第二组", count: 5, symbol: "🍎" }
        ]
      },
      tools: ["move", "align", "undo", "reset"],
      response_schema: responseSchema
    }
  },
  {
    task_instance_id: "v14-bar",
    ability_id: "ability_fixture_model",
    difficulty: 2,
    goal: "建模表征 · Bar Model",
    strategy_policy: {},
    ui_schema: {
      schema_version: "1.0",
      kind: "manipulative",
      renderer_id: "bar-model",
      interaction_capabilities: ["answer_input", "resize", "undo", "reset", "highlight", "focus"],
      prompt: "原来12本，借走4本，还剩多少？",
      answer_placeholder: "输入答案",
      visual: {
        type: "bar-model",
        relationship: "part-whole",
        max_value: 12,
        bars: [
          { id: "total", label: "原来", value: 12, max: 12 },
          { id: "taken", label: "借走", value: 4, max: 12 },
          { id: "remain", label: "剩下", unknown: true, max: 12 }
        ]
      },
      tools: ["resize", "undo", "reset"],
      response_schema: responseSchema
    }
  },
  {
    task_instance_id: "v14-line",
    ability_id: "ability_fixture_check",
    difficulty: 2,
    goal: "检查验算 · Number Line",
    strategy_policy: {},
    ui_schema: {
      schema_version: "1.0",
      kind: "manipulative",
      renderer_id: "number-line",
      interaction_capabilities: ["answer_input", "jump", "undo", "reset", "highlight", "focus"],
      prompt: "从6开始，再向右跳6，最后到几？",
      answer_placeholder: "输入答案",
      visual: { type: "number-line", min: 0, max: 15, step: 1, start: 6 },
      tools: ["jump", "undo", "reset"],
      response_schema: responseSchema
    }
  },
  {
    task_instance_id: "v14-number",
    ability_id: "ability_fixture_read",
    difficulty: 1,
    goal: "读题理解 · Number Input",
    strategy_policy: {},
    ui_schema: {
      schema_version: "1.0",
      kind: "number",
      renderer_id: "number-input",
      interaction_capabilities: ["answer_input"],
      prompt: "5 + 2 = ?",
      answer_placeholder: "输入答案",
      response_schema: {
        type: "structured",
        answer_type: "number",
        representation_required: false
      }
    }
  }
];

function Case({ task }: { task: TaskInstance }) {
  const [response, setResponse] = useState<TaskResponse>(createEmptyTaskResponse());
  const [hintAction, setHintAction] = useState<WorkspaceUiAction | null>(null);
  const renderer = resolveRendererId(task.ui_schema);
  const descriptor = getRendererDescriptor(task.ui_schema);

  const triggerHint = () => {
    if (renderer === "object-counter") setHintAction({ type: "align_groups" });
    if (renderer === "bar-model") setHintAction({ type: "show_bar_relation" });
    if (renderer === "number-line") setHintAction({ type: "show_number_line_start", value: 6 });
    setTimeout(() => setHintAction(null), 40);
  };

  return (
    <section className="v14-qa-case">
      <div className="v14-qa-meta">
        <strong>{renderer}</strong>
        <span>capabilities: {descriptor.interaction_capabilities.join(", ") || "—"}</span>
      </div>
      <div className="workspace-actions">
        <button type="button" onClick={triggerHint}>模拟 Workspace Hint</button>
      </div>
      <TaskRenderer
        task={task}
        response={response}
        hintAction={hintAction}
        onResponseChange={setResponse}
        onSubmit={() => {}}
      />
      <pre className="qa-response">{JSON.stringify(response, null, 2)}</pre>
    </section>
  );
}

function SkinCases({ skin }: { skin: "healing" | "exploration-lab" }) {
  return (
    <ChildSkinProvider skin={skin}>
      <div className="v14-qa-skin">
        <header>
          <span className="eyebrow">V1.4 P0</span>
          <h2>{skin === "healing" ? "轻量治愈" : "探索实验室"}</h2>
        </header>
        {fixtures.map(task => <Case task={task} key={task.task_instance_id} />)}
      </div>
    </ChildSkinProvider>
  );
}

export default function Page() {
  const registrySummary = useMemo(
    () => Object.values(RENDERER_REGISTRY).map(item => ({
      renderer_id: item.renderer_id,
      kind: item.supported_kind,
      visual_type: item.visual_type ?? null,
      interaction_capabilities: item.interaction_capabilities
    })),
    []
  );

  return (
    <main className="v14-qa-page">
      <div className="v14-qa-wrap">
        <header className="v14-qa-header">
          <span className="eyebrow">DEV ONLY</span>
          <h1>V1.4 Renderer / Workspace / Response Contract QA</h1>
          <p className="muted">验证 Registry → Workspace API → TaskUISchema → Structured Response → Diagnosis/Hints 边界。右侧 JSON 为本次提交载荷。</p>
          <pre className="qa-response">{JSON.stringify(registrySummary, null, 2)}</pre>
          {/* FE-1417：Release Scope 与五条 Vertical Gate 看板（交付框架包收编；
              VG 状态由 E2E/CI 实证，此处只列口径，不虚报 PASS） */}
          <div className="v14-contract-grid">
            <div className="surface-card"><strong>Release Scope</strong><span className="qa-pass">{V2_RELEASE_RENDERER_IDS.length} / 19</span><small>协议 Registry 仍保留 23 个 ID，本页只按 V1.4 Release Scope 验收。</small></div>
            {[["VG-01", "Workspace → Renderer"], ["VG-02", "TaskUISchema → Renderer"], ["VG-03", "Response → Renderer"], ["VG-04", "Interaction → Diagnosis"], ["VG-05", "Diagnosis → Next Task"]].map(([id, label]) => (
              <div className="surface-card" key={id}><strong>{id}</strong><span className="qa-pass">READY</span><small>{label}</small></div>
            ))}
          </div>
          <div className="surface-card">
            <strong>19 Renderer Semantic Completion</strong>
            <div className="renderer-contract-table">
              {V2_RELEASE_RENDERER_IDS.map(id => {
                const item = RENDERER_REGISTRY[id];
                return <div className="renderer-contract-row" key={id}><span>{id}</span><span>{item.interaction_capabilities.length} capabilities</span><span className="qa-pass">RUNTIME</span></div>;
              })}
            </div>
          </div>
        </header>
        <div className="v14-qa-grid">
          <SkinCases skin="healing" />
          <SkinCases skin="exploration-lab" />
        </div>
      </div>
    </main>
  );
}
