"use client";

import type { AbilityState, GuestActivity, LearnerProfile } from "@/src/lib/api/contracts";
import { CHALLENGE_CARDS, resolveAbilityId, type ChallengeKind } from "@/src/lib/challengeMapping";
import { ABILITY_NODES, findAbility, presentAbility } from "@/src/features/ui-v6/abilityPresentation";
import { planToday } from "@/src/features/ui-v6/dailyPlan";
import { ChildIcon } from "./ChildIcon";
import { HeroArt, PageFrame, PageState } from "./PageFrame";

export function HomeView({ childId, profile, abilities, activity, loading, starting, error, onStart, onReload }: {
  childId: string; profile: LearnerProfile | null; abilities: AbilityState[];
  activity: GuestActivity | null;
  loading: boolean; starting: boolean; error: string | null;
  onStart: (kind: ChallengeKind) => void; onReload: () => void;
}) {
  const developing = abilities.find(a => a.ability_id === profile?.developing?.[0] || a.name === profile?.developing?.[0]) ?? profile?.active_abilities?.[0] ?? abilities[0];
  const plan = planToday(abilities, profile, a => {
    const node = ABILITY_NODES.find(n => n.id === a.ability_id || n.aliases.includes(a.ability_id));
    return node?.label ?? a.name ?? a.ability_id;
  });
  // 主按钮优先跟着「今天该练什么」走；计划为空（无能力数据）时回落到原来的第一张卡。
  const primary = CHALLENGE_CARDS.find(c => resolveAbilityId(c.kind, abilities) === plan.primary?.abilityId)
    ?? CHALLENGE_CARDS.find(c => resolveAbilityId(c.kind, abilities) === developing?.ability_id)
    ?? CHALLENGE_CARDS[0];
  const recorded = ABILITY_NODES.filter(n => (findAbility(n, abilities)?.evidence_count ?? 0) > 0).length;
  const disabled = loading || starting;
  // 标题必须与「今天的安排」同一个来源：同一屏出现「来练一练数量关系」和
  // 「先练迁移变式」两句话，孩子不知道该听谁的。有安排就跟安排。
  const focusName = plan.primary?.label ?? developing?.name;
  const homeTitle = focusName ? `来练一练「${focusName}」` : "从一个数学小任务开始";
  return <PageFrame childId={childId} active="home">
    {loading ? <PageState title="正在准备今天的学习" text="读取你的学习状态，马上就好。" loading /> :
      error && !profile ? <PageState title="学习任务暂时没准备好" text="请稍后重新加载，不会改变你的学习记录。" onRetry={onReload} /> : <>
      <section className="v6-home-hero"><div className="v6-hero-copy"><span className="v6-eyebrow"><ChildIcon name="spark" />今天也来探索一下</span>
        <h1>{homeTitle}</h1><p>用自己的方法，观察、动手，再检查。</p>
        <button type="button" className="primary-button" disabled={disabled} onClick={() => onStart(primary.kind)} data-testid="v6-home-start">{starting ? "正在准备任务…" : "开始今天的学习"}<ChildIcon name="arrow" /></button>
      </div><HeroArt /></section>
      {error && <div className="v6-inline-error" role="alert">这次没有进入学习任务，请再试一次。</div>}
      {/*
        「今天的安排」按已有学习证据给，不是固定题数配额。
        以前这里是「今天还可以练 30 道题」——每天 30 题的硬限制已于 2026-11-01 取消，
        孩子想多练不会再被挡住；这里只说明建议练哪一项、练几个小任务。
      */}
      {plan.primary && <section className="v6-home-plan" data-testid="v6-home-plan">
        <span className="v6-home-plan-eyebrow"><ChildIcon name="compass" />今天的安排</span>
        <p className="v6-home-plan-line">
          先练<strong>「{plan.primary.label}」</strong>
          <span className="v6-home-plan-dot" aria-hidden="true">·</span>
          {plan.taskCount} 个小任务
          <span className="v6-home-plan-dot" aria-hidden="true">·</span>
          约 {plan.minutes} 分钟
        </p>
        <p className="v6-home-plan-reason">{plan.primary.reason}</p>
      </section>}
      <div className="v6-home-columns">
        <section className="surface-card v6-home-records"><span className="v6-eyebrow"><ChildIcon name="document" />我的学习状态</span>
          {/* 一条记录都没有时，七格灰点只是噪音：换成一句鼓励 + 树苗，不写「0 项」这种像成绩单的话。 */}
          {recorded === 0
            ? <div className="v6-home-empty" data-testid="v6-home-empty">
              <img src="/child-ui-v6/sprout.svg" alt="" aria-hidden="true" draggable={false} />
              <div><strong>你的数学探索才刚刚开始</strong><p>完成第一个小任务，就能留下第一条成长记录。</p></div>
            </div>
            : <>
              <h2>一点一点，积累好方法</h2>
              <div className="v6-record-count"><strong>{recorded}</strong><span>项能力已有学习记录</span></div>
              <p>{profile?.observations?.[0] ?? "做过的尝试，会成为了解自己的一部分。每一项能力，都有自己的成长节奏。"}</p>
              <div className="v6-home-mini-nodes" aria-label="能力记录概览">{ABILITY_NODES.map(node => {
                const value = presentAbility(findAbility(node, abilities));
                return <span key={node.id} title={`${node.label}：${value.status}`} className={value.explored ? "has-record" : ""}><ChildIcon name={node.icon} /></span>;
              })}</div>
            </>}
          {/* 真实作答数只作记录：它说明「今天动过手」，不代表掌握程度。 */}
          {/* 不再显示年级：题库没有年级字段、选题也不按年级过滤，宣称一个年级
              等于对家长做了一个系统并不支持的事实陈述。设计包 V1.4 也没有这句。 */}
          <p className="v6-home-record-note" data-testid="v6-home-answered">
            {activity && activity.answered_today > 0 ? `今天已经答了 ${activity.answered_today} 道题 · ` : ""}
            建议每次学习 10–15 分钟
          </p>
        </section>
        <section className="surface-card v6-home-tasks"><div className="v6-section-heading"><h2>我想自己选 · 自由探索</h2><span>点一个开始</span></div>
          <p className="v6-section-sub">从下面的小挑战中，选择一个你感兴趣的开始。它不会替代今天的安排。</p>
          <div className="v6-task-grid">{CHALLENGE_CARDS.map((card, i) => <button type="button" key={card.kind} className="v6-task-tile"
            data-testid={`v6-home-${card.kind}`} disabled={disabled} onClick={() => onStart(card.kind)}>
            <span className={`v6-task-tile-icon v6-task-icon--${i}`}><ChildIcon name={i === 0 ? "plus" : i === 1 ? "layers" : i === 2 ? "search" : i === 3 ? "flag" : "compass"} /></span>
            <strong>{card.tileTitle}</strong><small>{card.tileGoal}</small>
          </button>)}</div>
        </section>
      </div>
      {/* 「我的成长地图」入口在页头导航里已有，底部不再重复一张同功能大卡。 */}
      </>}
  </PageFrame>;
}
