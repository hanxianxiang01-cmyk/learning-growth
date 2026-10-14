"use client";

import { useEffect, useRef } from "react";
import type { LearningState } from "@/src/features/learning/machine";
import { ChildIcon, type ChildIconName } from "./ChildIcon";

/** Present server results only; there is no local correctness/diagnosis inference. */
export function LearningFeedback({ state, onHint, onRetry, onNext, onRecover }: {
  state: LearningState;
  onHint: () => void;
  onRetry: () => void;
  onNext: () => void;
  onRecover: () => void;
}) {
  const title = useRef<HTMLHeadingElement>(null);
  const status = state.status;
  const result = state.lastAttempt;
  const wrong = result?.correct === false && ["hint_available", "hint_active", "hint_loading", "retry"].includes(status);
  const editing = status === "answering" && result?.correct === false;
  const correct = result?.correct === true && ["correct", "completed"].includes(status);
  const busy = status === "submitting" || status === "hint_loading";
  const hasFeedback = wrong || editing || correct || busy || status === "error";

  useEffect(() => {
    if (["hint_available", "retry", "hint_active", "correct", "error"].includes(status)) {
      title.current?.focus({ preventScroll: true });
    }
  }, [status]);
  if (!hasFeedback) return null;

  const kind = status === "error" ? "error" : busy ? "busy" : correct ? "correct" : editing ? "retry" : "incorrect";
  const symbol: ChildIconName = busy ? "reset" : correct ? "check" : editing ? "edit" : "warning";
  const heading = status === "error" ? "这一步暂时没有完成" : busy ? (status === "hint_loading" ? "正在准备提示" : "正在检查") : correct ? (status === "completed" ? "本次任务完成了" : "这次答对了") : editing ? "接着修改，再试一次" : "这次还没对，再检查一下";
  const body = status === "error" ? state.error : busy ? "请稍等，不用再点一次。" : correct ? "你可以再看看刚才的做法，然后继续学习。" : "保留了刚才的操作，检查后再提交你的答案。";
  const canHint = wrong && !busy && !!result?.attempt_id && ["HINT", "TEACH"].includes(result.next_action.type);

  return <section className={`v6-feedback v6-feedback--${kind}`} data-testid="v6-learning-feedback" data-feedback-state={kind} aria-live="polite" aria-atomic="true" role="status" aria-busy={busy}>
    <span className="v6-feedback-symbol"><ChildIcon name={symbol} /></span>
    <div className="v6-feedback-content">
      <h2 ref={title} tabIndex={-1}>{heading}</h2><p>{body}</p>
      {state.hint && <aside className="v6-hint-content" aria-label={`提示${state.hint.hint_level}`}><strong>提示 {state.hint.hint_level}</strong><p>{state.hint.text}</p></aside>}
      <div className="v6-feedback-actions">
        {wrong && !busy && <button type="button" className="primary-button" onClick={onRetry} data-testid="v6-retry">继续修改<ChildIcon name="edit" /></button>}
        {canHint && status !== "hint_active" && <button type="button" onClick={onHint} data-testid="v6-hint">给我一点提示<ChildIcon name="hint" /></button>}
        {correct && status !== "completed" && <button type="button" className="primary-button" onClick={onNext} data-testid="v6-next">下一题<ChildIcon name="arrow" /></button>}
        {status === "error" && <button type="button" className="primary-button" onClick={onRecover} data-testid="v6-recover">重新尝试</button>}
      </div>
    </div>
  </section>;
}
