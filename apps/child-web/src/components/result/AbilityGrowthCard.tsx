import { SurfaceCard } from "../ui/SurfaceCard";
import type { AbilityTrend } from "@/src/lib/api/contracts";

const trendLabel: Record<AbilityTrend, string> = {
  up: "近期趋势上升",
  stable: "当前表现稳定",
  watch: "继续观察与积累证据",
  down_review: "需要进一步复核"
};

export function AbilityGrowthCard({
  ability,
  beforeLevel,
  afterLevel,
  trend,
  evidenceDelta
}: {
  ability: string;
  beforeLevel?: number;
  afterLevel: number;
  trend?: AbilityTrend;
  evidenceDelta?: number;
}) {
  const changed =
    typeof beforeLevel === "number" && beforeLevel !== afterLevel;

  return (
    <SurfaceCard className="ability-growth-card">
      <div className="eyebrow">🌱 能力成长</div>
      <h3>{ability}</h3>

      <div className="growth-level">
        {typeof beforeLevel === "number"
          ? changed
            ? `L${beforeLevel} → L${afterLevel}`
            : `L${afterLevel}`
          : `L${afterLevel}`}
      </div>

      <p className="muted">
        {typeof evidenceDelta === "number" && evidenceDelta > 0
          ? `本次新增 ${evidenceDelta} 条有效学习证据。`
          : trend
            ? trendLabel[trend]
            : "继续积累学习证据中。"}
      </p>
    </SurfaceCard>
  );
}
