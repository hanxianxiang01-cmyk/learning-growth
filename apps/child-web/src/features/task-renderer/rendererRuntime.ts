import type { InteractionEvent } from "@/src/lib/api/contracts";
import {
  getRendererDescriptorById,
  isImplementedRenderer,
  type InteractionCapability,
  type RendererId
} from "./rendererRegistry";

export type RendererAction<TState> =
  | { type: "SET_STATE"; state: TState; event?: InteractionEvent }
  | { type: "RESET"; event?: InteractionEvent }
  | { type: "UNDO"; event?: InteractionEvent }
  | { type: "EMIT"; event: InteractionEvent };

export type RendererWorkspaceState<TState> = {
  initial: TState;
  present: TState;
  history: TState[];
  events: InteractionEvent[];
};

export type RendererWorkspaceContract<TState, TResponse> = {
  renderer_id: RendererId;
  initial_state: TState;
  capabilities: InteractionCapability[];
  serialize: (state: TState) => TResponse;
};

const MAX_HISTORY = 20;

export function canRenderer(
  rendererId: RendererId,
  capability: InteractionCapability
): boolean {
  return getRendererDescriptorById(rendererId).interaction_capabilities.includes(capability);
}

export function isRenderableRenderer(rendererId: RendererId): boolean {
  return isImplementedRenderer(rendererId);
}

export function createRendererWorkspaceState<TState>(
  initialState: TState
): RendererWorkspaceState<TState> {
  return {
    initial: structuredClone(initialState),
    present: structuredClone(initialState),
    history: [],
    events: []
  };
}

export function rendererWorkspaceReducer<TState>(
  state: RendererWorkspaceState<TState>,
  action: RendererAction<TState>
): RendererWorkspaceState<TState> {
  switch (action.type) {
    case "SET_STATE":
      return {
        ...state,
        present: action.state,
        history: [...state.history, state.present].slice(-MAX_HISTORY),
        events: action.event ? [...state.events, action.event].slice(-100) : state.events
      };
    case "UNDO": {
      const previous = state.history[state.history.length - 1];
      if (previous === undefined) return state;
      return {
        ...state,
        present: previous,
        history: state.history.slice(0, -1),
        events: action.event ? [...state.events, action.event].slice(-100) : state.events
      };
    }
    case "RESET":
      return {
        ...state,
        present: structuredClone(state.initial),
        history: [],
        events: action.event ? [...state.events, action.event].slice(-100) : state.events
      };
    case "EMIT":
      return {
        ...state,
        events: [...state.events, action.event].slice(-100)
      };
    default:
      return state;
  }
}

export function buildRendererEvent(
  event_type: string,
  detail: {
    task_instance_id?: string;
    workspace_id?: string;
    renderer_id?: RendererId;
    capability_id?: string;
    payload?: Record<string, unknown>;
  } = {}
): InteractionEvent {
  const payload = Object.fromEntries(
    Object.entries(detail.payload ?? {}).filter(([, value]) =>
      ["string", "number", "boolean"].includes(typeof value) || value === null
    )
  ) as Record<string, string | number | boolean | null>;

  return {
    event_id:
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `evt-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    event_type: event_type as InteractionEvent["event_type"],
    occurred_at: new Date().toISOString(),
    task_instance_id: detail.task_instance_id,
    renderer_id: detail.renderer_id,
    capability_id: detail.capability_id,
    target_id: detail.workspace_id,
    payload
  };
}

export function serializeRendererWorkspace<TState, TResponse>(
  contract: RendererWorkspaceContract<TState, TResponse>,
  state: RendererWorkspaceState<TState>
): TResponse {
  return contract.serialize(state.present);
}
