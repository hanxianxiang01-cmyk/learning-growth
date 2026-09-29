"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { getLearningApi } from "@/src/lib/api";
import type { SessionResult } from "@/src/lib/api/contracts";
import {
  loadSessionSnapshot,
  type SessionSnapshot
} from "@/src/lib/runtime/sessionStore";
import {
  AbilityGrowthCard,
  CompletionHero,
  LearningBehaviorChecklist,
  NextTaskCard,
  PrimaryButton,
  SessionStats
} from "@/src/components";

type ResultStatus = "loading" | "success" | "fallback" | "error";

function formatDuration(ms: number) {
  if (!ms) return "—";
  const min = Math.max(1, Math.round(ms / 60_000));
  return `${min} 分钟`;
}

function buildFallbackResult(
  snapshot: SessionSnapshot,
  childId: string
): SessionResult {
  return {
    session_id: snapshot.sessionId,
    child_id: childId,
    status: snapshot.completedAt ? "completed" : "unknown",
    duration_ms:
      (snapshot.completedAt ?? Date.now()) - snapshot.startedAt,
    task_count: snapshot.tasksCompleted,
    completed_count: snapshot.tasksCompleted,
    attempt_count: snapshot.totalAttempts,
    hint_usage: snapshot.hintsUsed,
    learning_behaviors: [
      {
        code: "LOCAL_SESSION_COMPLETED",
        label: "完成了本次数学任务",
        achieved: snapshot.tasksCompleted > 0
      },
      {
        code: "LOCAL_RETRY",
        label: "遇到困难后继续尝试",
        achieved: snapshot.totalAttempts > snapshot.correctTasks
      }
    ],
    ability_changes: [],
    next_recommendation: {
      type: "FALLBACK",
      title: "返回数学首页",
      description: "正式学习记录暂未加载，可以稍后再查看结果。"
    }
  };
}

export function MathResultScreen({
  childId,
  sessionId
}: {
  childId: string;
  sessionId: string;
}) {
  const api = useMemo(() => getLearningApi(), []);
  const [result, setResult] = useState<SessionResult | null>(null);
  const [status, setStatus] = useState<ResultStatus>("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setStatus("loading");
    setErrorMessage(null);

    try {
      const data = await api.getSessionResult(sessionId);
      setResult(data);
      setStatus("success");
    } catch (error) {
      const snapshot = loadSessionSnapshot(sessionId);

      if (snapshot) {
        setResult(buildFallbackResult(snapshot, childId));
        setStatus("fallback");
        setErrorMessage(
          "正式学习记录暂时没有加载成功，下面先显示本机保存的临时记录。"
        );
      } else {
        setResult(null);
        setStatus("error");
        setErrorMessage(
          error instanceof Error
            ? "学习结果暂时没有加载成功，请重新尝试。"
            : "学习结果暂时没有加载成功。"
        );
      }
    }
  }, [api, childId, sessionId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (status === "loading") {
    return (
      <main className="page-shell">
        <div className="page-container">
          <div className="surface-card loading-panel">
            正在整理本次学习记录…
          </div>
        </div>
      </main>
    );
  }

  if (!result) {
    return (
      <main className="page-shell">
        <div className="page-container result-stack">
          <div className="surface-card result-error-card">
            <h2>暂时没有拿到学习结果</h2>
            <p className="muted">{errorMessage}</p>
            <PrimaryButton onClick={load}>重新加载</PrimaryButton>
          </div>
        </div>
      </main>
    );
  }

  const ability = result.ability_changes[0];
  const recommendation = result.next_recommendation;

  const nextHref =
    recommendation?.href ??
    `/child/math?child_id=${encodeURIComponent(childId)}`;

  return (
    <main className="page-shell">
      <div className="page-container result-stack">
        <CompletionHero subtitle="你完成了本次数学学习。这里记录的不只是对错，也包括你的尝试、提示使用和能力变化。" />

        {status === "fallback" && (
          <div className="fallback-banner">
            <strong>临时记录</strong>
            <span>{errorMessage}</span>
            <button type="button" onClick={load}>重新获取正式结果</button>
          </div>
        )}

        <div className="result-grid">
          <LearningBehaviorChecklist
            items={result.learning_behaviors.map(item => ({
              label: item.label,
              done: item.achieved
            }))}
          />

          {ability ? (
            <AbilityGrowthCard
              ability={ability.name ?? ability.ability_id}
              beforeLevel={ability.before_level}
              afterLevel={ability.after_level}
              trend={ability.trend}
              evidenceDelta={ability.evidence_delta}
            />
          ) : (
            <div className="surface-card ability-growth-card">
              <div className="eyebrow">🌱 能力成长</div>
              <h3>继续积累学习证据</h3>
              <p className="muted">
                本次结果中暂时没有新的能力等级变化。
              </p>
            </div>
          )}
        </div>

        <SessionStats
          duration={formatDuration(result.duration_ms)}
          tasks={result.completed_count ?? result.task_count}
          hints={result.hint_usage.length}
          attempts={result.attempt_count}
        />

        <NextTaskCard
          title={recommendation?.title ?? "返回数学首页"}
          description={
            recommendation?.description ??
            "系统会根据当前学习状态安排下一项任务。"
          }
          href={nextHref}
        />

        <a
          className="text-link centered-link"
          href={`/child/math/growth?child_id=${encodeURIComponent(childId)}`}
        >
          查看完整成长地图 →
        </a>
      </div>
    </main>
  );
}
