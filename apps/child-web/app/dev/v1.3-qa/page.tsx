"use client";

import { useState } from "react";
import { ChildSkinProvider } from "@/src/theme/ChildSkinProvider";
import { TaskRenderer, createEmptyTaskResponse } from "@/src/features/task-renderer";
import type { TaskInstance, TaskResponse, WorkspaceUiAction } from "@/src/lib/api/contracts";

const responseSchema = {
  type: "structured" as const,
  answer_type: "number" as const,
  representation_required: true
};

const fixtures: TaskInstance[] = [
  {
    task_instance_id: "qa-objects",
    ability_id: "REL",
    difficulty: 2,
    goal: "Object Counter",
    strategy_policy: {},
    ui_schema: {
      schema_version: "1.0",
      kind: "manipulative",
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
    task_instance_id: "qa-bar",
    ability_id: "STRAT",
    difficulty: 2,
    goal: "Bar Model",
    strategy_policy: {},
    ui_schema: {
      schema_version: "1.0",
      kind: "manipulative",
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
    task_instance_id: "qa-line",
    ability_id: "CALC",
    difficulty: 2,
    goal: "Number Line",
    strategy_policy: {},
    ui_schema: {
      schema_version: "1.0",
      kind: "manipulative",
      prompt: "从6开始，再向右跳6，最后到几？",
      answer_placeholder: "输入答案",
      visual: { type: "number-line", min: 0, max: 15, step: 1, start: 6 },
      tools: ["jump", "undo", "reset"],
      response_schema: responseSchema
    }
  }
];

function Case({ task }: { task: TaskInstance }) {
  const [response, setResponse] = useState<TaskResponse>(createEmptyTaskResponse());
  const [hintAction, setHintAction] = useState<WorkspaceUiAction | null>(null);
  const visualType = task.ui_schema.schema_version === "1.0" && task.ui_schema.kind === "manipulative" ? task.ui_schema.visual.type : "number";

  const triggerHint = () => {
    if (visualType === "objects") setHintAction({ type: "align_groups" });
    if (visualType === "bar-model") setHintAction({ type: "show_bar_relation" });
    if (visualType === "number-line") setHintAction({ type: "show_number_line_start", value: 6 });
    setTimeout(() => setHintAction(null), 30);
  };

  return (
    <section className="v13-qa-case">
      <div className="workspace-actions">
        <button type="button" onClick={triggerHint}>模拟Workspace Hint</button>
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
      <div className="v13-qa-skin">
        <header>
          <span className="eyebrow">QA-1312</span>
          <h2>{skin === "healing" ? "轻量治愈" : "探索实验室"}</h2>
        </header>
        {fixtures.map(task => <Case task={task} key={task.task_instance_id} />)}
      </div>
    </ChildSkinProvider>
  );
}

export default function Page() {
  return (
    <main className="v13-qa-page">
      <div className="v13-qa-wrap">
        <header className="v13-qa-header">
          <span className="eyebrow">DEV ONLY</span>
          <h1>V1.3 Math Interaction QA</h1>
          <p className="muted">Object Counter / Bar Model / Number Line × 两套Built-in Skin；右侧JSON实时展示Structured Response。</p>
        </header>
        <div className="v13-qa-grid">
          <SkinCases skin="healing" />
          <SkinCases skin="exploration-lab" />
        </div>
      </div>
    </main>
  );
}
