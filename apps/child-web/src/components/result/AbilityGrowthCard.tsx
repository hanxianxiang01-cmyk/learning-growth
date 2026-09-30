import { SurfaceCard } from "../ui/SurfaceCard";
import type { AbilityTrend } from "@/src/lib/api/contracts";
import { getAbilityStatusPresentation } from "@/src/lib/presentation/abilityStatus";

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
  const downgraded =
    typeof beforeLevel === "number" && beforeLevel > afterLevel;
  const status = getAbilityStatusPresentation(trend);

  return (
    <SurfaceCard className="ability-growth-card">
      <div className="eyebrow">🌱 能力成长</div>
      <h3>{ability}</h3>

      <div className="growth-level">
        {typeof beforeLevel === "number" && changed && !downgraded
          ? `L${beforeLevel} → L${afterLevel}`
          : `L${afterLevel}`}
      </div>

      <div className="ability-status-line">
        <strong>{status.label}</strong>
        <span>{status.description}</span>
      </div>

      {typeof evidenceDelta === "number" && evidenceDelta > 0 && (
        <p className="muted ability-evidence-note">
          本次新增 {evidenceDelta} 条有效学习证据。
        </p>
      )}
    </SurfaceCard>
  );
}
