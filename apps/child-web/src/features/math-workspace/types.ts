import type {
  InteractionEvent,
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
  | {
      type: "COMMIT";
      representation: WorkspaceRepresentation;
      event?: InteractionEvent;
    }
  | { type: "UNDO"; event?: InteractionEvent }
  | { type: "RESET"; event?: InteractionEvent }
  | { type: "APPLY_HINT"; action: WorkspaceUiAction; event?: InteractionEvent }
  | { type: "REINITIALIZE"; schema: ManipulativeTaskUiSchema };
