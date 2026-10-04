// FE-1415 R04 number-input 真实页面 E2E（B5 模板第三实例；submission_id 幂等专项）。
// 合同：B5_E2E_VERTICAL_GATE.md 口径 + docs/frontend/31 SEM-1413 / Gap R04。
// 数据卫生：CHILD=QA-Simulator …0099（QA_DATA_HYGIENE R1/R3）。
import { test, expect, request as pwRequest } from "@playwright/test";

const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8000";
const CHILD = process.env.E2E_CHILD_ID ?? "00000000-0000-0000-0000-000000000099";

const TASK_POOL_SIZE = 8;
let taskPool = null;
let poolCursor = 0;

async function buildTaskPool(n) {
  const ctx = await pwRequest.newContext({ baseURL: API });
  const tasks = [];
  for (let s = 0; s < 25 && tasks.length < n; s += 1) {
    const session = await ctx.post("/v1/learning/sessions", {
      data: { child_id: CHILD, subject: "math", requested_minutes: 15 }
    });
    const sid = (await session.json()).session_id;
    for (let i = 0; i < 16 && tasks.length < n; i += 1) {
      const resp = await ctx.post("/v1/learning/tasks/next", {
        data: { child_id: CHILD, session_id: sid, subject: "math", ability_id: "app_rel", requested_minutes: 15 }
      });
      const t = await resp.json();
      const ui = t.ui_schema || {};
      const ws = (ui.workspaces || [])[0] || {};
      if (ui.schema_version === "2.0" && ws.renderer === "number-input") {
        tasks.push({ task: t, sessionId: sid });
      }
    }
  }
  await ctx.dispose();
  if (tasks.length < n) throw new Error(`预取 R04 task 不足：${tasks.length}/${n}`);
  return tasks;
}

async function fetchR04Tasks(k) {
  if (!taskPool) taskPool = await buildTaskPool(TASK_POOL_SIZE);
  const out = [];
  for (let i = 0; i < k; i += 1) {
    if (poolCursor >= taskPool.length) taskPool.push(...(await buildTaskPool(k)));
    out.push(taskPool[poolCursor++]);
  }
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
  return `/child/math/session/e2e-${sid}?child_id=${CHILD}&ability_id=app_rel`;
}

const card = page => page.getByTestId("number-input-v2");
const input = page => page.getByTestId("ni-input");
const submitButton = page => page.getByTestId("ni-submit");

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

// ---------- G1：V2 number-input 渲染不降级（不回到 V1 AnswerComposer） ----------
test("R04-E2E-09 (G1) 渲染 number-input V2，无开发中卡", async ({ page }) => {
  const [r] = await fetchR04Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("g1"));
  await expect(card(page)).toBeVisible();
  await expect(page.getByTestId("planned-renderer")).toHaveCount(0);
  await expect(page.getByPlaceholder("0 ~ 20")).toBeVisible();
  await expect(submitButton(page)).toBeDisabled(); // EMPTY
});

// ---------- G2/G3：空/非法输入不可提交 ----------
test("R04-E2E-03 (G2/G3) 空输入与越界输入 → 提交禁用、不发请求", async ({ page }) => {
  const [r] = await fetchR04Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("empty"));
  await input(page).fill("99"); // 越界 → null
  await expect(page.getByTestId("ni-evaluation")).toContainText("还没写好答案");
  await expect(submitButton(page)).toBeDisabled();
  await input(page).fill("3.5"); // integer_only 拒小数
  await expect(submitButton(page)).toBeDisabled();
  let posted = false;
  page.on("request", q => { if (q.url().includes("/v1/learning/attempts")) posted = true; });
  await page.waitForTimeout(400);
  expect(posted).toBe(false);
});

