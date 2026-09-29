import type {
  AttemptResult,
  HintResponse,
  NextActionCode,
  TaskInstance,
  TaskResponse
} from "@/src/lib/api/contracts";
import { createEmptyTaskResponse } from "@/src/features/task-renderer";

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
  response: TaskResponse;
  attemptNo: number;
  lastAttempt: AttemptResult | null;
  hint: HintResponse | null;
  usedHintLevels: number[];
  error: string | null;
};

export type LearningAction =
  | { type: "LOAD_TASK" }
  | { type: "TASK_LOADED"; task: TaskInstance }
  | { type: "SET_RESPONSE"; response: TaskResponse }
  | { type: "SUBMIT" }
  | { type: "ATTEMPT_RESULT"; result: AttemptResult }
  | { type: "HINT_LOADING" }
  | { type: "HINT_LOADED"; hint: HintResponse }
  | { type: "RETRY" }
  | { type: "ERROR"; message: string };

export const initialLearningState: LearningState = {
  status: "idle",
  task: null,
  response: createEmptyTaskResponse(),
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
        response: createEmptyTaskResponse(),
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
        response: createEmptyTaskResponse(),
        attemptNo: 1,
        lastAttempt: null,
        hint: null,
        usedHintLevels: [],
        error: null
      };

    case "SET_RESPONSE":
      return { ...state, response: action.response };

    case "SUBMIT":
      return { ...state, status: "submitting", error: null };

    case "ATTEMPT_RESULT": {
      const code = getNextActionCode(action.result);

      // 每次「提交」都消耗一个 attempt_no，提交完成后递增，
      // 保证孩子改答案后直接再提交时得到新的 attempt_no，
      // 否则后端幂等会一直返回第一次的结果。
      if (action.result.correct) {
        return {
          ...state,
          lastAttempt: action.result,
          status: code === "COMPLETE" ? "completed" : "correct",
          attemptNo: state.attemptNo + 1
        };
      }

      if (code === "HINT" || code === "TEACH") {
        return {
          ...state,
          lastAttempt: action.result,
          status: "hint_available",
          attemptNo: state.attemptNo + 1
        };
      }

      return {
        ...state,
        lastAttempt: action.result,
        status: "retry",
        attemptNo: state.attemptNo + 1
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
        response: { ...state.response, answer: "" }
      };

    case "ERROR":
      return { ...state, status: "error", error: action.message };

    default:
      return state;
  }
}
