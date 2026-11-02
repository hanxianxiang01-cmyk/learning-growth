import type { AbilityState } from "@/src/lib/api/contracts";

/**
 * 首页挑战入口 → 目标能力 的语义映射。
 *
 * 不硬编码能力 ID（后端用 `app_rel`/`app_strat`、前端 mock 用 `REL`/`STRAT`，
 * 两套不一致），改为按「能力名称关键词」在已加载的能力列表里解析出真实 ability_id。
 * 解析不到时退回到 `fallback_ability_id`（FE-1428：卡片配置自带兜底 ID，
 * 后端 ability_seed 与 mock 均为 app_* 口径，兜底可命中）。
 *
 * FE-1428：入口从写死 2 张卡扩为 CHALLENGE_CARDS 配置表（5 个 V2 金题能力节点
 * 各一张手工测试入口卡）。测试期全量展示，验证通过后可在本表增删条目收起/优化，
 * 首页渲染逻辑不需要再改。
 */
export type ChallengeKind =
  | "quantity"
  | "strategy"
  | "modeling"
  | "reading"
  | "conditions";

export interface ChallengeCardDef {
  kind: ChallengeKind;
  icon: string;
  title: string;
  goal: string;
  /**
   * 首页 3+2 磁贴上的短名称与短说明（V1.4 移动端设计）。
   * 磁贴只有 105 宽，`title` 里的「挑战」后缀会把名称挤成两行，
   * 长句 goal 更放不下——所以磁贴专用一套短文案，内测展示台仍用 title/goal。
   */
  tileTitle: string;
  tileGoal: string;
  minutes: number;
  difficulty: 1 | 2 | 3 | 4 | 5;
  /** 名称关键词（在后端/mock 能力列表里解析真实 ability_id） */
  keywords: string[];
  /** 解析不到时的兜底 ability_id（app_* canonical 口径） */
  fallbackAbilityId: string;
}

export const CHALLENGE_CARDS: ChallengeCardDef[] = [
  {
    kind: "quantity",
    icon: "🔢",
    title: "数量关系挑战",
    goal: "通过摆一摆、画一画理解题目关系",
    tileTitle: "数量关系",
    tileGoal: "发现数量的联系",
    minutes: 8,
    difficulty: 2,
    keywords: ["数量关系"],
    fallbackAbilityId: "app_rel"
  },
  {
    kind: "modeling",
    icon: "📊",
    title: "建模表征挑战",
    goal: "用线段图、阵列、估算把题目画出来",
    tileTitle: "建模表征",
    tileGoal: "用图、表等表达",
    minutes: 8,
    difficulty: 2,
    keywords: ["建模表征", "建模"],
    fallbackAbilityId: "app_model"
  },
  {
    kind: "reading",
    icon: "🔍",
    title: "读题理解挑战",
    goal: "读清题目问的是什么、位值与排序",
    tileTitle: "读题理解",
    tileGoal: "读清题意与信息",
    minutes: 6,
    difficulty: 1,
    keywords: ["读题理解", "读题"],
    fallbackAbilityId: "app_rd"
  },
  {
    kind: "conditions",
    icon: "🧾",
    title: "条件识别挑战",
    goal: "找出竖式、图形里的关键条件",
    tileTitle: "条件识别",
    tileGoal: "找出关键条件",
    minutes: 6,
    difficulty: 2,
    keywords: ["条件识别", "条件"],
    fallbackAbilityId: "app_cond"
  },
  {
    kind: "strategy",
    icon: "🧩",
    title: "策略挑战",
    goal: "尝试用不同方法解决同一个问题",
    tileTitle: "策略挑战",
    tileGoal: "尝试不同方法",
    minutes: 6,
    difficulty: 2,
    keywords: ["策略"],
    fallbackAbilityId: "app_strat"
  }
];

export function resolveAbilityId(
  kind: ChallengeKind,
  abilities: AbilityState[]
): string | undefined {
  const card = CHALLENGE_CARDS.find(c => c.kind === kind);
  if (!card) return undefined;
  const hit = abilities.find(a =>
    card.keywords.some(kw => a.name?.includes(kw) || a.ability_id === kw)
  );
  return hit?.ability_id ?? card.fallbackAbilityId;
}
