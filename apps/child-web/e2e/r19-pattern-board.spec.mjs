// FE-1436 R19 pattern-board 真实页面 E2E（B5 模板第十八实例；ABAB 花边接着摆）。
// 合同：B5_E2E_VERTICAL_GATE.md + Gap R19（pattern evaluator/尝试顺序修改过程/规律识别错误 P0）。
// 可见 黄蓝黄蓝 + 2 空格；正解 [黄,蓝]=12。
// 分诊：全蓝 [2,2]=rule_ignored；[2,1]=phase_shift；改过珠凑对=判对+changed_once 留痕（解耦第九次）。
// 数据卫生：CHILD=QA-Simulator …0099；ability=app_rel（第四题）。
import { test, expect } from "@playwright/test";
import { fetchPinnedTasks } from "./pinned-tasks.mjs";

const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8000";
const CHILD = process.env.E2E_CHILD_ID ?? "00000000-0000-0000-0000-000000000099";
const ABILITY = "app_rel";

function r19Tasks(k) {
  return fetchPinnedTasks({ api: API, child: CHILD, renderer: "pattern-board", count: k });
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

const board = page => page.getByTestId("pattern-board-v2");
const submitButton = page => page.getByTestId("pb-submit");
const yellow = page => page.getByTestId("pb-token-1");
const blue = page => page.getByTestId("pb-token-2");
const blank = (page, i) => page.getByTestId(`pb-blank-${i}`);

async function submitAttempt(page) {
  const resPromise = page.waitForResponse(r => r.url().includes("/v1/learning/attempts") && r.status() === 200);
  await submitButton(page).click();
  return await (await resPromise).json();
}

test.beforeEach(async ({ page }) => {
  page.setDefaultTimeout(180_000);
});

test("R19-E2E-01 (G1) 渲染不降级：4 固定珠 + 2 空格 + 两色调色板", async ({ page }) => {
  const [entry] = await r19Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await expect(board(page)).toBeVisible();
  await expect(page.getByTestId("pb-strip").locator(".pb-bead")).toHaveCount(6);
  await expect(blank(page, 0)).toHaveClass(/blank/);
  await expect(blank(page, 1)).toHaveClass(/blank/);
  await expect(yellow(page)).toBeVisible();
  await expect(blue(page)).toBeVisible();
});

test("R19-E2E-02 (G2) 空格没填满拦提交（EMPTY）", async ({ page }) => {
  const [entry] = await r19Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await expect(submitButton(page)).toBeDisabled();
  await yellow(page).click(); // 填 1 颗
  await expect(submitButton(page)).toBeDisabled();
  await expect(page.getByTestId("pb-evaluation")).toContainText("还差 1 颗");
});

test("R19-E2E-03 正解：黄蓝填满 → PASS 提示 + 提交可用", async ({ page }) => {
  const [entry] = await r19Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await yellow(page).click();
  await blue(page).click();
  await expect(blank(page, 0)).toHaveCSS("background-color", "rgb(224, 168, 0)"); // 黄
  await expect(blank(page, 1)).toHaveCSS("background-color", "rgb(59, 111, 181)"); // 蓝
  await expect(page.getByTestId("pb-evaluation")).toContainText("摆对了");
  await expect(submitButton(page)).toBeEnabled();
});

test("R19-E2E-04 (G4/G6) envelope 合同：type/answer={value:12}/beads/事件链/无泄漏", async ({ page }) => {
  const [entry] = await r19Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await yellow(page).click();
  await blue(page).click();
  const req = page.waitForRequest(r => r.url().includes("/v1/learning/attempts") && r.method() === "POST");
  await submitButton(page).click();
  const payload = JSON.parse((await req).postData() ?? "{}");
  expect(payload.response.type).toBe("pattern_board");
  expect(payload.response.answer.value).toBe(12); // token 拼接
  const data = payload.response.workspaces[0].data;
  for (const key of ["visible", "beads", "period", "attempt_history", "answer", "structure"]) expect(data).toHaveProperty(key);
  expect(data.beads).toEqual([1, 2]);
  expect(data.period).toBe(2);
  expect(data.attempt_history).toEqual([[0, null, 1], [1, null, 2]]); // Gap"尝试顺序"
  expect(data.structure.changed_once).toBe(false);
  expect(payload.response.representation).toBeUndefined();
  const types = payload.response.interaction_events.map(e => e.event_type);
  expect(types.filter(t => t === "PATTERN_BEAD_PLACED")).toHaveLength(2);
});

test("R19-E2E-05 rule_ignored 专项：全摆蓝→判错+没找规律分诊", async ({ page }) => {
  const [entry] = await r19Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await blue(page).click();
  await blue(page).click(); // [2,2]
  await expect(page.getByTestId("pb-evaluation")).toContainText("全摆成一种颜色");
  const result = await submitAttempt(page);
  expect(result.correct).toBe(false); // 22≠12
  expect((result.next_action || {}).type).toBe("HINT");
});

test("R19-E2E-06 phase_shift 专项：[蓝,黄]→判错+相位偏移分诊", async ({ page }) => {
  const [entry] = await r19Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await blue(page).click();
  await yellow(page).click(); // [2,1]=后移一位
  await expect(page.getByTestId("pb-evaluation")).toContainText("从上一颗重新数");
  const result = await submitAttempt(page);
  expect(result.correct).toBe(false); // 21≠12
});

test("R19-E2E-07 解耦靶+修改留痕：先摆错[蓝蓝]→抠掉一颗→改成黄=[黄蓝]判对+changed_once", async ({ page }) => {
  const [entry] = await r19Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await blue(page).click();
  await blue(page).click(); // [2,2] wrong
  // 抠掉第 1 颗（点选中珠两次：第一次选中，第二次抠掉）
  await blank(page, 0).click();
  await blank(page, 0).click();
  await expect(blank(page, 0)).toHaveClass(/blank/); // slot0 空了 → [null,2]
  await yellow(page).click(); // 填回黄 → [1,2] 但 attempt 4>2
  await expect(page.getByTestId("pb-evaluation")).toContainText("改过一次也算数");
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
  expect(payload.response.answer.value).toBe(12);
  expect(payload.response.workspaces[0].data.structure.changed_once).toBe(true);
  expect(payload.response.workspaces[0].data.attempt_history.length).toBeGreaterThan(2); // Gap"修改过程"
});

test("R19-E2E-08 (G5/G7) 修正路径：rule_ignored 判错→抠换→NEXT_TASK", async ({ page }) => {
  const [entry] = await r19Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await blue(page).click();
  await blue(page).click();
  const first = await submitAttempt(page);
  expect(first.correct).toBe(false);
  await blank(page, 1).click();
  await blank(page, 1).click(); // 抠掉 slot1 → [2,null]
  await yellow(page).click(); // [2,1] phase_shift——先确认中间态提示
  await expect(page.getByTestId("pb-evaluation")).toContainText("从上一颗重新数");
  await blank(page, 0).click();
  await blank(page, 0).click(); // 抠 slot0 → [null,1]
  await yellow(page).click(); // [1,1]
  await blank(page, 1).click();
  await blank(page, 1).click(); // 抠 slot1 → [1,null]
  await blue(page).click(); // [1,2] PASS
  await expect(page.getByTestId("pb-evaluation")).toContainText("摆对了");
  const second = await submitAttempt(page);
  expect(second.correct).toBe(true);
  expect((second.next_action || {}).type).toBe("NEXT_TASK");
  expect(second.attempt_no ?? 2).toBeGreaterThanOrEqual(2);
});

test("R19-E2E-09 重置：填满后 RESET 回全空+拦提交", async ({ page }) => {
  const [entry] = await r19Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await yellow(page).click();
  await blue(page).click();
  await expect(submitButton(page)).toBeEnabled();
  await page.getByTestId("pb-reset").click();
  await expect(blank(page, 0)).toHaveClass(/blank/);
  await expect(blank(page, 1)).toHaveClass(/blank/);
  await expect(submitButton(page)).toBeDisabled();
});

test("R19-E2E-10 dblclick 防重入（R04-IDEM 同模式）", async ({ page }) => {
  const [entry] = await r19Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await yellow(page).click();
  await blue(page).click();
  let posts = 0;
  page.on("request", r => {
    if (r.url().includes("/v1/learning/attempts") && r.method() === "POST") posts += 1;
  });
  await submitButton(page).dblclick();
  await page.waitForResponse(r => r.url().includes("/v1/learning/attempts"));
  await page.waitForTimeout(2500);
  expect(posts).toBe(1);
});

test("R19-E2E-11 healing 皮肤同链可用", async ({ page }) => {
  const healBase = process.env.E2E_HEALING_BASE;
  test.skip(!healBase, "未配置 E2E_HEALING_BASE");
  const [entry] = await r19Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(`${healBase}/child/math/session/e2e-${entry.sessionId}?child_id=${CHILD}&ability_id=${ABILITY}`);
  await expect(page.locator("[data-child-math-skin]")).toHaveAttribute("data-child-math-skin", "healing");
  await expect(board(page)).toBeVisible();
  await yellow(page).click();
  await blue(page).click();
  const result = await submitAttempt(page);
  expect(result.correct).toBe(true);
});
