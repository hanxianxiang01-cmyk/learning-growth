import { SurfaceCard } from "../ui/SurfaceCard";

export function TodayGoalCard({
  title,
  tip
}: {
  title: string;
  tip?: string;
}) {
  return (
    <SurfaceCard className="today-goal-card">
      <div className="eyebrow">🎯 今日目标</div>
      <h2>{title}</h2>
      {tip && <p className="muted">{tip}</p>}
    </SurfaceCard>
  );
}
