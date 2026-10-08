// FE-1427 R15 direction-grid 真实页面 E2E（B5 模板第十四实例；5×5 路径导航）。
// 合同：B5_E2E_VERTICAL_GATE.md + Gap R15（route evaluator/移动序列/方向错误 P0）。
// 答案=终点格编码 19（3×5+4）；反走终点=(1,0)→answer=5 判错+direction_reversed 原料；
// 绕路到 ☆ → 判对+detour 留痕（解耦第六次运用）。
// 数据卫生：CHILD=QA-Simulator …0099；ability=app_model（第四题）。
// 钉题：FE-1422a 确定性 pin（v2-catalog → pin_resource_version_id）。
import { test, expect } from "@playwright/test";
import { fetchPinnedTasks } from "./pinned-tasks.mjs";

const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8000";
const CHILD = process.env.E2E_CHILD_ID ?? "00000000-0000-0000-0000-000000000099";
const ABILITY = "app_model";

function r15Tasks(k) {
  return fetchPinnedTasks({ api: API, child: CHILD, renderer: "direction-grid", count: k });
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

const board = page => page.getByTestId("direction-grid-v2");
const submitButton = page => page.getByTestId("dg-submit");
const cell = (page, r, c) => page.getByTestId(`dg-cell-${r}-${c}`);

/** 依次点格路径（只给"该点哪些格"，相邻性由被测组件校验）。 */
async function walk(page, path) {
  for (const [r, c] of path) await cell(page, r, c).click();
}

async function submitAttempt(page) {
  const resPromise = page.waitForResponse(r => r.url().includes("/v1/learning/attempts") && r.status() === 200);
  await submitButton(page).click();
  return await (await resPromise).json();
}

test.beforeEach(async ({ page }) => {
  page.setDefaultTimeout(180_000);
});

test("R15-E2E-01 (G1) 渲染不降级：25 格 + 起点/目标标注", async ({ page }) => {
  const [entry] = await r15Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await expect(board(page)).toBeVisible();
  await expect(page.getByTestId("dg-cell-2-2")).toHaveAttribute("data-role", "start");
  await expect(cell(page, 3, 4)).toHaveAttribute("data-role", "target");
  await expect(page.getByTestId("dg-grid").locator(".dg-cell")).toHaveCount(25);
});

test("R15-E2E-02 (G2) 未挪步拦提交（EMPTY=还在起点）", async ({ page }) => {
  const [entry] = await r15Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await expect(submitButton(page)).toBeDisabled();
  await expect(page.getByTestId("dg-evaluation")).toContainText("还在起点");
});

test("R15-E2E-03 相邻约束：对角/隔格拒绝，相邻接受", async ({ page }) => {
  const [entry] = await r15Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await cell(page, 3, 3).click(); // 对角 → 拒绝，脚下不变
  await expect(cell(page, 3, 3)).not.toHaveAttribute("data-role", "walker");
  await expect(cell(page, 2, 2)).toHaveText("起"); // 仍站在起点
  await cell(page, 3, 2).click(); // 相邻下 → 接受
  await expect(cell(page, 3, 2)).toHaveAttribute("data-role", "walker");
  await expect(cell(page, 2, 2)).toHaveAttribute("data-role", "start"); // 起点角色常驻（cellRole start 优先）
  await expect(page.getByTestId("dg-evaluation")).toContainText("还没走到");
});

test("R15-E2E-04 (G4/G6) envelope 合同：type/路径 Evidence/事件链/无 representation 泄漏", async ({ page }) => {
  const [entry] = await r15Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await walk(page, [[3, 2], [3, 3], [3, 4]]);
  const req = page.waitForRequest(r => r.url().includes("/v1/learning/attempts") && r.method() === "POST");
  await submitButton(page).click();
  const payload = JSON.parse((await req).postData() ?? "{}");
  expect(payload.response.type).toBe("direction_grid");
  expect(payload.response.answer.value).toBe(19); // 组件自动填终点编码（envelope 统一 answer={value}）
  const data = payload.response.workspaces[0].data;
  for (const key of ["path", "directions", "move_count", "turns", "answer", "structure"]) expect(data).toHaveProperty(key);
  expect(data.path).toEqual(["2,2", "3,2", "3,3", "3,4"]); // Gap"movement sequence"
  expect(data.directions).toEqual(["down", "right", "right"]);
  expect(data.turns).toBe(1);
  expect(payload.response.representation).toBeUndefined();
  const types = payload.response.interaction_events.map(e => e.event_type);
  expect(types.filter(t => t === "PATH_EXTENDED")).toHaveLength(3);
});

test("R15-E2E-05 direction_reversed 专项：反走上左左→判错但原料可分诊", async ({ page }) => {
  const [entry] = await r15Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await walk(page, [[1, 2], [1, 1], [1, 0]]);
  await expect(page.getByTestId("dg-evaluation")).toContainText("方向走反");
  const result = await submitAttempt(page);
  expect(result.correct).toBe(false); // answer=5≠19
  expect((result.next_action || {}).type).toBe("HINT");
});

test("R15-E2E-06 (G5/G7) 修正路径：reversed→重置→最短路 19→NEXT_TASK", async ({ page }) => {
  const [entry] = await r15Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await walk(page, [[1, 2], [1, 1], [1, 0]]);
  const first = await submitAttempt(page);
  expect(first.correct).toBe(false);
  await page.getByTestId("dg-reset").click();
  await expect(cell(page, 2, 2)).toHaveAttribute("data-role", "start");
  await expect(submitButton(page)).toBeDisabled(); // 重置回 EMPTY
  await walk(page, [[3, 2], [3, 3], [3, 4]]);
  await expect(page.getByTestId("dg-evaluation")).toContainText("走到了");
  const second = await submitAttempt(page);
  expect(second.correct).toBe(true);
  expect((second.next_action || {}).type).toBe("NEXT_TASK");
  expect(second.attempt_no ?? 2).toBeGreaterThanOrEqual(2);
});

test("R15-E2E-07 detour 留痕：多走回头步到 ☆→后端判对+Evidence detour", async ({ page }) => {
  const [entry] = await r15Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  // 右一步、退回、再下右右到 ☆（共 5 步 > 最短路 3 步）
  await walk(page, [[2, 3], [2, 2], [3, 2], [3, 3], [3, 4]]);
  const [req] = await Promise.all([
    page.waitForRequest(r => r.url().includes("/v1/learning/attempts") && r.method() === "POST"),
    submitButton(page).click().then(() =>
      page.waitForResponse(r => r.url().includes("/v1/learning/attempts") && r.status() === 200)
    ).then(async res => {
      const result = await res.json();
      expect(result.correct).toBe(true); // 到 ☆ 就是走到——后端只看答案值
      expect((result.next_action || {}).type).toBe("NEXT_TASK");
    }),
  ]);
  // Evidence 侧留痕：绕路事实进 structure.detour（判对+原料=R08 形态）
  const payload = JSON.parse(req.postData() ?? "{}");
  expect(payload.response.workspaces[0].data.structure.detour).toBe(true);
  expect(payload.response.workspaces[0].data.move_count).toBe(5);
});

test("R15-E2E-08 退一步：末步撤回脚下回退", async ({ page }) => {
  const [entry] = await r15Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await walk(page, [[3, 2], [3, 3]]);
  await page.getByTestId("dg-undo-move").click();
  await expect(cell(page, 3, 2)).toHaveAttribute("data-role", "walker");
  await page.getByTestId("dg-undo-move").click();
  await expect(cell(page, 2, 2)).toHaveAttribute("data-role", "start"); // 回到起点（start 常驻）
  await expect(page.getByTestId("dg-undo-move")).toBeDisabled(); // 起点不可再退
  await expect(submitButton(page)).toBeDisabled(); // 退回 EMPTY
});

test("R15-E2E-09 dblclick 防重入（R04-IDEM 同模式）", async ({ page }) => {
  const [entry] = await r15Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await walk(page, [[3, 2], [3, 3], [3, 4]]);
  let posts = 0;
  page.on("request", r => {
    if (r.url().includes("/v1/learning/attempts") && r.method() === "POST") posts += 1;
  });
  await submitButton(page).dblclick();
  await page.waitForResponse(r => r.url().includes("/v1/learning/attempts"));
  await page.waitForTimeout(2500);
  expect(posts).toBe(1);
});

test("R15-E2E-10 healing 皮肤同链可用", async ({ page }) => {
  const healBase = process.env.E2E_HEALING_BASE;
  test.skip(!healBase, "未配置 E2E_HEALING_BASE");
  const [entry] = await r15Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(`${healBase}/child/math/session/e2e-${entry.sessionId}?child_id=${CHILD}&ability_id=${ABILITY}`);
  await expect(page.locator("[data-child-math-skin]")).toHaveAttribute("data-child-math-skin", "healing");
  await expect(board(page)).toBeVisible();
  await walk(page, [[3, 2], [3, 3], [3, 4]]);
  const result = await submitAttempt(page);
  expect(result.correct).toBe(true);
});
