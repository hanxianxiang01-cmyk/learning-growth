// Isolated DEV-gallery browser suite. Never starts or seeds a learning backend.
import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e-v6", timeout: 90_000, expect: { timeout: 20_000 }, retries: 0, workers: 1,
  outputDir: "./test-results-v6", reporter: [["list"], ["json", { outputFile: "test-results-v6/results.json" }]],
  use: { baseURL: process.env.E2E_WEB_BASE || "http://127.0.0.1:3100", headless: true,
    viewport: { width: 1280, height: 1000 }, reducedMotion: "reduce", screenshot: "only-on-failure",
    trace: "retain-on-failure", ...(process.env.V6_BROWSER_CHANNEL ? { channel: process.env.V6_BROWSER_CHANNEL } : {}) }
});
