'use client';

import { useEffect, useState, type ReactNode } from 'react';
import { V2_RELEASE_RENDERER_IDS } from '@/src/features/task-renderer/rendererRegistry';
import {
  getOrLockImplementation,
  parseImplementationFlags,
  type ImplementationDecision
} from './implementationPolicy';

/** MIK-A5 review candidate: 16 distinct kernel UI mounts; the three A4
 * high-risk renderers remain legacy until their actual A4 source is supplied.
 * Runtime defaults to legacy. Flags are TaskInstance-pinned.
 */
export const MIK_KERNEL_PILOTS = [
  'number-input','formula-board','ten-frame','grouping-board','money-board',
  'bar-model','array-board','place-value','sorting-board','number-line','ruler',
  'direction-grid','shape-canvas','pattern-board','shape-gallery','estimation-canvas'
] as const;
const allowed = new Set<string>(MIK_KERNEL_PILOTS);

export function TaskRendererImplementationBoundary(props: {
  taskInstanceId: string;
  rendererId: string;
  uiRevision: string;
  legacy: ReactNode;
  kernel: ReactNode;
}) {
  const { taskInstanceId, rendererId, uiRevision, legacy, kernel } = props;
  const [decision, setDecision] = useState<ImplementationDecision | null>(null);

  useEffect(() => {
    let configured: 'kernel' | 'legacy' | undefined;
    try {
      const flags = parseImplementationFlags(
        process.env.NEXT_PUBLIC_MIK_RENDERER_FLAGS ?? '',
        V2_RELEASE_RENDERER_IDS
      );
      configured = flags[rendererId];
    } catch {
      configured = 'legacy'; // invalid deployment config fails closed
    }
    // localStorage getters can throw in sandboxed/opaque origins: fail closed safely.
    let storage: Storage | undefined;
    try { if (typeof window !== 'undefined') storage = window.localStorage; } catch { /* storage unavailable */ }
    const result = getOrLockImplementation({
      identity:{taskInstanceId,rendererId,uiRevision}, configured,
      kernelAvailable:allowed.has(rendererId), storage
    });
    setDecision(result);
  }, [taskInstanceId,rendererId,uiRevision]);

  if (!decision) return <div role="status" className="surface-card">正在准备数学工具…</div>;
  if (!decision.available) return <div role="alert" data-testid="mik-locked-implementation-missing" className="surface-card unsupported-task">
    当前练习使用的交互版本暂时不可用。原题和作答记录没有被自动切换，请稍后重试。
  </div>;
  // No internal flags or technical diagnostics in child-facing text.
  return <div className="mik-implementation-route" data-testid="mik-route" data-mik-implementation={decision.version}>
    {decision.version === 'kernel' ? kernel : legacy}
  </div>;
}
