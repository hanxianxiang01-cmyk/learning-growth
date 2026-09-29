"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useReducer,
  useRef
} from "react";
import type {
  ManipulativeTaskUiSchema,
  WorkspaceRepresentation,
  WorkspaceUiAction
} from "@/src/lib/api/contracts";
import { createWorkspaceState, workspaceReducer } from "./workspaceReducer";
import type { WorkspaceState } from "./types";

type WorkspaceContextValue = {
  state: WorkspaceState;
  commit: (representation: WorkspaceRepresentation) => void;
  undo: () => void;
  reset: () => void;
};

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({
  schema,
  hintAction,
  onRepresentationChange,
  children
}: {
  schema: ManipulativeTaskUiSchema;
  hintAction?: WorkspaceUiAction | null;
  onRepresentationChange?: (representation: WorkspaceRepresentation) => void;
  children: React.ReactNode;
}) {
  const [state, dispatch] = useReducer(
    workspaceReducer,
    schema,
    createWorkspaceState
  );
  const callbackRef = useRef(onRepresentationChange);
  callbackRef.current = onRepresentationChange;

  useEffect(() => {
    dispatch({ type: "REINITIALIZE", schema });
  }, [schema]);

  useEffect(() => {
    callbackRef.current?.(state.present);
  }, [state.present]);

  useEffect(() => {
    if (hintAction) {
      dispatch({ type: "APPLY_HINT", action: hintAction });
    }
  }, [hintAction]);

  const commit = useCallback((representation: WorkspaceRepresentation) => {
    dispatch({ type: "COMMIT", representation });
  }, []);
  const undo = useCallback(() => dispatch({ type: "UNDO" }), []);
  const reset = useCallback(() => dispatch({ type: "RESET" }), []);

  return (
    <WorkspaceContext.Provider value={{ state, commit, undo, reset }}>
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
