import type {
  AbilityState,
  ApiErrorBody,
  AttemptRequest,
  AttemptResult,
  HintResponse,
  LearnerProfile,
  LearningApi,
  LearningSession,
  SessionResult,
  Subject,
  TaskInstance
} from "./contracts";
import { normalizeSessionResult } from "./sessionResultNormalizer";

export class LearningApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
    public detail?: unknown
  ) {
    super(message);
  }
}

export class HttpLearningApi implements LearningApi {
  constructor(
    private baseUrl: string,
    private sessionResultPathTemplate: string
  ) {}

  private async request<T>(
    path: string,
    init?: RequestInit
  ): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {})
      },
      cache: "no-store"
    });

    if (!res.ok) {
      let body: ApiErrorBody = {};
      try {
        body = await res.json();
      } catch {}
      throw new LearningApiError(
        body.message ?? `Learning Engine request failed (${res.status})`,
        res.status,
        body.code,
        body.detail
      );
    }

    return (await res.json()) as T;
  }

  getProfile(childId: string) {
    return this.request<LearnerProfile>(
      `/v1/children/${encodeURIComponent(childId)}/profile`
    );
  }

  getAbilities(childId: string) {
    return this.request<AbilityState[]>(
      `/v1/children/${encodeURIComponent(childId)}/abilities`
    );
  }

  createSession(input: {
    child_id: string;
    subject: Subject;
    requested_minutes?: number;
    plan_id?: string;
  }) {
    return this.request<LearningSession>("/v1/learning/sessions", {
      method: "POST",
      body: JSON.stringify(input)
    });
  }

  getNextTask(input: {
    child_id: string;
    session_id: string;
    subject: Subject;
    requested_minutes?: number;
    ability_id?: string;
  }) {
    return this.request<TaskInstance>("/v1/learning/tasks/next", {
      method: "POST",
      body: JSON.stringify(input)
    });
  }

  submitAttempt(input: AttemptRequest) {
    return this.request<AttemptResult>("/v1/learning/attempts", {
      method: "POST",
      body: JSON.stringify(input)
    });
  }

  requestHint(input: {
    attempt_id: string;
    requested_level?: number;
  }) {
    return this.request<HintResponse>("/v1/learning/hints", {
      method: "POST",
      body: JSON.stringify(input)
    });
  }

  async getSessionResult(sessionId: string): Promise<SessionResult> {
    const path = this.sessionResultPathTemplate.replace(
      "{session_id}",
      encodeURIComponent(sessionId)
    );
    const raw = await this.request<unknown>(path);
    return normalizeSessionResult(raw, sessionId);
  }
}
