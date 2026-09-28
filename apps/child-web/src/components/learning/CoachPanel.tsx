import { PrimaryButton } from "../ui/PrimaryButton";
import type { LearningStatus } from "@/src/features/learning/machine";
import type { HintResponse } from "@/src/lib/api/contracts";

export function CoachPanel({
  status,
  hint,
  error,
  onHint,
  onRetry,
  onNext
}: {
  status: LearningStatus;
  hint: HintResponse | null;
  error?: string | null;
  onHint: () => void;
  onRetry: () => void;
  onNext: () => void;
}) {
  let message = "先自己想一想。需要时，我会给你一点提示。";
  if (status === "hint_available") {
    message = "这次答案还不对。我不会直接告诉你答案，可以先拿一个提示。";
  } else if (status === "hint_loading") {
    message = "正在准备提示…";
  } else if (status === "hint_active") {
    message =
      hint?.text ??
      `提示 ${hint?.hint_level ?? ""} 已准备好。`;
  } else if (status === "retry") {
    message = "换一种方法再试一次。";
  } else if (status === "correct") {
    message = "这一步完成了。继续看看下一道任务。";
  } else if (status === "completed") {
    message = "本次学习任务完成。";
  } else if (status === "error") {
    message = error ?? "暂时出现了问题。";
  }

  return (
    <aside className="surface-card coach-panel">
      <div className="coach-title">
        <span className="coach-avatar">AI</span>
        <strong>数学小助手</strong>
      </div>
      <p>{message}</p>

      {status === "hint_available" && (
        <PrimaryButton secondary onClick={onHint}>给我一点提示</PrimaryButton>
      )}
      {status === "hint_active" && (
        <PrimaryButton secondary onClick={onRetry}>我再想想</PrimaryButton>
      )}
      {status === "retry" && (
        <PrimaryButton secondary onClick={onRetry}>重新尝试</PrimaryButton>
      )}
      {status === "correct" && (
        <PrimaryButton onClick={onNext}>下一题 →</PrimaryButton>
      )}
    </aside>
  );
}
