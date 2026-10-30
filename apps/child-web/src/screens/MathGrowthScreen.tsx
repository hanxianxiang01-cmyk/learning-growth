"use client";

import { useEffect, useState } from "react";
import { AbilityMap } from "@/src/components";
import { getLearningApi } from "@/src/lib/api";
import type { AbilityState } from "@/src/lib/api/contracts";

/**
 * 成长地图。
 *
 * V1.4 游客模式：childId 不再由外部传入（URL 参数已移除），改为在组件内
 * `/v1/guest/me` 取回当前游客身份。服务端仍会校验归属——本组件拿到的 id
 * 一定是自己的，因为它是服务端从 Cookie 解析出来的，不是我们传进去的。
 */
export function MathGrowthScreen() {
  const api = getLearningApi();
  const [abilities, setAbilities] = useState<AbilityState[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    api
      .getGuest()
      .then(guest => api.getAbilities(guest.child_id))
      .then(a => {
        if (alive) setAbilities(a);
      })
      .catch(err => {
        if (alive) setError(err instanceof Error ? err.message : "加载失败");
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [api]);

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
          <a className="text-link" href="/child/math">
            ← 返回首页
          </a>
        </header>

        {error && <div className="error-banner">{error}</div>}

        {loading ? (
          <div className="surface-card loading-panel">正在读取能力状态…</div>
        ) : (
          <AbilityMap abilities={abilities} />
        )}
      </div>
    </main>
  );
}