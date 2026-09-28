import { SurfaceCard } from "../ui/SurfaceCard";

export function CompletionHero({
  subtitle
}: {
  subtitle: string;
}) {
  return (
    <SurfaceCard className="completion-hero">
      <div className="hero-star">⭐</div>
      <h1>挑战完成！</h1>
      <p>{subtitle}</p>
    </SurfaceCard>
  );
}
