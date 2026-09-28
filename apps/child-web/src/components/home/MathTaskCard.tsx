import { PrimaryButton } from "../ui/PrimaryButton";
import { SurfaceCard } from "../ui/SurfaceCard";

export function MathTaskCard({
  icon,
  title,
  goal,
  minutes,
  difficulty,
  loading,
  onStart
}: {
  icon: string;
  title: string;
  goal: string;
  minutes: number;
  difficulty: 1 | 2 | 3 | 4 | 5;
  loading?: boolean;
  onStart?: () => void;
}) {
  return (
    <SurfaceCard className="math-task-card">
      <div className="task-icon">{icon}</div>
      <h3>{title}</h3>
      <p className="muted">{goal}</p>
      <div className="task-meta">
        <span>{"★".repeat(difficulty)}{"☆".repeat(5 - difficulty)}</span>
        <span>约 {minutes} 分钟</span>
      </div>
      <PrimaryButton disabled={loading} onClick={onStart}>
        {loading ? "正在准备…" : "开始任务 →"}
      </PrimaryButton>
    </SurfaceCard>
  );
}
