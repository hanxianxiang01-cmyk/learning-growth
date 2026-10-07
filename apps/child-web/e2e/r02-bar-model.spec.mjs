// FE-1418 R02 bar-model 真实页面 E2E（B5 模板第五实例；模型结构 evaluator 专项）。
// 合同：B5_E2E_VERTICAL_GATE.md 口径 + Gap R02（Diagnosis=结构错误分类证据）。
// 数据卫生：CHILD=QA-Simulator …0099（QA_DATA_HYGIENE R1/R3）。金题 ability=app_model。
import { test, expect, request as pwRequest } from "@playwright/test";

const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8000";
const CHILD = process.env.E2E_CHILD_ID ?? "00000000-0000-0000-0000-000000000099";
const ABILITY = "app_model";

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
        data: { child_id: CHILD, session_id: sid, subject: "math", ability_id: ABILITY, requested_minutes: 15 }
      });
      const t = await resp.json();
      const ui = t.ui_schema || {};
      const ws = (ui.workspaces || [])[0] || {};
      if (ui.schema_version === "2.0" && ws.renderer === "bar-model") {
        tasks.push({ task: t, sessionId: sid });
      }
    }
  }
  await ctx.dispose();
  if (tasks.length < n) throw new Error(`预取 R02 task 不足：${tasks.length}/${n}`);
  return tasks;
}

async function fetchR02Tasks(k) {
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
  return `/child/math/session/e2e-${sid}?child_id=${CHILD}&ability_id=${ABILITY}`;
}

const card = page => page.getByTestId("bar-model-v2");
const submitButton = page => page.getByTestId("bm-submit");

/** 把某根条摆到 n 格（点击 plus n 次）。 */
async function fillBar(page, bar, n) {
  for (let i = 0; i < n; i += 1) await page.getByTestId(`bm-plus-${bar}`).click();
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

// ---------- G1：渲染不降级 + EMPTY 门禁 ----------
test("R02-E2E-09 (G1) 渲染 bar-model V2，空态禁提交", async ({ page }) => {
  const [r] = await fetchR02Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("g1"));
  await expect(card(page)).toBeVisible();
  await expect(page.getByTestId("planned-renderer")).toHaveCount(0);
  await expect(page.getByTestId("bm-evaluation")).toContainText("还没摆出答案条");
  await expect(submitButton(page)).toBeDisabled();
});

// ---------- G2/G3：只碰已知条不算答案（EMPTY 保持）----------
test("R02-E2E-03 (G2/G3) 摆已知条不碰答案条 → 仍 EMPTY 不可提交", async ({ page }) => {
  const [r] = await fetchR02Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("empty"));
  await fillBar(page, "a", 5);
  await fillBar(page, "b", 3);
  await expect(page.getByTestId("bm-count-c")).toHaveText("0");
  await expect(page.getByTestId("bm-evaluation")).toContainText("还没摆出答案条");
  let posted = false;
  page.on("request", q => { if (q.url().includes("/v1/learning/attempts")) posted = true; });
  await page.waitForTimeout(400);
  expect(posted).toBe(false);
  expect(await submitButton(page).isDisabled()).toBe(true);
});

// ---------- 结构错误分类专项：relation ----------
test("R02-STRUCT 整体条比部分短 → relation 分类提示", async ({ page }) => {
  const [r] = await fetchR02Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("relation"));
  await fillBar(page, "a", 5);
  await fillBar(page, "b", 3);
  await fillBar(page, "c", 4); // 整体 4 < 部分 5：数学上不存在的模型
  await expect(page.getByTestId("bm-evaluation")).toContainText("条的长短关系不对");
});

// ---------- 结构错误分类专项：modeling（已知条摆错）----------
test("R02-STRUCT 已知条摆错（a=6）→ modeling 分类提示", async ({ page }) => {
  const [r] = await fetchR02Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("modeling"));
  await fillBar(page, "a", 6);
  await fillBar(page, "b", 3);
  await fillBar(page, "c", 9); // 结构成立（9>6,9>3）但已知条读错题
  await expect(page.getByTestId("bm-evaluation")).toContainText("和题目说的不一样");
});

// ---------- G6/G4：数错（calc）可提交 + envelope 合同 ----------
test("R02-E2E-02 (G6/G4) 结构对数错 c=9 → envelope 合同 → correct=false → HINT", async ({ page }) => {
  const [r] = await fetchR02Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("calc"));
  await fillBar(page, "a", 5);
  await fillBar(page, "b", 3);
  await fillBar(page, "c", 9);
  await expect(page.getByTestId("bm-evaluation")).toContainText("数字再检查检查");
  await expect(submitButton(page)).toBeEnabled(); // FAIL 可提交（P0-01）

  const { body, result } = await submitAttempt(page);

  expect(body.task_instance_id).toBe(r.task.task_instance_id);
  const resp = body.response;
  expect(resp.schema_version).toBe("2.0");
  expect(resp.type).toBe("bar_model");
  expect(resp.answer.value).toBe(9);
  const data = resp.workspaces[0].data;
  expect(data.bars).toEqual({ a: 5, b: 3, c: 9 });
  expect(data.answer_bar).toBe("c");
  // 结构证据入库：calc 分类（R02 Diagnosis P0）
  expect(data.structure.status).toBe("FAIL");
  expect(data.structure.error).toBe("calc");
  expect(data.structure.relation).toBe("part_whole");
  const types = resp.interaction_events.map(e => e.event_type);
  expect(types).toContain("BAR_BLOCK_ADDED");

  expect(result.correct).toBe(false);
  expect(result.next_action.type).toBe("HINT");
  await expect(page.getByRole("button", { name: /给我一点提示/ })).toBeVisible();
});

