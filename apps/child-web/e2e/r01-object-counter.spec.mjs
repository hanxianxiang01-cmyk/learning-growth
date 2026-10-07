// FE-1414 R01 object-counter 真实页面 E2E（B5 模板第二个 Vertical Gate）。
// 合同：docs/governance/B5_E2E_VERTICAL_GATE.md G1~G9 口径 + docs/frontend/31 SEM-1410。
// 真实性：task 来自真实后端 /tasks/next（route 只做钉题重放）；/attempts、/hints 放行真实后端。
// 钉题：FE-1422a 确定性 pin（v2-catalog → pin_resource_version_id），不靠 band 运气。
// 数据卫生：CHILD=QA-Simulator …0099（docs/governance/QA_DATA_HYGIENE.md R1/R3）。
import { test, expect, request as pwRequest } from "@playwright/test";
import { fetchPinnedTasks } from "./pinned-tasks.mjs";

const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8000";
const CHILD = process.env.E2E_CHILD_ID ?? "00000000-0000-0000-0000-000000000099";

function r01Tasks(k) {
  return fetchPinnedTasks({ api: API, child: CHILD, renderer: "object-counter", count: k });
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
  return `/child/math/session/e2e-${sid}?child_id=${CHILD}&ability_id=app_rel`;
}

const card = page => page.getByTestId("object-counter-v2");
const submitButton = page => page.getByTestId("oc-submit");
const addBtn = (page, group) => page.getByTestId(`oc-add-${group}`);
const removeBtn = (page, group) => page.getByTestId(`oc-remove-${group}`);
const composeBtn = (page, source, target) => page.getByTestId(`oc-compose-${source}-into-${target}`);

async function submitAttempt(page) {
  const reqPromise = page.waitForRequest(
    r => r.url().includes("/v1/learning/attempts") && r.method() === "POST"
  );
  const resPromise = page.waitForResponse(
    r => r.url().includes("/v1/learning/attempts") && r.status() === 200
  );
  await submitButton(page).click();
  const req = await reqPromise;
  const body = JSON.parse(req.postData() ?? "{}");
  const result = await (await resPromise).json();
  return { body, result };
}

async function fillRight(page) {
  for (let i = 0; i < 4; i += 1) await addBtn(page, "g1").click();
  for (let i = 0; i < 3; i += 1) await addBtn(page, "g2").click();
}

// ---------- G1：V2 renderer 正确进入真实页面，不降级 ----------
test("R01-E2E-09 (G1) 渲染 object-counter，无降级卡、无开发中卡", async ({ page }) => {
  const [r01] = await r01Tasks(1);
  await pinTasks(page, [r01]);
  await page.goto(sessionUrl("g1"));
  await expect(card(page)).toBeVisible();
  await expect(page.getByTestId("planned-renderer")).toHaveCount(0);
  await expect(page.getByTestId("oc-group-g1")).toBeVisible();
  await expect(page.getByTestId("oc-group-g2")).toBeVisible();
  await expect(submitButton(page)).toBeDisabled();
});

// ---------- G2/G3：部分摆放不可提交 ----------
test("R01-E2E-03 (G2/G3) 只摆 1 个 → 提交禁用，不产生 attempt", async ({ page }) => {
  const [r01] = await r01Tasks(1);
  await pinTasks(page, [r01]);
  await page.goto(sessionUrl("partial"));
  await addBtn(page, "g1").click();
  await expect(page.getByTestId("oc-evaluation")).toContainText("还有组空着");
  await expect(submitButton(page)).toBeDisabled();
  let posted = false;
  page.on("request", r => { if (r.url().includes("/v1/learning/attempts")) posted = true; });
  await page.waitForTimeout(500);
  expect(posted).toBe(false);
});

