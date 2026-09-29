"use client";

import type { NumberLineRepresentation } from "@/src/lib/api/contracts";
import { useWorkspace } from "@/src/features/math-workspace";

export function NumberLine() {
  const { state, commit, undo, reset } = useWorkspace();
  const representation = state.present;
  if (representation.type !== "number-line") return null;

  const values: number[] = [];
  for (
    let value = representation.min;
    value <= representation.max && values.length < 31;
    value += representation.step
  ) {
    values.push(value);
  }

  const select = (value: number) => {
    let next: NumberLineRepresentation;
    if (representation.start === null || representation.current === null) {
      next = {
        ...representation,
        start: value,
        current: value,
        jumps: []
      };
    } else {
      const jump = value - representation.current;
      if (jump === 0) return;
      next = {
        ...representation,
        current: value,
        jumps: [...representation.jumps, jump]
      };
    }
    commit(next);
  };

  return (
    <div className="manipulative-card number-line" data-testid="number-line">
      <div className="manipulative-heading">
        <div>
          <strong>数轴跳一跳</strong>
          <span>先找起点，再点一个数字完成一次跳步。</span>
        </div>
        <div className="workspace-actions">
          <button type="button" onClick={undo}>撤销</button>
          <button type="button" onClick={reset}>重置</button>
        </div>
      </div>

      <div className={`number-line-board ${state.highlightedTargets.includes("number-line-start") ? "is-highlighted" : ""}`}>
        <div className="number-line-axis" />
        <div className="number-line-ticks">
          {values.map(value => {
            const isStart = representation.start === value;
            const isCurrent = representation.current === value;
            return (
              <button
                key={value}
                type="button"
                className={`number-tick ${isStart ? "is-start" : ""} ${isCurrent ? "is-current" : ""}`}
                onClick={() => select(value)}
              >
                <span className="tick-mark" />
                <span>{value}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="jump-history">
        {representation.start === null ? (
          <span>请选择起点</span>
        ) : representation.jumps.length === 0 ? (
          <span>起点：{representation.start}，再点一个数字完成跳步</span>
        ) : (
          <>
            <strong>起点 {representation.start}</strong>
            {representation.jumps.map((jump, index) => (
              <span className="jump-chip" key={`${jump}-${index}`}>{jump > 0 ? `+${jump}` : jump}</span>
            ))}
            <strong>到 {representation.current}</strong>
          </>
        )}
      </div>
    </div>
  );
}
