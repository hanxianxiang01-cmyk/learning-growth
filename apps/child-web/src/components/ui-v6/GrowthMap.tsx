"use client";

import { useEffect, useId, useRef, useState } from "react";
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
    <div className="v6-detail-heading"><span className="v6-ability-emblem"><ChildIcon name={node.icon} /></span><div><h2>{node.label}</h2><p>{node.subtitle}</p></div><span className="v6-level-badge">{value.level}</span></div>
    <p className="v6-detail-description">{node.description}</p>
    <div className="v6-detail-metrics"><div><span><ChildIcon name="layers" />当前等级</span><strong>{value.level}</strong></div><div><span><ChildIcon name="document" />学习证据</span><strong>{value.count ?? "—"}<small>{value.count === null ? "暂无数据" : "条"}</small></strong></div></div>
    <div className="v6-detail-status"><ChildIcon name={value.stable ? "check" : "hint"} /><div><strong>{value.status}</strong><p>{value.description}</p></div></div>
    <button type="button" className="v6-evidence-toggle" aria-expanded={open} aria-controls={id} onClick={() => setOpen(!open)}>查看相关记录<ChildIcon name={open ? "close" : "arrow"} /></button>
    <div id={id} className="v6-evidence-note" hidden={!open}><ChildIcon name="document" /><p>{value.count === null ? "这里还没有能力评价记录。" : value.count === 0 ? "暂时还没有可以展开的练习记录。" : `已有 ${value.count} 条相关证据，本页暂不展示逐条记录。`}</p></div>
    <div className="v6-detail-bottom"><p>回到今天的任务，继续积累自己的数学方法。</p><a className="primary-button" href={`/child/math?child_id=${encodeURIComponent(childId)}`}>去今天的任务<ChildIcon name="arrow" /></a></div>
  </section>;
}

export function GrowthMap({ abilities, childId }: { abilities: AbilityState[]; childId: string }) {
  const [selected, setSelected] = useState(ABILITY_NODES[0].id);
  const [expanded, setExpanded] = useState(false);
  const [paths, setPaths] = useState<string[]>([]);
  const plane = useRef<HTMLDivElement>(null);
  const selectedNode = ABILITY_NODES.find(n => n.id === selected) ?? ABILITY_NODES[0];
  const desktopDetailId = useId();
  useEffect(() => {
    const root = plane.current;
    if (!root) return;
    const draw = () => {
      const rect = root.getBoundingClientRect();
      if (rect.width < 400) { setPaths([]); return; }
      const nodes = Array.from(root.querySelectorAll<HTMLElement>("[data-v6-node]"));
      const points = nodes.map(n => { const r = n.getBoundingClientRect(); return { x: r.left - rect.left + r.width / 2, y: r.top - rect.top + r.height / 2 }; });
      const edges = [[0,1],[0,2],[1,3],[2,4],[3,5],[4,6],[5,6]];
      setPaths(edges.flatMap(([a,b]) => {
        const p = points[a], q = points[b]; if (!p || !q) return [];
        return [`M${p.x},${p.y} C${p.x},${(p.y+q.y)/2} ${q.x},${(p.y+q.y)/2} ${q.x},${q.y}`];
      }));
    };
    draw();
    const observer = new ResizeObserver(draw); observer.observe(root);
    window.addEventListener("resize", draw);
    return () => { observer.disconnect(); window.removeEventListener("resize", draw); };
  }, [abilities, selected, expanded]);
  const hasRecords = ABILITY_NODES.some(n => (findAbility(n, abilities)?.evidence_count ?? 0) > 0);
  return <>
    {!hasRecords && <div className="v6-map-empty-notice"><ChildIcon name="hint" /><div><strong>成长从一次尝试开始</strong><p>先了解七项能力，再慢慢积累自己的学习记录。每一项都可以点开看看。</p></div></div>}
    <div className="v6-growth-shell"><section className="v6-ability-map" aria-label="七项数学能力节点地图">
      <div className="v6-map-micro-heading"><h2>七项能力，各有成长节奏</h2><span><ChildIcon name="eye" />点选查看详情</span></div>
      <div className="v6-map-plane" ref={plane}><svg className="v6-map-links" aria-hidden="true" focusable="false">{paths.map((d, i) => <path key={i} d={d} />)}</svg>
        <ul className="v6-ability-nodes">{ABILITY_NODES.map(node => {
          const ability = findAbility(node, abilities), value = presentAbility(ability), chosen = selected === node.id;
          return <li className="v6-ability-node-wrap" key={node.id} style={nodeStyle(node)}>
            <button type="button" className={`v6-ability-node ${chosen ? "is-selected" : ""}`} data-v6-node={node.id} data-testid={`v6-node-${node.id}`}
              aria-pressed={chosen} aria-label={`${node.label}，${value.level}，${value.count === null ? "暂无数据" : value.count + "条证据"}，查看详情`}
              onClick={() => { setSelected(node.id); setExpanded(chosen ? !expanded : true); }}>
              <span className="v6-ability-emblem"><ChildIcon name={node.icon} /></span><span className="v6-node-copy"><span className="v6-node-name-row"><strong>{node.label}</strong><span className="v6-level-badge">{value.level}</span></span>
                <span className="v6-node-subtitle">{node.subtitle}</span><span className="v6-node-meta"><span className={value.stable ? "is-stable" : ""}><ChildIcon name={value.stable ? "check" : "document"} />{value.status}</span><span>{value.count === null ? "暂无数据" : `${value.count}条证据`}</span></span>
              </span>
            </button>
            {chosen && expanded && <div className="v6-mobile-node-detail"><Detail key={node.id} node={node} ability={ability} childId={childId} /></div>}
          </li>;
        })}</ul>
      </div>
    </section><aside className="v6-map-detail-wide" id={desktopDetailId}><Detail key={selectedNode.id} node={selectedNode} ability={findAbility(selectedNode, abilities)} childId={childId} /></aside></div>
    <p className="v6-map-note"><ChildIcon name="hint" />每一项都可以查看。连接线不表示先后顺序；等级不是完成百分比，也不按练习次数升级。</p>
  </>;
}
