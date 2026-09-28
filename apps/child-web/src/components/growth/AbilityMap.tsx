import type { AbilityState } from "@/src/lib/api/contracts";

const trendLabel = {
  up: "上升",
  stable: "稳定",
  watch: "观察中",
  down_review: "需复核"
} as const;

export function AbilityMap({
  abilities
}: {
  abilities: AbilityState[];
}) {
  return (
    <div className="surface-card ability-map">
      {abilities.map(item => {
        const pct = Math.max(5, Math.min(100, (item.level / 4) * 100));
        return (
          <div className="ability-row" key={item.ability_id}>
            <div>
              <strong>{item.name ?? item.ability_id}</strong>
              <small>
                {item.trend ? trendLabel[item.trend] : "观察中"}
                {" · "}
                {item.evidence_count}条证据
              </small>
            </div>
            <div className="ability-track">
              <span style={{ width: `${pct}%` }} />
            </div>
            <div className="ability-level">L{item.level}</div>
          </div>
        );
      })}
    </div>
  );
}
