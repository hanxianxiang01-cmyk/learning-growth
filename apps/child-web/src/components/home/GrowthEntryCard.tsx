import Link from "next/link";
import { SurfaceCard } from "../ui/SurfaceCard";

export function GrowthEntryCard({
  summary,
  href
}: {
  summary: string;
  href: string;
}) {
  return (
    <SurfaceCard className="growth-entry-card">
      <div>
        <div className="eyebrow">🌱 成长记录</div>
        <h3>我的数学成长地图</h3>
        <p className="muted">{summary}</p>
      </div>
      <Link className="text-link" href={href}>查看成长 →</Link>
    </SurfaceCard>
  );
}
