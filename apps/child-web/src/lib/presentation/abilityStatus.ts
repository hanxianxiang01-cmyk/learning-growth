import type { AbilityTrend } from "@/src/lib/api/contracts";

export type AbilityStatusPresentation = {
  label: string;
  description: string;
};

const presentations: Record<AbilityTrend, AbilityStatusPresentation> = {
  up: {
    label: "有进步",
    description: "最近的学习表现正在变得更稳定。"
  },
  stable: {
    label: "很稳定",
    description: "这项能力最近保持得不错。"
  },
  watch: {
    label: "继续积累",
    description: "再做几次不同的任务，系统会更了解你的学习状态。"
  },
  down_review: {
    label: "正在巩固",
    description: "系统会继续安排合适的练习，帮助你把这项能力练得更稳。"
  }
};

export function getAbilityStatusPresentation(
  trend?: AbilityTrend
): AbilityStatusPresentation {
  return trend
    ? presentations[trend]
    : {
        label: "继续积累",
        description: "继续完成学习任务，系统会逐步积累更多成长记录。"
      };
}
