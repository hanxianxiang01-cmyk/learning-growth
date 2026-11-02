"use client";

import { useId, useState } from "react";
import type { CSSProperties } from "react";
import type { AbilityState } from "@/src/lib/api/contracts";
import { ABILITY_NODES, findAbility, presentAbility, type AbilityNode } from "@/src/features/ui-v6/abilityPresentation";
import { ChildIcon } from "./ChildIcon";

function nodeStyle(node: AbilityNode): CSSProperties {
  return { "--node-ink": node.color, "--node-soft": node.soft } as CSSProperties;
}

function Detail({ node, ability, childId }: { node: AbilityNode; ability?: AbilityState; childId: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const value = presentAbility(ability);
  return <section className="v6-ability-detail" style={nodeStyle(node)} aria-label={`${node.label}的详情`} data-testid="v6-ability-detail">
    <div className="v6-detail-heading"><span className="v6-ability-emblem"><ChildIcon name={node.icon} /></span><div><h2>{node.label}</h2><p>{node.subtitle}</p></div>
      {/* 没有证据时不挂等级徽章：L0 读起来就是「评级」，而这里只是还没有记录。 */}
      {value.level ? <span className="v6-level-badge">{value.level}</span> : <span className="v6-explore-tag">{value.tag}</span>}
    </div>
    <p className="v6-detail-description">{node.description}</p>
    <div className="v6-detail-metrics"><div><span><ChildIcon name="layers" />当前等级</span><strong>{value.level || "—"}</strong></div>
      <div><span><ChildIcon name="document" />学习证据</span><strong>{value.count ?? "—"}{value.count !== null && <small>条</small>}</strong></div></div>
    <div className="v6-detail-status"><ChildIcon name={value.stable ? "check" : "hint"} /><div><strong>{value.status}</strong><p>{value.description}</p></div></div>
    <button type="button" className="v6-evidence-toggle" aria-expanded={open} aria-controls={id} onClick={() => setOpen(!open)}>查看相关记录<ChildIcon name={open ? "close" : "arrow"} /></button>
    <div id={id} className="v6-evidence-note" hidden={!open}><ChildIcon name="document" /><p>{value.count === null ? "这里还没有能力评价记录。" : value.count === 0 ? "暂时还没有可以展开的练习记录。" : `已有 ${value.count} 条相关证据，本页暂不展示逐条记录。`}</p></div>
    <div className="v6-detail-bottom"><p>回到今天的任务，继续积累自己的数学方法。</p><a className="primary-button" href={`/child/math?child_id=${encodeURIComponent(childId)}`}>去今天的任务<ChildIcon name="arrow" /></a></div>
  </section>;
}

/** 摘要只放一行数字 + 一句口径。放不进标题行就换行，绝不在请求没回来时先写 0/7
 *  （V1.4 设计 G-05：加载中把未知说成 0，是最常见的「假数据」）。 */
export function GrowthSummary({ abilities }: { abilities: AbilityState[] }) {
  const explored = ABILITY_NODES.filter(n => (findAbility(n, abilities)?.evidence_count ?? 0) > 0).length;
  return <div className="v6-growth-summary" data-testid="v6-growth-summary">
    {/* 环的长度按真实计数算，不做「看起来很努力」的固定弧度。 */}
    <div className="v6-growth-ring" style={{ "--ring": `${(explored / ABILITY_NODES.length * 100).toFixed(2)}%` } as CSSProperties} aria-hidden="true"><i className="v6-ring-track" /><strong>{explored}<small>/7</small></strong></div>
    <div className="v6-growth-summary-copy"><strong>已探索 {explored} 项能力</strong>
      <span>{explored === 0 ? "开始学习后，这里会记录你的探索与进步。" : "留下过学习记录才会算一项，它不是掌握等级。"}</span></div>
  </div>;
}

/**
 * 成长地图 = 一段真实摘要 + 七行能力列表。
 *
 * 改成列表不是为了「更好看」：原先的节点地图在手机上要两列磁贴才能一屏放下，
 * 而七项能力之间并没有先修关系，连线会让孩子误以为要按顺序解锁。
 * 现在每行只回答一件事——这项我练过没有（尚待探索 / 真实状态），点开才看细节。
 */
export function GrowthMap({ abilities, childId }: { abilities: AbilityState[]; childId: string }) {
  // 默认不选中任何一项。默认高亮第一项等于系统在替孩子推荐能力（V1.4 设计 G-04），
  // 而七项之间没有先后；空着反而把选择权留给孩子。
  const [openId, setOpenId] = useState<string | null>(null);
  const openedNode = openId ? ABILITY_NODES.find(n => n.id === openId) ?? null : null;
  return <>
    <div className="v6-growth-shell"><section className="v6-ability-map" aria-label="七项数学能力探索进展" data-testid="v6-growth-abilities">
      <div className="v6-ability-list-head"><h2>七项能力 · 探索进展</h2><span><ChildIcon name="eye" />点开看看</span></div>
      <ul className="v6-ability-rows">{ABILITY_NODES.map(node => {
        const ability = findAbility(node, abilities);
        const value = presentAbility(ability);
        const open = openId === node.id;
        return <li className="v6-ability-row-wrap" key={node.id} style={nodeStyle(node)}>
          <button type="button" className={`v6-ability-row ${open ? "is-open" : ""}`} data-testid={`v6-ability-row-${node.id}`}
            aria-expanded={open} aria-label={`${node.label}，${value.tag}，查看详情`}
            onClick={() => setOpenId(open ? null : node.id)}>
            <span className="v6-ability-emblem"><ChildIcon name={node.icon} /></span>
            <span className="v6-row-copy"><strong>{node.label}</strong><small>{node.subtitle}</small></span>
            <span className={`v6-explore-tag ${value.explored ? "has-record" : ""}`}>{value.tag}</span>
            <ChildIcon name="arrow" />
          </button>
          {open && <div className="v6-mobile-node-detail"><Detail key={node.id} node={node} ability={ability} childId={childId} /></div>}
        </li>;
      })}</ul>
    </section>
    <aside className="v6-map-detail-wide">
      {openedNode
        ? <Detail key={openedNode.id} node={openedNode} ability={findAbility(openedNode, abilities)} childId={childId} />
        : <div className="v6-detail-placeholder" data-testid="v6-detail-placeholder">
          <span className="v6-ability-emblem"><ChildIcon name="eye" /></span>
          <h2>想先看哪一项？</h2>
          <p>七项能力没有先后顺序，点左边的任意一项，这里会显示它的说明和学习记录。</p>
        </div>}
    </aside></div>
    <p className="v6-map-note"><ChildIcon name="hint" />「已探索」只表示这项留下了学习记录，不代表掌握程度；等级也不是完成百分比，不按练习次数升级。</p>
  </>;
}
