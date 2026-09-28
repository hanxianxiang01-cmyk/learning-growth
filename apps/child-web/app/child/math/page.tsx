import { MathHomeScreen } from "@/src/screens/MathHomeScreen";
import { config } from "@/src/config";

export default function Page({
  searchParams
}: {
  searchParams: { child_id?: string };
}) {
  const childId = searchParams.child_id ?? config.defaultChildId;
  return <MathHomeScreen childId={childId} />;
}
