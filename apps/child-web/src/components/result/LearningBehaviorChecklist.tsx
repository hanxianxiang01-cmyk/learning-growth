import { SurfaceCard } from "../ui/SurfaceCard";

export function LearningBehaviorChecklist({
  items
}: {
  items: Array<{ label: string; done: boolean }>;
}) {
  return (
    <SurfaceCard className="behavior-checklist">
      <h3>你做到了</h3>
      {items.map(item => (
        <div className="check-item" key={item.label}>
          <span>{item.done ? "✅" : "○"}</span>
          <span>{item.label}</span>
        </div>
      ))}
    </SurfaceCard>
  );
}
