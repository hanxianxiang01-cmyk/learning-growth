"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getLearningApi } from "@/src/lib/api";
import type { AbilityState, LearnerProfile } from "@/src/lib/api/contracts";
import {
  GrowthEntryCard,
  MathTaskCard,
  TodayGoalCard
} from "@/src/components";

export function MathHomeScreen({ childId }: { childId: string }) {
  const api = getLearningApi();
  const router = useRouter();
  const [profile, setProfile] = useState<LearnerProfile | null>(null);
  const [abilities, setAbilities] = useState<AbilityState[]>([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.getProfile(childId), api.getAbilities(childId)])
      .then(([p, a]) => {
        setProfile(p);
        setAbilities(a);
      })
      .catch(err => setError(err instanceof Error ? err.message : "加载失败"))
      .finally(() => setLoading(false));
  }, [api, childId]);

  const start = async () => {
    setStarting(true);
    setError(null);
    try {
      const session = await api.createSession({
        child_id: childId,
        subject: "math",
        requested_minutes: 15
      });
      router.push(
        `/child/math/session/${session.session_id}?child_id=${encodeURIComponent(childId)}`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建学习会话失败");
      setStarting(false);
    }
  };

  const developingId = profile?.developing?.[0];
  const developing =
    abilities.find(a =>
      a.ability_id === developingId || a.name === developingId
    ) ?? profile?.active_abilities?.[0] ?? abilities[0];

  return (
    <main className="page-shell">
      <div className="page-container">
        <header className="child-header">
          <div>
            <span className="muted">今天也来完成一个数学小任务</span>
            <h1>今天的数学任务</h1>
          </div>
          <div className="header-chip">
            {profile?.grade ?? "2"}年级数学
          </div>
        </header>

        {error && <div className="error-banner">{error}</div>}

        <TodayGoalCard
          title={
            developing?.name
              ? `${developing.level === 0 ? "开始" : "继续"}练习「${developing.name}」`
              : "看懂数量之间的关系"
          }
          tip="先观察，再动手，再检查。"
        />

        <section className="section-block">
          <div className="section-heading">
            <div>
              <span className="eyebrow">今日任务</span>
              <h2>从一个小挑战开始</h2>
            </div>
            <span className="muted">
              {loading ? "正在读取学习状态…" : "建议 10–15 分钟"}
            </span>
          </div>

          <div className="task-grid">
            <MathTaskCard
              icon="🔢"
              title="数量关系挑战"
              goal="通过摆一摆、画一画理解题目关系"
              minutes={8}
              difficulty={2}
              loading={starting}
              onStart={start}
            />
            <MathTaskCard
              icon="🧩"
              title="策略挑战"
              goal="尝试用不同方法解决同一个问题"
              minutes={6}
              difficulty={2}
              loading={starting}
              onStart={start}
            />
          </div>
        </section>

        <GrowthEntryCard
          summary={
            profile?.observations?.[0] ??
            "最近正在积累「数量关系」和「检查验证」的学习证据"
          }
          href={`/child/math/growth?child_id=${encodeURIComponent(childId)}`}
        />
      </div>
    </main>
  );
}
