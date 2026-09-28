import { MathGrowthScreen } from "@/src/screens/MathGrowthScreen";
import { config } from "@/src/config";

export default function Page({
  searchParams
}: {
  searchParams: { child_id?: string };
}) {
  return (
    <MathGrowthScreen
      childId={searchParams.child_id ?? config.defaultChildId}
    />
  );
}
