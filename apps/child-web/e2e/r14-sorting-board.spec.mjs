// FE-1426 R14 sorting-board 真实页面 E2E（B5 模板第十三实例；数字卡排序）。
// 合同：B5_E2E_VERTICAL_GATE.md + Gap R14（order evaluator/排序过程/比较维度错误）。
// Diagnosis 专项：卡面字号=干扰维度（与数值故意错开）——按字号排 →
// dimension_confusion 原料；answer=数值拼接 1247（正解）；视觉序=1274（判错+原料）。
// 数据卫生：CHILD=QA-Simulator …0099；ability=app_rd（第二题）。
// 钉题：FE-1422a 确定性 pin（v2-catalog → pin_resource_version_id），不靠 band 运气。
import { test, expect } from "@playwright/test";
import { fetchPinnedTasks } from "./pinned-tasks.mjs";

const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8000";
const CHILD = process.env.E2E_CHILD_ID ?? "00000000-0000-0000-0000-000000000099";
const ABILITY = "app_rd";

function r14Tasks(k) {
  return fetchPinnedTasks({ api: API, child: CHILD, renderer: "sorting-board", count: k });
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

const card = page => page.getByTestId("sorting-board-v2");
const submitButton = page => page.getByTestId("sb-submit");
const slot = (page, i) => page.getByTestId(`sb-card-${i}`);

/** 两步点选交换位置 i 与 j。 */
async function swap(page, i, j) {
  await slot(page, i).click();
  await slot(page, j).click();
}

async function submitAttempt(page) {
  const resPromise = page.waitForResponse(r => r.url().includes("/v1/learning/attempts") && r.status() === 200);
  await submitButton(page).click();
  return await (await resPromise).json();
}

test.beforeEach(async ({ page }) => {
  page.setDefaultTimeout(180_000);
});

test("R14-E2E-01 (G1) 渲染不降级：4 卡乱序 + 干扰字号显性化", async ({ page }) => {
  const [entry] = await r14Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await expect(card(page)).toBeVisible();
  // 初始 7,1,4,2
  await expect(slot(page, 0)).toHaveAttribute("data-value", "7");
  await expect(slot(page, 1)).toHaveAttribute("data-value", "1");
  // 干扰维度：数字 1 的卡字号最大（visual_rank=4→36px），数字 4 最小（rank1→15px）
  await expect(slot(page, 1)).toHaveCSS("font-size", "36px");
  await expect(slot(page, 2)).toHaveCSS("font-size", "15px");
});

test("R14-E2E-02 (G2) 零交换拦提交（EMPTY=还没动手比）", async ({ page }) => {
  const [entry] = await r14Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await expect(submitButton(page)).toBeDisabled();
  await page.getByTestId("sb-card-1").click(); // 只是拿起，不算交换
  await expect(submitButton(page)).toBeDisabled();
  await expect(page.getByTestId("sb-evaluation")).toContainText("先点两张卡交换");
});

test("R14-E2E-03 两步点选交换生效（位置互换）", async ({ page }) => {
  const [entry] = await r14Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await swap(page, 0, 1); // 7,1 → 1,7
  await expect(slot(page, 0)).toHaveAttribute("data-value", "1");
  await expect(slot(page, 1)).toHaveAttribute("data-value", "7");
  await expect(page.getByTestId("sb-evaluation")).toContainText("顺序还差一点"); // disordered
});

test("R14-E2E-04 toggle 放下：再点同一张取消选中", async ({ page }) => {
  const [entry] = await r14Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await slot(page, 0).click();
  await expect(slot(page, 0)).toHaveClass(/picked/);
  await slot(page, 0).click();
  await expect(slot(page, 0)).not.toHaveClass(/picked/);
});

test("R14-E2E-05 (G4/G6) envelope 合同：type/data/交换轨迹事件/无 representation 泄漏", async ({ page }) => {
  const [entry] = await r14Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await swap(page, 0, 1);
  await swap(page, 1, 3);
  const req = page.waitForRequest(r => r.url().includes("/v1/learning/attempts") && r.method() === "POST");
  await submitButton(page).click();
  const payload = JSON.parse((await req).postData() ?? "{}");
  expect(payload.response.type).toBe("sorting_board");
  const data = payload.response.workspaces[0].data;
  for (const key of ["order", "order_values", "swaps", "answer", "structure"]) expect(data).toHaveProperty(key);
  expect(data.order).toEqual(["c2", "c4", "c3", "c1"]); // id 轨迹
  expect(data.order_values).toEqual([1, 2, 4, 7]); // 数值轨迹
  expect(data.swaps).toEqual([[0, 1], [1, 3]]); // Gap"排序过程"
  expect(payload.response.representation).toBeUndefined();
  const types = payload.response.interaction_events.map(e => e.event_type);
  expect(types).toContain("SORT_CARD_SELECTED");
  expect(types.filter(t => t === "SORT_CARD_SWAPPED")).toHaveLength(2);
});

test("R14-E2E-06 dimension_confusion 专项：按字号排→判错但原料可分诊", async ({ page }) => {
  const [entry] = await r14Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  // (0,1),(1,3) → 1,2,4,7 再 (2,3) → 1,2,7,4 = 视觉字号序（4 字号最小排最后）
  await swap(page, 0, 1);
  await swap(page, 1, 3);
  await swap(page, 2, 3);
  await expect(slot(page, 2)).toHaveAttribute("data-value", "7");
  await expect(page.getByTestId("sb-evaluation")).toContainText("字的大小");
  const result = await submitAttempt(page);
  expect(result.correct).toBe(false); // answer=1274≠1247
  expect((result.next_action || {}).type).toBe("HINT");
});

test("R14-E2E-07 reversed 靶：完全降序判错 + 方向提示", async ({ page }) => {
  const [entry] = await r14Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await swap(page, 1, 2); // 7,4,1,2
  await swap(page, 2, 3); // 7,4,2,1 降序
  await expect(page.getByTestId("sb-evaluation")).toContainText("方向反啦");
  const result = await submitAttempt(page);
  expect(result.correct).toBe(false); // 7421
});

test("R14-E2E-08 (G5/G7) 修正路径：disordered→再交换→PASS 1247 NEXT_TASK", async ({ page }) => {
  const [entry] = await r14Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await swap(page, 0, 1); // 1,7,4,2
  const first = await submitAttempt(page);
  expect(first.correct).toBe(false);
  expect((first.next_action || {}).type).toBe("HINT");
  await swap(page, 1, 3); // 1,2,4,7
  await expect(page.getByTestId("sb-evaluation")).toContainText("从小到大排好了");
  const second = await submitAttempt(page);
  expect(second.correct).toBe(true);
  expect((second.next_action || {}).type).toBe("NEXT_TASK");
  expect(second.attempt_no ?? 2).toBeGreaterThanOrEqual(2);
});

test("R14-E2E-09 退回上次交换：撤销末次交换回中间态", async ({ page }) => {
  const [entry] = await r14Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await swap(page, 0, 1);
  await swap(page, 1, 3); // PASS 态
  await expect(page.getByTestId("sb-evaluation")).toContainText("从小到大排好了");
  await page.getByTestId("sb-undo-swap").click();
  // 末次交换是 [1,3]，退回 → order [c2,c1,c3,c4]=1,7,4,2（slot1=7、slot3=2）
  await expect(slot(page, 1)).toHaveAttribute("data-value", "7");
  await expect(slot(page, 3)).toHaveAttribute("data-value", "2");
  await expect(page.getByTestId("sb-evaluation")).toContainText("顺序还差一点");
});

test("R14-E2E-10 dblclick 防重入（R04-IDEM 同模式）", async ({ page }) => {
  const [entry] = await r14Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(sessionUrl(entry.sessionId));
  await swap(page, 0, 1);
  await swap(page, 1, 3);
  let posts = 0;
  page.on("request", r => {
    if (r.url().includes("/v1/learning/attempts") && r.method() === "POST") posts += 1;
  });
  await submitButton(page).dblclick();
  await page.waitForResponse(r => r.url().includes("/v1/learning/attempts"));
  await page.waitForTimeout(2500);
  expect(posts).toBe(1);
});

test("R14-E2E-11 healing 皮肤同链可用", async ({ page }) => {
  const healBase = process.env.E2E_HEALING_BASE;
  test.skip(!healBase, "未配置 E2E_HEALING_BASE");
  const [entry] = await r14Tasks(1);
  await pinTasks(page, [entry]);
  await page.goto(`${healBase}/child/math/session/e2e-${entry.sessionId}?child_id=${CHILD}&ability_id=${ABILITY}`);
  await expect(page.locator("[data-child-math-skin]")).toHaveAttribute("data-child-math-skin", "healing");
  await expect(card(page)).toBeVisible();
  await swap(page, 0, 1);
  await swap(page, 1, 3);
  const result = await submitAttempt(page);
  expect(result.correct).toBe(true);
});
