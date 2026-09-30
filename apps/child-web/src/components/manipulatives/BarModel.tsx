"use client";

import type { ChangeEvent } from "react";
import type { BarModelRepresentation, BarModelVisualSchema } from "@/src/lib/api/contracts";
import { useWorkspace } from "@/src/features/math-workspace";

export function BarModel({ schema }: { schema: BarModelVisualSchema }) {
  const { state, commit, undo, reset, can } = useWorkspace();
  const representation = state.present;
  if (representation.type !== "bar-model") return null;

  const max = Math.max(
    1,
    schema.max_value ?? 0,
    ...schema.bars.map(bar => bar.max ?? bar.value ?? 0),
    ...representation.bars.map(bar => bar.value)
  );

  const setValue = (id: string, value: number) => {
    const next: BarModelRepresentation = {
      ...representation,
      bars: representation.bars.map(bar =>
        bar.id === id ? { ...bar, value } : bar
      )
    };
    commit(next, { event_type: "resize", capability_id: "resize", target_id: id, payload: { value } });
  };

  return (
    <div className="manipulative-card bar-model" data-testid="bar-model">
      <div className="manipulative-heading">
        <div>
          <strong>线段图</strong>
          <span>{representation.relationship === "part-whole" ? "看看总量和部分之间是什么关系。" : "把两条线段左边对齐，更容易看出相差多少。"}</span>
        </div>
        <div className="workspace-actions">
          <button type="button" disabled={!can("undo")} onClick={undo}>撤销</button>
          <button type="button" disabled={!can("reset")} onClick={reset}>重置</button>
        </div>
      </div>

      <div className="bar-model-board">
        {representation.bars.map(bar => {
          const source = schema.bars.find(item => item.id === bar.id);
          const min = source?.min ?? 0;
          const barMax = source?.max ?? max;
          const highlighted = state.highlightedTargets.includes(bar.id);
          return (
            <div className={`bar-row ${highlighted ? "is-highlighted" : ""}`} key={bar.id}>
              <div className="bar-label">
                <strong>{bar.label}</strong>
                <span>{bar.unknown ? "?" : bar.value}</span>
              </div>
              <div className="bar-track">
                <div className="bar-fill" style={{ width: `${Math.max(4, (bar.value / max) * 100)}%` }}>
                  <span>{bar.unknown ? "?" : bar.value}</span>
                </div>
              </div>
              <label className="bar-slider-label">
                <span className="sr-only">调整{bar.label}</span>
                <input
                  disabled={!can("resize")}
                  type="range"
                  min={min}
                  max={Math.max(min + 1, barMax)}
                  step={1}
                  value={bar.value}
                  onChange={(event: ChangeEvent<HTMLInputElement>) => setValue(bar.id, Number(event.target.value))}
                />
              </label>
            </div>
          );
        })}
      </div>
      <div className="workspace-caption">拖动滑块调整线段长度，用图表示题目里的关系。</div>
    </div>
  );
}
