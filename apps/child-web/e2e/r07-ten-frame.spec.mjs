// FE-1416 R07 ten-frame 真实页面 E2E（B5 模板第四实例；20 以内数量结构）。
// 合同：B5_E2E_VERTICAL_GATE.md 口径 + docs/frontend/31 SEM-1416 / Gap R07。
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
      if (ui.schema_version === "2.0" && ws.renderer === "ten-frame") {
        tasks.push({ task: t, sessionId: sid });
      }
    }
  }
  await ctx.dispose();
  if (tasks.length < n) throw new Error(`预取 R07 task 不足：${tasks.length}/${n}`);
  return tasks;
}

async function fetchR07Tasks(k) {
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

const card = page => page.getByTestId("ten-frame-v2");
const cell = (page, i) => page.getByTestId(`tf-cell-${i}`);
const submitButton = page => page.getByTestId("tf-submit");

async function tapCells(page, from, to) {
  // 连续填充：点第 i 格 → count=i+1（第 i 格左侧都填满）
  for (let i = from; i < to; i += 1) await cell(page, i).click();
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

// ---------- G1：渲染 + EMPTY 态 ----------
test("R07-E2E-09 (G1) 渲染 ten-frame V2，空态禁提交", async ({ page }) => {
  const [r] = await fetchR07Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("g1"));
  await expect(card(page)).toBeVisible();
  await expect(page.getByTestId("planned-renderer")).toHaveCount(0);
  await expect(page.getByTestId("tf-current-frame")).toBeVisible();
  await expect(page.getByTestId("tf-evaluation")).toContainText("先放圆片");
  await expect(submitButton(page)).toBeDisabled();
});

// ---------- G5：1袋+3散=13 → PASS → 判对 → NEXT_TASK（make-ten 链） ----------
test("R07-E2E-01 (G5) 摆满框打包成袋再摆3 → correct=true", async ({ page }) => {
  const [r] = await fetchR07Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("right"));
  await tapCells(page, 0, 10); // 满 10
  await page.getByTestId("tf-make-ten").click(); // 打包成十
  await expect(page.getByTestId("tf-tens")).toBeVisible();
  await tapCells(page, 0, 3); // 第二框 3 个
  await expect(page.getByTestId("tf-evaluation")).toContainText("摆好了"); // PASS
  const { body, result } = await submitAttempt(page);
  expect(result.correct).toBe(true);
  expect(result.next_action.type).toBe("NEXT_TASK");
  // G4 结构断言：十与一分解 + make-ten 事件留痕
  expect(body.response.type).toBe("ten_frame");
  expect(body.response.answer.value).toBe(13);
  expect(body.response.workspaces[0].data.tens).toBe(1);
  expect(body.response.workspaces[0].data.current_frame_count).toBe(3);
  expect(body.response.workspaces[0].data.total).toBe(13);
  const types = body.response.interaction_events.map(e => e.event_type);
  expect(types).toContain("COUNTER_ADDED");
  expect(types).toContain("MAKE_TEN_COMPLETED");
  await expect(page.getByRole("button", { name: /下一题/ })).toBeVisible();
});

// ---------- G6/G4：数量错位（1袋+2散=12）FAIL 仍可提交 → correct=false → HINT ----------
test("R07-E2E-02 (G6) 摆成 12 → FAIL 可提交 → correct=false → HINT", async ({ page }) => {
  const [r] = await fetchR07Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("wrong"));
  await tapCells(page, 0, 10);
  await page.getByTestId("tf-make-ten").click();
  await tapCells(page, 0, 2);
  await expect(page.getByTestId("tf-evaluation")).toContainText("数量还要检查");
  await expect(submitButton(page)).toBeEnabled();
  const { body, result } = await submitAttempt(page);
  expect(body.response.answer.value).toBe(12);
  expect(result.correct).toBe(false);
  expect(result.next_action.type).toBe("HINT");
  await expect(page.getByRole("button", { name: /给我一点提示/ })).toBeVisible();
});

