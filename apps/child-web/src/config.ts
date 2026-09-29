import type { ChildMathSkin } from "@/src/theme/skins";

export const config = {
  apiMode:
    process.env.NEXT_PUBLIC_LEARNING_API_MODE === "http" ? "http" : "mock",
  apiBaseUrl:
    process.env.NEXT_PUBLIC_LEARNING_API_BASE_URL ?? "http://localhost:8000",

  /**
   * Current frozen local OpenAPI v1.3 does not yet contain the newly-ready
   * Session Result endpoint, so V1.2 keeps the path configurable.
   *
   * Replace this environment value with the authoritative backend route when
   * the OpenAPI baseline is updated.
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
      : "math-lab") as ChildMathSkin
} as const;