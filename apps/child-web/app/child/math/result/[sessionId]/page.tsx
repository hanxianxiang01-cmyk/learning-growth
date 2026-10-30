import { MathResultScreen } from "@/src/screens/MathResultScreen";

export default function Page({
  params
}: {
  params: { sessionId: string };
}) {
  // V1.4 游客模式（从主分支移植）：childId 由屏幕层从 session result 反查，
  // 页面只传 sessionId。
  return <MathResultScreen sessionId={params.sessionId} />;
}
