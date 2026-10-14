import { MathLearningScreen } from "@/src/screens/MathLearningScreen";
import { config } from "@/src/config";

export default function Page({
  params,
  searchParams
}: {
  params: { sessionId: string };
  searchParams: { child_id?: string; ability_id?: string };
}) {
  const childId = searchParams.child_id ?? config.defaultChildId;
  return (
    <MathLearningScreen
      key={`${childId}:${params.sessionId}`}
      childId={childId}
      sessionId={params.sessionId}
      abilityId={searchParams.ability_id}
    />
  );
}
