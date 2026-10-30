import type {
  AbilityState,
  ApiErrorBody,
  AttemptRequest,
  AttemptResult,
  GuestQuota,
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
      // V1.4 游客模式：身份在 HttpOnly Cookie 里，JS 拿不到也不需要拿。
      // credentials:"include" 让浏览器跨端口（3000→8000）也带上该 Cookie；
      // 服务端 CORS 已开 allow_credentials，两者必须同时成立才生效。
      credentials: "include",
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
      // FastAPI 把 dict 型 detail 包在 {"detail": {...}} 里，业务码（LE-4291 等）
      // 在 detail.code。不解包则 body.code 恒 undefined，humanizeError 的分支
      // 匹配永远不命中（死分支，10-29 核对证据链时发现）。
      const inner =
        body.detail && typeof body.detail === "object"
          ? (body.detail as ApiErrorBody)
          : undefined;
      const code = body.code ?? inner?.code;
      const message =
        body.message ??
        inner?.message ??
        `Learning Engine request failed (${res.status})`;
      // 401 = 游客会话失效（过期/被清）。这不是「加载失败」，而是「需要重新入学」，
      // 上层据此重新 bootstrap，而不是把裸错误丢给儿童看。
      throw new LearningApiError(message, res.status, code, body.detail);
    }

    return (await res.json()) as T;
  }

  /** 进入学习首页：有会话则复用，没有就新建一个游客（幂等）。 */
  bootstrapGuest() {
    return this.request<{
      child_id: string;
      is_new: boolean;
      expires_at: string;
      retention_days: number;
      quota: GuestQuota;
    }>("/v1/guest/bootstrap", { method: "POST" });
  }

  /** 当前游客身份 + 配额。用它替代原来的 ?child_id= 取身份。 */
  getGuest() {
    return this.request<{
      child_id: string;
      expires_at: string;
      retention_days: number;
      quota: GuestQuota;
    }>("/v1/guest/me");
  }

  /** 刷新保留期。只应在真实学习活动后调用，不要挂在页面挂载上。 */
  touchGuest() {
    return this.request<{ child_id: string; expires_at: string | null }>(
      "/v1/guest/heartbeat",
      { method: "POST" }
    );
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
