// FE-1420 R10 formula-board 真实页面 E2E（B5 模板第七实例；equation semantic evaluator）。
// 双金题：□+4=9（数字槽，relation 靶）与 7○2=5（符号槽，operator 靶）。
// 数据卫生：CHILD=QA-Simulator …0099；ability=app_strat。
import { test, expect, request as pwRequest } from "@playwright/test";

const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8000";
const CHILD = process.env.E2E_CHILD_ID ?? "00000000-0000-0000-0000-000000000099";
const ABILITY = "app_strat";

async function fetchTask(ctx, wantMode, n) {
  const tasks = [];
  for (let s = 0; s < 25 && tasks.length < n; s += 1) {
    const session = await ctx.post("/v1/learning/sessions", {
      data: { child_id: CHILD, subject: "math", requested_minutes: 15 }
    });
    const sid = (await session.json()).session_id;
    for (let i = 0; i < 20 && tasks.length < n; i += 1) {
      const resp = await ctx.post("/v1/learning/tasks/next", {
        data: { child_id: CHILD, session_id: sid, subject: "math", ability_id: ABILITY, requested_minutes: 15 }
      });
      const t = await resp.json();
      const ui = t.ui_schema || {};
      const ws = (ui.workspaces || [])[0] || {};
      if (ui.schema_version === "2.0" && ws.renderer === "formula-board" && ws.mode === wantMode) {
        tasks.push({ task: t, sessionId: sid });
      }
    }
  }
  return tasks;
}

let poolNumber = null;
let poolOperator = null;
let cursorNumber = 0;
let cursorOperator = 0;

async function numberTasks(k) {
  if (!poolNumber) {
    const ctx = await pwRequest.newContext({ baseURL: API });
    poolNumber = await fetchTask(ctx, "unknown_number", 6);
    await ctx.dispose();
  }
  const out = [];
  for (let i = 0; i < k; i += 1) out.push(poolNumber[cursorNumber++ % poolNumber.length]);
  return out;
}

async function operatorTasks(k) {
  if (!poolOperator) {
    const ctx = await pwRequest.newContext({ baseURL: API });
    poolOperator = await fetchTask(ctx, "unknown_operator", 4);
    await ctx.dispose();
  }
  const out = [];
  for (let i = 0; i < k; i += 1) out.push(poolOperator[cursorOperator++ % poolOperator.length]);
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

const card = page => page.getByTestId("formula-board-v2");
const submitButton = page => page.getByTestId("fb-submit");

async function fillNumber(page, slot, value) {
  await page.getByTestId(`fb-slot-${slot}`).click();
  for (const ch of String(value)) await page.getByTestId(`fb-key-${ch}`).click();
  // 收起键盘（再点一次槽）
  await page.getByTestId(`fb-slot-${slot}`).click();
}

async function pressOperatorKey(page, slot, which) {
  await page.getByTestId(`fb-slot-${slot}`).click();
  await page.getByTestId(which === "+" ? "fb-op-plus" : "fb-op-minus").click();
  await page.getByTestId(`fb-slot-${slot}`).click();
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
test("R10-E2E-09 (G1) 渲染 formula-board V2，空槽禁提交", async ({ page }) => {
  const [r] = await numberTasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("g1"));
  await expect(card(page)).toBeVisible();
  await expect(page.getByTestId("planned-renderer")).toHaveCount(0);
  await expect(page.getByTestId("fb-evaluation")).toContainText("还有空圈没填上");
  await expect(submitButton(page)).toBeDisabled();
});

// ---------- G2/G3：部分填空仍 EMPTY；清空退回 EMPTY ----------
test("R10-E2E-03 (G2/G3) 填一半/清空 → EMPTY 不可提交", async ({ page }) => {
  const [r] = await numberTasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("empty"));
  await fillNumber(page, "box", 5);
  await expect(submitButton(page)).toBeEnabled();
  // 清空退回 EMPTY（修改过程证据：SLOT_CLEARED）
  await page.getByTestId("fb-slot-box").click();
  await expect(page.getByTestId("fb-keypad")).toBeVisible();
  await page.getByTestId("fb-clear").click();
  await expect(page.getByTestId("fb-slot-box")).toContainText("○");
  await expect(submitButton(page)).toBeDisabled();
  let posted = false;
  page.on("request", q => { if (q.url().includes("/v1/learning/attempts")) posted = true; });
  await page.waitForTimeout(400);
  expect(posted).toBe(false);
});

// ---------- relation 分类：□+4=9 填 6 ----------
test("R10-RELATION 填 6（6+4≠9）→ relation 提示 → FAIL 可提交 → HINT", async ({ page }) => {
  const [r] = await numberTasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("relation"));
  await fillNumber(page, "box", 6);
  await expect(page.getByTestId("fb-evaluation")).toContainText("两边的数不相等");
  await expect(submitButton(page)).toBeEnabled();
  const { body, result } = await submitAttempt(page);
  expect(body.response.type).toBe("formula_board");
  expect(body.response.answer.value).toBe(6);
  const data = body.response.workspaces[0].data;
  expect(data.filled).toEqual({ box: 6 });
  expect(data.structure).toEqual({ status: "FAIL", error: "relation", equation: true });
  expect(result.correct).toBe(false);
  expect(result.next_action.type).toBe("HINT");
});

