import { MathLearningScreen } from "@/src/screens/MathLearningScreen";

/**
 * 学习页。
 *
 * V1.4 游客模式：不再从 `searchParams.child_id` 取身份。身份由客户端侧
 * `MathLearningScreen` 通过 `/v1/guest/me` 取回，服务端再按 Cookie 校验归属。
 *
 * `ability_id` / `challenge` 仍走 URL —— 它们是**意图**（想练哪个能力），
 * 不是身份，放在 URL 里既安全也便于回退。
 */
export default function Page({
  params,
  searchParams
}: {
  params: { sessionId: string };
  searchParams: { ability_id?: string; challenge?: string };
}) {
  return (
    <MathLearningScreen
      sessionId={params.sessionId}
      abilityId={searchParams.ability_id}
    />
  );
}