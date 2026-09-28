import type { AbilityState } from "@/src/lib/api/contracts";

/**
 * 首页挑战入口 → 目标能力 的语义映射。
 *
 * 不硬编码能力 ID（后端用 `app_rel`/`app_strat`、前端 mock 用 `REL`/`STRAT`，
 * 两套不一致），改为按「能力名称关键词」在已加载的能力列表里解析出真实 ability_id。
 * 解析不到时返回 undefined，调用方退回到「后端自选」的默认行为。
 */
export type ChallengeKind = "quantity" | "strategy";

const CHALLENGE_KEYWORDS: Record<ChallengeKind, string[]> = {
  quantity: ["数量关系"],
  strategy: ["策略"]
};

export function resolveAbilityId(
  kind: ChallengeKind,
  abilities: AbilityState[]
): string | undefined {
  const keywords = CHALLENGE_KEYWORDS[kind];
  const hit = abilities.find(a =>
    keywords.some(kw => a.name?.includes(kw) || a.ability_id === kw)
  );
  return hit?.ability_id;
}