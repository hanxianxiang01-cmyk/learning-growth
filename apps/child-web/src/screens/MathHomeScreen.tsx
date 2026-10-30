"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getLearningApi } from "@/src/lib/api";
import {
  CHALLENGE_CARDS,
  resolveAbilityId,
  type ChallengeKind
} from "@/src/lib/challengeMapping";
import type {
  AbilityState,
  GuestQuota,
  LearnerProfile
} from "@/src/lib/api/contracts";
import {
  GrowthEntryCard,
  MathTaskCard,
  TodayGoalCard
} from "@/src/components";
import type { LearningApi } from "@/src/lib/api/contracts";

/**
 * bootstrap 去重（10-29 实测修复）：dev 环境 React StrictMode 会双挂载，
 * 两次 effect 都在第一次的 Cookie 到达前发出 bootstrap → 每次开页多造一个
 * 孤儿游客（库中成对出现、时间戳差几十毫秒）。模块级 in-flight Promise 让
 * 同一次页面加载内的重复挂载复用同一个请求；失败时清空以便重试。
 * 刷新页面会重新执行模块 → 新 Promise，但此时已有 Cookie，服务端复用会话。
 */
let bootstrapInFlight: ReturnType<LearningApi["bootstrapGuest"]> | null = null;
function bootstrapOnce(api: LearningApi) {
  if (!bootstrapInFlight) {
    bootstrapInFlight = api.bootstrapGuest().catch(err => {
      bootstrapInFlight = null;
      throw err;
    });
  }
  return bootstrapInFlight;
}

/**
 * 学习首页。
 *
 * V1.4 游客模式：**不再从 URL 取 childId**。
 * 原实现 `searchParams.child_id ?? config.defaultChildId` 有三个问题：
 *   1. 所有人共用同一个 …0001（数据全混在一起）；
 *   2. 改一个 query 参数就能看别人的数据；
 *   3. 该 id 在治理脚本里被标记为「真实孩子」，游客流量会污染它。
 * 现在身份由服务端签发（HttpOnly Cookie），本组件先 bootstrap 再取回自己的 id。
 */
export function MathHomeScreen() {
  const api = getLearningApi();
  const router = useRouter();
  const [childId, setChildId] = useState<string | null>(null);
  const [quota, setQuota] = useState<GuestQuota | null>(null);
  const [profile, setProfile] = useState<LearnerProfile | null>(null);
  const [abilities, setAbilities] = useState<AbilityState[]>([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    // 先 bootstrap 拿身份，再并行取画像与能力。
    // 不能反过来：没有会话时 getProfile 会 401，那会让首屏闪一下错误。
    // 用 bootstrapOnce：StrictMode 双挂载不再各发一次（见模块顶部说明）。
    bootstrapOnce(api)
      .then(async guest => {
        if (!alive) return;
        setChildId(guest.child_id);
        setQuota(guest.quota);
        const [p, a] = await Promise.all([
          api.getProfile(guest.child_id),
          api.getAbilities(guest.child_id)
        ]);
        if (!alive) return;
        setProfile(p);
        setAbilities(a);
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

  const start = async (challenge: ChallengeKind) => {
    if (!childId) return;
    setStarting(true);
    setError(null);
    try {
      const session = await api.createSession({
        child_id: childId,
        subject: "math",
        requested_minutes: 15
      });
      const abilityId = resolveAbilityId(challenge, abilities);
      // 不再把 child_id 拼进 URL——身份在 Cookie 里，URL 里带 id 只是把
      // 「身份可以被写在地址栏里」这件事又请回来了。
      const params = new URLSearchParams();
      if (abilityId) params.set("ability_id", abilityId);
      if (challenge) params.set("challenge", challenge);
      const qs = params.toString();
      router.push(
        `/child/math/session/${session.session_id}${qs ? `?${qs}` : ""}`
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

        {/* 每日额度（方案第五章：达到上限时显示清晰提示，同时仍可查看已有记录） */}
        {quota && (
          <div className="quota-banner" data-testid="guest-quota">
            {quota.exhausted
              ? `今天的 ${quota.limit} 道题已经完成啦，明天再来吧`
              : `今天还可以练 ${quota.remaining} 道题`}
          </div>
        )}

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

          {/* FE-1428：挑战入口改为 CHALLENGE_CARDS 配置表驱动——V2 各能力节点
              先各放一张手工测试入口卡，测试通过后在配置表里增删即可收起/优化。 */}
          <div className="task-grid task-grid-challenge">
            {CHALLENGE_CARDS.map(card => (
              <MathTaskCard
                key={card.kind}
                icon={card.icon}
                title={card.title}
                goal={card.goal}
                minutes={card.minutes}
                difficulty={card.difficulty}
                loading={starting || quota?.exhausted === true}
                onStart={() => start(card.kind)}
              />
            ))}
          </div>
        </section>

        <GrowthEntryCard
          summary={
            profile?.observations?.[0] ??
            "最近正在积累「数量关系」和「检查验证」的学习证据"
          }
          href="/child/math/growth"
        />
      </div>
    </main>
  );
}
