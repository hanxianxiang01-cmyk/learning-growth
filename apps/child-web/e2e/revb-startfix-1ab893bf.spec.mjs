// 1ab893bf 起点修复验证（产品方批准方案 §二 第4条）：
// 新版 visual.start=0/max=23：真实轨迹 0→7→14→21 自然可达、无需反向修正；
// 提交答案 21 判对；旧版对照组仍呈现 start=3 反常起点（回归基线）。
import { test, expect } from "@playwright/test";
import { request as pwRequest } from "@playwright/test";
const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8000";
const CHILD = process.env.E2E_CHILD_ID ?? "00000000-0000-0000-0000-000000000099";
const NEW = process.env.REVB_NEW_RVID ?? "5bceb172-2b67-4421-99b2-175ec05b94e9";
const OLD = "1ab893bf-b293-41bb-8514-310a8b832c3e";

async function pin(rvid) {
  const ctx = await pwRequest.newContext({ baseURL: API });
  try {
    const s = await ctx.post("/v1/learning/sessions", { data: { child_id: CHILD, subject: "math", requested_minutes: 15 } });
    const sid = (await s.json()).session_id;
    const t = await ctx.post("/v1/learning/tasks/next", { data: { child_id: CHILD, session_id: sid, subject: "math", pin_resource_version_id: rvid } });
    return { sid, task: await t.json() };
  } finally { await ctx.dispose(); }
}
const url = sid => `/child/math/session/e2e-fix-${sid}?child_id=${CHILD}`;

test.setTimeout(180_000);

test("FIX-01 新版 0→7→14→21 无反向修正 + 判对", async ({ page }) => {
  const { sid, task } = await pin(NEW);
  expect(task.task_instance_id, JSON.stringify(task)).toBeTruthy();
  await page.route("**/v1/learning/tasks/next", r =>
    r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(task) }));
  await page.goto(url(sid));
  const line = page.getByTestId("number-line");
  await expect(line).toBeVisible({ timeout: 60_000 });
  const h0 = await line.locator(".jump-history").innerText();
  expect(h0).toContain("起点：0");
  const tick = v => line.locator(".number-tick span", { hasText: new RegExp(`^\\s*${v}\\s*$`) }).first();
  for (const v of [7, 14, 21]) await tick(v).click();
  const hist = (await line.locator(".jump-history").innerText()).replace(/\s+/g, " ");
  console.log("FIX-01 history:", hist.slice(0, 160));
  expect(hist).toContain("+7 +7 +7");
  expect(hist).not.toContain("-");     // 无任何反向修正跳
  expect(hist).toContain("到 21");
  // 作答提交 21 → 判对
  await page.locator("#math-answer").fill("21");
  const res = page.waitForResponse(r => r.url().includes("/attempts") && r.status() === 200);
  await page.getByText("提交答案").click();
  const j = await (await res).json();
  console.log("FIX-01 judge correct:", j.correct);
  expect(j.correct).toBe(true);
});

test("FIX-02 旧版对照：start=3 反常起点仍在（修复必要性基线）", async ({ page }) => {
  const { sid, task } = await pin(OLD);
  expect(task.task_instance_id).toBeTruthy();
  await page.route("**/v1/learning/tasks/next", r =>
    r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(task) }));
  await page.goto(url(sid));
  const line = page.getByTestId("number-line");
  await expect(line).toBeVisible();
  const h0 = await line.locator(".jump-history").innerText();
  console.log("FIX-02 旧版初始:", h0.replace(/\s+/g, " ").slice(0, 60));
  expect(h0).toContain("起点：3");
});
