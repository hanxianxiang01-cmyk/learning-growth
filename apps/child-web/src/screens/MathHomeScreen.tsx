"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { getLearningApi } from "@/src/lib/api";
import {
  CHALLENGE_CARDS,
  resolveAbilityId,
  type ChallengeKind
} from "@/src/lib/challengeMapping";
import type { AbilityState, GuestQuota, LearnerProfile } from "@/src/lib/api/contracts";
import {
  GrowthEntryCard,
  MathTaskCard,
  TodayGoalCard
} from "@/src/components";

import { useChildUi } from "@/src/theme/ChildSkinProvider";
import { HomeView } from "@/src/components/ui-v6/HomeView";
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

export function MathHomeScreen() {
  const { uiVersion } = useChildUi();
  const startLock = useRef(false);
  const [reload, setReload] = useState(0);
  const api = getLearningApi();
  const router = useRouter();
  const [profile, setProfile] = useState<LearnerProfile | null>(null);
  const [abilities, setAbilities] = useState<AbilityState[]>([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // V1.4 游客模式（从主分支移植）：身份由 bootstrap 现场签发。
  // 用 state 而非 ref 存 childId——没有 id 就发请求会 401，
  // 用户看到「这一步暂时没有完成」但他什么都没做错。
  const [childId, setChildId] = useState<string | null>(null);
  // V1.4 每日配额：bootstrap 一次就带回来了，之前只取了 child_id 丢掉 quota，
  // 导致 V6 首页看不到"今日剩余 N 题"。产品规则是每日 30 题，孩子需要看见。
  const [quota, setQuota] = useState<GuestQuota | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    setProfile(null);
    setAbilities([]);
    bootstrapOnce(api)
      .then(g => {
        if (!active) return null;
        setChildId(g.child_id);
        setQuota(g.quota);
        return Promise.all([api.getProfile(g.child_id), api.getAbilities(g.child_id)]);
      })
      .then(res => {
        if (!active || !res) return;
        const [p, a] = res;
        setProfile(p);
        setAbilities(a);
      })
      .catch(err => { if (active) setError(err instanceof Error ? err.message : "加载失败"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [api, reload]);

  const start = async (challenge: ChallengeKind) => {
    if (startLock.current || loading || !childId) return;
    startLock.current = true;
    // FE-1428：challenge 即卡片 kind；能力解析走 challengeMapping（关键词优先，app_* 兜底）
    setStarting(true);
    setError(null);
    try {
      const session = await api.createSession({
        child_id: childId,
        subject: "math",
        requested_minutes: 15
      });
      const abilityId = resolveAbilityId(challenge, abilities);
      const params = new URLSearchParams();
      if (abilityId) params.set("ability_id", abilityId);
      if (challenge) params.set("challenge", challenge);
      router.push(
        `/child/math/session/${session.session_id}?${params.toString()}`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建学习会话失败");
      startLock.current = false;
      setStarting(false);
    }
  };

  const developingId = profile?.developing?.[0];
  const developing =
    abilities.find(a =>
      a.ability_id === developingId || a.name === developingId
    ) ?? profile?.active_abilities?.[0] ?? abilities[0];

  // 游客身份还没签发（bootstrap 进行中或失败）：先给加载/错误面板。
  // 没有 id 就渲染会把 null 传进链接与请求，产生 401 假失败。
  if (!childId) {
    return (
      <main className="page-shell">
        <div className="page-container">
          {error ? (
            <div className="error-banner">
              {error}
              <button type="button" onClick={() => setReload(n => n + 1)}>重新加载</button>
            </div>
          ) : (
            <div className="surface-card loading-panel">正在准备入学…</div>
          )}
        </div>
      </main>
    );
  }

  if (uiVersion === "v6") return <HomeView childId={childId} profile={profile} abilities={abilities} quota={quota}
    loading={loading} starting={starting} error={error} onStart={start} onReload={() => setReload(n => n + 1)} />;

  return (
    <main className="page-shell">
      <div className="page-container">
        <header className="child-header">
          <div>
            <span className="muted">今天也来完成一个数学小任务</span>
            <h1>今天的数学任务</h1>
          </div>
          <div className="header-chip">
            {/* FE-1446：grade 口径兼容——库里存中文全称（"一年级"），mock/契约示例是数字（"2"）；
              原拼接对前者产出"一年级年级数学"。剥掉尾缀"年级"再拼。 */}
          {`${(profile?.grade ?? "2").replace(/年级$/, "")}年级数学`}
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
                loading={starting}
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
