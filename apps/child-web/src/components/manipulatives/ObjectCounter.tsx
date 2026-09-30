"use client";

import { useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import type { ObjectCounterRepresentation } from "@/src/lib/api/contracts";
import { alignObjectCounter, useWorkspace } from "@/src/features/math-workspace";

const clamp = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value));

export function ObjectCounter({ symbolByGroup }: { symbolByGroup: Record<string, string> }) {
  const { state, commit, undo, reset, can } = useWorkspace();
  const representation = state.present;
  const dragRef = useRef<{
    pointerId: number;
    groupId: string;
    itemId: string;
    left: number;
    width: number;
  } | null>(null);
  const [preview, setPreview] = useState<Record<string, number>>({});

  if (representation.type !== "object-counter") return null;

  const updateItem = (groupId: string, itemId: string, x: number) => {
    const next: ObjectCounterRepresentation = {
      ...representation,
      aligned: false,
      groups: representation.groups.map(group =>
        group.id !== groupId
          ? group
          : {
              ...group,
              items: group.items.map(item =>
                item.id === itemId ? { ...item, x } : item
              )
            }
      )
    };
    commit(next, { event_type: "drag", capability_id: "drag", target_id: itemId, payload: { x } });
  };

  return (
    <div className="manipulative-card object-counter" data-testid="object-counter">
      <div className="manipulative-heading">
        <div>
          <strong>摆一摆 · 一一对应</strong>
          <span>拖动小物件，让两组更容易比较。</span>
        </div>
        <div className="workspace-actions">
          <button type="button" disabled={!can("align")} onClick={() => { const next = alignObjectCounter(representation); commit(next, { event_type: "align", capability_id: "align" }); }}>一一对齐</button>
          <button type="button" disabled={!can("undo")} onClick={undo}>撤销</button>
          <button type="button" disabled={!can("reset")} onClick={reset}>重置</button>
        </div>
      </div>

      <div className="object-lanes">
        {representation.groups.map(group => {
          const highlighted = state.highlightedTargets.includes(group.id);
          return (
            <div className={`object-group ${highlighted ? "is-highlighted" : ""}`} key={group.id}>
              <div className="object-group-label">
                <strong>{group.label}</strong>
                <span>{group.count} 个</span>
              </div>
              <div className="object-lane">
                {group.items.map(item => {
                  const x = preview[item.id] ?? item.x;
                  return (
                    <button
                      key={`${group.id}-${item.id}`}
                      type="button"
                      disabled={!can("drag")}
                      className="draggable-token"
                      style={{ left: `calc(${x}% - 19px)` }}
                      aria-label={`${group.label}的第${item.id.split("_item_")[1] ?? item.id}个物件`}
                      onPointerDown={(event: ReactPointerEvent<HTMLButtonElement>) => {
                        const lane = event.currentTarget.parentElement;
                        if (!lane) return;
                        const rect = lane.getBoundingClientRect();
                        dragRef.current = {
                          pointerId: event.pointerId,
                          groupId: group.id,
                          itemId: item.id,
                          left: rect.left,
                          width: rect.width
                        };
                        event.currentTarget.setPointerCapture(event.pointerId);
                      }}
                      onPointerMove={(event: ReactPointerEvent<HTMLButtonElement>) => {
                        const drag = dragRef.current;
                        if (!drag || drag.pointerId !== event.pointerId || drag.itemId !== item.id) return;
                        const nextX = clamp(((event.clientX - drag.left) / drag.width) * 100, 3, 97);
                        setPreview(current => ({ ...current, [item.id]: nextX }));
                      }}
                      onPointerUp={(event: ReactPointerEvent<HTMLButtonElement>) => {
                        const drag = dragRef.current;
                        if (!drag || drag.itemId !== item.id) return;
                        const finalX = clamp(((event.clientX - drag.left) / drag.width) * 100, 3, 97);
                        updateItem(drag.groupId, drag.itemId, finalX);
                        setPreview(current => {
                          const next = { ...current };
                          delete next[item.id];
                          return next;
                        });
                        dragRef.current = null;
                        try { event.currentTarget.releasePointerCapture(event.pointerId); } catch {}
                      }}
                    >
                      {symbolByGroup[group.id] ?? "●"}
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
      <div className="workspace-caption">
        {representation.aligned ? "已经按一一对应对齐。看看哪一组多出来了。" : "可以拖动物件，也可以用“一一对齐”检查关系。"}
      </div>
    </div>
  );
}
