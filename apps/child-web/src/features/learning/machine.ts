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

      // FE-1466 Q07（裁决 21:26 §三）：后端 task_expired → 不得对同一失效
      // 任务反复提交——清 task 引用并回 idle，由既有 loadTask 入口重新取
      // 有效任务；不消耗 Hint 阶梯、不产生"答错"态。
      if (action.result.expired === true ||
          (code === "RETRY" && action.result.next_action.policy_id === "task_expired")) {
        return {
          ...state,
          status: "idle",
          task: null,
          response: createEmptyTaskResponse(),
          attemptNo: 1,
          lastAttempt: action.result,
          hint: null,
          usedHintLevels: state.usedHintLevels,
          error: null
        };
      }

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