// ---------- PASS：□+4=9 填 5 ----------
test("R10-E2E-01 (G5) 填 5 等式成立 → correct=true → NEXT_TASK", async ({ page }) => {
  const [r] = await numberTasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("pass"));
  await fillNumber(page, "box", 5);
  await expect(page.getByTestId("fb-evaluation")).toContainText("等式成立啦");
  const { result } = await submitAttempt(page);
  expect(result.correct).toBe(true);
  await expect(page.getByRole("button", { name: /下一题/ })).toBeVisible();
});

// ---------- operator 分类专项：7○2=5 选 + ----------
test("R10-OPERATOR 选＋（7+2≠5 但翻转可救）→ operator 提示 → 证据入库", async ({ page }) => {
  const [r] = await operatorTasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("operator"));
  await pressOperatorKey(page, "op0", "+");
  await expect(page.getByTestId("fb-evaluation")).toContainText("符号选错了");
  const { body, result } = await submitAttempt(page);
  // 非数字答案（字符串 "-"语义面）：answer.value 原样入 envelope
  expect(body.response.answer.value).toBe("+");
  expect(body.response.workspaces[0].data.structure.error).toBe("operator");
  expect(result.correct).toBe(false);
  expect(result.next_action.type).toBe("HINT");
  await expect(page.getByRole("button", { name: /给我一点提示/ })).toBeVisible();
});

// ---------- 符号替换改对（R10 Evidence"替换过程"）+ G7 ----------
test("R10-G7 选+错 → 提示 → 换 − 改对：OPERATOR_REPLACED、attempt_no=2", async ({ page }) => {
  const [r] = await operatorTasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("replace"));
  await pressOperatorKey(page, "op0", "+");
  const first = await submitAttempt(page);
  expect(first.result.correct).toBe(false);
  await page.getByRole("button", { name: /给我一点提示/ }).click();
  await page.getByRole("button", { name: /我再想想/ }).click();
  await pressOperatorKey(page, "op0", "-"); // 替换
  const second = await submitAttempt(page);
  expect(second.result.correct).toBe(true);
  expect(second.body.attempt_no).toBe(2);
  const types = second.body.response.interaction_events.map(e => e.event_type);
  expect(types).toContain("OPERATOR_REPLACED");
  await expect(page.getByRole("button", { name: /下一题/ })).toBeVisible();
});

// ---------- 多位数字键盘 + UNDO + 防重入 ----------
test("R10-INPUT 数字键盘追加/越界拒绝；UNDO；双击只 1 POST", async ({ page }) => {
  const [r] = await numberTasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("input"));
  await page.getByTestId("fb-slot-box").click();
  await page.getByTestId("fb-key-1").click();
  await page.getByTestId("fb-key-2").click();
  await expect(page.getByTestId("fb-slot-box")).toContainText("12");
  await page.getByTestId("fb-key-9").click(); // 129 > 20 拒绝——仍是 12
  await expect(page.getByTestId("fb-slot-box")).toContainText("12");
  // UNDO 三步（activate/追加各是事件步，数字 12 由两次追加合成）：回退到 1
  await page.getByTestId("fb-undo").click();
  await expect(page.getByTestId("fb-slot-box")).toContainText("1");
  // 改对 5：清空后填
  await page.getByTestId("fb-clear").click();
  await page.getByTestId("fb-key-5").click();
  await page.getByTestId("fb-slot-box").click(); // 收起
  await expect(page.getByTestId("fb-evaluation")).toContainText("等式成立啦");
  let posts = 0;
  page.on("request", q => {
    if (q.url().includes("/v1/learning/attempts") && q.method() === "POST") posts += 1;
  });
  await submitButton(page).dblclick();
  await page.waitForTimeout(2500);
  expect(posts).toBe(1);
});

// ---------- E2E-08：revision 切换清态 ----------
test("R10-E2E-08 下一题清空所有槽", async ({ page }) => {
  const two = await numberTasks(2);
  const task2 = structuredClone(two[1].task);
  task2.ui_schema.ui_revision = `${two[1].task.ui_schema.ui_revision}-rev2`;
  await pinTasks(page, [two[0], { task: task2, sessionId: two[1].sessionId }]);
  await page.goto(sessionUrl("rev"));
  await fillNumber(page, "box", 5);
  await submitAttempt(page);
  await page.getByRole("button", { name: /下一题/ }).click();
  await expect(card(page)).toBeVisible();
  await expect(page.getByTestId("fb-slot-box")).toContainText("○");
  await expect(submitButton(page)).toBeDisabled();
});

// ---------- 双皮肤 ----------
test("R10-E2E-10 healing 皮肤同契约", async ({ page }) => {
  test.skip(!process.env.E2E_HEALING_BASE, "需 3101 healing 实例");
  const [r] = await operatorTasks(1);
  await pinTasks(page, [r]);
  const url = new URL(sessionUrl("healing"), process.env.E2E_HEALING_BASE);
  await page.goto(url.toString());
  await expect(page.locator("[data-child-math-skin]")).toHaveAttribute("data-child-math-skin", "healing");
  await pressOperatorKey(page, "op0", "-");
  const { body, result } = await submitAttempt(page);
  expect(body.response.type).toBe("formula_board");
  expect(result.correct).toBe(true);
});
