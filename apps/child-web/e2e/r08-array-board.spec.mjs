// FE-1421 R08 array-board 真实页面 E2E（B5 模板第八实例；product/structure 解耦专项）。
// 合同：B5_E2E_VERTICAL_GATE.md + Gap R08（Diagnosis=行列概念错误 P0）。
// 数据卫生：CHILD=QA-Simulator …0099；ability=app_model，target=3行×4列。
import { test, expect, request as pwRequest } from "@playwright/test";

const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8000";
const CHILD = process.env.E2E_CHILD_ID ?? "00000000-0000-0000-0000-000000000099";
const ABILITY = "app_model";

async function fetchTasks(n) {
  const ctx = await pwRequest.newContext({ baseURL: API });
  const tasks = [];
  for (let s = 0; s < 30 && tasks.length < n; s += 1) {
    const session = await ctx.post("/v1/learning/sessions", {
      data: { child_id: CHILD, subject: "math", requested_minutes: 15 }
    });
    const sid = (await session.json()).session_id;
    for (let i = 0; i < 16 && tasks.length < n; i += 1) {
      const resp = await ctx.post("/v1/learning/tasks/next", {
        data: { child_id: CHILD, session_id: sid, subject: "math", ability_id: ABILITY, requested_minutes: 15 }
      });
      const t = await resp.json();
      const ui = t.ui_schema || {};
      const ws = (ui.workspaces || [])[0] || {};
      if (ui.schema_version === "2.0" && ws.renderer === "array-board") {
        tasks.push({ task: t, sessionId: sid });
      }
    }
  }
  await ctx.dispose();
  if (tasks.length < n) throw new Error(`预取 R08 task 不足：${tasks.length}/${n}`);
  return tasks;
}

let taskPool = null;
let poolCursor = 0;

async function r08Tasks(k) {
  if (!taskPool) taskPool = await fetchTasks(8);
  const out = [];
  for (let i = 0; i < k; i += 1) out.push(taskPool[poolCursor++ % taskPool.length]);
  return out;
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

const card = page => page.getByTestId("array-board-v2");
const submitButton = page => page.getByTestId("ab-submit");

async function grow(page, rows, cols) {
  for (let i = 0; i < rows; i += 1) await page.getByTestId("ab-row-plus").click();
  for (let i = 0; i < cols; i += 1) await page.getByTestId("ab-col-plus").click();
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
test("R08-E2E-09 (G1) 渲染 array-board V2，空阵列禁提交", async ({ page }) => {
  const [r] = await r08Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("g1"));
  await expect(card(page)).toBeVisible();
  await expect(page.getByTestId("planned-renderer")).toHaveCount(0);
  await expect(page.getByTestId("ab-evaluation")).toContainText("还没排出阵列");
  await expect(submitButton(page)).toBeDisabled();
});

// ---------- G2/G3：只加行不加列仍 EMPTY ----------
test("R08-E2E-03 (G2/G3) 只加行 → 积 0 仍 EMPTY 不可提交", async ({ page }) => {
  const [r] = await r08Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("empty"));
  for (let i = 0; i < 3; i += 1) await page.getByTestId("ab-row-plus").click();
  await expect(page.getByTestId("ab-evaluation")).toContainText("还没排出阵列");
  await expect(submitButton(page)).toBeDisabled();
  let posted = false;
  page.on("request", q => { if (q.url().includes("/v1/learning/attempts")) posted = true; });
  await page.waitForTimeout(400);
  expect(posted).toBe(false);
});

// ---------- R08 核心专项：transpose（积对但行列互换=判对+原料留痕） ----------
test("R08-TRANSPOSE 摆 4×3（目标3×4）→ 提示'说反了' → 后端 correct=true 但 structure=transpose", async ({ page }) => {
  const [r] = await r08Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("transpose"));
  await grow(page, 4, 3);
  await expect(page.getByTestId("ab-evaluation")).toContainText("行和列说反了");
  await expect(submitButton(page)).toBeEnabled(); // FAIL 可提交（P0-01）

  const { body, result } = await submitAttempt(page);

  expect(body.response.type).toBe("array_board");
  const data = body.response.workspaces[0].data;
  expect(data.rows).toBe(4);
  expect(data.columns).toBe(3);
  expect(data.product).toBe(12);
  expect(data.target_structure).toEqual({ rows: 3, columns: 4 });
  // 解耦实锤：积对→后端判对；结构互换→原料留痕
  expect(data.structure.error).toBe("transpose");
  expect(result.correct).toBe(true);

  const types = body.response.interaction_events.map(e => e.event_type);
  expect(types).toContain("ARRAY_ROW_ADDED");
  expect(types).toContain("ARRAY_COL_ADDED");
});

