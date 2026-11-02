"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  BREAK_TASKS,
  type BreakState,
  type NudgeDecision,
  loadState,
  markNudged,
  recordTask,
  saveState,
  shouldNudge
} from "@/src/features/learning/breakReminder";
import { ChildIcon } from "./ChildIcon";

/**
 * 连续学习提醒（浮层，不挡操作）。
 *
 * 刻意做成浮层而不是页内横幅：学习页在 768 高的屏幕上已经是「一屏刚好」，
 * 插一条 44px 的横幅会直接把页面顶出滚动条——为了提醒反而制造了要滚动的页面。
 *
 * 两个出口都不是「禁止」：想继续随时继续，只是先问一句。
 */
export function BreakNudge({ taskId, onRest }: { taskId?: string; onRest: () => void }) {
  const [decision, setDecision] = useState<NudgeDecision | null>(null);
  const stateRef = useRef<BreakState | null>(null);

  // 每换一题记一次「完成了一个任务」：一轮 session 只有 3 题，
  // 计数必须跨轮累积，否则 5 题的门槛永远到不了。
  useEffect(() => {
    if (!taskId) return;
    const now = Date.now();
    const next = recordTask(loadState(now), now);
    stateRef.current = next;
    saveState(next);
    setDecision(shouldNudge(next, now));
  }, [taskId]);

  // 时间型提醒：孩子停在一题上很久也要提醒；30 秒检查一次足够。
  useEffect(() => {
    const timer = setInterval(() => {
      const now = Date.now();
      const current = loadState(now);
      stateRef.current = current;
      const d = shouldNudge(current, now);
      if (d.show) setDecision(d);
    }, 30_000);
    return () => clearInterval(timer);
  }, []);

  const dismiss = useCallback(() => {
    const now = Date.now();
    const next = markNudged(stateRef.current ?? loadState(now), now);
    stateRef.current = next;
    saveState(next);
    setDecision({ show: false, reason: null, minutes: 0 });
  }, []);

  const rest = useCallback(() => {
    dismiss();
    onRest();
  }, [dismiss, onRest]);

  if (!decision?.show) return null;
  return <div className="v6-break-nudge" role="status" data-testid="v6-break-nudge">
    <span className="v6-break-icon"><ChildIcon name="spark" /></span>
    <div className="v6-break-copy">
      <strong>{decision.reason === "tasks" ? `已经连做 ${BREAK_TASKS} 个小任务了` : `已经连续学了 ${decision.minutes} 分钟`}</strong>
      <span>起来动一动、看看远处，回来接着练也很好。</span>
    </div>
    <div className="v6-break-actions">
      <button type="button" className="v6-break-rest" onClick={rest} data-testid="v6-break-rest">先休息一下</button>
      <button type="button" className="v6-break-more" onClick={dismiss} data-testid="v6-break-continue">我还不累，继续</button>
    </div>
  </div>;
}
