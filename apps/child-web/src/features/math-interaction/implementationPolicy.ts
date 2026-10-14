/** MIK SPIKE only: implementation selection, not a new Renderer or learning policy.
 * Only public/non-sensitive routing metadata is stored; never store an answer.
 * Default legacy; explicit kernel opt-in by renderer ID.
 */
export type RendererImplementation = 'legacy' | 'kernel';
export type TaskImplementationIdentity = {
  taskInstanceId: string;
  rendererId: string;
  uiRevision: string;
};
export type ImplementationLock = TaskImplementationIdentity & {
  version: RendererImplementation;
  selectedAt: number;
};
export type KeyValueStorage = Pick<Storage, 'getItem' | 'setItem'>;
export type ImplementationDecision = {
  version: RendererImplementation;
  reason: 'flag_default_legacy' | 'flag_kernel' | 'flag_legacy' | 'kernel_unavailable' | 'pinned' | 'pinned_implementation_missing' | 'invalid_record' | 'task_identity_mismatch' | 'storage_unavailable';
  available: boolean;
  pinned: boolean;
  persisted: boolean;
};
export const ROUTER_STORAGE_PREFIX = 'mik:task-implementation:v1:';
// No time-based expiry while a task could still be active. Cleanup is explicit.

export function parseImplementationFlags(raw: string, allowedRendererIds: readonly string[]): Readonly<Record<string, RendererImplementation>> {
  const allowed = new Set(allowedRendererIds);
  const flags: Record<string, RendererImplementation> = {};
  if (!raw.trim()) return Object.freeze(flags);
  for (const item of raw.split(',')) {
    const entry = item.trim();
    if (!entry) continue;
    const [rendererId, value, extra] = entry.split('=');
    if (!rendererId || extra !== undefined || !allowed.has(rendererId) || (value !== 'legacy' && value !== 'kernel')) {
      throw new Error(`Invalid MIK implementation flag: ${entry}`);
    }
    if (Object.hasOwn(flags, rendererId)) throw new Error(`Duplicate MIK implementation flag: ${rendererId}`);
    flags[rendererId] = value;
  }
  return Object.freeze(flags);
}

function validIdentity(id: TaskImplementationIdentity) {
  // Reject invalid identities instead of creating a shared empty-key lock.
  return Boolean(id.taskInstanceId.trim() && id.rendererId.trim() && id.uiRevision.trim());
}

export function taskImplementationLockKey(identity: TaskImplementationIdentity): string {
  if (!validIdentity(identity)) throw new Error('MIK implementation lock requires task, renderer and UI revision');
  // Task-instance scoped, NOT ui_revision scoped: a change of revision during
  // the same task must be detected instead of silently choosing a new version.
  return ROUTER_STORAGE_PREFIX + encodeURIComponent(identity.taskInstanceId);
}

function sameIdentity(id: TaskImplementationIdentity, lock: ImplementationLock) {
  return id.taskInstanceId === lock.taskInstanceId && id.rendererId === lock.rendererId && id.uiRevision === lock.uiRevision;
}

/** Choose and pin exactly once per TaskInstance × Renderer × revision.
 * Pinned kernel with no deployed implementation => BLOCKED, not silent legacy remap.
 * Caller owns visual fallback and should report blocked status.
 */
export function getOrLockImplementation(args: {
  identity: TaskImplementationIdentity;
  configured: RendererImplementation | undefined;
  kernelAvailable: boolean;
  storage?: KeyValueStorage;
  now?: number;
}): ImplementationDecision {
  const {identity, configured, kernelAvailable, storage} = args;
  const now = args.now ?? Date.now();
  const key = taskImplementationLockKey(identity);
  let previous: ImplementationLock | undefined;
  let storageAvailable = storage !== undefined;
  let invalidRecord = false;
  let identityMismatch = false;
  let text: string | null | undefined;
  try { text = storage?.getItem(key); } catch { storageAvailable = false; invalidRecord = true; }
  if (text) {
    try {
      const candidate: unknown = JSON.parse(text);
      if (candidate && typeof candidate === 'object') {
        const lock = candidate as Partial<ImplementationLock>;
        if ((lock.version === 'legacy' || lock.version === 'kernel') &&
            typeof lock.taskInstanceId === 'string' && typeof lock.rendererId === 'string' &&
            typeof lock.uiRevision === 'string' && typeof lock.selectedAt === 'number' &&
            lock.selectedAt >= 0 && lock.selectedAt <= now && lock.taskInstanceId === identity.taskInstanceId) {
          previous = lock as ImplementationLock;
          identityMismatch = !sameIdentity(identity, previous);
        } else invalidRecord = true;
      } else invalidRecord = true;
    } catch { invalidRecord = true; }
  }
  if (previous) return {
    version: previous.version,
    reason: identityMismatch ? 'task_identity_mismatch' : previous.version === 'kernel' && !kernelAvailable ? 'pinned_implementation_missing' : 'pinned',
    available: !identityMismatch && (previous.version === 'legacy' || kernelAvailable),
    pinned: true, persisted: true
  };
  // A corrupt existing lock cannot be treated as a new task: fail blocked.
  if (invalidRecord && storageAvailable) return {
    version: 'legacy',reason:'invalid_record',available:false,pinned:false,persisted:false
  };
  // Failed record must not result in an implicit switch to another new implementation.
  const target: RendererImplementation = !storageAvailable ? 'legacy' : (configured ?? 'legacy');
  const version: RendererImplementation = target === 'kernel' && !kernelAvailable ? 'legacy' : target;
  let persisted = false;
  if (storageAvailable) {
    try {
      storage!.setItem(key, JSON.stringify({...identity,version,selectedAt:now} satisfies ImplementationLock));
      persisted = true;
    } catch { storageAvailable = false; }
  }
  return { version, available:true,pinned:false,persisted,
    reason: !storageAvailable ? 'storage_unavailable' : invalidRecord ? 'invalid_record' :
      target==='kernel' && !kernelAvailable ? 'kernel_unavailable' :
      configured==='kernel' ? 'flag_kernel' : configured==='legacy' ? 'flag_legacy' : 'flag_default_legacy'
  };
}

/** Call only after authoritative task completion/abandonment.
 * The SPIKE does not wire this to the learning reducer yet.
 */
export function clearTaskImplementationLock(identity: TaskImplementationIdentity, storage: Pick<Storage,'removeItem'>): void {
  storage.removeItem(taskImplementationLockKey(identity));
}
