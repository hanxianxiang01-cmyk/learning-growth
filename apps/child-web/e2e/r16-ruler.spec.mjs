// FE-1429 R16 ruler 真实页面 E2E（B5 模板第十五实例；两点标记量铅笔）。
// 合同：B5_E2E_VERTICAL_GATE.md + Gap R16（tolerance evaluator/起止点读数/刻度读取错误 P0）。
// 答案=标记间隔 5；零起误读 {0,8}→answer=8 判错+from_zero_reading；
// 平移段 {4,9}→answer=5 判对+aligned=false 留痕（解耦第七次运用）。
// 数据卫生：CHILD=QA-Simulator …0099；ability=app_model（第五题）。
import { test, expect } from "@playwright/test";
import { fetchPinnedTasks } from "./pinned-tasks.mjs";

const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8000";
const CHILD = process.env.E2E_CHILD_ID ?? "00000000-0000-0000-0000-000000000099";
const ABILITY = "app_model";

function r16Tasks(k) {
  return fetchPinnedTasks({ api: API, child: CHILD, renderer: "ruler", count: k });
}

async function pinTasks(page, tasks) {
  let cursor = 0;
  await page.route("**/v1/learning/tasks/next", async route => {
    const entry = tasks[Math.min(cursor, tasks.length - 1)];
    cursor += 1;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(entry.task) });
  });
}

function sessionUrl(sid) {
  return `/child/math/session/e2e-${sid}?child_id=${CHILD}&ability_id=${ABILITY}`;
}

const board = page => page.getByTestId("ruler-v2");
const submitButton = page => page.getByTestId("rl-submit");
const tick = (page, v) => page.getByTestId(`rl-tick-${v}`);

async function place(page, values) {
  for (const v of values) await tick(page, v).click();
}

async function submitAttempt(page) {
  const resPromise = page.waitForResponse(r => r.url().includes("/v1/learning/attempts") && r.status() === 200);
  await submitButton(page).click();
  return await (await resPromise).json();
}

test.beforeEach(async ({ page }) => {
  page.setDefaultTimeout(180_000);
});

test("R16-E2E-01 (G1) 渲染不降级：21 刻度 + 铅笔跨 3..8", async ({ page }) => {
  const [entry] = await r16Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await expect(board(page)).toBeVisible();
  await expect(page.getByTestId("rl-tick-0")).toBeVisible();
  await expect(page.getByTestId("rl-tick-20")).toBeVisible();
  const obj = page.getByTestId("rl-object");
  await expect(obj).toHaveAttribute("data-left", "3");
  await expect(obj).toHaveAttribute("data-right", "8");
});

test("R16-E2E-02 (G2) 标记不足 2 个拦提交（EMPTY）", async ({ page }) => {
  const [entry] = await r16Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await expect(submitButton(page)).toBeDisabled();
  await place(page, [3]); // 只放了左标记
  await expect(submitButton(page)).toBeDisabled();
  await expect(page.getByTestId("rl-evaluation")).toContainText("再点右头");
});

test("R16-E2E-03 对准两端：{3,8} → PASS 提示 + 答案自动 5", async ({ page }) => {
  const [entry] = await r16Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await place(page, [3, 8]);
  await expect(tick(page, 3)).toHaveClass(/marked/);
  await expect(tick(page, 8)).toHaveClass(/marked/);
  await expect(page.getByTestId("rl-evaluation")).toContainText("夹住了");
  await expect(submitButton(page)).toBeEnabled();
});

test("R16-E2E-04 (G4/G6) envelope 合同：type/answer={value:5}/marks 轨迹/事件链/无泄漏", async ({ page }) => {
  const [entry] = await r16Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await place(page, [3, 8]);
  const req = page.waitForRequest(r => r.url().includes("/v1/learning/attempts") && r.method() === "POST");
  await submitButton(page).click();
  const payload = JSON.parse((await req).postData() ?? "{}");
  expect(payload.response.type).toBe("ruler");
  expect(payload.response.answer.value).toBe(5); // envelope 统一 {value:N}（R15 坑口径）
  const data = payload.response.workspaces[0].data;
  for (const key of ["marks", "span", "reading", "answer", "object", "structure"]) expect(data).toHaveProperty(key);
  expect(data.marks).toEqual([3, 8]); // Gap"起止点"
  expect(data.span).toBe(5);
  expect(data.structure.aligned).toBe(true);
  expect(payload.response.representation).toBeUndefined();
  const types = payload.response.interaction_events.map(e => e.event_type);
  expect(types.filter(t => t === "RULER_MARK_SET")).toHaveLength(2);
});

