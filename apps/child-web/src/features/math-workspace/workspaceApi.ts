import type {
  InteractionEvent,
  InteractionEventType,
  WorkspaceRepresentation,
  WorkspaceUiAction
} from "@/src/lib/api/contracts";
import type { WorkspaceState } from "./types";
import type { InteractionCapability } from "@/src/features/task-renderer/rendererRegistry";

export type WorkspaceCommitDetail = Omit<InteractionEvent, "event_id" | "occurred_at">;

export type WorkspaceApi = {
  state: WorkspaceState;
  capabilities: InteractionCapability[];
  can: (capability: InteractionCapability) => boolean;
  commit: (representation: WorkspaceRepresentation, event?: WorkspaceCommitDetail) => void;
  undo: () => void;
  reset: () => void;
  applyHint: (action: WorkspaceUiAction) => void;
  emitInteraction: (
    event_type: InteractionEventType,
    detail?: Omit<InteractionEvent, "event_id" | "occurred_at" | "event_type">
  ) => void;
};

export function buildWorkspaceEvent(
  event_type: InteractionEventType,
  detail?: Omit<InteractionEvent, "event_id" | "occurred_at" | "event_type">
): InteractionEvent {
  return {
    event_id:
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `evt-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    occurred_at: new Date().toISOString(),
    event_type,
    ...detail
  };
}
