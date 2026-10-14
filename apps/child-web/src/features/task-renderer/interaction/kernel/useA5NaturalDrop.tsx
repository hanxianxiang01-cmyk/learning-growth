"use client";

/**
 * A5 integration candidate for apps/child-web/src/features/task-renderer/interaction/kernel/.
 * Uses a standalone pointer coordinator because SAFE-01 archive omits the historic A4 hook.
 * Must be checked by actual React/Next build before enabling in production.
 * The caller owns hit testing, domain state, existing event emission and reducer.
 */
import { useCallback, useEffect, useRef, type PointerEvent } from "react";
import { useKernelPointerGesture } from "./useKernelPointerGesture";
import {
  resolveNaturalIntent,
  type A5Context,
  type A5Intent,
  type DomainCommand,
  type A5Resolution
} from "./naturalIntent";

type ClientPoint = Readonly<{ x: number; y: number }>;
type A5PointerOptions<TSource> = {
  context: A5Context;
  /** Source captured at gesture start; must be an actual visible rendered object. */
  toIntent: (source: TSource, point: ClientPoint) => A5Intent | null;
  /** Domain-driven preflight; do not approximate correctness with the answer key. */
  canApply: (command: DomainCommand) => boolean;
  /** Exactly one existing domain action, reducer commit and native event. */
  onDomainCommand: (command: DomainCommand) => void;
  onResolution?: (status: A5Resolution) => void;
};

/**
 * Apply only to a specific draggable element. Do NOT also attach an onClick
 * that commits the same action: PointerUp may synthesize a click.
 * UI CSS must set touch-action:none on the draggable element only.
 */
export function useA5NaturalDrop<TSource>(opts: A5PointerOptions<TSource>) {
  const optsRef = useRef(opts);
  optsRef.current = opts;
  const start = useRef<{ source: TSource; pointerId: number; task: string; rev: string | number } | null>(null);
  const gesture = useKernelPointerGesture<ClientPoint, DomainCommand>(cmd =>
    optsRef.current.onDomainCommand(cmd)
  );
  const gestureRef = useRef(gesture);
  gestureRef.current = gesture;

  const cancel = useCallback((id?: number) => {
    gestureRef.current.cancelPointer(id);
    if (id === undefined || start.current?.pointerId === id) start.current = null;
  }, []);

  useEffect(() => {
    cancel();
  }, [opts.context.taskInstanceId, opts.context.uiRevision, opts.context.disabled, cancel]);

  const getPointerProps = (source: TSource) => ({
    onPointerDown: (event: PointerEvent<HTMLElement>) => {
      const c = optsRef.current.context;
      if (c.disabled || event.button !== 0 || start.current) return;
      const point: ClientPoint = { x: event.clientX, y: event.clientY };
      if (!gestureRef.current.beginPointer(event.pointerId, point)) return;
      start.current = { source, pointerId: event.pointerId, task: c.taskInstanceId, rev: c.uiRevision };
      try { event.currentTarget.setPointerCapture(event.pointerId); }
      catch { cancel(event.pointerId); }
    },
    onPointerMove: (event: PointerEvent<HTMLElement>) => {
      if (start.current?.pointerId !== event.pointerId) return;
      gestureRef.current.movePointer(event.pointerId, { x: event.clientX, y: event.clientY });
    },
    onPointerUp: (event: PointerEvent<HTMLElement>) => {
      const active = start.current;
      if (!active || active.pointerId !== event.pointerId) return;
      const options = optsRef.current;
      const c = options.context;
      const point = { x: event.clientX, y: event.clientY };
      let resolution: A5Resolution = { status: 'cancelled', reason: 'task-invalidated' };
      try {
        gestureRef.current.finishPointer(event.pointerId, point, p => {
          if (c.taskInstanceId !== active.task || c.uiRevision !== active.rev) return null;
          resolution = resolveNaturalIntent(options.toIntent(active.source, p), c);
          if (resolution.status !== 'ready') return null;
          if (!options.canApply(resolution.command)) {
            resolution = { status: 'blocked', reason: 'existing-domain-preflight-rejected' };
            return null;
          }
          return resolution.command;
        });
        options.onResolution?.(resolution);
      } finally {
        start.current = null;
        if (event.currentTarget.hasPointerCapture(event.pointerId)) {
          event.currentTarget.releasePointerCapture(event.pointerId);
        }
      }
    },
    onPointerCancel: (event: PointerEvent<HTMLElement>) => cancel(event.pointerId),
    onLostPointerCapture: (event: PointerEvent<HTMLElement>) => cancel(event.pointerId)
  });

  /** Semantic keyboard action; caller handles Enter/Space and key-repeat policy. */
  const commitAccessible = useCallback((intent: A5Intent): A5Resolution => {
    const opts = optsRef.current;
    const resolution = resolveNaturalIntent(intent, { ...opts.context, modality: 'accessible-control' });
    if (resolution.status !== 'ready') return resolution;
    if (!opts.canApply(resolution.command)) {
      return { status: 'blocked', reason: 'existing-domain-preflight-rejected' };
    }
    opts.onDomainCommand(resolution.command);
    return resolution;
  }, []);

  return { getPointerProps, commitAccessible, cancelPointer: cancel, preview: gesture.preview };
}
