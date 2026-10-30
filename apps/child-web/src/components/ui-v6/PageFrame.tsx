"use client";

import type { ReactNode } from "react";
import { useChildUi } from "@/src/theme/ChildSkinProvider";
import { ChildIcon } from "./ChildIcon";
import { LearningChrome, LearningScenery } from "./LearningChrome";

export function PageFrame({ childId, active, children }: {
  childId: string; active: "home" | "growth" | "result"; children: ReactNode;
}) {
  return <main className={`page-shell v6-page v6-page--${active}`} data-testid={`v6-${active}-screen`}>
    <LearningScenery />
    <div className="v6-page-container"><LearningChrome childId={childId} active={active} />{children}</div>
  </main>;
}
export function HeroArt() {
  const { skin } = useChildUi();
  return <img src={`/child-ui-v6/hero-${skin}.svg`} className="v6-hero-art" alt="" aria-hidden="true" draggable={false} />;
}
export function PageState({ title, text, loading = false, onRetry, childId }: {
  title: string; text?: string; loading?: boolean; onRetry?: () => void; childId?: string;
}) {
  return <section className="surface-card v6-page-state" role={loading ? "status" : "alert"} aria-busy={loading}>
    <span className="v6-state-symbol"><ChildIcon name={loading ? "clock" : "warning"} /></span>
    <h1>{title}</h1>{text && <p>{text}</p>}
    {loading && <div className="v6-skeleton-stack" aria-hidden="true"><i /><i /><i /></div>}
    <div className="v6-state-actions">{onRetry && <button type="button" className="primary-button" onClick={onRetry}>重新加载<ChildIcon name="reset" /></button>}
      {childId && <a className="v6-secondary-link" href={`/child/math?child_id=${encodeURIComponent(childId)}`}>返回今日学习</a>}</div>
  </section>;
}
