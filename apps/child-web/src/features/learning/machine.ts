import type {
  AttemptResult,
  HintResponse,
  NextActionCode,
  TaskInstance
} from "@/src/lib/api/contracts";

export type LearningStatus =
  | "idle"
  | "loading_task"
  | "answering"
  | "submitting"
  | "hint_available"
  | "hint_loading"
  | "hint_active"
  | "retry"
  | "correct"
  | "completed"
  | "error";

export type LearningState = {
  status: LearningStatus;
  task: TaskInstance | null;
  answer: string;
  attemptNo: number;
  lastAttempt: AttemptResult | null;
  hint: HintResponse | null;
  usedHintLevels: number[];
  error: string | null;
};

export type LearningAction =
  | { type: "LOAD_TASK" }
  | { type: "TASK_LOADED"; task: TaskInstance }
  | { type: "SET_ANSWER"; answer: string }
  | { type: "SUBMIT" }
  | { type: "ATTEMPT_RESULT"; result: AttemptResult }
  | { type: "HINT_LOADING" }
  | { type: "HINT_LOADED"; hint: HintResponse }
  | { type: "RETRY" }
  | { type: "ERROR"; message: string };

export const initialLearningState: LearningState = {
  status: "idle",
  task: null,
  answer: "",
  attemptNo: 1,
  lastAttempt: null,
  hint: null,
  usedHintLevels: [],
  error: null
};

export function getNextActionCode(result: AttemptResult): NextActionCode {
  return result.next_action.type;
}

export function learningReducer(
  state: LearningState,
  action: LearningAction
): LearningState {
  switch (action.type) {
    case "LOAD_TASK":
      return {
        ...state,
        status: "loading_task",
        task: null,
        answer: "",
        attemptNo: 1,
        lastAttempt: null,
        hint: null,
        usedHintLevels: [],
        error: null
      };

    case "TASK_LOADED":
      return {
        ...state,
        status: "answering",
        task: action.task,
        answer: "",
        attemptNo: 1,
        lastAttempt: null,
        hint: null,
        usedHintLevels: [],
        error: null
      };

    case "SET_ANSWER":
      return { ...state, answer: action.answer };

    case "SUBMIT":
      return { ...state, status: "submitting", error: null };

    case "ATTEMPT_RESULT": {
      const code = getNextActionCode(action.result);

      if (action.result.correct) {
        return {
          ...state,
          lastAttempt: action.result,
          status: code === "COMPLETE" ? "completed" : "correct"
        };
      }

      if (code === "HINT" || code === "TEACH") {
        return {
          ...state,
          lastAttempt: action.result,
          status: "hint_available"
        };
      }

      return {
        ...state,
        lastAttempt: action.result,
        status: "retry"
      };
    }

    case "HINT_LOADING":
      return { ...state, status: "hint_loading" };

    case "HINT_LOADED":
      return {
        ...state,
        status: "hint_active",
        hint: action.hint,
        usedHintLevels: Array.from(
          new Set([...state.usedHintLevels, action.hint.hint_level])
        )
      };

    case "RETRY":
      return {
        ...state,
        status: "answering",
        answer: "",
        attemptNo: state.attemptNo + 1
      };

    case "ERROR":
      return { ...state, status: "error", error: action.message };

    default:
      return state;
  }
}
