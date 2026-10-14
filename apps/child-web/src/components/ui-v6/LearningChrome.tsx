"use client";

import { ChildIcon } from "./ChildIcon";
import { useChildUi } from "@/src/theme/ChildSkinProvider";

export function LearningChrome({ childId, completed, active }: {
  childId: string; completed?: number; active?: "home" | "growth" | "result";
}) {
  const home = `/child/math?child_id=${encodeURIComponent(childId)}`;
  return <header className="v6-learning-header">
    <a href={home} className="v6-brand"><span className="v6-brand-icon"><ChildIcon name="spark" /></span><strong>数学探索</strong></a>
    {completed !== undefined && <span className="v6-task-position" aria-label={`本次已完成${completed}道题`}>本次已完成 {completed} 道</span>}
    <nav aria-label="学习导航"><a href={home} aria-current={active === "home" ? "page" : undefined}><ChildIcon name="book" />今日学习</a>
      <a href={`/child/math/growth?child_id=${encodeURIComponent(childId)}`} aria-current={active === "growth" ? "page" : undefined}><ChildIcon name="map" />我的成长地图</a></nav>
  </header>;
}

/** Decorative SVG extracted from the supplied V6 reference. All data/text remain React-owned. */
export function LearningScenery() {
  const { skin } = useChildUi();
  return <img className="v6-learning-scenery" src={`/child-ui-v6/scenery-${skin}.svg`} alt="" aria-hidden="true" draggable={false} />;
}
