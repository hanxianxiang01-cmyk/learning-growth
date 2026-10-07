// FE-1403 P0-03/04/06 + §7 场景矩阵：B5 column-arithmetic 真实页面 E2E。
// 合同：docs/governance/B5_E2E_VERTICAL_GATE.md（G1~G9）+《B5 真实页面E2E联调方案》§7/§10。
//
// 真实性口径（§24：不以 Mock/纯函数替代）：
// - task 来自真实后端 /tasks/next（route 只做「钉题重放」，task_instance_id 真实存在）；
// - /attempts、/hints 全部放行真实后端（判分、evidence、attempt_no 递增、diagnosis 均为后端权威）。
import { test, expect, request as pwRequest } from "@playwright/test";
import { fetchPinnedTasks } from "./pinned-tasks.mjs";

const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8000";
// 钉题：FE-1422a 确定性 pin（v2-catalog → pin_resource_version_id），不靠 band 运气。
// 数据卫生（docs/governance/QA_DATA_HYGIENE.md）：E2E 一律用 QA-Simulator child，
// 禁止写入真实演示孩子 …0001 的 mastery 窗口。RDS 需预建该 child（scripts/qa_child_setup.py）。
const CHILD = process.env.E2E_CHILD_ID ?? "00000000-0000-0000-0000-000000000099";

/**
 * 向真实后端预取 B5 task，模块级缓存（跨测试复用，只打一轮 RDS）。
 * 每测试需要独立的 task_instance_id（提交幂等键），故预取一批（8 个）分配。
 * 缓存 + 180s timeout 组合解决跨网阿里云 RDS 往返慢导致的超时。
 */
function b5Tasks(k) {
  return fetchPinnedTasks({ api: API, child: CHILD, renderer: "column-arithmetic", count: k });
}

/** route 钉题：/tasks/next 按顺序重放预取的真实 task；提交/提示链路放行。 */
async function pinTasks(page, tasks) {
  let cursor = 0;
  await page.route("**/v1/learning/tasks/next", async route => {
    const entry = tasks[Math.min(cursor, tasks.length - 1)];
    cursor += 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(entry.task)
    });
  });
}

function sessionUrl(sid) {
  return `/child/math/session/e2e-${sid}?child_id=${CHILD}&ability_id=app_rel`;
}

const digit = (page, place, value) =>
  page.getByLabel(`${place}位结果`, { exact: false }).fill(String(value));

async function submitAttempt(page) {
  const reqPromise = page.waitForRequest(
    r => r.url().includes("/v1/learning/attempts") && r.method() === "POST"
  );
  const resPromise = page.waitForResponse(
    r => r.url().includes("/v1/learning/attempts") && r.status() === 200
  );
  await page.getByRole("button", { name: /提交这道题/ }).click();
  const req = await reqPromise;
  const body = JSON.parse(req.postData() ?? "{}");
  const result = await (await resPromise).json();
  return { body, result };
}

const columnCard = page => page.getByTestId("column-arithmetic");
const submitButton = page => page.getByRole("button", { name: /提交这道题/ });

// ---------- G1 / E2E-09：V2 renderer 正确进入真实页面，不降级 ----------
test("B5-E2E-09 (G1) 渲染 column-arithmetic，无 number-input、无开发中卡", async ({ page }) => {
  const [b5] = await b5Tasks(1);
  await pinTasks(page, [b5]);
  await page.goto(sessionUrl("g1"));
  await expect(columnCard(page)).toBeVisible();
  await expect(page.getByTestId("planned-renderer")).toHaveCount(0);
  await expect(page.locator('input[inputmode="numeric"]')).toHaveCount(3);
  await expect(page.getByPlaceholder("我的答案")).toHaveCount(0);
});

// ---------- E2E-03 (G2/G3)：部分填写不可提交 ----------
test("B5-E2E-03 (G2/G3) 只填个位 → 提交禁用，不产生 attempt", async ({ page }) => {
  const [b5] = await b5Tasks(1);
  await pinTasks(page, [b5]);
  await page.goto(sessionUrl("partial"));
  await expect(columnCard(page)).toBeVisible();
  await digit(page, "个", 5);
  await expect(submitButton(page)).toBeDisabled();
  let posted = false;
  page.on("request", r => {
    if (r.url().includes("/v1/learning/attempts")) posted = true;
  });
  await page.waitForTimeout(500);
  expect(posted).toBe(false);
});

