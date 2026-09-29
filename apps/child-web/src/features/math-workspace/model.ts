import type {
  BarModelRepresentation,
  ManipulativeTaskUiSchema,
  NumberLineRepresentation,
  ObjectCounterRepresentation,
  WorkspaceRepresentation
} from "@/src/lib/api/contracts";

function spreadPositions(count: number, denominator: number, prefix: string) {
  if (count <= 0) return [];
  const slots = Math.max(1, denominator - 1);
  return Array.from({ length: count }, (_, index) => ({
    id: `${prefix}_item_${index + 1}`,
    x: denominator <= 1 ? 50 : 5 + (90 * index) / slots
  }));
}

export function createInitialRepresentation(
  schema: ManipulativeTaskUiSchema
): WorkspaceRepresentation {
  const visual = schema.visual;

  if (visual.type === "objects") {
    return {
      type: "object-counter",
      aligned: false,
      groups: visual.groups.map(group => ({
        id: group.id,
        label: group.label,
        count: group.count,
        items: spreadPositions(group.count, Math.max(1, group.count), group.id)
      }))
    } satisfies ObjectCounterRepresentation;
  }

  if (visual.type === "bar-model") {
    const inferredMax = Math.max(
      10,
      visual.max_value ?? 0,
      ...visual.bars.map(bar => bar.max ?? bar.value ?? 0)
    );

    return {
      type: "bar-model",
      relationship: visual.relationship,
      bars: visual.bars.map(bar => ({
        id: bar.id,
        label: bar.label,
        value:
          bar.value ??
          Math.max(bar.min ?? 0, Math.round(inferredMax / 3)),
        unknown: bar.unknown
      }))
    } satisfies BarModelRepresentation;
  }

  return {
    type: "number-line",
    min: visual.min,
    max: visual.max,
    step: visual.step,
    start: visual.start ?? null,
    current: visual.start ?? null,
    jumps: []
  } satisfies NumberLineRepresentation;
}

export function alignObjectCounter(
  representation: ObjectCounterRepresentation
): ObjectCounterRepresentation {
  const max = Math.max(1, ...representation.groups.map(group => group.count));
  return {
    ...representation,
    aligned: true,
    groups: representation.groups.map(group => ({
      ...group,
      items: group.items.map((item, index) => ({
        ...item,
        x: max <= 1 ? 50 : 5 + (90 * index) / (max - 1)
      }))
    }))
  };
}
