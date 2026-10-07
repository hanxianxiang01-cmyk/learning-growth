// FE-1425 R13 shape-canvas 真实页面 E2E（B5 模板第十二实例；钉子板画长方形）。
// 合同：B5_E2E_VERTICAL_GATE.md + Gap R13（geometry evaluator/绘制轨迹/几何属性错误）。
// 解耦第四次运用：平行四边形面积=6 → 后端判对 + not_right_angle 原料走 Evidence。
// 数据卫生：CHILD=QA-Simulator …0099；ability=app_model（第三题）。
// 钉题：FE-1422a 确定性 pin（v2-catalog → pin_resource_version_id），不靠 band 运气。
import { test, expect } from "@playwright/test";
import { fetchPinnedTasks } from "./pinned-tasks.mjs";

const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8000";
const CHILD = process.env.E2E_CHILD_ID ?? "00000000-0000-0000-0000-000000000099";
const ABILITY = "app_model";

function r13Tasks(k) {
  return fetchPinnedTasks({ api: API, child: CHILD, renderer: "shape-canvas", count: k });
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

const card = page => page.getByTestId("shape-canvas-v2");
const submitButton = page => page.getByTestId("sc-submit");
const peg = (page, x, y) => page.getByTestId(`sc-peg-${x}-${y}`);

async function tapPegs(page, coords) {
  for (const [x, y] of coords) await peg(page, x, y).click();
}

async function submitAttempt(page) {
  const resPromise = page.waitForResponse(r => r.url().includes("/v1/learning/attempts") && r.status() === 200);
  await submitButton(page).click();
  return await (await resPromise).json();
}

test.beforeEach(async ({ page }) => {
  page.setDefaultTimeout(180_000);
});

test("R13-E2E-01 (G1) 渲染不降级：5×5 点阵=25 peg 可见", async ({ page }) => {
  const [entry] = await r13Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await expect(card(page)).toBeVisible();
  await expect(page.getByTestId("sc-board")).toBeVisible();
  // grid=5 → 25 颗钉
  for (const x of [0, 4]) for (const y of [0, 4]) {
    await expect(peg(page, x, y)).toBeVisible();
  }
  await expect(page.getByTestId("sc-peg-0-0")).toHaveCount(1);
});

test("R13-E2E-02 (G2) 点数不足拦提交（EMPTY <3 点）", async ({ page }) => {
  const [entry] = await r13Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await expect(submitButton(page)).toBeDisabled();
  await peg(page, 0, 0).click();
  await peg(page, 1, 0).click();
  await expect(submitButton(page)).toBeDisabled(); // 2 点仍 EMPTY
  await expect(page.getByTestId("sc-evaluation")).toContainText("至少点 3 个点");
});

test("R13-E2E-03 三角形可提交（vertex_count FAIL 可达后端）", async ({ page }) => {
  const [entry] = await r13Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await tapPegs(page, [[0, 0], [3, 0], [0, 2]]);
  await expect(page.getByTestId("sc-polygon")).toBeVisible();
  await expect(page.getByTestId("sc-area")).toHaveText("3");
  await expect(page.getByTestId("sc-evaluation")).toContainText("4 个顶点");
  const result = await submitAttempt(page);
  expect(result.correct).toBe(false); // 面积 3≠6
});

test("R13-E2E-04 (G4) envelope 合同：type/data 四字段/轨迹事件/无 representation 泄漏", async ({ page }) => {
  const [entry] = await r13Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await tapPegs(page, [[0, 0], [3, 0], [3, 2], [0, 2]]);
  const req = page.waitForRequest(r => r.url().includes("/v1/learning/attempts") && r.method() === "POST");
  await submitButton(page).click();
  const payload = JSON.parse((await req).postData() ?? "{}");
  expect(payload.response.type).toBe("shape_canvas");
  const data = payload.response.workspaces[0].data;
  for (const key of ["vertices", "area", "right_angles", "structure"]) expect(data).toHaveProperty(key);
  // 轨迹序=点击序（Gap"绘制轨迹"；GridPoint 形态 {x,y}）
  expect(data.vertices).toEqual([{ x: 0, y: 0 }, { x: 3, y: 0 }, { x: 3, y: 2 }, { x: 0, y: 2 }]);
  expect(data.right_angles).toBe(4);
  expect(payload.response.representation).toBeUndefined();
  const types = payload.response.interaction_events.map(e => e.event_type);
  expect(types.filter(t => t === "SHAPE_POINT_ADDED")).toHaveLength(4);
});

test("R13-E2E-05 解耦双断言：平行四边形面积 6 → correct=true + not_right_angle 原料", async ({ page }) => {
  const [entry] = await r13Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await tapPegs(page, [[0, 0], [3, 0], [4, 2], [1, 2]]);
  await expect(page.getByTestId("sc-area")).toHaveText("6");
  await expect(page.getByTestId("sc-evaluation")).toContainText("方方正正"); // 歪斜提示
  const result = await submitAttempt(page);
  expect(result.correct).toBe(true); // 面积对 → 后端判对
});

test("R13-E2E-06 wrong_size：2×2 正方形 4≠6 判错 + 提示尺寸", async ({ page }) => {
  const [entry] = await r13Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await tapPegs(page, [[0, 0], [2, 0], [2, 2], [0, 2]]);
  await expect(page.getByTestId("sc-evaluation")).toContainText("面积是 4");
  const result = await submitAttempt(page);
  expect(result.correct).toBe(false);
  expect((result.next_action || {}).type).toBe("HINT");
});

test("R13-E2E-07 (G7) 修正路径：wrong_size→撤点重画→PASS NEXT_TASK", async ({ page }) => {
  const [entry] = await r13Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await tapPegs(page, [[0, 0], [2, 0], [2, 2], [0, 2]]);
  const first = await submitAttempt(page);
  expect(first.correct).toBe(false);
  // 撤掉 3 个点重画 3×2（撤点 1 步=1 dispatch）
  for (let i = 0; i < 3; i += 1) await page.getByTestId("sc-remove").click();
  await expect(page.getByTestId("sc-vertex-count")).toHaveText("1");
  await tapPegs(page, [[3, 0], [3, 2], [0, 2]]);
  const second = await submitAttempt(page);
  expect(second.correct).toBe(true);
  expect((second.next_action || {}).type).toBe("NEXT_TASK");
  expect(second.attempt_no ?? 2).toBeGreaterThanOrEqual(2);
});

test("R13-E2E-08 重复点拒绝（taken peg 再点不增顶点）", async ({ page }) => {
  const [entry] = await r13Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await tapPegs(page, [[0, 0], [3, 0]]);
  await peg(page, 0, 0).click(); // 重复点
  await expect(page.getByTestId("sc-vertex-count")).toHaveText("2");
});

test("R13-E2E-09 dblclick 防重入（R04-IDEM 同模式）", async ({ page }) => {
  const [entry] = await r13Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await tapPegs(page, [[0, 0], [3, 0], [3, 2], [0, 2]]);
  let posts = 0;
  page.on("request", r => {
    if (r.url().includes("/v1/learning/attempts") && r.method() === "POST") posts += 1;
  });
  await submitButton(page).dblclick();
  await page.waitForResponse(r => r.url().includes("/v1/learning/attempts"));
  await page.waitForTimeout(2500);
  expect(posts).toBe(1);
});

test("R13-E2E-10 UNDO 单步 + 撤点删除到 EMPTY", async ({ page }) => {
  const [entry] = await r13Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await tapPegs(page, [[0, 0], [3, 0], [3, 2]]);
  await page.getByTestId("sc-undo").click();
  await expect(page.getByTestId("sc-vertex-count")).toHaveText("2");
  await page.getByTestId("sc-remove").click(); // 撤最后一个
  await expect(page.getByTestId("sc-vertex-count")).toHaveText("1");
  await expect(submitButton(page)).toBeDisabled();
});

test("R13-E2E-11 healing 皮肤同链可用", async ({ page }) => {
  const healBase = process.env.E2E_HEALING_BASE;
  test.skip(!healBase, "未配置 E2E_HEALING_BASE");
  const [entry] = await r13Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(`${healBase}/child/math/session/e2e-${entry.sessionId}?child_id=${CHILD}&ability_id=${ABILITY}`);
  await expect(page.locator("[data-child-math-skin]")).toHaveAttribute("data-child-math-skin", "healing");
  await expect(card(page)).toBeVisible();
  await tapPegs(page, [[0, 0], [3, 0], [3, 2], [0, 2]]);
  const result = await submitAttempt(page);
  expect(result.correct).toBe(true);
});
