import { SurfaceCard } from "../ui/SurfaceCard";

export function SessionStats({
  duration,
  hints,
  attempts,
  tasks
}: {
  duration: string;
  hints: number;
  attempts: number;
  tasks?: number;
}) {
  const data = [
    ["⏱", "本次用时", duration],
    ["📚", "完成任务", tasks === undefined ? "—" : `${tasks} 个`],
    ["💡", "提示层级", hints ? `${hints} 个` : "未使用"],
    ["✍️", "作答次数", String(attempts)]
  ];

  return (
    <div className="session-stats">
      {data.map(([icon, label, value]) => (
        <SurfaceCard className="stat-card" key={label}>
          <span>{icon}</span>
          <small>{label}</small>
          <strong>{value}</strong>
        </SurfaceCard>
      ))}
    </div>
  );
}