// ---------- G2：跳格不产生洞（连续填充语义） ----------
test("R07-G2 直接点第 5 格 → 填充前 5 格而非留洞", async ({ page }) => {
  const [r] = await fetchR07Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("dense"));
  await cell(page, 4).click();
  await expect(page.getByTestId("tf-total")).toContainText("现在一共 5 个");
  // 再点第 2 格 → 取消到 2 个（i<count 收缩）
  await cell(page, 2).click();
  await expect(page.getByTestId("tf-total")).toContainText("现在一共 2 个");
});

// ---------- G7：重试链（12 提交错 → 提示 → 补成 13） ----------
test("R07-G7 错 12 后补 1 格改对：attempt_no=2", async ({ page }) => {
  const [r] = await fetchR07Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("retry"));
  await tapCells(page, 0, 10);
  await page.getByTestId("tf-make-ten").click();
  await tapCells(page, 0, 2);
  const first = await submitAttempt(page);
  expect(first.result.correct).toBe(false);

  await page.getByRole("button", { name: /给我一点提示/ }).click();
  await expect(page.getByRole("button", { name: /我再想想/ })).toBeVisible();
  await page.getByRole("button", { name: /我再想想/ }).click();

  await cell(page, 2).click(); // count 2→3 = 13
  const second = await submitAttempt(page);
  expect(second.result.correct).toBe(true);
  expect(second.body.attempt_no).toBe(2);
});

// ---------- 防重入 + UNDO ----------
test("R07-E2E-07 双击只一个 POST；UNDO 可回退打包", async ({ page }) => {
  const [r] = await fetchR07Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("undo"));
  await tapCells(page, 0, 10);
  await page.getByTestId("tf-make-ten").click();
  await tapCells(page, 0, 3);
  // 撤销一步：3→2（UNDO 事件 + 数量回退）
  await page.getByTestId("tf-undo").click();
  await expect(page.getByTestId("tf-total")).toContainText("现在一共 12 个");
  let posts = 0;
  page.on("request", q => {
    if (q.url().includes("/v1/learning/attempts") && q.method() === "POST") posts += 1;
  });
  await submitButton(page).dblclick();
  await page.waitForTimeout(2500);
  expect(posts).toBe(1);
});

// ---------- E2E-08：revision 切换清态 ----------
test("R07-E2E-08 下一题清空十格框", async ({ page }) => {
  const two = await fetchR07Tasks(2);
  const task2 = structuredClone(two[1].task);
  task2.ui_schema.ui_revision = `${two[1].task.ui_schema.ui_revision}-rev2`;
  await pinTasks(page, [two[0], { task: task2, sessionId: two[1].sessionId }]);
  await page.goto(sessionUrl("rev"));
  await tapCells(page, 0, 10);
  await page.getByTestId("tf-make-ten").click();
  await tapCells(page, 0, 3);
  await submitAttempt(page);
  await page.getByRole("button", { name: /下一题/ }).click();
  await expect(card(page)).toBeVisible();
  await expect(page.getByTestId("tf-tens")).toHaveCount(0);
  await expect(page.getByTestId("tf-total")).toContainText("现在一共 0 个");
  await expect(submitButton(page)).toBeDisabled();
});

// ---------- 双皮肤 ----------
test("R07-E2E-10 healing 皮肤同契约", async ({ page }) => {
  test.skip(!process.env.E2E_HEALING_BASE, "需 3101 healing 实例");
  const [r] = await fetchR07Tasks(1);
  await pinTasks(page, [r]);
  const url = new URL(sessionUrl("healing"), process.env.E2E_HEALING_BASE);
  await page.goto(url.toString());
  await expect(page.locator("[data-child-math-skin]")).toHaveAttribute("data-child-math-skin", "healing");
  await tapCells(page, 0, 10);
  await page.getByTestId("tf-make-ten").click();
  await tapCells(page, 0, 3);
  const { body, result } = await submitAttempt(page);
  expect(body.response.type).toBe("ten_frame");
  expect(result.correct).toBe(true);
});