// ---------- G6/G4：错误答案可提交 + V2 envelope 合同 ----------
test("R01-E2E-02 (G6/G4) 摆成 4+2 报 6 → envelope 完整 → correct=false → HINT", async ({ page }) => {
  const [r01] = await r01Tasks(1);
  await pinTasks(page, [r01]);
  await page.goto(sessionUrl("wrong"));
  for (let i = 0; i < 4; i += 1) await addBtn(page, "g1").click();
  for (let i = 0; i < 2; i += 1) await addBtn(page, "g2").click();
  await expect(page.getByTestId("oc-evaluation")).toContainText("数量还要检查"); // FAIL
  await expect(submitButton(page)).toBeEnabled(); // P0-01 口径：FAIL 可提交

  const { body, result } = await submitAttempt(page);

  expect(body.task_instance_id).toBe(r01.task.task_instance_id);
  expect(body.attempt_no).toBe(1);
  expect(typeof body.submission_id).toBe("string");
  const resp = body.response;
  expect(resp.schema_version).toBe("2.0");
  expect(resp.ui_revision).toBe(r01.task.ui_schema.ui_revision);
  expect(resp.type).toBe("object_count");
  expect(resp.workspaces[0].workspace_id).toBe("main");
  expect(resp.answer.value).toBe(6);
  expect(resp.workspaces[0].data.total).toBe(6);
  expect(resp.workspaces[0].data.groups).toHaveLength(2);
  expect(resp.interaction_events.length).toBeGreaterThan(0);
  expect(JSON.stringify(resp)).not.toContain("\"representation\"");

  expect(result.correct).toBe(false);
  expect(["HINT", "TEACH", "RETRY"]).toContain(result.next_action.type);
  expect(result.diagnosis === null || typeof result.diagnosis.code === "string").toBe(true);
  await expect(page.getByRole("button", { name: /给我一点提示/ })).toBeVisible();
});

// ---------- G5：正确摆法 + compose 过程 → 判对 → 下一题 ----------
test("R01-E2E-01 (G5) 4+3 合起来提交 → correct=true → NEXT_TASK", async ({ page }) => {
  const [r01] = await r01Tasks(1);
  await pinTasks(page, [r01]);
  await page.goto(sessionUrl("right"));
  await fillRight(page);
  await composeBtn(page, "g1", "g2").click();
  await expect(page.getByTestId("oc-evaluation")).toContainText("摆好了");
  const { body, result } = await submitAttempt(page);
  expect(result.correct).toBe(true);
  expect(result.next_action.type).toBe("NEXT_TASK");
  expect(body.response.workspaces[0].data.groups[0].composed_into).toBe("g2");
  expect(body.response.workspaces[0].data.groups[0].composed_count).toBe(4);
  expect(body.response.answer.value).toBe(7);
  await expect(page.getByRole("button", { name: /下一题/ })).toBeVisible();
});

// ---------- G7：重试 attempt_no 递增、单 Task 单证据 ----------
test("R01-G7 错误后改对再提交：attempt_no=2、首轮证据保留", async ({ page }) => {
  const [r01] = await r01Tasks(1);
  await pinTasks(page, [r01]);
  await page.goto(sessionUrl("retry"));

  for (let i = 0; i < 4; i += 1) await addBtn(page, "g1").click();
  for (let i = 0; i < 2; i += 1) await addBtn(page, "g2").click();
  const first = await submitAttempt(page);
  expect(first.result.correct).toBe(false);

  await page.getByRole("button", { name: /给我一点提示/ }).click();
  await expect(page.getByRole("button", { name: /我再想想/ })).toBeVisible();
  await page.getByRole("button", { name: /我再想想/ }).click();

  await addBtn(page, "g2").click(); // 4+3=7
  await expect(submitButton(page)).toBeEnabled();
  const second = await submitAttempt(page);
  expect(second.result.correct).toBe(true);
  expect(second.body.attempt_no).toBe(2);
});

// ---------- 防重入：双击只发一个 POST ----------
test("R01-E2E-07 防重入：双击提交只发一个 POST", async ({ page }) => {
  const [r01] = await r01Tasks(1);
  await pinTasks(page, [r01]);
  await page.goto(sessionUrl("dup"));
  await fillRight(page);
  let posts = 0;
  page.on("request", r => {
    if (r.url().includes("/v1/learning/attempts") && r.method() === "POST") posts += 1;
  });
  await submitButton(page).dblclick();
  await page.waitForTimeout(2500);
  expect(posts).toBe(1);
});

