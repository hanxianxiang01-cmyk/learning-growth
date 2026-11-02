#!/usr/bin/env node
/**
 * 今日安排 / 休息提醒的离线判据（无需构建 Next、无需后端）。
 *
 * 为什么单独写这个脚本：这两条是纯函数（`dailyPlan.ts` / `breakReminder.ts`），
 * 但它们的行为直接对应用户定的产品规则（按证据安排、提醒不禁止）。只靠页面截图
 * 看不出「什么时候会提醒」「计划会不会退化成 30 题」，必须有能跑数字的判据。
 *
 * 运行：
 *   node --experimental-strip-types scripts/check-break-plan.mjs
 *
 * 退出码：0 全过 / 1 有 FAIL / 2 输入缺失（模块加载不到）。
 */
import { readFileSync } from "node:fs";
import { planToday, MINUTES_PER_TASK, TASK_GOAL } from "../apps/child-web/src/features/ui-v6/dailyPlan.ts";
import {
  BREAK_MINUTES,
  BREAK_TASKS,
  freshState,
  markNudged,
  recordTask,
  shouldNudge
} from "../apps/child-web/src/features/learning/breakReminder.ts";

const results = [];
const rec = (name, ok, detail = "") => {
  results.push({ name, ok, detail });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? `  — ${detail}` : ""}`);
};

// ---------- 今日安排 ----------
const label = a => a.name ?? a.ability_id;

// 1) 有空能力时，从「完全没记录」的那一项开始
const planEmpty = planToday(
  [
    { ability_id: "app_rel", name: "数量关系", evidence_count: 6, trend: "stable", level: 2 },
    { ability_id: "app_rd", name: "读题理解", evidence_count: 0, trend: "stable", level: 0 }
  ],
  null,
  label
);
rec(
  "无记录的能力优先，3 个小任务",
  planEmpty.primary?.abilityId === "app_rd" && planEmpty.taskCount === 3,
  `primary=${planEmpty.primary?.abilityId} tasks=${planEmpty.taskCount}`
);
rec(
  "预计时长 = 任务数 × 5 分钟",
  planEmpty.minutes === planEmpty.taskCount * MINUTES_PER_TASK,
  `${planEmpty.minutes} 分钟`
);

// 2) 有「需要回看」的能力时，优先巩固它（即使它记录很多）
const planReview = planToday(
  [
    { ability_id: "app_rel", name: "数量关系", evidence_count: 9, trend: "down_review", level: 2 },
    { ability_id: "app_rd", name: "读题理解", evidence_count: 1, trend: "stable", level: 1 }
  ],
  null,
  label
);
rec(
  "需要回看的能力优先于「记录少」",
  planReview.primary?.abilityId === "app_rel" && planReview.taskCount === 3,
  `primary=${planReview.primary?.abilityId}`
);

// 3) 都稳定时只保持手感：任务数必须下降，且给出次要能力
const planStable = planToday(
  [
    { ability_id: "app_rel", name: "数量关系", evidence_count: 8, trend: "stable", level: 3 },
    { ability_id: "app_rd", name: "读题理解", evidence_count: 6, trend: "stable", level: 2 }
  ],
  { developing: ["数量关系"] },
  label
);
rec(
  "都稳定时仍按一轮任务走（不因为表现好就多塞题）",
  planStable.taskCount === TASK_GOAL && planStable.minutes === TASK_GOAL * MINUTES_PER_TASK,
  `tasks=${planStable.taskCount} minutes=${planStable.minutes}`
);
rec(
  "都稳定时给一个次要能力交替练",
  !!planStable.secondary && planStable.secondary.abilityId !== planStable.primary?.abilityId,
  `secondary=${planStable.secondary?.abilityId}`
);

// 4) 计划题数必须与后端「会话目标」一致。
//    只断言「不超过 3」是不够的：写 2 也能过，而首页会因此承诺「2 个小任务」、
//    孩子却要做满 3 道才算完成一轮。所以直接读后端常量做交叉核对。
const rulesPy = readFileSync(
  new URL("../apps/learning-api/app/core/education_rules.py", import.meta.url),
  "utf8"
);
const backendGoal = Number(/^SESSION_TASK_GOAL\s*=\s*(\d+)/m.exec(rulesPy)?.[1]);
rec(
  "能读到后端 SESSION_TASK_GOAL（读不到就是判据空跑）",
  Number.isInteger(backendGoal) && backendGoal > 0,
  `SESSION_TASK_GOAL=${backendGoal}`
);
const every = [planEmpty, planReview, planStable];
rec(
  "计划题数与后端会话目标逐档一致（首页说的量和实际要做的量同源）",
  every.every(p => p.taskCount === backendGoal) && TASK_GOAL === backendGoal,
  `计划=${every.map(p => p.taskCount).join("/")} TASK_GOAL=${TASK_GOAL} 后端=${backendGoal}`
);
rec(
  "任何情况下计划都不超过一轮的量（防止把「每天 30 题」换个名字塞回来）",
  every.every(p => p.taskCount <= backendGoal),
  `tasks=${every.map(p => p.taskCount).join("/")}`
);

// 5) 没有能力数据时不编造计划
const planNone = planToday([], null, label);
rec(
  "没有能力数据时不给计划（taskCount=0，不显示区块）",
  planNone.primary === null && planNone.taskCount === 0,
  `primary=${planNone.primary}`
);

// ---------- 休息提醒 ----------
const t0 = new Date(2026, 10, 1, 9, 0, 0).getTime();

let s = freshState(t0);
rec("刚开始学习时不该提醒", shouldNudge(s, t0 + 60_000).show === false);

for (let i = 0; i < BREAK_TASKS - 1; i++) s = recordTask(s, t0);
rec(
  `连做 ${BREAK_TASKS - 1} 题还不提醒`,
  shouldNudge(s, t0 + 60_000).show === false,
  `tasksSinceNudge=${s.tasksSinceNudge}`
);
s = recordTask(s, t0);
const byTasks = shouldNudge(s, t0 + 60_000);
rec(`连做 ${BREAK_TASKS} 题后提醒（按任务数）`, byTasks.show && byTasks.reason === "tasks", `reason=${byTasks.reason}`);

// 提醒后重置：立刻再判断不该再弹
const afterNudge = markNudged(s, t0 + 60_000);
rec("提醒过一次后不会立刻重复弹", shouldNudge(afterNudge, t0 + 61_000).show === false);

// 时间型：停在一题上很久也要提醒
let s2 = freshState(t0);
const byTime = shouldNudge(s2, t0 + BREAK_MINUTES * 60_000 + 1_000);
rec(
  `连续 ${BREAK_MINUTES} 分钟时提醒（按时间）`,
  byTime.show && byTime.reason === "minutes",
  `reason=${byTime.reason} minutes=${byTime.minutes}`
);
rec("时间未到不提醒", shouldNudge(s2, t0 + (BREAK_MINUTES - 1) * 60_000).show === false);

// 跨天清零：昨天连做很多题，今天不该一进页面就提醒
const yesterday = { ...freshState(t0 - 24 * 3600_000), tasksSinceNudge: 99, startedAt: t0 - 24 * 3600_000 };
rec(
  "跨天自动清零（昨天的疲劳不带到今天）",
  shouldNudge(yesterday, t0).show === false,
  `tasksSinceNudge=${yesterday.tasksSinceNudge}`
);

const failed = results.filter(r => !r.ok);
console.log(`\n${failed.length === 0 ? "✔ 全部通过" : `✗ ${failed.length} 项未通过`}  (${results.length} 项)`);
process.exit(failed.length === 0 ? 0 : 1);
