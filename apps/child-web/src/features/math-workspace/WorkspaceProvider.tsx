"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useReducer,
  useRef,
  useState
} from "react";
import type {
  InteractionEvent,
  InteractionEventType,
  ManipulativeTaskUiSchema,
  WorkspaceRepresentation,
  WorkspaceUiAction
} from "@/src/lib/api/contracts";
import { createWorkspaceState, workspaceReducer } from "./workspaceReducer";
import type { WorkspaceState } from "./types";
import type { WorkspaceApi, WorkspaceCommitDetail } from "./workspaceApi";
import { buildWorkspaceEvent } from "./workspaceApi";
import { getInteractionCapabilities } from "@/src/features/task-renderer/rendererRegistry";

const WorkspaceContext = createContext<WorkspaceApi | null>(null);

export function WorkspaceProvider({
  schema,
  taskInstanceId,
  hintAction,
  onWorkspaceChange,
  children
}: {
  schema: ManipulativeTaskUiSchema;
  taskInstanceId?: string;
  hintAction?: WorkspaceUiAction | null;
  onWorkspaceChange?: (representation: WorkspaceRepresentation, events: InteractionEvent[]) => void;
  children: React.ReactNode;
}) {
  const [state, dispatch] = useReducer(
    workspaceReducer,
    schema,
    createWorkspaceState
  );
  const [interactionEvents, setInteractionEvents] = useState<InteractionEvent[]>([]);
  const capabilities = getInteractionCapabilities(schema);
  const can = useCallback((capability: Parameters<WorkspaceApi["can"]>[0]) => capabilities.includes(capability), [capabilities]);
  const callbackRef = useRef(onWorkspaceChange);
  callbackRef.current = onWorkspaceChange;

  useEffect(() => {
    dispatch({ type: "REINITIALIZE", schema });
    setInteractionEvents([]);
  }, [schema]);

  useEffect(() => {
    callbackRef.current?.(state.present, interactionEvents);
  }, [state.present, interactionEvents]);

  const appendEvent = useCallback((event: InteractionEvent) => {
    setInteractionEvents(current => [...current, event].slice(-100));
  }, []);

  const commit = useCallback(
    (
      representation: WorkspaceRepresentation,
      detail?: WorkspaceCommitDetail
    ) => {
      const eventType = detail?.event_type ?? "representation_changed";
      const { event_type: _ignored, ...eventDetail } = detail ?? {};
      const event = buildWorkspaceEvent(eventType, {
        task_instance_id: taskInstanceId,
        renderer_id: schema.renderer_id,
        ...eventDetail
      });
      dispatch({ type: "COMMIT", representation, event });
      appendEvent(event);
    },
    [appendEvent, schema.renderer_id, taskInstanceId]
  );

  const undo = useCallback(() => {
    const event = buildWorkspaceEvent("undo", {
      task_instance_id: taskInstanceId,
      renderer_id: schema.renderer_id,
      capability_id: "undo"
    });
    dispatch({ type: "UNDO", event });
    appendEvent(event);
  }, [appendEvent, can, schema.renderer_id, taskInstanceId]);

  const reset = useCallback(() => {
    const event = buildWorkspaceEvent("reset", {
      task_instance_id: taskInstanceId,
      renderer_id: schema.renderer_id,
      capability_id: "reset"
    });
    dispatch({ type: "RESET", event });
    appendEvent(event);
  }, [appendEvent, can, schema.renderer_id, taskInstanceId]);

  const applyHint = useCallback(
    (action: WorkspaceUiAction) => {
      const requiredCapability =
        action.type === "align_groups"
          ? "align"
          : action.type === "show_bar_relation" || action.type === "show_number_line_start" || action.type === "highlight"
            ? "highlight"
            : action.type === "focus"
              ? "focus"
              : null;
      if (requiredCapability && !can(requiredCapability)) return;

      const event = buildWorkspaceEvent("hint_applied", {
        task_instance_id: taskInstanceId,
        renderer_id: schema.renderer_id,
        capability_id: action.type
      });
      dispatch({ type: "APPLY_HINT", action, event });
      appendEvent(event);
    },
    [appendEvent, can, schema.renderer_id, taskInstanceId]
  );

  useEffect(() => {
    if (hintAction) applyHint(hintAction);
  }, [applyHint, hintAction]);

  const emitInteraction = useCallback(
    (
      event_type: InteractionEventType,
      detail?: Omit<InteractionEvent, "event_id" | "occurred_at" | "event_type">
    ) => {
      appendEvent(
        buildWorkspaceEvent(event_type, {
          task_instance_id: taskInstanceId,
          renderer_id: schema.renderer_id,
          ...detail
        })
      );
    },
    [appendEvent, schema.renderer_id, taskInstanceId]
  );

  return (
    <WorkspaceContext.Provider
      value={{
        state,
        capabilities,
        can,
        commit,
        undo,
        reset,
        applyHint,
        emitInteraction
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) {
    throw new Error("useWorkspace must be used inside WorkspaceProvider");
  }
  return value;
}
