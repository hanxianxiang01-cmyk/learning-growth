"use client";

import { useMemo } from "react";
import { AnswerComposer } from "@/src/components/learning/AnswerComposer";
import { ColumnArithmetic } from "@/src/components/renderers/ColumnArithmetic";
import { NumberLineV2 } from "@/src/components/renderers/NumberLineV2";
import { NumberInputV2 } from "@/src/components/renderers/NumberInputV2";
import { ObjectCounterV2 } from "@/src/components/renderers/ObjectCounterV2";
import { BarModelV2 } from "@/src/components/renderers/BarModelV2";
import { PlaceValueV2 } from "@/src/components/renderers/PlaceValueV2";
import { FormulaBoardV2 } from "@/src/components/renderers/FormulaBoardV2";
import { TenFrameV2 } from "@/src/components/renderers/TenFrameV2";
import {
  ChoiceGrid, ArrayBoard, GroupingBoard, EstimationCanvas,
  ShapeGallery, ShapeCanvas, SortingBoard, DirectionGrid, Ruler, Clock, Timeline, MoneyBoard,
  DataTable, Pictograph, PatternBoard
} from "@/src/components/renderers/V2RendererLibrary";

import { MathQuestionCard } from "@/src/components/learning/MathQuestionCard";
import { BarModel } from "@/src/components/manipulatives/BarModel";
import { NumberLine } from "@/src/components/manipulatives/NumberLine";
import { ObjectCounter } from "@/src/components/manipulatives/ObjectCounter";
import { WorkspaceProvider } from "@/src/features/math-workspace";
import { getRendererDescriptor, isImplementedRenderer, resolveRendererId } from "./rendererRegistry";
import { assertTaskUiSchemaV2 } from "./rendererContract";
import type {
  InteractionEvent,
  ManipulativeTaskUiSchema,
  TaskInstance,
  TaskResponse,
  WorkspaceRepresentation,
  WorkspaceUiAction,
  V2TaskUiSchema
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

  if (task?.ui_schema.schema_version === "2.0") {
    return Array.isArray(response.v2_workspaces) && response.v2_workspaces.length > 0;
  }

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
  if (schema.schema_version !== "1.0" || schema.kind !== "number") return null;

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
  const rendererId = resolveRendererId(schema);

  // FE-1411：identity 稳定化。WorkspaceProvider 以 [schema] 为 REINITIALIZE 依赖，
  // 而此前这里的 spread 每次渲染都产生新对象 → 每帧重置工作区并回调 → 无限循环
  // （Maximum update depth exceeded，dev 下 F12 刷屏）。
  const providerSchema = useMemo(
    () => ({ ...schema, renderer_id: rendererId }),
    [schema, rendererId]
  );

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
        schema={providerSchema}
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


function V2Renderer(props: CommonRendererProps & { schema: V2TaskUiSchema }) {
  const { task, schema, response, disabled, onResponseChange, onSubmit } = props;
  // FE-1417（交付框架包收编）：V2 契约入口校验——workspace 缺 renderer_version/
  // capabilities 等字段属于内容事故，显式失败优于静默渲染错误。
  assertTaskUiSchemaV2(schema);
  const rendererId = resolveRendererId(schema);
  const workspace = schema.workspaces[0];
  if (!workspace) return null;

  if (rendererId === "number-line") {
    return (
      <>
        <MathQuestionCard prompt={schema.prompt.text} goal={task.goal} />
        <NumberLineV2
          taskInstanceId={task.task_instance_id}
          schema={schema}
          response={response}
          disabled={disabled}
          onResponseChange={onResponseChange}
          onSubmit={onSubmit}
        />
      </>
    );
  }

  const commonV2Props = {
    taskInstanceId: task.task_instance_id,
    schema,
    workspace,
    response,
    disabled,
    onResponseChange,
    onSubmit
  };

  if (rendererId === "column-arithmetic") {
    return (
      <>
        <MathQuestionCard prompt={schema.prompt.text} goal={task.goal} />
        <ColumnArithmetic
          taskInstanceId={task.task_instance_id}
          schema={schema}
          response={response}
          disabled={disabled}
          onResponseChange={onResponseChange}
          onSubmit={onSubmit}
        />
      </>
    );
  }

  if (rendererId === "number-input") {
    return (
      <>
        <MathQuestionCard prompt={schema.prompt.text} goal={task.goal} />
        <NumberInputV2
          taskInstanceId={task.task_instance_id}
          schema={schema}
          response={response}
          disabled={disabled}
          onResponseChange={onResponseChange}
          onSubmit={onSubmit}
        />
      </>
    );
  }

  if (rendererId === "object-counter") {
    return (
      <>
        <MathQuestionCard prompt={schema.prompt.text} goal={task.goal} />
        <ObjectCounterV2
          taskInstanceId={task.task_instance_id}
          schema={schema}
          response={response}
          disabled={disabled}
          onResponseChange={onResponseChange}
          onSubmit={onSubmit}
        />
      </>
    );
  }

  if (rendererId === "ten-frame") {
    return (
      <>
        <MathQuestionCard prompt={schema.prompt.text} goal={task.goal} />
        <TenFrameV2
          taskInstanceId={task.task_instance_id}
          schema={schema}
          response={response}
          disabled={disabled}
          onResponseChange={onResponseChange}
          onSubmit={onSubmit}
        />
      </>
    );
  }

  if (rendererId === "bar-model") {
    return (
      <>
        <MathQuestionCard prompt={schema.prompt.text} goal={task.goal} />
        <BarModelV2
          taskInstanceId={task.task_instance_id}
          schema={schema}
          response={response}
          disabled={disabled}
          onResponseChange={onResponseChange}
          onSubmit={onSubmit}
        />
      </>
    );
  }

  if (rendererId === "place-value") {
    return (
      <>
        <MathQuestionCard prompt={schema.prompt.text} goal={task.goal} />
        <PlaceValueV2
          taskInstanceId={task.task_instance_id}
          schema={schema}
          response={response}
          disabled={disabled}
          onResponseChange={onResponseChange}
          onSubmit={onSubmit}
        />
      </>
    );
  }

  if (rendererId === "formula-board") {
    return (
      <>
        <MathQuestionCard prompt={schema.prompt.text} goal={task.goal} />
        <FormulaBoardV2
          taskInstanceId={task.task_instance_id}
          schema={schema}
          response={response}
          disabled={disabled}
          onResponseChange={onResponseChange}
          onSubmit={onSubmit}
        />
      </>
    );
  }

  if (rendererId === "choice-grid") return <ChoiceGrid {...commonV2Props} />;
  if (rendererId === "array-board") return <ArrayBoard {...commonV2Props} />;
  if (rendererId === "grouping-board") return <GroupingBoard {...commonV2Props} />;
  if (rendererId === "estimation-canvas") return <EstimationCanvas {...commonV2Props} />;
  if (rendererId === "shape-gallery") return <ShapeGallery {...commonV2Props} />;
  if (rendererId === "shape-canvas") return <ShapeCanvas {...commonV2Props} />;
  if (rendererId === "sorting-board") return <SortingBoard {...commonV2Props} />;
  if (rendererId === "direction-grid") return <DirectionGrid {...commonV2Props} />;
  if (rendererId === "ruler") return <Ruler {...commonV2Props} />;
  if (rendererId === "clock") return <Clock {...commonV2Props} />;
  if (rendererId === "timeline") return <Timeline {...commonV2Props} />;
  if (rendererId === "money-board") return <MoneyBoard {...commonV2Props} />;
  if (rendererId === "data-table") return <DataTable {...commonV2Props} />;
  if (rendererId === "pictograph") return <Pictograph {...commonV2Props} />;
  if (rendererId === "pattern-board") return <PatternBoard {...commonV2Props} />;

  return (
    <div className="surface-card unsupported-task" data-testid="planned-renderer">
      <strong>这个学习工具还在开发中</strong>
      <p className="muted">当前 Renderer 已注册，但尚未开放下发。</p>
      <small className="renderer-debug">Renderer: {rendererId}</small>
    </div>
  );
}

export function TaskRenderer(props: CommonRendererProps) {
  const { task } = props;
  const rendererId = resolveRendererId(task.ui_schema);
  const descriptor = getRendererDescriptor(task.ui_schema);

  if (task.ui_schema.schema_version === "2.0") {
    if (!isImplementedRenderer(rendererId)) {
      return (
        <div className="surface-card unsupported-task" data-testid="planned-renderer">
          <strong>这个学习工具还在开发中</strong>
          <p className="muted">当前 Renderer 已注册，但尚未开放下发。</p>
          <small className="renderer-debug">Renderer: {rendererId}</small>
        </div>
      );
    }
    return <V2Renderer {...props} schema={task.ui_schema} />;
  }

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
