"use client";

import { useEffect, useState } from "react";
import { AbilityMap } from "@/src/components";
import { getLearningApi } from "@/src/lib/api";
import type { AbilityState } from "@/src/lib/api/contracts";

export function MathGrowthScreen({ childId }: { childId: string }) {
  const api = getLearningApi();
  const [abilities, setAbilities] = useState<AbilityState[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getAbilities(childId)
      .then(setAbilities)
      .finally(() => setLoading(false));
  }, [api, childId]);

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

        {loading ? (
          <div className="surface-card loading-panel">正在读取能力状态…</div>
        ) : (
          <AbilityMap abilities={abilities} />
        )}
      </div>
    </main>
  );
}
