"use client";

import type { ReactNode } from "react";
import { ChildIcon, type ChildIconName } from "./ChildIcon";

const icons: Record<string, ChildIconName> = {
  "object-counter": "plus", "bar-model": "layers", "number-line": "transfer",
  "number-input": "edit", "column-arithmetic": "grid", "place-value": "layers",
  "ten-frame": "grid", "array-board": "grid", "grouping-board": "grid",
  "formula-board": "plus", "estimation-canvas": "eye", "shape-gallery": "shapes",
  "shape-canvas": "edit", "sorting-board": "transfer", "direction-grid": "compass",
  "ruler": "ruler", "clock": "clock", "money-board": "wallet", "pattern-board": "shapes"
};

/** V6 presentation only. Readiness comes from the existing renderer; no local grading. */
export function RendererFrame({ rendererId, title, instruction, actions, children,
  submitDisabled, locked, onSubmit, submitTestId, testId, className = "", summary
}: {
  rendererId: string;
  title: string;
  instruction: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  submitDisabled?: boolean;
  locked?: boolean;
  onSubmit: () => void;
  submitTestId?: string;
  testId?: string;
  className?: string;
  summary?: ReactNode;
}) {
  return <section className={`manipulative-card v6-renderer v6-renderer--${rendererId} ${className}`}
    data-v6-renderer={rendererId} data-testid={testId}>
    <header className="v6-workspace-head">
      <div className="v6-workspace-title"><span className="v6-workspace-medallion"><ChildIcon name={icons[rendererId] ?? "spark"} /></span>
        <div><h2>{title}</h2><p>{instruction}</p></div>
      </div>
      {actions && <div className="v6-workspace-tools" aria-label="操作工具">{actions}</div>}
    </header>
    <div className="v6-board-body">{children}</div>
    <footer className="v6-answer-dock">
      <div className="v6-answer-note" aria-live="polite" aria-atomic="true">
        <strong>{summary ?? (locked ? "刚才的操作已保留" : submitDisabled ? "动手试一试" : "准备好就提交吧")}</strong>
        <span>{locked ? "请先看一看下面的学习反馈。" : submitDisabled ? "完成上面的操作，再提交你的想法。" : "还可以检查和修改，不着急。"}</span>
      </div>
      <button type="button" className="primary-button" data-testid={submitTestId ?? "v6-renderer-submit"}
        disabled={submitDisabled} onClick={onSubmit}>提交我的答案<ChildIcon name="arrow" /></button>
    </footer>
  </section>;
}

/** Finite, deterministic representations of task quantities, not generated illustrations. */
export function ReferenceObjects({ count, label, hiddenCount = false }: { count: number; label: string; hiddenCount?: boolean }) {
  return <div className="v6-reference-objects"><strong>{label}</strong>
    <div className="v6-object-shelf" role="img" aria-label={hiddenCount ? `${label}，请结合题干估一估` : `${label}，${count}个`}>
      {Array.from({ length: Math.max(0, Math.min(100, count)) }, (_, i) => <span key={i} className="v6-book-shape" aria-hidden="true" />)}
    </div>
    {!hiddenCount && <span>{count} 个</span>}
  </div>;
}

export function ShapeSymbol({ kind }: { kind: string }) {
  return <svg viewBox="0 0 72 72" className="v6-shape-symbol" aria-hidden="true" focusable="false" fill="currentColor" stroke="currentColor" strokeWidth="2">
    {kind === "circle" ? <circle cx="36" cy="36" r="27" /> :
     kind === "triangle" ? <path d="M36 8 66 62H6Z" /> :
     kind === "square" ? <rect x="10" y="10" width="52" height="52" rx="2" /> :
     kind === "rectangle" ? <rect x="3" y="18" width="66" height="36" rx="2" /> :
     <path d="M36 6 64 36 36 66 8 36Z" />}
  </svg>;
}
