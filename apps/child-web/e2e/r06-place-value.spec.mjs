// FE-1419 R06 place-value 真实页面 E2E（B5 模板第六实例；位值混淆诊断专项）。
// 合同：B5_E2E_VERTICAL_GATE.md 口径 + Gap R06（Diagnosis=位值混淆 P0）。
// 钉题：FE-1422a 确定性 pin（v2-catalog → pin_resource_version_id），不靠 band 运气。
// 数据卫生：CHILD=QA-Simulator …0099。金题 ability=app_rd，target=352，pool=[2,5,3]。
import { test, expect, request as pwRequest } from "@playwright/test";
import { fetchPinnedTasks } from "./pinned-tasks.mjs";

const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8000";
const CHILD = process.env.E2E_CHILD_ID ?? "00000000-0000-0000-0000-000000000099";
const ABILITY = "app_rd";

function r06Tasks(k) {
  return fetchPinnedTasks({ api: API, child: CHILD, renderer: "place-value", count: k });
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

const card = page => page.getByTestId("place-value-v2");
const submitButton = page => page.getByTestId("pv-submit");
const tile = (page, d) => page.getByTestId(`pv-tile-${d}`);
const slot = (page, j) => page.getByTestId(`pv-slot-${j}`);

/** 牌→框：点数字卡再点第 j 个框。 */
async function putDigit(page, d, j) {
  await tile(page, d).click();
  await slot(page, j).click();
}

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

// ---------- G1：渲染不降级 + EMPTY ----------
test("R06-E2E-09 (G1) 渲染 place-value V2，未放满禁提交", async ({ page }) => {
  const [r] = await r06Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("g1"));
  await expect(card(page)).toBeVisible();
  await expect(page.getByTestId("planned-renderer")).toHaveCount(0);
  await expect(page.getByTestId("pv-evaluation")).toContainText("还有框没放上数字");
  await expect(submitButton(page)).toBeDisabled();
});

// ---------- G2/G3：只放一部分仍 EMPTY ----------
test("R06-E2E-03 (G2/G3) 放两张不放第三张 → 仍 EMPTY 不可提交", async ({ page }) => {
  const [r] = await r06Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("partial"));
  await putDigit(page, 3, 0);
  await putDigit(page, 5, 1);
  await expect(page.getByTestId("pv-evaluation")).toContainText("还有框没放上数字");
  await expect(submitButton(page)).toBeDisabled();
  let posted = false;
  page.on("request", q => { if (q.url().includes("/v1/learning/attempts")) posted = true; });
  await page.waitForTimeout(400);
  expect(posted).toBe(false);
});

// ---------- R06 专项：位值混淆（FAIL 可提交 + place_confusion 证据） ----------
test("R06-CONFUSE (G6/G4) 百3十2个5=325 → place_confusion 提示 → envelope 证据 → HINT", async ({ page }) => {
  const [r] = await r06Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("confuse"));
  await putDigit(page, 3, 0); // 百=3 对
  await putDigit(page, 2, 1); // 十=2 错（该是5）
  await putDigit(page, 5, 2); // 个=5 错（该是2）
  await expect(page.getByTestId("pv-evaluation")).toContainText("站错了位置");
  await expect(submitButton(page)).toBeEnabled(); // FAIL 可提交（P0-01）

  const { body, result } = await submitAttempt(page);

  const resp = body.response;
  expect(resp.schema_version).toBe("2.0");
  expect(resp.type).toBe("place_value");
  expect(resp.answer.value).toBe(325);
  const data = resp.workspaces[0].data;
  expect(data.slots).toEqual([3, 2, 5]);
  expect(data.pool_remaining).toEqual([]);
  expect(data.target_digits).toEqual([3, 5, 2]);
  // R06 Diagnosis P0 核心断言：位值混淆原料入库
  expect(data.structure.error).toBe("place_confusion");
  expect(data.structure.place_value).toBe(true);
  const types = resp.interaction_events.map(e => e.event_type);
  expect(types).toContain("DIGIT_PICKED");
  expect(types).toContain("DIGIT_PLACED");

  expect(result.correct).toBe(false);
  expect(result.next_action.type).toBe("HINT");
  await expect(page.getByRole("button", { name: /给我一点提示/ })).toBeVisible();
});

// ---------- swap 修正路径：把站错的 2/5 交换回来 → PASS ----------
test("R06-SWAP 交换十/个两张卡改对 → structure PASS → correct=true", async ({ page }) => {
  const [r] = await r06Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("swap"));
  await putDigit(page, 3, 0);
  await putDigit(page, 2, 1); // 错位
  await putDigit(page, 5, 2); // 错位
  // 修正：拾 5（收回后在框 2？——先点框 2 收回 5 到堆），再 5→十、2→个
  await slot(page, 2).click(); // 无选中态点框 = return 5 回堆
  await expect(tile(page, 5)).toBeVisible();
  await putDigit(page, 5, 1); // 十=5（swap：挤回 2 到堆）
  await expect(tile(page, 2)).toBeVisible(); // 2 回到堆
  await putDigit(page, 2, 2); // 个=2
  await expect(page.getByTestId("pv-evaluation")).toContainText("位值放对了：352");
  const { body, result } = await submitAttempt(page);
  expect(body.response.workspaces[0].data.structure).toEqual({
    status: "PASS", error: null, place_value: true
  });
  expect(result.correct).toBe(true);
  expect(result.next_action.type).toBe("NEXT_TASK");
});