// ---------- count：行列数真错 ----------
test("R08-COUNT 摆 2×5=10 → count 提示 → correct=false → HINT", async ({ page }) => {
  const [r] = await r08Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("count"));
  await grow(page, 2, 5);
  await expect(page.getByTestId("ab-evaluation")).toContainText("和题目要的不一样");
  const { body, result } = await submitAttempt(page);
  expect(body.response.workspaces[0].data.structure.error).toBe("count");
  expect(result.correct).toBe(false);
  expect(result.next_action.type).toBe("HINT");
  await expect(page.getByRole("button", { name: /给我一点提示/ })).toBeVisible();
});

// ---------- G5：正确 3×4 ----------
test("R08-E2E-01 (G5) 3行4列=12 → PASS → correct=true → NEXT_TASK", async ({ page }) => {
  const [r] = await r08Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("pass"));
  await grow(page, 3, 4);
  await expect(page.getByTestId("ab-evaluation")).toContainText("摆对啦");
  await expect(page.getByTestId("ab-grid").locator(".ab-dot")).toHaveCount(12);
  const { body, result } = await submitAttempt(page);
  expect(body.response.workspaces[0].data.structure).toEqual({
    status: "PASS", error: null, array: true
  });
  expect(result.correct).toBe(true);
  await expect(page.getByRole("button", { name: /下一题/ })).toBeVisible();
});

// ---------- G7：count 错改对 ----------
test("R08-G7 2×5 错 → 提示 → 改成 3×4：attempt_no=2", async ({ page }) => {
  const [r] = await r08Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("retry"));
  await grow(page, 2, 5);
  const first = await submitAttempt(page);
  expect(first.result.correct).toBe(false);
  await page.getByRole("button", { name: /给我一点提示/ }).click();
  await page.getByRole("button", { name: /我再想想/ }).click();
  // 调整：行+1、列-1
  await page.getByTestId("ab-row-plus").click();
  await page.getByTestId("ab-col-minus").click();
  await expect(page.getByTestId("ab-rows")).toHaveText("3");
  await expect(page.getByTestId("ab-cols")).toHaveText("4");
  const second = await submitAttempt(page);
  expect(second.result.correct).toBe(true);
  expect(second.body.attempt_no).toBe(2);
});

// ---------- 钳制 + UNDO + 防重入 ----------
test("R08-E2E-07 越界钳制；UNDO 回退一行；双击只 1 POST", async ({ page }) => {
  const [r] = await r08Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("undo"));
  // 行加到 8（max）：第 9 次按钮应 disabled
  for (let i = 0; i < 8; i += 1) await page.getByTestId("ab-row-plus").click();
  await expect(page.getByTestId("ab-row-plus")).toBeDisabled();
  await page.getByTestId("ab-row-minus").click();
  await grow(page, 0, 4); // 列 4（现 7×4）
  // UNDO 一步：回退最后一个动作（第4次加列）→ 7×3
  await page.getByTestId("ab-undo").click();
  await expect(page.getByTestId("ab-cols")).toHaveText("3");
  // 重置后摆成正确 3×4
  await page.getByTestId("ab-reset").click();
  await expect(page.getByTestId("ab-rows")).toHaveText("0");
  await grow(page, 3, 4);
  let posts = 0;
  page.on("request", q => {
    if (q.url().includes("/v1/learning/attempts") && q.method() === "POST") posts += 1;
  });
  await submitButton(page).dblclick();
  await page.waitForTimeout(2500);
  expect(posts).toBe(1);
});

// ---------- E2E-08：revision 切换清态 ----------
test("R08-E2E-08 下一题清空行列", async ({ page }) => {
  const two = await r08Tasks(2);
  const task2 = structuredClone(two[1].task);
  task2.ui_schema.ui_revision = `${two[1].task.ui_schema.ui_revision}-rev2`;
  await pinTasks(page, [two[0], { task: task2, sessionId: two[1].sessionId }]);
  await page.goto(sessionUrl("rev"));
  await grow(page, 3, 4);
  await submitAttempt(page);
  await page.getByRole("button", { name: /下一题/ }).click();
  await expect(card(page)).toBeVisible();
  await expect(page.getByTestId("ab-rows")).toHaveText("0");
  await expect(page.getByTestId("ab-cols")).toHaveText("0");
  await expect(submitButton(page)).toBeDisabled();
});

// ---------- 双皮肤 ----------
test("R08-E2E-10 healing 皮肤同契约", async ({ page }) => {
  test.skip(!process.env.E2E_HEALING_BASE, "需 3101 healing 实例");
  const [r] = await r08Tasks(1);
  await pinTasks(page, [r]);
  const url = new URL(sessionUrl("healing"), process.env.E2E_HEALING_BASE);
  await page.goto(url.toString());
  await expect(page.locator("[data-child-math-skin]")).toHaveAttribute("data-child-math-skin", "healing");
  await grow(page, 3, 4);
  const { body, result } = await submitAttempt(page);
  expect(body.response.type).toBe("array_board");
  expect(result.correct).toBe(true);
});