// ---------- G6/G4：错误答案可提交 + envelope 合同 + HINT 链 ----------
test("R04-E2E-02 (G6/G4) 答 3 → envelope 合同 → correct=false → HINT", async ({ page }) => {
  const [r] = await fetchR04Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("wrong"));
  await input(page).fill("3");
  await expect(submitButton(page)).toBeEnabled();

  const { body, result } = await submitAttempt(page);

  expect(body.task_instance_id).toBe(r.task.task_instance_id);
  expect(typeof body.submission_id).toBe("string");
  const resp = body.response;
  expect(resp.schema_version).toBe("2.0");
  expect(resp.type).toBe("number_input");
  expect(resp.answer.value).toBe(3);
  expect(resp.workspaces[0].data.answer).toBe(3);
  expect(Array.isArray(resp.workspaces[0].data.input_history)).toBe(true);
  const types = resp.interaction_events.map(e => e.event_type);
  expect(types).toContain("NUMBER_INPUT_CHANGED");

  expect(result.correct).toBe(false);
  expect(result.next_action.type).toBe("HINT");
  await expect(page.getByRole("button", { name: /给我一点提示/ })).toBeVisible();
});

// ---------- 幂等专项（Gap R04 核心使命）：双击只一个 attempt ----------
test("R04-IDEM 防重入：双击提交只发一个 POST（submission_id 唯一）", async ({ page }) => {
  const [r] = await fetchR04Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("idem"));
  await input(page).fill("5");

  const submissions = [];
  page.on("request", q => {
    if (q.url().includes("/v1/learning/attempts") && q.method() === "POST") {
      submissions.push(JSON.parse(q.postData() ?? "{}").submission_id);
    }
  });
  await submitButton(page).dblclick();
  await page.waitForTimeout(2500);
  expect(submissions).toHaveLength(1); // adapter 每次提交生成唯一 submission_id，重入被按钮 disabled 拦住
});

// ---------- G5/G7：重试链（attempt_no 递增 + 单 Task 单证据） ----------
test("R04-G7 答错改对：attempt_no=2、重试后可提交且判对", async ({ page }) => {
  const [r] = await fetchR04Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("retry"));

  await input(page).fill("4");
  const first = await submitAttempt(page);
  expect(first.result.correct).toBe(false);

  await page.getByRole("button", { name: /给我一点提示/ }).click();
  await expect(page.getByRole("button", { name: /我再想想/ })).toBeVisible();
  await page.getByRole("button", { name: /我再想想/ }).click();

  // RETRY 态：answer 清、输入框由用户重填
  await input(page).fill("5");
  const second = await submitAttempt(page);
  expect(second.result.correct).toBe(true);
  expect(second.body.attempt_no).toBe(2);
  await expect(page.getByRole("button", { name: /下一题/ })).toBeVisible();
});

// ---------- E2E-08：revision 切换清态 ----------
test("R04-E2E-08 下一题清空输入，不继承答案", async ({ page }) => {
  const two = await fetchR04Tasks(2);
  const task2 = structuredClone(two[1].task);
  task2.ui_schema.ui_revision = `${two[1].task.ui_schema.ui_revision}-rev2`;
  await pinTasks(page, [two[0], { task: task2, sessionId: two[1].sessionId }]);
  await page.goto(sessionUrl("rev"));

  await input(page).fill("5");
  await submitAttempt(page);
  await page.getByRole("button", { name: /下一题/ }).click();

  await expect(card(page)).toBeVisible();
  await expect(input(page)).toHaveValue("");
  await expect(submitButton(page)).toBeDisabled();
});

// ---------- 双皮肤 ----------
test("R04-E2E-10 healing 皮肤同契约", async ({ page }) => {
  test.skip(!process.env.E2E_HEALING_BASE, "需 3101 healing 实例");
  const [r] = await fetchR04Tasks(1);
  await pinTasks(page, [r]);
  const url = new URL(sessionUrl("healing"), process.env.E2E_HEALING_BASE);
  await page.goto(url.toString());
  await expect(page.locator("[data-child-math-skin]")).toHaveAttribute("data-child-math-skin", "healing");
  await input(page).fill("5");
  const { body, result } = await submitAttempt(page);
  expect(body.response.type).toBe("number_input");
  expect(result.correct).toBe(true);
});
