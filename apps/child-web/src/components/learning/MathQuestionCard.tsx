import { SurfaceCard } from "../ui/SurfaceCard";

export function MathQuestionCard({
  prompt,
  goal
}: {
  prompt: string;
  goal?: string;
}) {
  return (
    <SurfaceCard className="math-question-card">
      {goal && <div className="ability-badge">{goal}</div>}
      <div className="question-text">{prompt}</div>
    </SurfaceCard>
  );
}
