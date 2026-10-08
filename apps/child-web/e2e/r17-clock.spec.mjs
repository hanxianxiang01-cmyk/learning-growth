// FE-1430 R17 clock 真实页面 E2E（B5 模板第十六实例；拨钟面指针）。
// 合同：B5_E2E_VERTICAL_GATE.md + Gap R17（time evaluator/指针调整过程/时针分针关系错误 P0）。
// 金题：3:00 → 拨到 6:00；答案=总分钟 360。
// 分诊靶：点 12 拨成 12:00（把长针指的 12 当时针读）→ hand_swap，answer=720 判错。
// 数据卫生：CHILD=QA-Simulator …0099；ability=app_cond（第三题）。
import { test, expect } from "@playwright/test";
import { fetchPinnedTasks } from "./pinned-tasks.mjs";

const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8000";
const CHILD = process.env.E2E_CHILD_ID ?? "00000000-0000-0000-0000-000000000099";
const ABILITY = "app_cond";

function r17Tasks(k) {
  return fetchPinnedTasks({ api: API, child: CHILD, renderer: "clock", count: k });
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

const board = page => page.getByTestId("clock-v2");
const submitButton = page => page.getByTestId("ck-submit");
const hourBtn = (page, n) => page.getByTestId(`ck-hour-${n}`);

async function submitAttempt(page) {
  const resPromise = page.waitForResponse(r => r.url().includes("/v1/learning/attempts") && r.status() === 200);
  await submitButton(page).click();
  return await (await resPromise).json();
}

test.beforeEach(async ({ page }) => {
  page.setDefaultTimeout(180_000);
});

test("R17-E2E-01 (G1) 渲染不降级：钟面 12 数字 + 3:00 初始态", async ({ page }) => {
  const [entry] = await r17Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await expect(board(page)).toBeVisible();
  await expect(hourBtn(page, 12)).toBeVisible();
  await expect(hourBtn(page, 6)).toBeVisible();
  // 初始时针=3
  await expect(hourBtn(page, 3)).toHaveClass(/picked/);
  await expect(page.getByTestId("ck-minute-0")).toHaveClass(/picked/); // 整点
});

test("R17-E2E-02 (G2) 零拨针拦提交（EMPTY）", async ({ page }) => {
  const [entry] = await r17Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await expect(submitButton(page)).toBeDisabled();
  await expect(page.getByTestId("ck-evaluation")).toContainText("钟面还在原位");
});

test("R17-E2E-03 拨针生效：点 6 → 时针数字切换 + 指针旋转", async ({ page }) => {
  const [entry] = await r17Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await hourBtn(page, 6).click();
  await expect(hourBtn(page, 6)).toHaveClass(/picked/);
  await expect(hourBtn(page, 3)).not.toHaveClass(/picked/);
  await expect(page.getByTestId("ck-hour-hand")).toHaveAttribute("transform", "rotate(180 100 100)");
  await expect(page.getByTestId("ck-evaluation")).toContainText("拨好了：6:00");
});

test("R17-E2E-04 (G4/G6) envelope 合同：type/answer={value:360}/调整过程/事件链/无泄漏", async ({ page }) => {
  const [entry] = await r17Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await hourBtn(page, 6).click();
  const req = page.waitForRequest(r => r.url().includes("/v1/learning/attempts") && r.method() === "POST");
  await submitButton(page).click();
  const payload = JSON.parse((await req).postData() ?? "{}");
  expect(payload.response.type).toBe("clock");
  expect(payload.response.answer.value).toBe(360); // h*60+m 口径
  const data = payload.response.workspaces[0].data;
  for (const key of ["h", "m", "time_text", "adjust_history", "answer", "structure"]) expect(data).toHaveProperty(key);
  expect(data.time_text).toBe("6:00");
  expect(data.adjust_history).toEqual([["hour", 3, 6]]); // Gap"指针调整过程"
  expect(payload.response.representation).toBeUndefined();
  const types = payload.response.interaction_events.map(e => e.event_type);
  expect(types).toContain("CLOCK_HOUR_SET");
});

test("R17-E2E-05 hand_swap 专项：读长针数字拨 12 → 判错+关系错误分诊", async ({ page }) => {
  const [entry] = await r17Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await hourBtn(page, 12).click(); // 把长针指的 12 当时针读
  await expect(page.getByTestId("ck-evaluation")).toContainText("看着**长针**指的数字读钟");
  const result = await submitAttempt(page);
  expect(result.correct).toBe(false); // answer=720≠360
  expect((result.next_action || {}).type).toBe("HINT");
});

test("R17-E2E-06 半点链：长针拨半点（30）+ 时针合法组合", async ({ page }) => {
  const [entry] = await r17Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await page.getByTestId("ck-minute-30").click();
  await expect(page.getByTestId("ck-minute-30")).toHaveClass(/picked/);
  await expect(page.getByTestId("ck-minute-hand")).toHaveAttribute("transform", "rotate(180 100 100)");
  await hourBtn(page, 6).click(); // 6:30 合法组合
  await expect(page.getByTestId("ck-evaluation")).toContainText("差 30 分钟");
});

test("R17-E2E-07 (G5/G7) 修正路径：swap 判错→拨回→6:00→NEXT_TASK", async ({ page }) => {
  const [entry] = await r17Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await hourBtn(page, 12).click();
  const first = await submitAttempt(page);
  expect(first.correct).toBe(false);
  await hourBtn(page, 6).click();
  const second = await submitAttempt(page);
  expect(second.correct).toBe(true);
  expect((second.next_action || {}).type).toBe("NEXT_TASK");
  expect(second.attempt_no ?? 2).toBeGreaterThanOrEqual(2);
});

test("R17-E2E-08 撤销与重置：UNDO 回末次拨针，RESET 回 3:00+EMPTY", async ({ page }) => {
  const [entry] = await r17Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await hourBtn(page, 9).click();
  await page.getByTestId("ck-undo").click();
  await expect(hourBtn(page, 3)).toHaveClass(/picked/);
  await hourBtn(page, 6).click();
  await expect(hourBtn(page, 6)).toHaveClass(/picked/);
  await page.getByTestId("ck-reset").click();
  await expect(hourBtn(page, 3)).toHaveClass(/picked/);
  await expect(submitButton(page)).toBeDisabled(); // 重置回 EMPTY
});

test("R17-E2E-09 dblclick 防重入（R04-IDEM 同模式）", async ({ page }) => {
  const [entry] = await r17Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await hourBtn(page, 6).click();
  let posts = 0;
  page.on("request", r => {
    if (r.url().includes("/v1/learning/attempts") && r.method() === "POST") posts += 1;
  });
  await submitButton(page).dblclick();
  await page.waitForResponse(r => r.url().includes("/v1/learning/attempts"));
  await page.waitForTimeout(2500);
  expect(posts).toBe(1);
});

test("R17-E2E-10 healing 皮肤同链可用", async ({ page }) => {
  const healBase = process.env.E2E_HEALING_BASE;
  test.skip(!healBase, "未配置 E2E_HEALING_BASE");
  const [entry] = await r17Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(`${healBase}/child/math/session/e2e-${entry.sessionId}?child_id=${CHILD}&ability_id=${ABILITY}`);
  await expect(page.locator("[data-child-math-skin]")).toHaveAttribute("data-child-math-skin", "healing");
  await expect(board(page)).toBeVisible();
  await hourBtn(page, 6).click();
  const result = await submitAttempt(page);
  expect(result.correct).toBe(true);
});
