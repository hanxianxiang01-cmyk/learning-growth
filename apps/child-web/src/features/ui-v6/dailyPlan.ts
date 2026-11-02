import type { AbilityState, LearnerProfile } from "@/src/lib/api/contracts";
// 这里刻意用相对路径而不是 `@/src/...` 别名：本文件要能被
// `node --experimental-strip-types` 直接跑（见文件末尾的说明），而 node 不认识
// tsconfig 里的 paths 别名。用别名时脚本一进来就 ERR_MODULE_NOT_FOUND，
// 判据等于从来没跑过。
import { SESSION_TASK_GOAL } from "../../lib/learningRules";

/**
 * 今日学习安排：**按已有学习证据**决定练什么、练几题。
 *
 * 为什么不是「每天 30 题」：题数不是学习目标，掌握才是。固定的题数配额
 * （2026-11-01 已取消）既会在孩子想多练时挡人，也会在只该练 10 分钟时逼人做完。
 *
 * 规则（可解释、可单测，不含随机）：
 * 1. 有「需要回看 / 需要观察」的能力 → 本轮集中练它，3 个小任务；
 * 2. 否则挑证据最少（还没怎么练过）的能力，3 个小任务；
 * 3. 所有能力都稳定 → 保持手感，仍是这一轮的 3 个小任务，并给一个次要能力换换脑子。
 *
 * 只会少不会多：越熟练越短。没有「必须做满 N 题」这回事。
 *
 * 本文件刻意**不 import** 展示层（图标/文案表）：这样它能被 `node --experimental-strip-types`
 * 直接跑单测，不需要先构建整个 Next 应用。能力名称由调用方通过 `labelOf` 注入。
 */

export type PlanTarget = { abilityId: string; label: string; reason: string };

export type DailyPlan = {
  primary: PlanTarget | null;
  secondary: PlanTarget | null;
  taskCount: number;
  minutes: number;
};

/** 每个小任务的预估时长（分钟）。与后端 MINUTES_PER_TASK 同一口径。 */
export const MINUTES_PER_TASK = 5;

/** 一轮学习的小任务数。与 mock 会话推进、后端会话目标同一份来源。 */
export const TASK_GOAL = SESSION_TASK_GOAL;

export type LabelResolver = (ability: AbilityState) => string;

const defaultLabel: LabelResolver = a => a.name ?? a.ability_id;

/** 证据越少越该先练；非法值按 0 计（缺记录 = 没练过）。 */
export function evidenceOf(ability: AbilityState): number {
  return Number.isInteger(ability.evidence_count) && ability.evidence_count >= 0 ? ability.evidence_count : 0;
}

export function planToday(
  abilities: AbilityState[],
  profile?: LearnerProfile | null,
  labelOf: LabelResolver = defaultLabel
): DailyPlan {
  const known = abilities.filter(a => !!a?.ability_id);
  if (known.length === 0) return { primary: null, secondary: null, taskCount: 0, minutes: 0 };

  // 1) 需要回看的最优先：这些是「已经练过但不稳」的能力，
  //    再刷新题不如把这一项练扎实。
  const needsReview = known.filter(a => {
    return evidenceOf(a) > 0 && (a.trend === "watch" || a.trend === "down_review");
  });
  if (needsReview.length > 0) {
    // 同样的「需要回看」里，先练证据少的（练得越少越可能是不熟，而不是忘了）
    const pick = [...needsReview].sort((a, b) => evidenceOf(a) - evidenceOf(b))[0];
    return {
      primary: { abilityId: pick.ability_id, label: labelOf(pick), reason: "这一项最近还不太稳，先把它练扎实。" },
      secondary: null,
      taskCount: TASK_GOAL,
      minutes: TASK_GOAL * MINUTES_PER_TASK
    };
  }

  // 2) 挑证据最少的能力：还没怎么练过的地方最值得先看。
  const thinnest = [...known].sort((a, b) => evidenceOf(a) - evidenceOf(b))[0];
  if (evidenceOf(thinnest) < 2) {
    return {
      primary: {
        abilityId: thinnest.ability_id,
        label: labelOf(thinnest),
        reason: evidenceOf(thinnest) === 0 ? "这一项还没有学习记录，从它开始最合适。" : "这一项练得还不多，再多看几种情况。"
      },
      secondary: null,
      taskCount: TASK_GOAL,
      minutes: TASK_GOAL * MINUTES_PER_TASK
    };
  }

  // 3) 都稳定了：不追求题量，保持手感就够，并换一个能力交替练。
  const developing = profile?.developing?.[0];
  const primaryAbility =
    known.find(a => a.ability_id === developing || a.name === developing) ??
    [...known].sort((a, b) => evidenceOf(b) - evidenceOf(a))[0];
  const other = known.find(a => a.ability_id !== primaryAbility.ability_id) ?? null;
  return {
    primary: {
      abilityId: primaryAbility.ability_id,
      label: labelOf(primaryAbility),
      reason: "最近的表现比较稳定，做完这一轮保持手感就好。"
    },
    secondary: other ? { abilityId: other.ability_id, label: labelOf(other), reason: "再换一项练练" } : null,
    taskCount: TASK_GOAL,
    minutes: TASK_GOAL * MINUTES_PER_TASK
  };
}
