import Link from "next/link";
import { SurfaceCard } from "../ui/SurfaceCard";

export function NextTaskCard({
  title,
  description,
  href
}: {
  title: string;
  description?: string;
  href: string;
}) {
  return (
    <SurfaceCard className="next-task-card">
      <div>
        <div className="eyebrow">🪧 下一步</div>
        <h3>{title}</h3>
        {description && <p className="muted">{description}</p>}
      </div>
      <Link className="primary-link" href={href}>继续 →</Link>
    </SurfaceCard>
  );
}
