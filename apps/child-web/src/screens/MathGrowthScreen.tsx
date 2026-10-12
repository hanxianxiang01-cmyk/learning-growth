"use client";

import { useEffect, useState } from "react";
import { AbilityMap } from "@/src/components";
import { getLearningApi } from "@/src/lib/api";
import type { AbilityState } from "@/src/lib/api/contracts";

import { useChildUi } from "@/src/theme/ChildSkinProvider";
import { GrowthMap } from "@/src/components/ui-v6/GrowthMap";
import { PageFrame, PageState } from "@/src/components/ui-v6/PageFrame";
import { ChildIcon } from "@/src/components/ui-v6/ChildIcon";

export function MathGrowthScreen({ childId }: { childId: string }) {
  const { uiVersion } = useChildUi();
  const [error, setError] = useState(false);
  const [reload, setReload] = useState(0);
  const api = getLearningApi();
  const [abilities, setAbilities] = useState<AbilityState[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true); setError(false); setAbilities([]);
    api.getAbilities(childId)
      .then(data => { if (active) setAbilities(data); })
      .catch(() => { if (active) setError(true); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [api, childId, reload]);

  if (uiVersion === "v6") return <PageFrame childId={childId} active="growth">
    <header className="v6-growth-heading"><span className="v6-eyebrow"><ChildIcon name="map" />我的成长记录</span><h1>数学成长地图</h1><p>看看自己会了什么，也看看下一步可以怎么探索。</p></header>
    {loading ? <PageState loading title="正在读取成长记录" text="每一项能力，都有自己的成长节奏。" /> :
      error ? <PageState title="成长记录暂时没加载成功" text="这不会改变已有记录，请稍后重新试试。" onRetry={() => setReload(n => n + 1)} childId={childId} /> :
      <GrowthMap abilities={abilities} childId={childId} />}
  </PageFrame>;

  return (
    <main className="page-shell">
      <div className="page-container">
        <header className="section-heading">
          <div>
            <span className="eyebrow">成长地图</span>
            <h1>数学能力正在怎么长</h1>
            <p className="muted">
              这里记录你最近在不同数学能力上的成长。
            </p>
          </div>
          <a className="text-link" href={`/child/math?child_id=${encodeURIComponent(childId)}`}>
            ← 返回首页
          </a>
        </header>

        {error ? <div className="surface-card" role="alert">成长记录暂时没有加载成功。<button type="button" onClick={() => setReload(n => n + 1)}>重新加载</button></div> : loading ? (
          <div className="surface-card loading-panel">正在读取能力状态…</div>
        ) : (
          <AbilityMap abilities={abilities} />
        )}
      </div>
    </main>
  );
}
