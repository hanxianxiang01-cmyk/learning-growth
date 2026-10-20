// FE-1466 B6 替代题真实 UI 冒烟（lab/healing 双皮肤由 E2E_WEB_BASE 切换）。
// 真实 React 交互→后端序列化→process_constraint 判定→Evidence 门槛。
// 缺失态=UI_PREVENTED 断言（EMPTY 拦提交）；合法态=真实摆卡/摆珠提交判对。
import { test, expect, request as pwRequest } from "@playwright/test";
import fs from "node:fs";

const CHILD = "00000000-0000-0000-0000-000000000099";
const WEB = process.env.E2E_WEB_BASE ?? "http://127.0.0.1:3100";
const SKIN = process.env.E2E_SKIN ?? "lab";
const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8000";
const B6 = JSON.parse(fs.readFileSync("e2e/fe1466-b6-rvids.json", "utf8"));

async function openTask(page, rvid, caseId) {
  const ctx = await pwRequest.newContext({ baseURL: API });
  let task;
  try {
    const s = await (await ctx.post("/v1/learning/sessions", { data: { child_id: CHILD, subject: "math", requested_minutes: 15 } })).json();
    task = await (await ctx.post("/v1/learning/tasks/next", { data: { child_id: CHILD, session_id: s.session_id, subject: "math", pin_resource_version_id: rvid } })).json();
    if (!task.task_instance_id) throw new Error(`pin 拒: ${task.reason}`);
    await page.route("**/v1/learning/tasks/next", r =>
      r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(task) }));
    await page.goto(`${WEB}/child/math/session/b6-${caseId}-${String(Math.random()).slice(2, 8)}?child_id=${CHILD}&ability_id=${task.ability_id}`);
  } finally { await ctx.dispose(); }
  return task;
}
async function submit(page) {
  const resP = page.waitForResponse(r => r.url().includes("/attempts") && r.status() === 200);
  await page.locator("[data-testid$='-submit']").click();
  return await (await resP).json();
}
test.setTimeout(180_000);

test("B6-A place-value 空摆=UI 拦提交；按数位条件真实摆卡判对", async ({ page }) => {
  await openTask(page, B6.A, "a");
  const card = page.getByTestId("place-value-v2");
  await expect(card).toBeVisible({ timeout: 30_000 });
  await expect(page.locator("[data-testid$='-submit']")).toBeDisabled();  // 未摆卡 EMPTY
  // 题面条件独立推理：百=3；个>十 → 十=0 个=5（儿童自己摆，UI 不代答）
  for (const [d, j] of [[3, 0], [0, 1], [5, 2]]) {
    await page.getByTestId(`pv-tile-${d}`).click();
    await page.getByTestId(`pv-slot-${j}`).click();
  }
  await expect(page.locator("[data-testid$='-submit']")).toBeEnabled();
  const r = await submit(page);
  expect(r.correct, "真实摆卡+305 → valid").toBe(true);
  expect(r.process_status).toBe("valid");
  expect(r.evidence_id, "合法操作产证据").toBeTruthy();
});

test("B6-B pattern ABBA 真实摆珠判对；空摆被 UI 拦", async ({ page }) => {
  await openTask(page, B6.B, "b");
  const card = page.getByTestId("pattern-board-v2");
  await expect(card).toBeVisible({ timeout: 30_000 });
  await expect(page.locator("[data-testid$='-submit']")).toBeDisabled();
  // 新组周期头两个 = 红(1)、黄(2)：token 点击自动落第一/第二空槽
  await page.getByTestId("pb-token-1").click();
  await page.getByTestId("pb-token-2").click();
  const r = await submit(page);
  console.log("B6-B RESULT:", JSON.stringify(r));
  expect(r.correct, "ABB 迁移正确 → valid").toBe(true);
  expect(r.process_status).toBe("valid");
  expect(r.evidence_id).toBeTruthy();
});
