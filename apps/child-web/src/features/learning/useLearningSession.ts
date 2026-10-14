"use client";

import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";
import { getLearningApi } from "@/src/lib/api";
import { LearningApiError } from "@/src/lib/api/http";
import { isTaskResponseReady } from "@/src/features/task-renderer/taskResponse";
import { initialLearningState, learningReducer, getNextActionCode } from "./machine";
import type { AttemptRequest, TaskInstance, TaskResponse } from "@/src/lib/api/contracts";
import { loadSessionSnapshot, saveSessionSnapshot, type SessionSnapshot } from "@/src/lib/runtime/sessionStore";

type FailureStage = "load" | "submit" | "hint" | null;
function humanizeError(err: unknown) {
  if (err instanceof LearningApiError) {
    if (err.code === "LE-4291") return "操作有点快，请稍后再试。";
    if (err.code === "AG-5031") return "小助手暂时没有响应，可以稍后再试。";
  }
  return "这一步暂时没有完成，请再试一次。";
}

export function useLearningSession({ childId, sessionId, abilityId }: {
  childId: string; sessionId: string; abilityId?: string;
}) {
  const api = useMemo(() => getLearningApi(), []);
  const [state, dispatch] = useReducer(learningReducer, initialLearningState);
  const [failureStage, setFailureStage] = useState<FailureStage>(null);
  const startedAt = useRef(Date.now());
  const loadingRef = useRef(false), submittingRef = useRef(false), hintingRef = useRef(false);
  // Ambiguous network failure: retransmit the exact body with the existing stable submission_id.
  // Never apply a newly edited answer to the same attempt_no.
  const pending = useRef<{ request: AttemptRequest; task: TaskInstance } | null>(null);
  const acknowledged = useRef(new Set<string>());
  const stats = useRef<SessionSnapshot>({
    childId, sessionId, startedAt: Date.now(), tasksCompleted: 0, correctTasks: 0,
    totalAttempts: 0, hintsUsed: [], diagnosisCodes: []
  });
  // Read browser-only cache after hydration. The server and first client render agree.
  useEffect(() => {
    const saved = loadSessionSnapshot(sessionId);
    if (saved?.childId === childId && saved.sessionId === sessionId) stats.current = saved;
  }, [childId, sessionId]);
  const persist = useCallback(() => { saveSessionSnapshot(stats.current); }, []);

  const loadTask = useCallback(async () => {
    if (loadingRef.current || submittingRef.current || hintingRef.current || pending.current) return;
    loadingRef.current = true;
    setFailureStage(null);
    dispatch({ type: "LOAD_TASK" });
    try {
      const task = await api.getNextTask({ child_id: childId, session_id: sessionId, subject: "math", requested_minutes: 15, ability_id: abilityId });
      startedAt.current = Date.now();
      stats.current.lastAbilityId = task.ability_id;
      persist();
      dispatch({ type: "TASK_LOADED", task });
    } catch (err) {
      setFailureStage("load");
      dispatch({ type: "ERROR", message: humanizeError(err) });
    } finally { loadingRef.current = false; }
  }, [api, childId, sessionId, abilityId, persist]);

  useEffect(() => { if (state.status === "idle") void loadTask(); }, [state.status, loadTask]);

  const setResponse = useCallback((response: TaskResponse) => {
    if (submittingRef.current || pending.current) return;
    dispatch({ type: "SET_RESPONSE", response });
  }, []);

  const submit = useCallback(async () => {
    if (submittingRef.current || loadingRef.current || hintingRef.current || !state.task) return;
    if (!pending.current && (["correct", "completed"].includes(state.status) || !isTaskResponseReady(state.response, state.task))) return;
    const entry = pending.current ?? {
      task: state.task,
      request: structuredClone({
        task_instance_id: state.task.task_instance_id, attempt_no: state.attemptNo,
        response: state.response, client_elapsed_ms: Date.now() - startedAt.current,
        used_hint_levels: state.usedHintLevels
      })
    };
    const key = `${entry.request.task_instance_id}:${entry.request.attempt_no}`;
    if (acknowledged.current.has(key)) return;
    submittingRef.current = true;
    pending.current = entry;
    setFailureStage(null);
    dispatch({ type: "SUBMIT" });
    try {
      const result = await api.submitAttempt(entry.request, entry.task);
      acknowledged.current.add(key);
      pending.current = null;
      stats.current.totalAttempts += 1;
      if (result.diagnosis?.code?.startsWith("E")) stats.current.diagnosisCodes.push(result.diagnosis.code);
      if (result.correct) { stats.current.tasksCompleted += 1; stats.current.correctTasks += 1; }
      if (getNextActionCode(result) === "COMPLETE") stats.current.completedAt = Date.now();
      persist();
      dispatch({ type: "ATTEMPT_RESULT", result });
    } catch (err) {
      setFailureStage("submit");
      dispatch({ type: "ERROR", message: "这次提交还没有确认结果。刚才的答案已保留，请重试这次提交。" });
    } finally { submittingRef.current = false; }
  }, [api, persist, state]);

  const requestHint = useCallback(async () => {
    const attempt = state.lastAttempt;
    if (!attempt?.attempt_id || !["HINT", "TEACH"].includes(attempt.next_action.type) || hintingRef.current || submittingRef.current || loadingRef.current || pending.current) return;
    hintingRef.current = true;
    setFailureStage(null);
    dispatch({ type: "HINT_LOADING" });
    try {
      const hint = await api.requestHint({ attempt_id: attempt.attempt_id, requested_level: attempt.next_action.hint_level ?? Math.min(state.attemptNo, 4) });
      stats.current.hintsUsed = Array.from(new Set([...stats.current.hintsUsed, hint.hint_level]));
      persist();
      dispatch({ type: "HINT_LOADED", hint });
    } catch (err) {
      setFailureStage("hint");
      dispatch({ type: "ERROR", message: humanizeError(err) });
    } finally { hintingRef.current = false; }
  }, [api, persist, state.lastAttempt, state.attemptNo]);

  const retry = useCallback(() => {
    if (submittingRef.current || hintingRef.current || pending.current) return;
    setFailureStage(null);
    dispatch({ type: "RETRY" });
  }, []);
  const retryFailedOperation = useCallback(() => {
    if (failureStage === "submit") void submit();
    else if (failureStage === "hint") void requestHint();
    else void loadTask();
  }, [failureStage, submit, requestHint, loadTask]);

  return { state, setResponse, submit, requestHint, retry, loadTask, retryFailedOperation, failureStage, pendingSubmission: pending.current !== null, snapshot: stats.current };
}
