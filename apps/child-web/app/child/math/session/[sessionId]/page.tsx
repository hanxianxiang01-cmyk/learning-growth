import { MathLearningScreen } from "@/src/screens/MathLearningScreen";

export default function Page({
  params,
  searchParams
}: {
  params: { sessionId: string };
  searchParams: { ability_id?: string };
}) {
  // V1.4 游客模式（从主分支移植）：childId 由屏幕层经 getGuest 解析，
  // 页面只传 sessionId / abilityId。key 用 sessionId 保证换会话重挂载。
  return (
    <MathLearningScreen
      key={params.sessionId}
      sessionId={params.sessionId}
      abilityId={searchParams.ability_id}
    />
  );
}
