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

  /**
   * V1.4 游客模式：**刻意移除了 defaultChildId**。
   *
   * 原实现 `NEXT_PUBLIC_DEFAULT_CHILD_ID ?? "00000000-…-0001"` 是
   * 《V1.4 纯游客模式设计方案》2.1 明令禁止的「固定的公共游客 ID」：
   * 所有浏览器共用同一个 child，学习记录混在一起；改一个 URL 参数就能读写
   * 他人数据；且该 id 在 scripts/check-data-hygiene.mjs 中被标记为
   * REAL_CHILD（真实孩子）——游客流量会污染真实数据。
   *
   * 现在身份一律由服务端在 POST /v1/guest/bootstrap 时用
   * gen_random_uuid() 生成，通过 HttpOnly Cookie 下发给浏览器，
   * 前端不再有任何「默认身份」可以回退。
   *
   * 若某个部署确实需要固定身份（如单机演示），
   * 请用 POST /v1/guest/qa-session 显式取得 QA 会话，
   * 而不是把默认 id 请回前端配置。
   */

  childMathSkin:
    (process.env.NEXT_PUBLIC_CHILD_MATH_SKIN === "healing"
      ? "healing"
      : "exploration-lab") as ChildMathSkin
} as const;