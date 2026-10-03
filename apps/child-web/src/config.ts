import type { ChildMathSkin } from "@/src/theme/skins";

export const config = {
  apiMode:
    process.env.NEXT_PUBLIC_LEARNING_API_MODE === "http" ? "http" : "mock",
  apiBaseUrl:
    process.env.NEXT_PUBLIC_LEARNING_API_BASE_URL ?? "http://localhost:8000",

  /**
   * Session Result endpoint 已写入权威 OpenAPI v1.3.1
   *（GET /v1/learning/sessions/{session_id}/result）。
   *
   * 默认路径已与权威路由一致；保留环境变量仅为异构部署留兜底，
   * 正常情况下无需覆盖。
   */
  sessionResultPathTemplate:
    process.env.NEXT_PUBLIC_SESSION_RESULT_PATH_TEMPLATE ??
    "/v1/learning/sessions/{session_id}/result",

  defaultChildId:
    process.env.NEXT_PUBLIC_DEFAULT_CHILD_ID ??
    "00000000-0000-0000-0000-000000000001",

  childMathSkin:
    (process.env.NEXT_PUBLIC_CHILD_MATH_SKIN === "healing"
      ? "healing"
      : "exploration-lab") as ChildMathSkin
} as const;