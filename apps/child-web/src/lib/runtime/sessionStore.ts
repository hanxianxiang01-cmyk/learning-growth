export type SessionSnapshot = {
  childId: string;
  sessionId: string;
  startedAt: number;
  completedAt?: number;
  tasksCompleted: number;
  correctTasks: number;
  totalAttempts: number;
  hintsUsed: number[];
  lastAbilityId?: string;
  diagnosisCodes: string[];
};

const key = (sessionId: string) => `math-session:${sessionId}`;

export function saveSessionSnapshot(snapshot: SessionSnapshot) {
  if (typeof window === "undefined") return;
  try { sessionStorage.setItem(key(snapshot.sessionId), JSON.stringify(snapshot)); }
  catch { /* Local cache is optional; never turn an acknowledged server result into an error. */ }
}

export function loadSessionSnapshot(
  sessionId: string
): SessionSnapshot | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(key(sessionId));
    if (!raw) return null;
    return JSON.parse(raw) as SessionSnapshot;
  } catch {
    return null;
  }
}
