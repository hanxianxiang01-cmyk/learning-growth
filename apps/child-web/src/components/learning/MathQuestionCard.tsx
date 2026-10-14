"use client";

import { useChildUi } from "@/src/theme/ChildSkinProvider";
import { SurfaceCard } from "../ui/SurfaceCard";

export function MathQuestionCard({
  prompt,
  goal
}: {
  prompt: string;
  goal?: string;
}) {
  const { uiVersion } = useChildUi();
  return (
    <SurfaceCard className="math-question-card">
      {uiVersion !== "v6" && goal && <div className="ability-badge">{goal}</div>}
      {uiVersion === "v6" ? <h1 className="question-text">{prompt}</h1> : <div className="question-text">{prompt}</div>}
    </SurfaceCard>
  );
}
