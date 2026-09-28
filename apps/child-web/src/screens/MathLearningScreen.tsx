"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AnswerComposer,
  CoachPanel,
  ManipulativeToolbar,
  MathQuestionCard,
  MathWorkspace,
  ProgressDots
} from "@/src/components";
import { useLearningSession } from "@/src/features/learning/useLearningSession";
import type { MathTool } from "@/src/components/learning/ManipulativeToolbar";

export function MathLearningScreen({
  childId,
  sessionId
}: {
  childId: string;
  sessionId: string;
}) {
  const router = useRouter();
  const [tool, setTool] = useState<MathTool | undefined>();
  const {
    state,
    setAnswer,
    submit,
    requestHint,
    retry,
    loadTask,
    snapshot
  } = useLearningSession({ childId, sessionId });

  useEffect(() => {
    if (state.status === "completed") {
      const timer = setTimeout(() => {
        router.push(
          `/child/math/result/${sessionId}?child_id=${encodeURIComponent(childId)}`
        );
      }, 550);
      return () => clearTimeout(timer);
    }
  }, [state.status, router, sessionId, childId]);

  const task = state.task;

  return (
    <main className="page-shell">
      <div className="page-container">
        <header className="learning-topbar">
          <button
            className="back-button"
            onClick={() => router.push(`/child/math?child_id=${encodeURIComponent(childId)}`)}
          >
            ←
          </button>
          <div>
            <span className="eyebrow">数学任务</span>
            <h2>{task?.goal ?? "正在准备任务…"}</h2>
          </div>
          <ProgressDots
            current={Math.min(snapshot.tasksCompleted + 1, 3)}
            total={3}
          />
        </header>

        {state.error && <div className="error-banner">{state.error}</div>}

        {state.status === "loading_task" || !task ? (
          <div className="surface-card loading-panel">正在准备下一项数学任务…</div>
        ) : (
          <div className="learning-layout">
            <div className="learning-main">
              <MathQuestionCard
                prompt={task.ui_schema.prompt ?? "请完成这道数学任务。"}
                goal={task.goal}
              />
              <MathWorkspace uiSchema={task.ui_schema} />

              <AnswerComposer
                value={state.answer}
                placeholder={task.ui_schema.answer_placeholder}
                disabled={state.status === "submitting"}
                onChange={setAnswer}
                onSubmit={submit}
              />
            </div>

            <aside className="learning-aside">
              <ManipulativeToolbar
                active={tool}
                onSelect={setTool}
              />
              {tool && (
                <div className="tool-note">
                  已选择「{tool === "draw" ? "画一画" : tool === "blocks" ? "摆一摆" : "数一数"}」。
                  试着用这个工具把题目里的数量关系表示出来。
                </div>
              )}
              <CoachPanel
                status={state.status}
                hint={state.hint}
                error={state.error}
                onHint={requestHint}
                onRetry={retry}
                onNext={loadTask}
              />
            </aside>
          </div>
        )}
      </div>
    </main>
  );
}