// ---------- E2E-02 (G6) + P0-04 (G4)：错误答案可提交，payload 合同完整 ----------
test("B5-E2E-02 (G6/G4) 答 65 可提交 → V2 envelope 完整 → correct=false → HINT", async ({ page }) => {
  const [b5] = await b5Tasks(1);
  await pinTasks(page, [b5]);
  await page.goto(sessionUrl("wrong"));
  await expect(columnCard(page)).toBeVisible();

  // 47+28 错算成 65，进位照填（过程真实）
  await digit(page, "个", 5);
  await digit(page, "十", 6);
  await digit(page, "百", 0);
  await page.getByLabel("个位进位到十位").click();
  await expect(submitButton(page)).toBeEnabled(); // P0-01：FAIL 不再被拦

  const { body, result } = await submitAttempt(page);

  // G4：MathResponse V2 合同
  expect(body.task_instance_id).toBe(b5.task.task_instance_id);
  expect(body.attempt_no).toBe(1);
  expect(typeof body.submission_id).toBe("string");
  const resp = body.response;
  expect(resp.schema_version).toBe("2.0");
  expect(resp.ui_revision).toBe(b5.task.ui_schema.ui_revision);
  expect(resp.type).toBe("column_arithmetic");
  expect(resp.workspaces[0].workspace_id).toBe("main");
  expect(resp.answer.value).toBe(65);
  expect(resp.workspaces[0].data.result_digits).toHaveLength(3);
  expect(resp.interaction_events.length).toBeGreaterThan(0);
  // §24：workspace 不被改写为 number-input 主响应
  expect(JSON.stringify(resp)).not.toContain("\"representation\"");

  // G6：后端权威判定 + 诊断/下一步
  expect(result.correct).toBe(false);
  expect(["HINT", "TEACH", "RETRY"]).toContain(result.next_action.type);
  // FE-1406：无观察支持时 diagnosis=null 合法（不强造标签）
  expect(result.diagnosis === null || typeof result.diagnosis.code === "string").toBe(true);

  // UI 进入提示态（重试链可继续）
  await expect(page.getByRole("button", { name: /给我一点提示/ })).toBeVisible();
});

// ---------- E2E-01 (G5) + E2E-07 半 + 提示链 ----------
test("B5-E2E-01 (G5) 正确答案提交 → correct=true → 下一题", async ({ page }) => {
  const [b5] = await b5Tasks(1);
  await pinTasks(page, [b5]);
  await page.goto(sessionUrl("right"));
  await digit(page, "个", 5);
  await digit(page, "十", 7);
  await digit(page, "百", 0);
  await page.getByLabel("个位进位到十位").click();

  const { result } = await submitAttempt(page);
  expect(result.correct).toBe(true);
  await expect(page.getByRole("button", { name: /下一题/ })).toBeVisible();
});

// ---------- G7 / E2E-06 05：重试 attempt_no 递增、evidence 不丢 + undo/reset ----------
test("B5-G7 错误后改对再提交：attempt_no=2 递增、首轮证据保留（单Task单证据）", async ({ page }) => {
  const [b5] = await b5Tasks(1);
  await pinTasks(page, [b5]);
  await page.goto(sessionUrl("retry"));

  await digit(page, "个", 5);
  await digit(page, "十", 6); // 65 错
  await digit(page, "百", 0);
  const first = await submitAttempt(page);
  expect(first.result.correct).toBe(false);

  // 提示 → 我再想想（真实 /hints 链 → hint_active → RETRY）
  await page.getByRole("button", { name: /给我一点提示/ }).click();
  await expect(page.getByRole("button", { name: /我再想想/ })).toBeVisible();
  await page.getByRole("button", { name: /我再想想/ }).click();

  // RETRY 清空 answer → 重填正确 75（工作区 present 仍在，覆盖填对即可；进位上一轮已开）
  await digit(page, "个", 5);
  await digit(page, "十", 7);
  await digit(page, "百", 0);
  const second = await submitAttempt(page);
  expect(second.result.correct).toBe(true);
  expect(second.body.attempt_no).toBe(2); // G7：重试 attempt_no 正确递增（首轮 65 的证据不覆盖此轮）
});

// ---------- E2E-07 (P0)：快速重复点击只产生一次 attempt ----------
test("B5-E2E-07 防重入：双击提交只发一个 POST", async ({ page }) => {
  const [b5] = await b5Tasks(1);
  await pinTasks(page, [b5]);
  await page.goto(sessionUrl("dup"));
  await digit(page, "个", 5);
  await digit(page, "十", 7);
  await digit(page, "百", 0);

  let posts = 0;
  page.on("request", r => {
    if (r.url().includes("/v1/learning/attempts") && r.method() === "POST") posts += 1;
  });
  await page.getByRole("button", { name: /提交这道题/ }).dblclick();
  await page.waitForTimeout(2500);
  expect(posts).toBe(1);
});

