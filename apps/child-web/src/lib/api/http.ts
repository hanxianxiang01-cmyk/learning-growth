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
import { normalizeTaskUiSchema } from "./taskUiSchemaNormalizer";
import { normalizeAttemptResult } from "./attemptResultNormalizer";
import { normalizeHintResponse } from "./hintNormalizer";
import { buildAttemptPayload } from "./v2AttemptAdapter";

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

type RawTaskInstance = Omit<TaskInstance, "ui_schema"> & {
  ui_schema: unknown;
};

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

  async getNextTask(input: {
    child_id: string;
    session_id: string;
    subject: Subject;
    requested_minutes?: number;
    ability_id?: string;
  }): Promise<TaskInstance> {
    const raw = await this.request<RawTaskInstance>("/v1/learning/tasks/next", {
      method: "POST",
      body: JSON.stringify(input)
    });

    return {
      ...raw,
      ui_schema: normalizeTaskUiSchema(raw.ui_schema)
    };
  }

  async submitAttempt(input: AttemptRequest, task?: TaskInstance): Promise<AttemptResult> {
    // V2 资源：按 MathResponseSchema V2 构造提交信封（submission_id 幂等键）；V1 原样透传。
    const payload = buildAttemptPayload(task, input);
    const raw = await this.request<unknown>("/v1/learning/attempts", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    return normalizeAttemptResult(raw);
  }

  async requestHint(input: {
    attempt_id: string;
    requested_level?: number;
  }): Promise<HintResponse> {
    const raw = await this.request<unknown>("/v1/learning/hints", {
      method: "POST",
      body: JSON.stringify(input)
    });
    return normalizeHintResponse(raw);
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
