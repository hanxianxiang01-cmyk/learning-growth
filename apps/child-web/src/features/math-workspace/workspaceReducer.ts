import type { WorkspaceRepresentation } from "@/src/lib/api/contracts";
import { alignObjectCounter, createInitialRepresentation } from "./model";
import type { WorkspaceAction, WorkspaceState } from "./types";

const MAX_HISTORY = 20;

function pushHistory(
  history: WorkspaceRepresentation[],
  value: WorkspaceRepresentation
) {
  return [...history, value].slice(-MAX_HISTORY);
}

export function createWorkspaceState(schema: Parameters<typeof createInitialRepresentation>[0]): WorkspaceState {
  const representation = createInitialRepresentation(schema);
  return {
    initial: representation,
    present: representation,
    history: [],
    highlightedTargets: []
  };
}

export function workspaceReducer(
  state: WorkspaceState,
  action: WorkspaceAction
): WorkspaceState {
  switch (action.type) {
    case "COMMIT":
      return {
        ...state,
        present: action.representation,
        history: pushHistory(state.history, state.present)
      };

    case "UNDO": {
      const previous = state.history[state.history.length - 1];
      if (!previous) return state;
      return {
        ...state,
        present: previous,
        history: state.history.slice(0, -1)
      };
    }

    case "RESET":
      return {
        ...state,
        present: state.initial,
        history: [],
        highlightedTargets: [],
        focusedTarget: undefined,
        lastHintAction: undefined
      };

    case "REINITIALIZE":
      return createWorkspaceState(action.schema);

    case "APPLY_HINT": {
      const hint = action.action;
      let present = state.present;
      let highlightedTargets = state.highlightedTargets;
      let focusedTarget = state.focusedTarget;

      if (hint.type === "highlight") {
        highlightedTargets = hint.targets;
      } else if (hint.type === "focus") {
        focusedTarget = hint.target;
        highlightedTargets = [hint.target];
      } else if (
        hint.type === "align_groups" &&
        present.type === "object-counter"
      ) {
        present = alignObjectCounter(present);
      } else if (hint.type === "show_bar_relation") {
        highlightedTargets =
          hint.targets ??
          (present.type === "bar-model"
            ? present.bars.map(bar => bar.id)
            : []);
      } else if (
        hint.type === "show_number_line_start" &&
        present.type === "number-line"
      ) {
        const value = hint.value ?? present.start ?? present.min;
        present = {
          ...present,
          start: value,
          current: present.current ?? value
        };
        highlightedTargets = ["number-line-start"];
      }

      return {
        ...state,
        present,
        highlightedTargets,
        focusedTarget,
        lastHintAction: hint
      };
    }

    default:
      return state;
  }
}
