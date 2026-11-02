/**
 * 连续学习提醒：**提醒，不是禁止**。
 *
 * 为什么不是「今天已经 30 题，不能再做」：那正是 2026-11-01 取消的东西。
 * 孩子学得起劲是好事，我们能做的是在合适的时机递一句「起来动一动」，
 * 而不是替他把门关上。
 *
 * 判据（纯函数，可单测）：
 * - 连续学习时长 ≥ 15 分钟，或
 * - 自上次提醒后完成 ≥ 5 个任务
 * 满足其一就提醒；提醒过就重新计数，不会每 10 秒弹一次。
 *
 * 计数按天存在 localStorage：一轮 session 只有 3 个任务，
 * 只看单个 session 的计时器永远到不了 5 题——那样写出来的提醒是死代码。
 */

export const BREAK_MINUTES = 15;
export const BREAK_TASKS = 5;

const STORAGE_KEY = "iqc:break-nudge";

export type BreakState = {
  /** 统计日期（本地时区），跨天自动清零 */
  date: string;
  /** 本轮连续学习开始时间（毫秒） */
  startedAt: number;
  /** 上次提醒后完成的任务数 */
  tasksSinceNudge: number;
  /** 上次提醒时间（毫秒），0 表示今天还没提醒过 */
  lastNudgeAt: number;
};

function todayKey(now: number): string {
  const d = new Date(now);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function freshState(now: number): BreakState {
  return { date: todayKey(now), startedAt: now, tasksSinceNudge: 0, lastNudgeAt: 0 };
}

export function normalizeState(raw: BreakState | null, now: number): BreakState {
  if (!raw || raw.date !== todayKey(now)) return freshState(now);
  return raw;
}

/** 完成一个任务后调用：同一天累加，跨天重置。 */
export function recordTask(state: BreakState, now: number): BreakState {
  const base = normalizeState(state, now);
  return { ...base, tasksSinceNudge: base.tasksSinceNudge + 1 };
}

export type NudgeDecision = { show: boolean; reason: "minutes" | "tasks" | null; minutes: number };

/** 现在该不该提醒。提醒过之后（lastNudgeAt 更新）不会重复触发。 */
export function shouldNudge(state: BreakState, now: number): NudgeDecision {
  const s = normalizeState(state, now);
  const minutes = Math.max(0, Math.round((now - s.startedAt) / 60000));
  if (s.tasksSinceNudge >= BREAK_TASKS) return { show: true, reason: "tasks", minutes };
  if (now - s.startedAt >= BREAK_MINUTES * 60000) return { show: true, reason: "minutes", minutes };
  return { show: false, reason: null, minutes };
}

/**
 * 提醒过之后重置连续计数：继续学就重新开始计 15 分钟 / 5 题。
 * 不能把 startedAt 归零成「今天 0 点」，否则第二条提醒永远不来。
 */
export function markNudged(state: BreakState, now: number): BreakState {
  return { ...normalizeState(state, now), tasksSinceNudge: 0, startedAt: now, lastNudgeAt: now };
}

export function loadState(now: number): BreakState {
  if (typeof window === "undefined") return freshState(now);
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return normalizeState(raw ? (JSON.parse(raw) as BreakState) : null, now);
  } catch {
    return freshState(now);
  }
}

export function saveState(state: BreakState): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // 隐私模式下写不进去：提醒会退化（每次重新计时），但不该把学习页搞崩。
  }
}
