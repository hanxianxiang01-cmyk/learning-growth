import type { AbilityState } from "@/src/lib/api/contracts";
import { getAbilityStatusPresentation } from "@/src/lib/presentation/abilityStatus";

export function AbilityMap({
  abilities
}: {
  abilities: AbilityState[];
}) {
  return (
    <div className="surface-card ability-map">
      {abilities.map(item => {
        const pct = Math.max(5, Math.min(100, (item.level / 4) * 100));
        const status = getAbilityStatusPresentation(item.trend);
        return (
          <div
            className={`ability-row ability-row-${item.trend ?? "watch"}`}
            key={item.ability_id}
          >
            <div>
              <strong>{item.name ?? item.ability_id}</strong>
              <small>
                {status.label}
                {" · "}
                {item.evidence_count}条证据
              </small>
            </div>
            <div className="ability-track" aria-label={`${item.name ?? item.ability_id} 当前 L${item.level}`}>
              <span style={{ width: `${pct}%` }} />
            </div>
            <div className="ability-level">L{item.level}</div>
          </div>
        );
      })}
    </div>
  );
}
