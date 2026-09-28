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
  sessionStorage.setItem(key(snapshot.sessionId), JSON.stringify(snapshot));
}

export function loadSessionSnapshot(
  sessionId: string
): SessionSnapshot | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem(key(sessionId));
  if (!raw) return null;
  try {
    return JSON.parse(raw) as SessionSnapshot;
  } catch {
    return null;
  }
}
