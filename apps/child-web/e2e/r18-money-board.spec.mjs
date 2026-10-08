// FE-1431 R18 money-board 真实页面 E2E（B5 模板第十七实例；凑付 3 元 5 角）。
// 合同：B5_E2E_VERTICAL_GATE.md + Gap R18（monetary evaluator/选择与换算过程/面值金额关系错误 P0）。
// 答案=付出总角数 35；混淆靶 {3枚1元+5枚5角}=55 判错；笨凑法 {2元+3×5角}=35 判对+uses_extra 留痕。
// 数据卫生：CHILD=QA-Simulator …0099；ability=app_strat（第三题）。
import { test, expect } from "@playwright/test";
import { fetchPinnedTasks } from "./pinned-tasks.mjs";

const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8000";
const CHILD = process.env.E2E_CHILD_ID ?? "00000000-0000-0000-0000-000000000099";
const ABILITY = "app_strat";

function r18Tasks(k) {
  return fetchPinnedTasks({ api: API, child: CHILD, renderer: "money-board", count: k });
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

const board = page => page.getByTestId("money-board-v2");
const submitButton = page => page.getByTestId("mb-submit");
const addBtn = (page, d) => page.getByTestId(`mb-add-${d}`);
const countOf = (page, d) => page.getByTestId(`mb-count-${d}`);

async function pay(page, spec) {
  for (const [d, n] of spec) for (let i = 0; i < n; i++) await addBtn(page, d).click();
}

async function submitAttempt(page) {
  const resPromise = page.waitForResponse(r => r.url().includes("/v1/learning/attempts") && r.status() === 200);
  await submitButton(page).click();
  return await (await resPromise).json();
}

test.beforeEach(async ({ page }) => {
  page.setDefaultTimeout(180_000);
});

test("R18-E2E-01 (G1) 渲染不降级：四档钱包 + 价格 3元5角", async ({ page }) => {
  const [entry] = await r18Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await expect(board(page)).toBeVisible();
  await expect(page.getByTestId("mb-price")).toContainText("3元5角");
  for (const d of [1, 5, 10, 50]) await expect(addBtn(page, d)).toBeVisible();
});

test("R18-E2E-02 (G2) 一枚没拿拦提交（EMPTY）", async ({ page }) => {
  const [entry] = await r18Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await expect(submitButton(page)).toBeDisabled();
  await expect(page.getByTestId("mb-evaluation")).toContainText("一枚钱还没拿出来");
});

test("R18-E2E-03 拿币/取回生效", async ({ page }) => {
  const [entry] = await r18Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await addBtn(page, 10).click();
  await expect(countOf(page, 10)).toContainText("1元");
  await addBtn(page, 10).click();
  await expect(countOf(page, 10)).toContainText("1元1元");
  await page.getByTestId("mb-remove-10").click();
  await expect(countOf(page, 10)).not.toHaveText(/1元1元/);
  await expect(page.getByTestId("mb-evaluation")).toContainText("还差"); // underpaid 10 角
});

test("R18-E2E-04 (G4/G6) envelope 合同：type/answer={value:35}/选择过程/事件链/无泄漏", async ({ page }) => {
  const [entry] = await r18Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await pay(page, [[10, 3], [5, 1]]); // 最优凑法
  const req = page.waitForRequest(r => r.url().includes("/v1/learning/attempts") && r.method() === "POST");
  await submitButton(page).click();
  const payload = JSON.parse((await req).postData() ?? "{}");
  expect(payload.response.type).toBe("money_board");
  expect(payload.response.answer.value).toBe(35);
  const data = payload.response.workspaces[0].data;
  for (const key of ["counts", "coins", "total", "selection_history", "answer", "structure"]) expect(data).toHaveProperty(key);
  expect(data.counts).toEqual({ "10": 3, "5": 1 });
  expect(data.coins).toBe(4);
  expect(data.total_text).toBe("3元5角");
  expect(data.structure.uses_extra).toBe(false);
  expect(payload.response.representation).toBeUndefined();
  const types = payload.response.interaction_events.map(e => e.event_type);
  expect(types.filter(t => t === "MONEY_COIN_ADDED")).toHaveLength(4);
});

test("R18-E2E-05 denomination_confusion 专项：5角当5元数→判错+面值关系分诊", async ({ page }) => {
  const [entry] = await r18Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await pay(page, [[10, 3], [5, 5]]); // 3元 + 5枚5角 = 55 角
  await expect(page.getByTestId("mb-evaluation")).toContainText("把「5角」当成「5元」");
  const result = await submitAttempt(page);
  expect(result.correct).toBe(false); // 55≠35
  expect((result.next_action || {}).type).toBe("HINT");
});

test("R18-E2E-06 解耦靶：笨凑法 2元+3×5角=35 → 判对 + uses_extra 留痕", async ({ page }) => {
  const [entry] = await r18Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await pay(page, [[10, 2], [5, 3]]); // 20+15=35，5 枚 > 最少 4
  await expect(page.getByTestId("mb-evaluation")).toContainText("凑对了");
  await expect(page.getByTestId("mb-evaluation")).toContainText("最少 4 枚");
  const [req, result] = await Promise.all([
    page.waitForRequest(r => r.url().includes("/v1/learning/attempts") && r.method() === "POST"),
    (async () => {
      const res = page.waitForResponse(r => r.url().includes("/v1/learning/attempts") && r.status() === 200);
      await submitButton(page).click();
      return await (await res).json();
    })(),
  ]);
  expect(result.correct).toBe(true);
  const payload = JSON.parse(req.postData() ?? "{}");
  expect(payload.response.workspaces[0].data.structure.uses_extra).toBe(true);
});

test("R18-E2E-07 (G5/G7) 修正路径：confusion 判错→取回补正→NEXT_TASK", async ({ page }) => {
  const [entry] = await r18Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await pay(page, [[10, 3], [5, 5]]);
  const first = await submitAttempt(page);
  expect(first.correct).toBe(false);
  // 4 枚 5 角取回
  for (let i = 0; i < 4; i++) await page.getByTestId("mb-remove-5").click();
  await expect(page.getByTestId("mb-evaluation")).toContainText("正好 3元5角");
  const second = await submitAttempt(page);
  expect(second.correct).toBe(true);
  expect((second.next_action || {}).type).toBe("NEXT_TASK");
  expect(second.attempt_no ?? 2).toBeGreaterThanOrEqual(2);
});

test("R18-E2E-08 取回下限：没有该档币时取回禁用", async ({ page }) => {
  const [entry] = await r18Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await expect(page.getByTestId("mb-remove-10")).toBeDisabled();
  await addBtn(page, 10).click();
  await expect(page.getByTestId("mb-remove-10")).toBeEnabled();
  await page.getByTestId("mb-remove-10").click();
  await expect(page.getByTestId("mb-remove-10")).toBeDisabled();
  await expect(submitButton(page)).toBeDisabled(); // 拿空回 EMPTY
});

test("R18-E2E-09 dblclick 防重入（R04-IDEM 同模式）", async ({ page }) => {
  const [entry] = await r18Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await pay(page, [[10, 3], [5, 1]]);
  let posts = 0;
  page.on("request", r => {
    if (r.url().includes("/v1/learning/attempts") && r.method() === "POST") posts += 1;
  });
  await submitButton(page).dblclick();
  await page.waitForResponse(r => r.url().includes("/v1/learning/attempts"));
  await page.waitForTimeout(2500);
  expect(posts).toBe(1);
});

test("R18-E2E-10 healing 皮肤同链可用", async ({ page }) => {
  const healBase = process.env.E2E_HEALING_BASE;
  test.skip(!healBase, "未配置 E2E_HEALING_BASE");
  const [entry] = await r18Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(`${healBase}/child/math/session/e2e-${entry.sessionId}?child_id=${CHILD}&ability_id=${ABILITY}`);
  await expect(page.locator("[data-child-math-skin]")).toHaveAttribute("data-child-math-skin", "healing");
  await expect(board(page)).toBeVisible();
  await pay(page, [[10, 3], [5, 1]]);
  const result = await submitAttempt(page);
  expect(result.correct).toBe(true);
});