// ---------- E2E-08 (P0-06)：ui_revision 变化不串题 ----------
test("B5-E2E-08 下一题后 Workspace 重置，不继承上一题", async ({ page }) => {
  const two = await b5Tasks(2);
  // 服务端同资源 revision 相同；注入第二题改 revision 以驱动 RESET（提交链不校验 revision）
  const task2 = structuredClone(two[1].task);
  task2.ui_schema.ui_revision = `${two[1].task.ui_schema.ui_revision}-rev2`;
  await pinTasks(page, [two[0], { task: task2, sessionId: two[1].sessionId }]);
  await page.goto(sessionUrl("rev"));

  await digit(page, "个", 5);
  await digit(page, "十", 7);
  await digit(page, "百", 0);
  await submitAttempt(page); // 正确 → correct 态
  await page.getByRole("button", { name: /下一题/ }).click();

  await expect(columnCard(page)).toBeVisible();
  await expect(page.getByLabel("个位结果", { exact: false })).toHaveValue("");
  await expect(page.getByLabel("十位结果", { exact: false })).toHaveValue("");
  // 新题答案为空 → 不可提交（证明没继承上一题 response/answer）
  await expect(submitButton(page)).toBeDisabled();
  let posted = false;
  page.on("request", r => {
    if (r.url().includes("/v1/learning/attempts")) posted = true;
  });
  await page.waitForTimeout(500);
  expect(posted).toBe(false);
});

// ---------- E2E-04/05/06 (P1)：事件、undo、reset 可追溯 ----------
test("B5-P1 事件模型：DIGIT_ENTERED/CARRY_CREATED/UNDO/RESET 入 payload", async ({ page }) => {
  const [b5] = await b5Tasks(1);
  await pinTasks(page, [b5]);
  await page.goto(sessionUrl("events"));
  await digit(page, "个", 9);
  await page.getByLabel("个位进位到十位").click();
  await columnCard(page).getByRole("button", { name: "撤销" }).click();
  await columnCard(page).getByRole("button", { name: "重置" }).click();
  await digit(page, "个", 5);
  await digit(page, "十", 7);
  await digit(page, "百", 0);
  await page.getByLabel("个位进位到十位").click();
  const { body } = await submitAttempt(page);
  const types = body.response.interaction_events.map(e => e.event_type);
  expect(types).toContain("DIGIT_ENTERED");
  expect(types).toContain("CARRY_CREATED");
  expect(types).toContain("UNDO");
  expect(types).toContain("RESET");
  expect(body.response.answer.value).toBe(75);
});

// ---------- E2E-10 (P1)：双皮肤同契约（3101 = healing 实例） ----------
test("B5-E2E-10 healing 皮肤：交互合同与数据结构与默认皮肤一致", async ({ page }) => {
  test.skip(!process.env.E2E_HEALING_BASE, "需 3101 healing 实例（playwright webServer 自动拉起）");
  const [b5] = await b5Tasks(1);
  await pinTasks(page, [b5]);
  const url = new URL(sessionUrl("healing"), process.env.E2E_HEALING_BASE);
  await page.goto(url.toString());
  await expect(page.locator("[data-child-math-skin]")).toHaveAttribute("data-child-math-skin", "healing");
  await digit(page, "个", 5);
  await digit(page, "十", 7);
  await digit(page, "百", 0);
  await page.getByLabel("个位进位到十位").click();
  const { body, result } = await submitAttempt(page);
  expect(body.response.type).toBe("column_arithmetic");
  expect(result.correct).toBe(true);
});

// ---------- G9：V1 number-input 回归（V2 分流不破坏 V1） ----------
// app_cond 有 6 道 kind=number 题（app_strat 全为必填表征题，不适合 number-input 路径）
test("B5-G9 (E2E 附带) V1 数字题回归：正常渲染、提交、判分", async ({ page }) => {
  const ctx = await pwRequest.newContext({ baseURL: API });
  const session = await ctx.post("/v1/learning/sessions", { data: { child_id: CHILD, subject: "math", requested_minutes: 15 } });
  const sid = (await session.json()).session_id;
  let v1task = null;
  for (let i = 0; i < 8 && !v1task; i += 1) {
    const r = await ctx.post("/v1/learning/tasks/next", { data: { child_id: CHILD, session_id: sid, subject: "math", ability_id: "app_cond", requested_minutes: 15 } });
    const t = await r.json();
    // kind=number 即 number-input 路径（representation_required 由题决定，answer composer 均可填）
    if (t.ui_schema?.schema_version === "1.0" && t.ui_schema?.kind === "number") v1task = t;
  }
  await ctx.dispose();
  test.skip(!v1task, "未取到 V1 数字题");
  await pinTasks(page, [{ task: v1task, sessionId: sid }]);
  await page.goto(`/child/math/session/e2e-v1?child_id=${CHILD}&ability_id=app_cond`);
  const answer = page.locator("#math-answer");
  await expect(answer).toBeVisible();
  await answer.fill("3");
  const resPromise = page.waitForResponse(r => r.url().includes("/v1/learning/attempts") && r.status() === 200);
  await page.getByRole("button", { name: /提交/ }).click();
  const json = await (await resPromise).json();
  expect(typeof json.correct).toBe("boolean");
  expect(json.attempt_id).toBeTruthy();
});
