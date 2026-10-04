// FE-1403 P0-03：B5 真实页面 E2E harness（Playwright + 系统 Chrome）
// 依据《B5 真实页面E2E联调方案》§7 场景矩阵 + §10 验收顺序 + docs/governance/B5_E2E_VERTICAL_GATE.md。
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 240_000, // 预取打真实 RDS（跨网），全局缓存后单测试仍留足操作时间
  expect: { timeout: 30_000 }, // 首用例含 dev 冷编译窗口，放宽避免环境抖动误报
  retries: 0,
  workers: 1, // 串行：共享真实后端 RDS，防并发 session 干扰
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_WEB_BASE ?? "http://127.0.0.1:3100",
    headless: true,
    trace: "off",
    screenshot: "only-on-failure"
  },
  projects: [
    {
      name: "chrome-system",
      use: { channel: "chrome" } // 用系统 Chrome，不下载浏览器二进制
    }
  ]
});
