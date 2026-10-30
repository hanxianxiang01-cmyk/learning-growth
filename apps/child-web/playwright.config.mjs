// FE-1403 P0-03：B5 真实页面 E2E harness（Playwright + 系统 Chrome）
// 依据《B5 真实页面E2E联调方案》§7 场景矩阵 + §10 验收顺序 + docs/governance/B5_E2E_VERTICAL_GATE.md。
//
// V1.4 游客模式：`require` 指向 e2e/guest-fixture.mjs —— 每个测试前自动签发
// QA 会话（HttpOnly Cookie），让 25 个既有 spec 继续以 …0099 身份跑真实后端。
// 详见该文件顶部说明。
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  // V1.4 游客模式：把 `test`/`expect` 的导出来源换成带 QA 会话夹具的模块。
  // 这一步是**必须**的——只写注释不会让 25 个 spec 拿到会话 Cookie，
  // 它们会各自变成匿名新游客，测试流量就不再落在 …0099（违反数据卫生 R1）。
  require: "./e2e/guest-fixture.mjs",
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