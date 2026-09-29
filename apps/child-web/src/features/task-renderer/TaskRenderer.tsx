"use client";

import { useCallback } from "react";
import { AnswerComposer } from "@/src/components/learning/AnswerComposer";
import { MathQuestionCard } from "@/src/components/learning/MathQuestionCard";
import { BarModel } from "@/src/components/manipulatives/BarModel";
import { NumberLine } from "@/src/components/manipulatives/NumberLine";
import { ObjectCounter } from "@/src/components/manipulatives/ObjectCounter";
import { WorkspaceProvider } from "@/src/features/math-workspace";
import type {
  ManipulativeTaskUiSchema,
  TaskInstance,
  TaskResponse,
  WorkspaceRepresentation,
  WorkspaceUiAction
} from "@/src/lib/api/contracts";

export function createEmptyTaskResponse(): TaskResponse {
  return { schema_version: "1.0", answer: "" };
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

function NumberRenderer({
  task,
  response,
  disabled,
  onResponseChange,
  onSubmit
}: CommonRendererProps) {
  const schema = task.ui_schema;
  if (schema.kind !== "number") return null;

  return (
    <>
      <MathQuestionCard prompt={schema.prompt} goal={task.goal} />
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

type CommonRendererProps = {
  task: TaskInstance;
  response: TaskResponse;
  disabled?: boolean;
  hintAction?: WorkspaceUiAction | null;
  onResponseChange: (response: TaskResponse) => void;
  onSubmit: () => void;
};

function ManipulativeRenderer(props: CommonRendererProps & { schema: ManipulativeTaskUiSchema }) {
  const { task, schema, response, disabled, hintAction, onResponseChange, onSubmit } = props;

  const handleRepresentation = useCallback(
    (representation: WorkspaceRepresentation) => {
      onResponseChange({
        ...response,
        representation
      });
    },
    [onResponseChange, response.answer]
  );

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

  return (
    <>
      <MathQuestionCard prompt={schema.prompt} goal={task.goal} />
      <WorkspaceProvider
        schema={schema}
        hintAction={hintAction}
        onRepresentationChange={handleRepresentation}
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
  const schema = task.ui_schema;

  if (schema.kind === "number") {
    return <NumberRenderer {...props} />;
  }

  if (schema.kind === "manipulative") {
    return (
      <ManipulativeRenderer
        {...props}
        key={task.task_instance_id}
        schema={schema}
      />
    );
  }

  return (
    <div className="surface-card unsupported-task">
      <strong>这道题暂时需要新的学习工具</strong>
      <p className="muted">题目已经保留，不会丢失。请稍后再试。</p>
    </div>
  );
}