// ---------- revision 变化不串题 ----------
test("R01-E2E-08 下一题后 Workspace 重置，不继承上一题", async ({ page }) => {
  const two = await r01Tasks(2);
  const task2 = structuredClone(two[1].task);
  task2.ui_schema.ui_revision = `${two[1].task.ui_schema.ui_revision}-rev2`;
  await pinTasks(page, [two[0], { task: task2, sessionId: two[1].sessionId }]);
  await page.goto(sessionUrl("rev"));

  await fillRight(page);
  await submitAttempt(page);
  await page.getByRole("button", { name: /下一题/ }).click();

  await expect(card(page)).toBeVisible();
  await expect(page.getByTestId("oc-evaluation")).toContainText("先放物体");
  await expect(submitButton(page)).toBeDisabled();
  let posted = false;
  page.on("request", r => { if (r.url().includes("/v1/learning/attempts")) posted = true; });
  await page.waitForTimeout(500);
  expect(posted).toBe(false);
});

// ---------- P1：语义事件可追溯 ----------
test("R01-P1 事件模型：COUNT_ADDED/COMPOSED/DECOMPOSED/UNDO/RESET 入 payload", async ({ page }) => {
  const [r01] = await r01Tasks(1);
  await pinTasks(page, [r01]);
  await page.goto(sessionUrl("events"));
  await addBtn(page, "g1").click();
  await addBtn(page, "g1").click();
  await composeBtn(page, "g1", "g2").click();
  await page.getByTestId("oc-undo").click();
  await page.getByTestId("oc-reset").click();
  await fillRight(page);
  // g2=3 拆 1 → g1=4 g2=2 d1=1，总数 7；结构 FAIL（g2<3）→ 可提交
  await page.getByTestId("oc-decompose-g2").click();
  await expect(submitButton(page)).toBeEnabled();
  const { body, result } = await submitAttempt(page);
  const types = body.response.interaction_events.map(e => e.event_type);
  expect(types).toContain("COUNT_ADDED");
  expect(types).toContain("GROUP_COMPOSED");
  expect(types).toContain("GROUP_DECOMPOSED");
  expect(types).toContain("UNDO");
  expect(types).toContain("RESET");
  expect(body.response.answer.value).toBe(7);
  expect(result.correct).toBe(true);
});

// ---------- COUNT_REMOVED 独立覆盖 ----------
test("R01-P1b COUNT_REMOVED：放5减1成4+3 → 判对", async ({ page }) => {
  const [r01] = await r01Tasks(1);
  await pinTasks(page, [r01]);
  await page.goto(sessionUrl("events2"));
  for (let i = 0; i < 5; i += 1) await addBtn(page, "g1").click();
  for (let i = 0; i < 3; i += 1) await addBtn(page, "g2").click();
  await removeBtn(page, "g1").click();
  const { body, result } = await submitAttempt(page);
  const types = body.response.interaction_events.map(e => e.event_type);
  expect(types).toContain("COUNT_REMOVED");
  expect(body.response.answer.value).toBe(7);
  expect(result.correct).toBe(true);
});

// ---------- P1 双皮肤（3101 healing） ----------
test("R01-E2E-10 healing 皮肤：同契约同数据结构", async ({ page }) => {
  test.skip(!process.env.E2E_HEALING_BASE, "需 3101 healing 实例");
  const [r01] = await r01Tasks(1);
  await pinTasks(page, [r01]);
  const url = new URL(sessionUrl("healing"), process.env.E2E_HEALING_BASE);
  await page.goto(url.toString());
  await expect(page.locator("[data-child-math-skin]")).toHaveAttribute("data-child-math-skin", "healing");
  await fillRight(page);
  const { body, result } = await submitAttempt(page);
  expect(body.response.type).toBe("object_count");
  expect(result.correct).toBe(true);
});
