/**
 * 一轮学习的小任务数（会话目标）。
 *
 * **必须等于后端 `app/core/education_rules.py` 的 `SESSION_TASK_GOAL`。**
 * 会话就是答对这么多题才结束；首页「今天的安排」写「N 个小任务」如果和它不一致，
 * 就是在承诺一个错的数字（曾经写过 2，而实际要做满 3 道）。
 *
 * 前后端一致性不靠人记：`scripts/check-break-plan.mjs` 会直接读后端那个 Python
 * 常量，与本文件的值逐个比对。改任何一边而不同步，那条判据会红。
 */
export const SESSION_TASK_GOAL = 3;
