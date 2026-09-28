"use client";

import { useCallback, useEffect, useReducer, useRef } from "react";
import { getLearningApi } from "@/src/lib/api";
import { LearningApiError } from "@/src/lib/api/http";
import {
  initialLearningState,
  learningReducer,
  getNextActionCode
} from "./machine";
import {
  loadSessionSnapshot,
  saveSessionSnapshot,
  type SessionSnapshot
} from "@/src/lib/runtime/sessionStore";

function humanizeError(err: unknown) {
  if (err instanceof LearningApiError) {
    if (err.code === "LE-4291") return "操作有点快，请稍后再试。";
    if (err.code === "AG-5031") return "小助手暂时没有响应，可以稍后再试。";
    return "这一步暂时没有完成，请再试一次。";
  }
  return err instanceof Error ? err.message : "发生未知错误";
}

export function useLearningSession({
  childId,
  sessionId
}: {
  childId: string;
  sessionId: string;
}) {
  const api = getLearningApi();
  const [state, dispatch] = useReducer(
    learningReducer,
    initialLearningState
  );
  const startedAt = useRef(Date.now());
  const stats = useRef<SessionSnapshot>(
    loadSessionSnapshot(sessionId) ?? {
      childId,
      sessionId,
      startedAt: Date.now(),
      tasksCompleted: 0,
      correctTasks: 0,
      totalAttempts: 0,
      hintsUsed: [],
      diagnosisCodes: []
    }
  );

  const persist = useCallback(() => {
    saveSessionSnapshot(stats.current);
  }, []);

  const loadTask = useCallback(async () => {
    dispatch({ type: "LOAD_TASK" });
    try {
      const task = await api.getNextTask({
        child_id: childId,
        session_id: sessionId,
        subject: "math",
        requested_minutes: 15
      });
      stats.current.lastAbilityId = task.ability_id;
      persist();
      dispatch({ type: "TASK_LOADED", task });
    } catch (err) {
      dispatch({ type: "ERROR", message: humanizeError(err) });
    }
  }, [api, childId, sessionId, persist]);

  useEffect(() => {
    if (state.status === "idle") void loadTask();
  }, [state.status, loadTask]);

  const setAnswer = useCallback((answer: string) => {
    dispatch({ type: "SET_ANSWER", answer });
  }, []);

  const submit = useCallback(async () => {
    if (!state.task || !state.answer.trim()) return;
    dispatch({ type: "SUBMIT" });

    try {
      const result = await api.submitAttempt({
        task_instance_id: state.task.task_instance_id,
        attempt_no: state.attemptNo,
        response: state.answer,
        client_elapsed_ms: Date.now() - startedAt.current,
        used_hint_levels: state.usedHintLevels
      });

      stats.current.totalAttempts += 1;

      const diagnosis = result.diagnosis;
      if (diagnosis?.code?.startsWith("E")) {
        stats.current.diagnosisCodes.push(diagnosis.code);
      }

      if (result.correct) {
        stats.current.tasksCompleted += 1;
        stats.current.correctTasks += 1;
      }

      const action = getNextActionCode(result);
      if (action === "COMPLETE") {
        stats.current.completedAt = Date.now();
      }

      persist();
      dispatch({ type: "ATTEMPT_RESULT", result });
    } catch (err) {
      dispatch({ type: "ERROR", message: humanizeError(err) });
    }
  }, [api, persist, state]);

  const requestHint = useCallback(async () => {
    if (!state.lastAttempt?.attempt_id) return;
    dispatch({ type: "HINT_LOADING" });

    try {
      const requested = state.lastAttempt.next_action.hint_level;
      const hint = await api.requestHint({
        attempt_id: state.lastAttempt.attempt_id,
        requested_level: requested ?? Math.min(state.attemptNo, 4)
      });

      stats.current.hintsUsed = Array.from(
        new Set([...stats.current.hintsUsed, hint.hint_level])
      );
      persist();
      dispatch({ type: "HINT_LOADED", hint });
    } catch (err) {
      dispatch({ type: "ERROR", message: humanizeError(err) });
    }
  }, [api, persist, state.lastAttempt, state.attemptNo]);

  const retry = useCallback(() => dispatch({ type: "RETRY" }), []);

  return {
    state,
    setAnswer,
    submit,
    requestHint,
    retry,
    loadTask,
    snapshot: stats.current
  };
}
