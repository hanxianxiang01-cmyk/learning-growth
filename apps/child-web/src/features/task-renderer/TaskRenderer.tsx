"use client";

import { AnswerComposer } from "@/src/components/learning/AnswerComposer";
import { MathQuestionCard } from "@/src/components/learning/MathQuestionCard";
import { BarModel } from "@/src/components/manipulatives/BarModel";
import { NumberLine } from "@/src/components/manipulatives/NumberLine";
import { ObjectCounter } from "@/src/components/manipulatives/ObjectCounter";
import { WorkspaceProvider } from "@/src/features/math-workspace";
import { getRendererDescriptor, resolveRendererId } from "./rendererRegistry";
import type {
  InteractionEvent,
  ManipulativeTaskUiSchema,
  TaskInstance,
  TaskResponse,
  WorkspaceRepresentation,
  WorkspaceUiAction
} from "@/src/lib/api/contracts";

export function createEmptyTaskResponse(): TaskResponse {
  return { schema_version: "1.0", answer: "", interaction_events: [] };
}

export function isTaskResponseReady(
  response: TaskResponse,
  task?: TaskInstance
) {
  const hasAnswer = String(response.answer ?? "").trim().length > 0;
  if (!hasAnswer) return false;
  if (task?.ui_schema.response_schema.representation_required) {
    return Boolean(response.representation);
  }
  return true;
}

type CommonRendererProps = {
  task: TaskInstance;
  response: TaskResponse;
  disabled?: boolean;
  hintAction?: WorkspaceUiAction | null;
  onResponseChange: (response: TaskResponse) => void;
  onSubmit: () => void;
};

function NumberRenderer({ task, response, disabled, onResponseChange, onSubmit }: CommonRendererProps) {
  const schema = task.ui_schema;
  if (schema.kind !== "number") return null;

  const setAnswer = (answer: string) => {
    const event: InteractionEvent = {
      event_id: `answer-${Date.now()}-${Math.random().toString(16).slice(2)}`,
      event_type: "answer_changed",
      occurred_at: new Date().toISOString(),
      task_instance_id: task.task_instance_id,
      renderer_id: "number-input",
      capability_id: "answer_input"
    };
    onResponseChange({
      ...response,
      answer,
      interaction_events: [...(response.interaction_events ?? []), event].slice(-100)
    });
  };

  return (
    <>
      <MathQuestionCard prompt={schema.prompt} goal={task.goal} />
      <AnswerComposer
        value={response.answer}
        placeholder={schema.answer_placeholder}
        disabled={disabled || (schema.response_schema.representation_required && !response.representation)}
        onChange={setAnswer}
        onSubmit={onSubmit}
      />
    </>
  );
}

function ManipulativeRenderer(
  props: CommonRendererProps & { schema: ManipulativeTaskUiSchema }
) {
  const { task, schema, response, disabled, hintAction, onResponseChange, onSubmit } = props;

  const visual = schema.visual;
  const workspace =
    visual.type === "objects" ? (
      <ObjectCounter
        symbolByGroup={Object.fromEntries(
          visual.groups.map(group => [group.id, group.symbol ?? "●"])
        )}
      />
    ) : visual.type === "bar-model" ? (
      <BarModel schema={visual} />
    ) : (
      <NumberLine />
    );

  const rendererId = resolveRendererId(schema);

  return (
    <>
      <MathQuestionCard prompt={schema.prompt} goal={task.goal} />
      <WorkspaceProvider
        schema={{ ...schema, renderer_id: rendererId }}
        taskInstanceId={task.task_instance_id}
        hintAction={hintAction}
        onWorkspaceChange={(representation, events) => {
          onResponseChange({ ...response, representation, interaction_events: events });
        }}
      >
        {workspace}
      </WorkspaceProvider>
      <AnswerComposer
        value={response.answer}
        placeholder={schema.answer_placeholder}
        disabled={disabled || (schema.response_schema.representation_required && !response.representation)}
        onChange={answer => onResponseChange({ ...response, answer })}
        onSubmit={onSubmit}
      />
    </>
  );
}

export function TaskRenderer(props: CommonRendererProps) {
  const { task } = props;
  const rendererId = resolveRendererId(task.ui_schema);
  const descriptor = getRendererDescriptor(task.ui_schema);

  if (rendererId === "number-input") return <NumberRenderer {...props} />;

  if (rendererId === "object-counter" && task.ui_schema.kind === "manipulative") {
    return <ManipulativeRenderer {...props} schema={task.ui_schema} />;
  }

  if (rendererId === "bar-model" && task.ui_schema.kind === "manipulative") {
    return <ManipulativeRenderer {...props} schema={task.ui_schema} />;
  }

  if (rendererId === "number-line" && task.ui_schema.kind === "manipulative") {
    return <ManipulativeRenderer {...props} schema={task.ui_schema} />;
  }

  return (
    <div className="surface-card unsupported-task">
      <strong>这道题暂时需要新的学习工具</strong>
      <p className="muted">题目已经保留，不会丢失。请稍后再试。</p>
      <small className="renderer-debug">Renderer: {descriptor.renderer_id}</small>
    </div>
  );
}
