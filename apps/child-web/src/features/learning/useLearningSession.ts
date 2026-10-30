"use client";

import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";
import { getLearningApi } from "@/src/lib/api";
import { LearningApiError } from "@/src/lib/api/http";
import { isTaskResponseReady } from "@/src/features/task-renderer";
import {
  initialLearningState,
  learningReducer,
  getNextActionCode
} from "./machine";
import type { TaskResponse } from "@/src/lib/api/contracts";
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
  sessionId,
  abilityId
}: {
  /** V1.4：可选。不传时由 hook 自己从会话取（`/v1/guest/me`）。 */
  childId?: string;
  sessionId: string;
  abilityId?: string;
}) {
  const api = useMemo(() => getLearningApi(), []);
  const [state, dispatch] = useReducer(
    learningReducer,
    initialLearningState
  );
  const startedAt = useRef(Date.now());
  const loadingRef = useRef(false);

  // V1.4 游客模式：身份来自服务端会话，不在 URL 里。
  // 用 state 而不是 ref，因为 loadTask 必须在拿到 id 之后才能跑
  //（没有 id 就发请求 → 服务端 401 → 用户看到「这一步暂时没有完成」，
  //  而他其实什么都没做错）。
  const [resolvedChildId, setResolvedChildId] = useState<string | null>(
    childId ?? null
  );

  useEffect(() => {
    if (resolvedChildId) return;
    let alive = true;
    api
      .getGuest()
      .then(g => {
        if (alive) setResolvedChildId(g.child_id);
      })
      .catch(err => {
        if (alive) dispatch({ type: "ERROR", message: humanizeError(err) });
      });
    return () => {
      alive = false;
    };
  }, [api, resolvedChildId]);

  const stats = useRef<SessionSnapshot>(
    loadSessionSnapshot(sessionId) ?? {
      childId: resolvedChildId ?? "",
      sessionId,
      startedAt: Date.now(),
      tasksCompleted: 0,
      correctTasks: 0,
      totalAttempts: 0,
      hintsUsed: [],
      diagnosisCodes: []
    }
  );

  // 身份后到时把 stats 里占位的空 id 补上，避免快照里存一个空 childId
  useEffect(() => {
    if (resolvedChildId && !stats.current.childId) {
      stats.current.childId = resolvedChildId;
    }
  }, [resolvedChildId]);

  const persist = useCallback(() => {
    saveSessionSnapshot(stats.current);
  }, []);

  const loadTask = useCallback(async () => {
    // 防重入：首屏 StrictMode 双跑 / 连续点「下一题」时，避免同一道题生成多个 task_instance。
    if (loadingRef.current) return;
    // 身份还没解析出来：不发请求，等 resolvedChildId 到位后 effect 会再触发
    if (!resolvedChildId) return;
    loadingRef.current = true;
    dispatch({ type: "LOAD_TASK" });
    try {
      const task = await api.getNextTask({
        child_id: resolvedChildId,
        session_id: sessionId,
        subject: "math",
        requested_minutes: 15,
        ability_id: abilityId
      });
      stats.current.lastAbilityId = task.ability_id;
      persist();
      dispatch({ type: "TASK_LOADED", task });
    } catch (err) {
      dispatch({ type: "ERROR", message: humanizeError(err) });
    } finally {
      loadingRef.current = false;
    }
  }, [api, resolvedChildId, sessionId, abilityId, persist]);

  useEffect(() => {
    if (state.status === "idle") void loadTask();
  }, [state.status, loadTask]);

  const setResponse = useCallback((response: TaskResponse) => {
    dispatch({ type: "SET_RESPONSE", response });
  }, []);

  const submit = useCallback(async () => {
    if (!state.task || !isTaskResponseReady(state.response, state.task)) return;
    dispatch({ type: "SUBMIT" });

    try {
      const result = await api.submitAttempt({
        task_instance_id: state.task.task_instance_id,
        attempt_no: state.attemptNo,
        response: state.response,
        client_elapsed_ms: Date.now() - startedAt.current,
        used_hint_levels: state.usedHintLevels
      }, state.task);

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
    setResponse,
    submit,
    requestHint,
    retry,
    loadTask,
    snapshot: stats.current
  };
}
