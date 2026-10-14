import type { AbilityState } from "@/src/lib/api/contracts";
import type { ChildIconName } from "@/src/components/ui-v6/ChildIcon";
import { getAbilityStatusPresentation } from "@/src/lib/presentation/abilityStatus";

/** Labels/order are the approved V6 presentation, not a prerequisite graph or mastery rule. */
export const ABILITY_NODES: ReadonlyArray<{
  id: string; label: string; subtitle: string; description: string;
  icon: ChildIconName; color: string; soft: string; aliases: string[];
}> = [
  { id: "app_rel", label: "数量关系", subtitle: "看清数量怎样联系", description: "把题目中的数量放在一起比较，看看它们是合起来、相差，还是一组一组。", icon: "plus", color: "#3979ba", soft: "#e9f3ff", aliases: ["REL"] },
  { id: "app_check", label: "检查验算", subtitle: "换个办法，再确认一次", description: "先找到要核对的结论，再用重算、回看或比较的方法，检查哪里对、哪里需要改。", icon: "search", color: "#9c751e", soft: "#fff5d8", aliases: ["CHECK"] },
  { id: "app_rd", label: "读题理解", subtitle: "读清楚题目在问什么", description: "读清题目里的信息，明白它要你解决什么问题。", icon: "book", color: "#398768", soft: "#e7f7ed", aliases: ["READ", "RD"] },
  { id: "app_transfer", label: "迁移变式", subtitle: "把方法用到新问题里", description: "碰到不同的情境或条件时，想一想学过的方法能不能用上。", icon: "transfer", color: "#805eb5", soft: "#f1ebff", aliases: ["TRANSFER"] },
  { id: "app_model", label: "建模表征", subtitle: "用图或工具表达关系", description: "用线段、图形或数学工具，把自己理解的数量关系表示出来。", icon: "layers", color: "#a66085", soft: "#fff0f5", aliases: ["MODEL"] },
  { id: "app_cond", label: "条件识别", subtitle: "找到真正有用的信息", description: "分清题目已经告诉你的条件，再看看哪些信息能够帮助解决问题。", icon: "flag", color: "#357d98", soft: "#e7f8ff", aliases: ["COND"] },
  { id: "app_strat", label: "策略选择", subtitle: "选择适合自己的方法", description: "根据题目的特点选择合适的方法；遇到困难时，也可以换一种办法试试。", icon: "compass", color: "#7c57a6", soft: "#f2ecff", aliases: ["STRAT"] }
];
export type AbilityNode = (typeof ABILITY_NODES)[number];

export function findAbility(node: AbilityNode, abilities: AbilityState[]): AbilityState | undefined {
  // Only explicit canonical/legacy IDs: a vague name match must not borrow another ability's data.
  return abilities.find(a => a.ability_id === node.id) ?? abilities.find(a => node.aliases.includes(a.ability_id));
}
export function presentAbility(ability?: AbilityState) {
  const hasLevel = !!ability && Number.isFinite(ability.level) && ability.level >= 0;
  const hasCount = !!ability && Number.isInteger(ability.evidence_count) && ability.evidence_count >= 0;
  const count = hasCount ? ability!.evidence_count : null;
  const trend = ["up", "stable", "watch", "down_review"].includes(ability?.trend ?? "")
    ? ability?.trend : undefined;
  const base = getAbilityStatusPresentation(trend);
  return {
    level: hasLevel ? `L${ability!.level}` : "待了解", count,
    status: !ability || count === null ? "尚待了解" : count === 0 ? "暂无记录" : base.label,
    description: !ability || count === null ? "有了更多学习记录后，再回来看看。" : count === 0 ? "这里暂时还没有可查看的学习记录。" : base.description,
    stable: count !== null && count > 0 && ability?.trend === "stable"
  };
}
