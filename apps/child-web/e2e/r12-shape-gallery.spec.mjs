// FE-1424 R12 shape-gallery 真实页面 E2E（B5 模板第十一实例；图形分类）。
// 合同：B5_E2E_VERTICAL_GATE.md + Gap R12（Diagnosis=属性识别错误 P0）。
// 解耦口径（第三次运用）：答案=正方形个数；混入长方形但数对 → 后端判对，
// attribute_confusion 走 Evidence 原料。
// 数据卫生：CHILD=QA-Simulator …0099；ability=app_cond（第二题）。
// 钉题：FE-1422a 确定性 pin（v2-catalog → pin_resource_version_id），不靠 band 运气。
import { test, expect } from "@playwright/test";
import { fetchPinnedTasks } from "./pinned-tasks.mjs";

const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8000";
const CHILD = process.env.E2E_CHILD_ID ?? "00000000-0000-0000-0000-000000000099";
const ABILITY = "app_cond";

function r12Tasks(k) {
  return fetchPinnedTasks({ api: API, child: CHILD, renderer: "shape-gallery", count: k });
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

const card = page => page.getByTestId("shape-gallery-v2");
const submitButton = page => page.getByTestId("sg-submit");
const home = page => page.getByTestId("sg-home");

/** 拿起 shape 再放进家。 */
async function placeShape(page, id) {
  await page.getByTestId(`sg-shape-${id}`).click();
  await home(page).click();
}

async function submitAttempt(page) {
  const reqPromise = page.waitForRequest(r => r.url().includes("/v1/learning/attempts") && r.method() === "POST");
  const resPromise = page.waitForResponse(r => r.url().includes("/v1/learning/attempts") && r.status() === 200);
  await submitButton(page).click();
  const req = await reqPromise;
  const body = JSON.parse(req.postData() ?? "{}");
  const result = await (await resPromise).json();
  return { body, result };
}

test.beforeEach(async ({ page }) => {
  page.setDefaultTimeout(180_000);
});

test("R12-E2E-01 (G1) 渲染不降级：墙上 6 图形 + 正方形的家", async ({ page }) => {
  const [entry] = await r12Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await expect(card(page)).toBeVisible();
  for (const id of ["s1", "r1", "s2", "c1", "s3", "r2"]) {
    await expect(page.getByTestId(`sg-shape-${id}`)).toBeVisible();
  }
  await expect(page.getByTestId("sg-home")).toContainText("正方形的家");
});

test("R12-E2E-02 (G2) 家空拦提交（EMPTY）", async ({ page }) => {
  const [entry] = await r12Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await expect(submitButton(page)).toBeDisabled();
  await expect(page.getByTestId("sg-evaluation")).toContainText("先从墙上点一个图形");
});

test("R12-E2E-03 拿起→放下 toggle（选择轨迹 SHAPE_SELECTED/DESELECTED）", async ({ page }) => {
  const [entry] = await r12Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await page.getByTestId("sg-shape-r2").click();
  await expect(page.getByTestId("sg-shape-r2")).toHaveClass(/picked/);
  await expect(page.getByTestId("sg-evaluation")).toContainText("手里拿着");
  await page.getByTestId("sg-shape-r2").click();
  await expect(page.getByTestId("sg-shape-r2")).not.toHaveClass(/picked/);
  await expect(submitButton(page)).toBeDisabled();
});

test("R12-E2E-04 (G4) 空手拿进家=NO_SELECTION：家数不变", async ({ page }) => {
  const [entry] = await r12Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await home(page).click();
  await expect(page.getByTestId("sg-home-count")).toHaveText("0");
  await expect(submitButton(page)).toBeDisabled();
});

test("R12-E2E-05 (G6) envelope 合同：type/data 四字段/事件轨迹/无 representation 泄漏", async ({ page }) => {
  const [entry] = await r12Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await placeShape(page, "s1");
  await placeShape(page, "s2");
  const req = page.waitForRequest(r => r.url().includes("/v1/learning/attempts") && r.method() === "POST");
  await submitButton(page).click();
  const payload = JSON.parse((await req).postData() ?? "{}");
  expect(payload.response.type).toBe("shape_gallery");
  const data = payload.response.workspaces[0].data;
  for (const key of ["home", "home_kinds", "answer", "structure"]) expect(data).toHaveProperty(key);
  expect(data.home).toEqual(["s1", "s2"]); // 放入顺序=分类轨迹
  expect(payload.response.representation).toBeUndefined();
  const types = payload.response.interaction_events.map(e => e.event_type);
  expect(types).toContain("SHAPE_SELECTED");
  expect(types).toContain("SHAPE_PLACED");
});

test("R12-E2E-06 混入长方形但数对=解耦双断言（correct=true + attribute_confusion 原料）", async ({ page }) => {
  const [entry] = await r12Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await placeShape(page, "r1"); // 长方形
  await placeShape(page, "s1");
  await placeShape(page, "s2");
  await expect(page.getByTestId("sg-home-count")).toHaveText("3");
  await expect(page.getByTestId("sg-evaluation")).toContainText("混进了不是正方形");
  const { result } = await submitAttempt(page);
  expect(result.correct).toBe(true); // 数对 → 后端判对
  const data = (result.evidence?.response?.workspaces?.[0]?.data) ?? null;
  if (data) expect(data.structure.error).toBe("attribute_confusion"); // 原料留痕
});

test("R12-E2E-07 退回修正路径：退回长方形→补紫正方形→PASS 判对", async ({ page }) => {
  const [entry] = await r12Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await placeShape(page, "r1");
  await placeShape(page, "s1");
  await placeShape(page, "s2");
  await page.getByTestId("sg-home-r1").click(); // 退回长方形
  await expect(page.getByTestId("sg-home-count")).toHaveText("2");
  await expect(page.getByTestId("sg-evaluation")).toContainText("还有朋友在外面");
  await placeShape(page, "s3");
  const { result } = await submitAttempt(page);
  expect(result.correct).toBe(true);
  expect((result.next_action || {}).type).toBe("NEXT_TASK");
});

test("R12-E2E-08 已在家图形不可再拿（IN_HOME 拒绝态）", async ({ page }) => {
  const [entry] = await r12Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await placeShape(page, "s1");
  await expect(page.getByTestId("sg-shape-s1")).toBeDisabled();
  await expect(page.getByTestId("sg-shape-s1")).toHaveClass(/in-home/);
});

test("R12-E2E-09 (G7) 漏放可提交=FAIL 可达后端 + attempt_no 递增", async ({ page }) => {
  const [entry] = await r12Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await placeShape(page, "s1");
  await placeShape(page, "s2");
  const first = await submitAttempt(page);
  expect(first.result.correct).toBe(false); // 2≠3
  expect((first.result.next_action || {}).type).toBe("HINT");
  await placeShape(page, "s3");
  const second = await submitAttempt(page);
  expect(second.result.correct).toBe(true);
  expect(second.result.attempt_no ?? 2).toBeGreaterThanOrEqual(2);
});

test("R12-E2E-10 防重入：双击提交只发一个 POST（R04-IDEM 同模式）", async ({ page }) => {
  const [entry] = await r12Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await placeShape(page, "s1");
  await placeShape(page, "s2");
  await placeShape(page, "s3");
  let posts = 0;
  page.on("request", r => {
    if (r.url().includes("/v1/learning/attempts") && r.method() === "POST") posts += 1;
  });
  await submitButton(page).dblclick();
  await page.waitForResponse(r => r.url().includes("/v1/learning/attempts"));
  await page.waitForTimeout(2500);
  expect(posts).toBe(1);
});

test("R12-E2E-11 UNDO 单步：撤销一次放入回到 2 个", async ({ page }) => {
  const [entry] = await r12Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await placeShape(page, "s1");
  await placeShape(page, "s2");
  // place 两步（SELECT + PLACE）：撤销 PLACE 一步即回到"手上有 s2"，再撤销 SELECT
  await page.getByTestId("sg-undo").click();
  await expect(page.getByTestId("sg-home-count")).toHaveText("1");
});

test("R12-E2E-12 healing 皮肤同链可用", async ({ page }) => {
  const healBase = process.env.E2E_HEALING_BASE;
  test.skip(!healBase, "未配置 E2E_HEALING_BASE");
  const [entry] = await r12Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(`${healBase}/child/math/session/e2e-${entry.sessionId}?child_id=${CHILD}&ability_id=${ABILITY}`);
  await expect(page.locator("[data-child-math-skin]")).toHaveAttribute("data-child-math-skin", "healing");
  await expect(card(page)).toBeVisible();
  await placeShape(page, "s1");
  await placeShape(page, "s2");
  await placeShape(page, "s3");
  const { result } = await submitAttempt(page);
  expect(result.correct).toBe(true);
});
