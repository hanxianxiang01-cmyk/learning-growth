"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { CoachPanel, ProgressDots } from "@/src/components";
import { TaskRenderer } from "@/src/features/task-renderer";
import { useLearningSession } from "@/src/features/learning/useLearningSession";

export function MathLearningScreen({
  childId,
  sessionId,
  abilityId
}: {
  childId: string;
  sessionId: string;
  abilityId?: string;
}) {
  const router = useRouter();
  const {
    state,
    setResponse,
    submit,
    requestHint,
    retry,
    loadTask,
    snapshot
  } = useLearningSession({ childId, sessionId, abilityId });

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
              <TaskRenderer
                task={task}
                response={state.response}
                disabled={state.status === "submitting"}
                hintAction={state.hint?.ui_action}
                onResponseChange={setResponse}
                onSubmit={submit}
              />
            </div>

            <aside className="learning-aside">
              <div className="surface-card method-card">
                <div className="eyebrow">数学方法</div>
                <strong>
                  {task.ui_schema.kind === "manipulative"
                    ? task.ui_schema.visual.type === "objects"
                      ? "摆一摆 · 一一对应"
                      : task.ui_schema.visual.type === "bar-model"
                        ? "线段图"
                        : "数轴"
                    : "直接作答"}
                </strong>
                <p className="muted">操作区记录的是你的数学表示方法，不会由前端直接判断能力等级。</p>
              </div>
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
