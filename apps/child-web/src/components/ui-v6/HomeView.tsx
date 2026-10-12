"use client";

import type { AbilityState, LearnerProfile } from "@/src/lib/api/contracts";
import { CHALLENGE_CARDS, resolveAbilityId, type ChallengeKind } from "@/src/lib/challengeMapping";
import { ABILITY_NODES, findAbility, presentAbility } from "@/src/features/ui-v6/abilityPresentation";
import { ChildIcon } from "./ChildIcon";
import { HeroArt, PageFrame, PageState } from "./PageFrame";

export function HomeView({ childId, profile, abilities, loading, starting, error, onStart, onReload }: {
  childId: string; profile: LearnerProfile | null; abilities: AbilityState[];
  loading: boolean; starting: boolean; error: string | null;
  onStart: (kind: ChallengeKind) => void; onReload: () => void;
}) {
  const developing = abilities.find(a => a.ability_id === profile?.developing?.[0] || a.name === profile?.developing?.[0]) ?? profile?.active_abilities?.[0] ?? abilities[0];
  const primary = CHALLENGE_CARDS.find(c => resolveAbilityId(c.kind, abilities) === developing?.ability_id) ?? CHALLENGE_CARDS[0];
  const recorded = ABILITY_NODES.filter(n => (findAbility(n, abilities)?.evidence_count ?? 0) > 0).length;
  const disabled = loading || starting;
  const homeTitle = developing?.name ? `来练一练「${developing.name}」` : "从一个数学小任务开始";
  return <PageFrame childId={childId} active="home">
    {loading ? <PageState title="正在准备今天的学习" text="读取你的学习状态，马上就好。" loading /> :
      error && !profile ? <PageState title="学习任务暂时没准备好" text="请稍后重新加载，不会改变你的学习记录。" onRetry={onReload} /> : <>
      <section className="v6-home-hero"><div className="v6-hero-copy"><span className="v6-eyebrow"><ChildIcon name="spark" />今天也来探索一下</span>
        <h1>{homeTitle}</h1><p>用自己的方法，观察、动手，再检查。</p>
        <button type="button" className="primary-button" disabled={disabled} onClick={() => onStart(primary.kind)} data-testid="v6-home-start">{starting ? "正在准备任务…" : "开始今天的学习"}<ChildIcon name="arrow" /></button>
      </div><HeroArt /></section>
      {error && <div className="v6-inline-error" role="alert">这次没有进入学习任务，请再试一次。</div>}
      <div className="v6-home-columns">
        <section className="surface-card v6-home-records"><span className="v6-eyebrow"><ChildIcon name="document" />我的学习状态</span><h2>一点一点，积累好方法</h2>
          <div className="v6-record-count"><strong>{recorded}</strong><span>项能力已有学习记录</span></div>
          <p>{profile?.observations?.[0] ?? "做过的尝试，会成为了解自己的一部分。每一项能力，都有自己的成长节奏。"}</p>
          <div className="v6-home-mini-nodes" aria-label="能力记录概览">{ABILITY_NODES.map(node => {
            const value = presentAbility(findAbility(node, abilities));
            return <span key={node.id} title={`${node.label}：${value.status}`} className={value.count !== null && value.count > 0 ? "has-record" : ""}><ChildIcon name={node.icon} /></span>;
          })}</div>
          <p className="v6-home-record-note">{profile?.grade ? `${profile.grade.replace(/年级$/, "")}年级数学 · ` : ""}建议每次学习 10–15 分钟</p>
        </section>
        <section className="surface-card v6-home-tasks"><div className="v6-section-heading"><h2>选择一个小挑战</h2><span>先选你想练的</span></div>
          <div className="v6-task-list">{CHALLENGE_CARDS.map((card, i) => <button type="button" key={card.kind} className="v6-task-entry"
            data-testid={`v6-home-${card.kind}`} disabled={disabled} onClick={() => onStart(card.kind)}>
            <span className={`v6-task-icon v6-task-icon--${i}`}><ChildIcon name={i === 0 ? "plus" : i === 1 ? "layers" : i === 2 ? "search" : i === 3 ? "flag" : "compass"} /></span>
            <span className="v6-task-entry-copy"><strong>{card.title}</strong><small>{card.goal}</small></span><span className="v6-task-estimate">约 {card.minutes} 分钟</span><ChildIcon name="arrow" />
          </button>)}</div>
        </section>
      </div>
      <a className="v6-map-entry" href={`/child/math/growth?child_id=${encodeURIComponent(childId)}`}><span className="v6-map-entry-icon"><ChildIcon name="map" /></span>
        <span><strong>我的成长地图</strong><small>看看七项能力的当前表现，了解自己的成长。</small></span><ChildIcon name="arrow" /></a>
      </>}
  </PageFrame>;
}