// ---------- G5：摆对 → 判对 → NEXT_TASK ----------
test("R02-E2E-01 (G5) 5+3 摆成整体 8 → correct=true → NEXT_TASK", async ({ page }) => {
  const [r] = await fetchR02Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("right"));
  await fillBar(page, "a", 5);
  await fillBar(page, "b", 3);
  await fillBar(page, "c", 8);
  await expect(page.getByTestId("bm-evaluation")).toContainText("条形图摆对了");
  const { body, result } = await submitAttempt(page);
  expect(result.correct).toBe(true);
  expect(result.next_action.type).toBe("NEXT_TASK");
  // PASS 的结构证据也在（error=null）——诊断原料完整
  expect(body.response.workspaces[0].data.structure).toEqual({
    status: "PASS", error: null, relation: "part_whole"
  });
  await expect(page.getByRole("button", { name: /下一题/ })).toBeVisible();
});

// ---------- G7：重试链 ----------
test("R02-G7 数错改对：attempt_no=2", async ({ page }) => {
  const [r] = await fetchR02Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("retry"));
  await fillBar(page, "a", 5);
  await fillBar(page, "b", 3);
  await fillBar(page, "c", 9);
  const first = await submitAttempt(page);
  expect(first.result.correct).toBe(false);

  await page.getByRole("button", { name: /给我一点提示/ }).click();
  await expect(page.getByRole("button", { name: /我再想想/ })).toBeVisible();
  await page.getByRole("button", { name: /我再想想/ }).click();

  // RETRY 不清模型（R07 同款语义）：整体条 9 减一格到 8
  await page.getByTestId("bm-minus-c").click();
  await expect(page.getByTestId("bm-count-c")).toHaveText("8");
  const second = await submitAttempt(page);
  expect(second.result.correct).toBe(true);
  expect(second.body.attempt_no).toBe(2);
  await expect(page.getByRole("button", { name: /下一题/ })).toBeVisible();
});

// ---------- 防重入 + UNDO ----------
test("R02-E2E-07 双击只一个 POST；UNDO 回退一格", async ({ page }) => {
  const [r] = await fetchR02Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("undo"));
  await fillBar(page, "a", 5);
  await fillBar(page, "b", 3);
  await fillBar(page, "c", 8);
  await page.getByTestId("bm-undo").click();
  await expect(page.getByTestId("bm-count-c")).toHaveText("7");
  await page.getByTestId("bm-plus-c").click(); // 回到 8

  let posts = 0;
  page.on("request", q => {
    if (q.url().includes("/v1/learning/attempts") && q.method() === "POST") posts += 1;
  });
  await submitButton(page).dblclick();
  await page.waitForTimeout(2500);
  expect(posts).toBe(1);
});

// ---------- E2E-08：revision 切换清态 ----------
test("R02-E2E-08 下一题清空三根条", async ({ page }) => {
  const two = await fetchR02Tasks(2);
  const task2 = structuredClone(two[1].task);
  task2.ui_schema.ui_revision = `${two[1].task.ui_schema.ui_revision}-rev2`;
  await pinTasks(page, [two[0], { task: task2, sessionId: two[1].sessionId }]);
  await page.goto(sessionUrl("rev"));
  await fillBar(page, "a", 5);
  await fillBar(page, "b", 3);
  await fillBar(page, "c", 8);
  await submitAttempt(page);
  await page.getByRole("button", { name: /下一题/ }).click();
  await expect(card(page)).toBeVisible();
  await expect(page.getByTestId("bm-count-a")).toHaveText("0");
  await expect(page.getByTestId("bm-count-c")).toHaveText("0");
  await expect(submitButton(page)).toBeDisabled();
});

// ---------- 双皮肤 ----------
test("R02-E2E-10 healing 皮肤同契约", async ({ page }) => {
  test.skip(!process.env.E2E_HEALING_BASE, "需 3101 healing 实例");
  const [r] = await fetchR02Tasks(1);
  await pinTasks(page, [r]);
  const url = new URL(sessionUrl("healing"), process.env.E2E_HEALING_BASE);
  await page.goto(url.toString());
  await expect(page.locator("[data-child-math-skin]")).toHaveAttribute("data-child-math-skin", "healing");
  await fillBar(page, "a", 5);
  await fillBar(page, "b", 3);
  await fillBar(page, "c", 8);
  const { body, result } = await submitAttempt(page);
  expect(body.response.type).toBe("bar_model");
  expect(result.correct).toBe(true);
});
