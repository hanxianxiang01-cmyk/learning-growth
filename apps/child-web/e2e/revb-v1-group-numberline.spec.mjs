// Rev.B 开发核验点：V1 数轴 1ab893bf「三组一样多」(3袋×7珠=21, visual.start=3, max=23)
// 疑点：start=3 预置下，孩子能否完整表征"从0累加三个7"？实测：
//  A. 起点3 → +7×3 → 24（超 max=23，刻度不存在→不可达）
//  B. 改道 3→0（jump=-3）→ 0→7→14→21（可完成但轨迹含 -3 首跳）
import { test, expect } from "@playwright/test";
import { request as pwRequest } from "@playwright/test";
const API = "http://127.0.0.1:8000";
const CHILD = "00000000-0000-0000-0000-000000000099";
test.setTimeout(180_000);
test("REV-B-V1 三组一样多 start=3 表征可达性", async ({ page }) => {
  const ctx = await pwRequest.newContext({ baseURL: API });
  const s = await ctx.post("/v1/learning/sessions", { data: { child_id: CHILD, subject: "math", requested_minutes: 15 } });
  const sid = (await s.json()).session_id;
  const resp = await ctx.post("/v1/learning/tasks/next", { data: {
    child_id: CHILD, session_id: sid, subject: "math",
    pin_resource_version_id: "1ab893bf-b293-41bb-8514-310a8b832c3e" } });
  const task = await resp.json(); await ctx.dispose();
  expect(task.task_instance_id).toBeTruthy();
  await page.route("**/v1/learning/tasks/next", r =>
    r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(task) }));
  await page.goto(`/child/math/session/e2e-revb-${sid}?child_id=${CHILD}`);
  const line = page.getByTestId("number-line");
  await expect(line).toBeVisible({ timeout: 60_000 });
  const nums = (await line.locator(".number-tick span:last-child").allInnerTexts())
    .map(t => parseInt(t.trim(), 10)).filter(Number.isFinite);
  console.log(`V1REV 刻度[${nums[0]}..${nums[nums.length-1]}] 含24=${nums.includes(24)} 含21=${nums.includes(21)} 含0=${nums.includes(0)}`);
  const tick = v => line.locator(".number-tick span", { hasText: new RegExp(`^\\s*${v}\\s*$`) }).first();
  // 预置状态：history 应显示 起点：3
  const h0 = await line.locator(".jump-history").innerText();
  console.log("V1REV 初始 history:", h0.replace(/\s+/g, " ").slice(0, 80));
  // A. 题序累加 3→10→17→24（模拟"三个7"直觉路径，终点应24？不：3+7+7+7=24≠21）
  await tick(3).click();  // start/current=3 预置：点同值 jump=0 → 组件 return（无事件）
  await tick(10).click(); await tick(17).click();
  const has24 = await line.locator(".number-tick span", { hasText: /^\s*24\s*$/ }).count();
  console.log(`V1REV 3→10→17 后：24 刻度存在=${has24 > 0}`);
  // B. 改道：回 0 再三次 +7
  await tick(0).click(); await tick(7).click(); await tick(14).click(); await tick(21).click();
  const hist = await line.locator(".jump-history").innerText();
  console.log("V1REV 改道后 history:", hist.replace(/\s+/g, " ").slice(0, 200));
  expect(nums).toContain(21);
});