test("R16-E2E-05 from_zero_reading 专项：{0,8}→判错+刻度读取分诊", async ({ page }) => {
  const [entry] = await r16Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await place(page, [0, 8]);
  await expect(page.getByTestId("rl-evaluation")).toContainText("放在 0 上");
  const result = await submitAttempt(page);
  expect(result.correct).toBe(false); // answer=8≠5
  expect((result.next_action || {}).type).toBe("HINT");
});

test("R16-E2E-06 解耦靶：平移段 {4,9} span=5 → 判对 + aligned=false 留痕", async ({ page }) => {
  const [entry] = await r16Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await place(page, [4, 9]);
  await expect(page.getByTestId("rl-evaluation")).toContainText("没夹在铅笔两头");
  const req = page.waitForRequest(r => r.url().includes("/v1/learning/attempts") && r.method() === "POST");
  await submitButton(page).click();
  const payload = JSON.parse((await req).postData() ?? "{}");
  expect(payload.response.answer.value).toBe(5);
  expect(payload.response.workspaces[0].data.structure.aligned).toBe(false);
  const res = await page.waitForResponse(r => r.url().includes("/v1/learning/attempts") && r.status() === 200);
  const result = await res.json();
  expect(result.correct).toBe(true); // 量对=后端判，准没对准=结构层说
});

test("R16-E2E-07 (G5/G7) 修正路径：from_zero→清标记→对准→NEXT_TASK", async ({ page }) => {
  const [entry] = await r16Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await place(page, [0, 8]);
  const first = await submitAttempt(page);
  expect(first.correct).toBe(false);
  await page.getByTestId("rl-clear").click();
  await expect(tick(page, 0)).not.toHaveClass(/marked/);
  await expect(submitButton(page)).toBeDisabled(); // 清回 EMPTY
  await place(page, [3, 8]);
  const second = await submitAttempt(page);
  expect(second.correct).toBe(true);
  expect((second.next_action || {}).type).toBe("NEXT_TASK");
  expect(second.attempt_no ?? 2).toBeGreaterThanOrEqual(2);
});

test("R16-E2E-08 第三点重放：放满 2 个再点=清空重放", async ({ page }) => {
  const [entry] = await r16Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await place(page, [3, 8]);
  await tick(page, 5).click(); // 第 3 点 → 重放：只剩 5
  await expect(tick(page, 5)).toHaveClass(/marked/);
  await expect(tick(page, 3)).not.toHaveClass(/marked/);
  await expect(page.getByTestId("rl-evaluation")).toContainText("第一个标记放好了");
});

test("R16-E2E-09 dblclick 防重入（R04-IDEM 同模式）", async ({ page }) => {
  const [entry] = await r16Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await place(page, [3, 8]);
  let posts = 0;
  page.on("request", r => {
    if (r.url().includes("/v1/learning/attempts") && r.method() === "POST") posts += 1;
  });
  await submitButton(page).dblclick();
  await page.waitForResponse(r => r.url().includes("/v1/learning/attempts"));
  await page.waitForTimeout(2500);
  expect(posts).toBe(1);
});

test("R16-E2E-10 healing 皮肤同链可用", async ({ page }) => {
  const healBase = process.env.E2E_HEALING_BASE;
  test.skip(!healBase, "未配置 E2E_HEALING_BASE");
  const [entry] = await r16Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(`${healBase}/child/math/session/e2e-${entry.sessionId}?child_id=${CHILD}&ability_id=${ABILITY}`);
  await expect(page.locator("[data-child-math-skin]")).toHaveAttribute("data-child-math-skin", "healing");
  await expect(board(page)).toBeVisible();
  await place(page, [3, 8]);
  const result = await submitAttempt(page);
  expect(result.correct).toBe(true);
});
