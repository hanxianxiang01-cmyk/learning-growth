// FE-1423 R11 estimation-canvas 真实页面 E2E（B5 模板第十实例；估算+理由）。
// 合同：B5_E2E_VERTICAL_GATE.md + Gap R11（五状态/tolerance evaluator/调整过程 Evidence）。
// 判分口径：金题=近似数（38≈40，答案唯一）；too_high/too_low+close 是诊断原料走 Evidence。
// 数据卫生：CHILD=QA-Simulator …0099；ability=app_model；shopping 族首题。
// 钉题：FE-1422a 确定性 pin（v2-catalog → pin_resource_version_id），不靠 band 运气。
import { test, expect } from "@playwright/test";
import { fetchPinnedTasks } from "./pinned-tasks.mjs";

const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8000";
const CHILD = process.env.E2E_CHILD_ID ?? "00000000-0000-0000-0000-000000000099";
const ABILITY = "app_model";

function r11Tasks(k) {
  return fetchPinnedTasks({ api: API, child: CHILD, renderer: "estimation-canvas", count: k });
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

const card = page => page.getByTestId("estimation-canvas-v2");
const submitButton = page => page.getByTestId("ec-submit");
const slider = page => page.getByTestId("ec-slider");

/** 拖滑条到 v（range input 用 evaluate 设值并派发 input 事件）。 */
async function dragTo(page, v) {
  await slider(page).evaluate((el, val) => {
    const native = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
    native.call(el, String(val));
    el.dispatchEvent(new Event("input", { bubbles: true }));
  }, v);
}

const pickReason = (page, id) => page.getByTestId(`ec-reason-${id}`).click();

async function submitAttempt(page) {
  const resPromise = page.waitForResponse(r => r.url().includes("/v1/learning/attempts"));
  await submitButton(page).click();
  const resp = await resPromise;
  return { status: resp.status(), body: await resp.json() };
}

test.beforeEach(async ({ page }) => {
  page.setDefaultTimeout(180_000);
});

test("R11-E2E-01 渲染不降级（G1）：滑条+参照+理由 chip 齐全", async ({ page }) => {
  const [entry] = await r11Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await expect(card(page)).toBeVisible();
  await expect(slider(page)).toBeVisible();
  await expect(page.getByTestId("ec-reference-count")).toHaveText("10");
  await expect(page.getByTestId("ec-reason-group_by_ten")).toBeVisible();
  await expect(page.getByTestId("ec-reason-use_reference")).toBeVisible();
  await expect(page.getByTestId("ec-reason-quick_guess")).toBeVisible();
});

test("R11-E2E-02 未拖动拦提交（EMPTY estimate）", async ({ page }) => {
  const [entry] = await r11Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await expect(submitButton(page)).toBeDisabled();
  await expect(page.getByTestId("ec-evaluation")).toContainText("先拖动滑条");
});

test("R11-E2E-03 拖了未选理由仍拦提交（EMPTY reason，五态之二）", async ({ page }) => {
  const [entry] = await r11Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await dragTo(page, 45);
  await expect(page.getByTestId("ec-estimate-value")).toHaveText("45");
  await expect(submitButton(page)).toBeDisabled();
  await expect(page.getByTestId("ec-evaluation")).toContainText("选一选");
});

test("R11-E2E-04 envelope 合同（G4/G6）：type、data 五字段、事件链、无 representation 泄漏", async ({ page }) => {
  const [entry] = await r11Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await dragTo(page, 45);
  await pickReason(page, "quick_guess");
  const req = page.waitForRequest(r => r.url().includes("/v1/learning/attempts"));
  await submitButton(page).click();
  const payload = JSON.parse((await req).postData());
  expect(payload.response.type).toBe("estimation_canvas");
  const data = payload.response.workspaces[0].data;
  for (const key of ["estimate", "reason", "adjust_history", "answer", "structure"]) {
    expect(data).toHaveProperty(key);
  }
  expect(payload.response.representation).toBeUndefined();
  const types = payload.response.interaction_events.map(e => e.event_type);
  expect(types).toContain("ESTIMATE_CHANGED");
  expect(types).toContain("REASON_SELECTED");
});

test("R11-E2E-05 too_high 可提交且带方向原料（P0-01 FAIL 可达后端）", async ({ page }) => {
  const [entry] = await r11Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await dragTo(page, 45);
  await pickReason(page, "quick_guess");
  await expect(page.getByTestId("ec-evaluation")).toContainText("偏高");
  const { status, body } = await submitAttempt(page);
  expect(status).toBe(200);
  expect(body.correct).toBe(false);
  expect((body.next_action || {}).type).toBe("HINT");
});

test("R11-E2E-06 调整过程 Evidence（G5 前置）：三次拖动=三段历史", async ({ page }) => {
  const [entry] = await r11Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await dragTo(page, 20);
  await dragTo(page, 35);
  await dragTo(page, 40);
  await pickReason(page, "group_by_ten");
  const req = page.waitForRequest(r => r.url().includes("/v1/learning/attempts"));
  await submitButton(page).click();
  const payload = JSON.parse((await req).postData());
  const data = payload.response.workspaces[0].data;
  expect(data.adjust_history).toEqual([20, 35, 40]);
  expect(data.structure.status).toBe("PASS");
});

test("R11-E2E-07 判对 PASS→NEXT_TASK + attempt_no 递增（G7 修正路径）", async ({ page }) => {
  const [entry] = await r11Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  // 第一次估低 30（too_low）
  await dragTo(page, 30);
  await pickReason(page, "quick_guess");
  const first = await submitAttempt(page);
  expect(first.body.correct).toBe(false);
  // RETRY 态保留板面：拖到 40 改对（不再选理由——已选）
  await dragTo(page, 40);
  const second = await submitAttempt(page);
  expect(second.body.correct).toBe(true);
  expect((second.body.next_action || {}).type).toBe("NEXT_TASK");
  expect(second.body.attempt_no ?? 2).toBeGreaterThanOrEqual(2);
});

test("R11-E2E-08 防重入：双击提交只发一个 POST（R04-IDEM 同模式）", async ({ page }) => {
  const [entry] = await r11Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await dragTo(page, 40);
  await pickReason(page, "use_reference");
  let posts = 0;
  page.on("request", r => {
    if (r.url().includes("/v1/learning/attempts") && r.method() === "POST") posts += 1;
  });
  await submitButton(page).dblclick();
  await page.waitForResponse(r => r.url().includes("/v1/learning/attempts"));
  await page.waitForTimeout(2500);
  expect(posts).toBe(1); // 第二击被 submitting 态 disabled 拦住
});

test("R11-E2E-09 UNDO 单步：撤销回未选理由态（EMPTY reason）", async ({ page }) => {
  const [entry] = await r11Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await dragTo(page, 45);
  await pickReason(page, "quick_guess");
  await page.getByTestId("ec-undo").click();
  await expect(submitButton(page)).toBeDisabled();
  await expect(page.getByTestId("ec-evaluation")).toContainText("选一选");
});

test("R11-E2E-10 healing 皮肤同链可用", async ({ page, baseURL }) => {
  const healBase = process.env.E2E_HEALING_BASE;
  test.skip(!healBase, "未配置 E2E_HEALING_BASE");
  const [entry] = await r11Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(`${healBase}/child/math/session/e2e-${entry.sessionId}?child_id=${CHILD}&ability_id=${ABILITY}`);
  await expect(page.locator("[data-child-math-skin]")).toHaveAttribute("data-child-math-skin", "healing");
  await expect(card(page)).toBeVisible();
  await dragTo(page, 40);
  await pickReason(page, "group_by_ten");
  const { status, body } = await submitAttempt(page);
  expect(status).toBe(200);
  expect(body.correct).toBe(true);
});
