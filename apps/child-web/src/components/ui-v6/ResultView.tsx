"use client";

import type { SessionResult } from "@/src/lib/api/contracts";
import { ABILITY_NODES } from "@/src/features/ui-v6/abilityPresentation";
import { ChildIcon } from "./ChildIcon";
import { HeroArt, PageFrame, PageState } from "./PageFrame";

function safeCount(value: number | undefined): string {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 ? String(value) : "—";
}
function level(value: number | undefined) {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 ? `L${value}` : "待了解";
}
/** Official results and local fallback records must never be presented as equivalent evidence. */
export function ResultView({ childId, result, status, errorMessage, onReload }: {
  childId: string; result: SessionResult | null; status: "loading" | "success" | "fallback" | "error";
  errorMessage: string | null; onReload: () => void;
}) {
  const home = `/child/math?child_id=${encodeURIComponent(childId)}`;
  if (status === "loading") return <PageFrame childId={childId} active="result"><PageState loading title="正在整理这次学习" text="看看你留下了哪些尝试和记录。" /></PageFrame>;
  if (!result) return <PageFrame childId={childId} active="result"><PageState title="暂时没有拿到学习小结" text={errorMessage ?? "请稍后重新加载。"} childId={childId} onRetry={onReload} /></PageFrame>;
  const provisional = status === "fallback";
  const completed = result.status === "completed";
  const elapsed = Number.isFinite(result.duration_ms) && result.duration_ms > 0
    ? `${Math.max(1, Math.round(result.duration_ms / 60_000))}` : "—";
  const href = result.next_recommendation?.href;
  // Only app-internal navigation is rendered; no open redirect or script URL from data.
  const nextHref = typeof href === "string" && /^\/child\/math(?:[/?]|$)/.test(href) && !href.includes("\\") ? href : home;
  return <PageFrame childId={childId} active="result">
    <section className="v6-result-hero"><div><span className="v6-eyebrow"><ChildIcon name="spark" />本次学习小结</span>
      <h1>{provisional ? "先看看本机的学习记录" : completed ? "这次探索，告一段落" : "看看这次留下的记录"}</h1>
      <p>{provisional ? "正式记录暂未加载，这里不显示能力评价。" : "不只看对错，也看你怎样观察、尝试和检查。"}</p></div><HeroArt /></section>
    {provisional && <section className="v6-provisional" role="status"><ChildIcon name="warning" /><div><strong>本机临时记录 · 不是正式学习结果</strong><p>{errorMessage}</p></div><button type="button" onClick={onReload}>重新获取正式结果</button></section>}
    <section className="v6-result-stats" aria-label="本次学习数据">{[
      ["学习时长", elapsed, "分钟"], ["完成任务", safeCount(result.completed_count), "题"],
      ["作答尝试", safeCount(result.attempt_count), "次"], ["提示记录", result.hint_usage.length
        ? Array.from(new Set(result.hint_usage)).map(n => `第${n}级`).join("、") : "未使用", ""]]
      .map(([label, value, unit]) => <div className="surface-card" key={label}><span>{label}</span><strong>{value}<small>{unit}</small></strong></div>)}</section>
    <div className="v6-result-columns"><section className="surface-card v6-result-behaviors"><span className="v6-eyebrow"><ChildIcon name="check" />学习的方法</span><h2>{provisional ? "临时尝试记录" : "值得留意的小行动"}</h2>
      {provisional ? <p>本机保存了 {safeCount(result.attempt_count)} 次尝试。行为评价和能力变化以重新获取的正式结果为准。</p> :
       result.learning_behaviors.length ? <ul>{result.learning_behaviors.map(item => <li key={item.code} className={item.achieved ? "achieved" : "not-observed"}><span><ChildIcon name={item.achieved ? "check" : "eye"} /></span><div><strong>{item.label}</strong><small>{item.achieved ? "本次已记录" : "本次暂未记录，不代表你不会"}</small></div></li>)}</ul> :
       <p>本次结果没有返回行为明细，继续保留自己的思考过程。</p>}
    </section><section className="surface-card v6-result-growth"><span className="v6-eyebrow"><ChildIcon name="map" />能力记录</span><h2>成长，藏在方法里</h2>
      {!provisional && result.ability_changes.length ? <div className="v6-result-changes">{result.ability_changes.map(item => {
        const node = ABILITY_NODES.find(n => n.id === item.ability_id || n.aliases.includes(item.ability_id));
        return <article key={item.ability_id}><span className="v6-change-icon"><ChildIcon name={node?.icon ?? "layers"} /></span><div><h3>{item.name ?? node?.label ?? item.ability_id}</h3>
          <p>{item.before_level !== undefined ? `${level(item.before_level)} → ${level(item.after_level)}` : `当前 ${level(item.after_level)}`}</p>
          <small>{item.evidence_delta === undefined ? "以正式能力记录为准" : `本次证据变化：${item.evidence_delta > 0 ? "+" : ""}${item.evidence_delta} 条`}</small></div></article>;
      })}</div> : <div className="v6-result-no-change"><ChildIcon name="layers" /><p>{provisional ? "正式记录加载成功后，再查看能力变化。" : "本次没有返回能力变化记录。一次练习不一定带来等级变化。"}</p></div>}
      <a className="v6-secondary-link" href={`/child/math/growth?child_id=${encodeURIComponent(childId)}`}>查看完整成长地图<ChildIcon name="arrow" /></a>
    </section></div>
    <section className="v6-next-task"><div><span className="v6-eyebrow">接下来</span><h2>{result.next_recommendation?.title ?? "回到今天的任务"}</h2><p>{result.next_recommendation?.description ?? "按自己的节奏，继续一个小挑战，也可以先休息一下。"}</p></div><a className="primary-button" href={nextHref}>继续探索<ChildIcon name="arrow" /></a></section>
  </PageFrame>;
}
