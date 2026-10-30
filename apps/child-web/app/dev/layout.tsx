import { notFound } from "next/navigation";

/**
 * DEV ONLY 收口：`/dev/*` 全部内测台（题型展示、渲染器视觉复核、UI kit 切片）
 * 在生产构建下一律 404。
 *
 * 为什么要放在 layout 而不是逐页加：本目录 6 个页面里原本只有 3 个自己写了
 * `if (process.env.NODE_ENV === "production") notFound()`，另外 3 个
 * （`v1.3-qa`/`v1.4-qa`/`renderer-gallery`）是 `"use client"` 页面，
 * 服务端 `notFound()` 天然写不进去，于是被静默漏掉——生产构建实测仍返回 200，
 * 其中 `v1.4-qa` 的 SSR HTML 里直接带着题干。
 *
 * 放在 layout 一处，既补上漏掉的三个，也让以后新增的 `/dev/*` 页面自动继承，
 * 不必再指望每个新页面作者记得手写守卫。
 */
export default function DevLayout({ children }: { children: React.ReactNode }) {
  if (process.env.NODE_ENV === "production") notFound();
  return <>{children}</>;
}
