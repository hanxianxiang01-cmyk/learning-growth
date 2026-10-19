// FE-1455b E2E 哨兵：约束版数轴 e0a2a067（jump_constraint 右5×3）
// ①非法轨迹（一步 20→35）→ correct=false + process_violation
// ②合法轨迹（20→25→30→35）→ correct=true 无 violation
// ③兼容：旧无约束题（pin 8eb5de92 v1 qa_staged 无约束版）一步到终点 → 仍判对（原行为）
import { test, expect } from "@playwright/test";
import { request as pwRequest } from "@playwright/test";

const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8000";
const CHILD = process.env.E2E_CHILD_ID ?? "00000000-0000-0000-0000-000000000099";
const CONSTRAINED = "e0a2a067-175b-480d-a614-e326212923f7";
// 2026-10-19 更新：原 LEGACY 8eb5de92 已 superseded（qa_staged 通道 pin 拒），哨兵红=钉题过期
// 非判分回归（干净 main worktree 同证）；换现行 published 无约束数轴题（左跳14→9）。
const LEGACY = "e1314829-19ff-4929-80e4-70c334c4015e";

async function pin(rvid) {
  const ctx = await pwRequest.newContext({ baseURL: API });
  try {
    const s = await ctx.post("/v1/learning/sessions",
      { data: { child_id: CHILD, subject: "math", requested_minutes: 15 } });
    const sid = (await s.json()).session_id;
    const resp = await ctx.post("/v1/learning/tasks/next",
      { data: { child_id: CHILD, session_id: sid, subject: "math", pin_resource_version_id: rvid } });
    return { sid, task: await resp.json() };
  } finally { await ctx.dispose(); }
}
const url = sid => `/child/math/session/e2e-1455-${sid}?child_id=${CHILD}`;

async function submitJump(page, seq) {
  const line = page.getByTestId("number-line-v2");
  await expect(line).toBeVisible({ timeout: 60_000 });
  for (const v of seq) {
    await line.locator(".number-tick span", { hasText: new RegExp(`^\\s*${v}\\s*$`) }).first().click();
  }
  const btn = page.getByTestId("number-line-v2-submit");
  await expect(btn).toBeEnabled();
  const res = page.waitForResponse(r => r.url().includes("/attempts") && r.status() === 200);
  await btn.click();
  return await (await res).json();
}

test.setTimeout(180_000);

test("FE1455-01 非法轨迹（一步 20→35）判错+违规码", async ({ page }) => {
  const { sid, task } = await pin(CONSTRAINED);
  expect(task.task_instance_id).toBeTruthy();
  await page.route("**/v1/learning/tasks/next", r =>
    r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(task) }));
  await page.goto(url(sid));
  const j = await submitJump(page, [20, 35]);
  console.log("FE1455-01:", JSON.stringify({ correct: j.correct, pv: j.process_violation }));
  expect(j.correct).toBe(false);
  expect(j.process_violation).toBeTruthy();
});

test("FE1455-02 合法轨迹（+5×3）判对无违规", async ({ page }) => {
  const { sid, task } = await pin(CONSTRAINED);
  await page.route("**/v1/learning/tasks/next", r =>
    r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(task) }));
  await page.goto(url(sid));
  const j = await submitJump(page, [20, 25, 30, 35]);
  console.log("FE1455-02:", JSON.stringify({ correct: j.correct, pv: j.process_violation ?? null }));
  expect(j.correct).toBe(true);
  expect(j.process_violation).toBeUndefined();
});

test("FE1455-03 兼容：无约束旧版一步到终点仍判对（原行为不变）", async ({ page }) => {
  const { sid, task } = await pin(LEGACY);
  expect(task.task_instance_id).toBeTruthy();
  await page.route("**/v1/learning/tasks/next", r =>
    r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(task) }));
  await page.goto(url(sid));
  // e1314829：14 起左跳一次落 9（无 jump_constraint/process_constraint）；
  // 兼容断言=无过程校验→终点值判分原样，且不产 process_violation
  const j = await submitJump(page, [9]);
  console.log("FE1455-03:", JSON.stringify({ correct: j.correct, pv: j.process_violation ?? null }));
  expect(j.correct).toBe(true);          // 兼容红线：未声明约束 → 终点判分原样
  expect(j.process_violation).toBeUndefined();
});