// ---------- G5：直接摆对 ----------
test("R06-E2E-01 (G5) 3→百 5→十 2→个 → correct=true → NEXT_TASK", async ({ page }) => {
  const [r] = await r06Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("right"));
  await putDigit(page, 3, 0);
  await putDigit(page, 5, 1);
  await putDigit(page, 2, 2);
  await expect(page.getByTestId("pv-evaluation")).toContainText("位值放对了：352");
  const { result } = await submitAttempt(page);
  expect(result.correct).toBe(true);
  await expect(page.getByRole("button", { name: /下一题/ })).toBeVisible();
});

// ---------- G7：重试链 ----------
test("R06-G7 混淆提交错 → 提示 → 改对：attempt_no=2", async ({ page }) => {
  const [r] = await r06Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("retry"));
  await putDigit(page, 3, 0);
  await putDigit(page, 2, 1);
  await putDigit(page, 5, 2);
  const first = await submitAttempt(page);
  expect(first.result.correct).toBe(false);

  await page.getByRole("button", { name: /给我一点提示/ }).click();
  await expect(page.getByRole("button", { name: /我再想想/ })).toBeVisible();
  await page.getByRole("button", { name: /我再想想/ }).click();

  // RETRY 不清板：直接交换修正（同 SWAP 用例路径）
  await slot(page, 2).click();
  await putDigit(page, 5, 1);
  await putDigit(page, 2, 2);
  const second = await submitAttempt(page);
  expect(second.result.correct).toBe(true);
  expect(second.body.attempt_no).toBe(2);
});

// ---------- 防重入 + UNDO ----------
test("R06-E2E-07 双击只一个 POST；UNDO 收回最后一张", async ({ page }) => {
  const [r] = await r06Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("undo"));
  await putDigit(page, 3, 0);
  await putDigit(page, 5, 1);
  await putDigit(page, 2, 2);
  // pick 与 place 各是一步 history：两次撤销回"2 还在牌堆"的干净态
  await page.getByTestId("pv-undo").click();
  await page.getByTestId("pv-undo").click();
  await expect(page.getByTestId("pv-slot-digit-2")).toHaveText(" ");
  await expect(page.getByTestId("pv-evaluation")).toContainText("还有框没放上数字");
  await putDigit(page, 2, 2);

  let posts = 0;
  page.on("request", q => {
    if (q.url().includes("/v1/learning/attempts") && q.method() === "POST") posts += 1;
  });
  await submitButton(page).dblclick();
  await page.waitForTimeout(2500);
  expect(posts).toBe(1);
});

// ---------- E2E-08：revision 切换清态 ----------
test("R06-E2E-08 下一题清空框和牌堆", async ({ page }) => {
  const two = await r06Tasks(2);
  const task2 = structuredClone(two[1].task);
  task2.ui_schema.ui_revision = `${two[1].task.ui_schema.ui_revision}-rev2`;
  await pinTasks(page, [two[0], { task: task2, sessionId: two[1].sessionId }]);
  await page.goto(sessionUrl("rev"));
  await putDigit(page, 3, 0);
  await putDigit(page, 5, 1);
  await putDigit(page, 2, 2);
  await submitAttempt(page);
  await page.getByRole("button", { name: /下一题/ }).click();
  await expect(card(page)).toBeVisible();
  await expect(page.getByTestId("pv-slot-digit-0")).toHaveText(" ");
  await expect(tile(page, 2)).toBeVisible();
  await expect(tile(page, 5)).toBeVisible();
  await expect(tile(page, 3)).toBeVisible();
  await expect(submitButton(page)).toBeDisabled();
});

// ---------- 双皮肤 ----------
test("R06-E2E-10 healing 皮肤同契约", async ({ page }) => {
  test.skip(!process.env.E2E_HEALING_BASE, "需 3101 healing 实例");
  const [r] = await r06Tasks(1);
  await pinTasks(page, [r]);
  const url = new URL(sessionUrl("healing"), process.env.E2E_HEALING_BASE);
  await page.goto(url.toString());
  await expect(page.locator("[data-child-math-skin]")).toHaveAttribute("data-child-math-skin", "healing");
  await putDigit(page, 3, 0);
  await putDigit(page, 5, 1);
  await putDigit(page, 2, 2);
  const { body, result } = await submitAttempt(page);
  expect(body.response.type).toBe("place_value");
  expect(result.correct).toBe(true);
});
