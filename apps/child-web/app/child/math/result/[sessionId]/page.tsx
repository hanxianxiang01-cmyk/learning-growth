import { MathResultScreen } from "@/src/screens/MathResultScreen";
import { config } from "@/src/config";

export default function Page({
  params,
  searchParams
}: {
  params: { sessionId: string };
  searchParams: { child_id?: string };
}) {
  const childId = searchParams.child_id ?? config.defaultChildId;
  return (
    <MathResultScreen
      childId={childId}
      sessionId={params.sessionId}
    />
  );
}
