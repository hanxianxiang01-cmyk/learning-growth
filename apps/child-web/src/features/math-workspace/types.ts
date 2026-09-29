import type {
  ManipulativeTaskUiSchema,
  WorkspaceRepresentation,
  WorkspaceUiAction
} from "@/src/lib/api/contracts";

export type WorkspaceState = {
  initial: WorkspaceRepresentation;
  present: WorkspaceRepresentation;
  history: WorkspaceRepresentation[];
  highlightedTargets: string[];
  focusedTarget?: string;
  lastHintAction?: WorkspaceUiAction;
};

export type WorkspaceAction =
  | { type: "COMMIT"; representation: WorkspaceRepresentation }
  | { type: "UNDO" }
  | { type: "RESET" }
  | { type: "APPLY_HINT"; action: WorkspaceUiAction }
  | { type: "REINITIALIZE"; schema: ManipulativeTaskUiSchema };
