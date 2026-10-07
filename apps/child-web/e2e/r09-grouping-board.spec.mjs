// FE-1422 R09 grouping-board 真实页面 E2E（B5 模板第九实例；主动建组平均分物）。
// 合同：B5_E2E_VERTICAL_GATE.md + Gap R09（Diagnosis=分组数量/每组数量错误 P0）。
// 数据卫生：CHILD=QA-Simulator …0099；ability=app_rel，12糖分3组答案4。
// 钉题：FE-1422a 确定性 pin（查 /v1/content/v2-catalog → 逐 task 新 session + pin），
// 不再靠 band 运气抽题。
import { test, expect, request as pwRequest } from "@playwright/test";
import { fetchPinnedTasks } from "./pinned-tasks.mjs";

const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8000";
const CHILD = process.env.E2E_CHILD_ID ?? "00000000-0000-0000-0000-000000000099";
const ABILITY = "app_rel";

function r09Tasks(k) {
  return fetchPinnedTasks({ api: API, child: CHILD, renderer: "grouping-board", count: k });
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

const card = page => page.getByTestId("grouping-board-v2");
const submitButton = page => page.getByTestId("gb-submit");

/** 建 g 个组，然后轮转发放共 n 颗。 */
async function buildAndDistribute(page, groups, perGroup, rounds = 1) {
  for (let g = 0; g < groups; g += 1) await page.getByTestId("gb-add-group").click();
  for (let r = 0; r < rounds; r += 1) {
    for (let j = 0; j < groups; j += 1) {
      for (let i = 0; i < (perGroup[j] ?? perGroup); i += 1) {
        await page.getByTestId(`gb-give-${j}`).click();
      }
    }
  }
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
test("R09-E2E-09 (G1) 渲染 grouping-board V2，池满未分禁提交", async ({ page }) => {
  const [r] = await r09Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("g1"));
  await expect(card(page)).toBeVisible();
  await expect(page.getByTestId("planned-renderer")).toHaveCount(0);
  await expect(page.getByTestId("gb-pool-count")).toHaveText("12");
  await expect(page.getByTestId("gb-evaluation")).toContainText("先圈一个组吧");
  await expect(submitButton(page)).toBeDisabled();
});

// ---------- G2/G3：没发完仍 EMPTY ----------
test("R09-E2E-03 (G2/G3) 建3组只发11颗 → 池剩1 仍 EMPTY", async ({ page }) => {
  const [r] = await r09Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("partial"));
  await page.getByTestId("gb-add-group").click();
  await page.getByTestId("gb-add-group").click();
  await page.getByTestId("gb-add-group").click();
  for (let j = 0; j < 3; j += 1)
    for (let i = 0; i < (j === 2 ? 3 : 4); i += 1) await page.getByTestId(`gb-give-${j}`).click();
  await expect(page.getByTestId("gb-pool-count")).toHaveText("1");
  await expect(page.getByTestId("gb-evaluation")).toContainText("还有 1 颗没分出去");
  await expect(submitButton(page)).toBeDisabled();
});

// ---------- count 靶：2组发完 → 组数不对提示 → FAIL 可提交 ----------
test("R09-COUNT 建2组(6,6)发完 → count 提示 → correct=false HINT + 证据", async ({ page }) => {
  const [r] = await r09Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("count"));
  await buildAndDistribute(page, 2, 6);
  await expect(page.getByTestId("gb-evaluation")).toContainText("你现在分了 2 组");
  await expect(submitButton(page)).toBeEnabled();
  const { body, result } = await submitAttempt(page);
  expect(body.response.type).toBe("grouping_board");
  const data = body.response.workspaces[0].data;
  expect(data.groups).toEqual([6, 6]);
  expect(data.pool_remaining).toBe(0);
  expect(data.structure.error).toBe("count");
  expect(data.target_groups).toBe(3);
  expect(result.correct).toBe(false);
  expect(result.next_action.type).toBe("HINT");
  const types = body.response.interaction_events.map(e => e.event_type);
  expect(types).toContain("GROUP_CREATED");
  expect(types).toContain("ITEM_ADDED");
});

// ---------- unequal 靶：3组不均 → 公平提示 → 证据 ----------
test("R09-UNEQUAL 3组(5,4,3) → unequal 提示 → correct=false HINT", async ({ page }) => {
  const [r] = await r09Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("unequal"));
  await page.getByTestId("gb-add-group").click();
  await page.getByTestId("gb-add-group").click();
  await page.getByTestId("gb-add-group").click();
  for (let i = 0; i < 5; i += 1) await page.getByTestId("gb-give-0").click();
  for (let i = 0; i < 4; i += 1) await page.getByTestId("gb-give-1").click();
  for (let i = 0; i < 3; i += 1) await page.getByTestId("gb-give-2").click();
  await expect(page.getByTestId("gb-evaluation")).toContainText("平均才公平");
  const { body, result } = await submitAttempt(page);
  expect(body.response.workspaces[0].data.structure.error).toBe("unequal");
  expect(result.correct).toBe(false);
});

// ---------- 修正路径（R09 独有）：收回多发的一颗补给少的组 ----------
test("R09-FIX (5,4,3)→收回1→补组2→(4,4,4) PASS 判对", async ({ page }) => {
  const [r] = await r09Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("fix"));
  await page.getByTestId("gb-add-group").click();
  await page.getByTestId("gb-add-group").click();
  await page.getByTestId("gb-add-group").click();
  for (let i = 0; i < 5; i += 1) await page.getByTestId("gb-give-0").click();
  for (let i = 0; i < 4; i += 1) await page.getByTestId("gb-give-1").click();
  for (let i = 0; i < 3; i += 1) await page.getByTestId("gb-give-2").click();
  // 修正：组0 收回 1 → 组2 补 1
  await page.getByTestId("gb-take-0").click();
  await page.getByTestId("gb-give-2").click();
  await expect(page.getByTestId("gb-group-count-0")).toHaveText("4");
  await expect(page.getByTestId("gb-group-count-2")).toHaveText("4");
  await expect(page.getByTestId("gb-evaluation")).toContainText("每组分 4 颗");
  const { result } = await submitAttempt(page);
  expect(result.correct).toBe(true);
  await expect(page.getByRole("button", { name: /下一题/ })).toBeVisible();
});

// ---------- 解散空组 + 防丢物（非空组不可解散） ----------
test("R09-DISMISS 有糖组不可解散；收空后可解散", async ({ page }) => {
  const [r] = await r09Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("dismiss"));
  await page.getByTestId("gb-add-group").click();
  await page.getByTestId("gb-add-group").click();
  await page.getByTestId("gb-give-0").click();
  // 组0 有 1 颗糖：解散 disabled
  await expect(page.getByTestId("gb-dismiss-0")).toBeDisabled();
  await page.getByTestId("gb-take-0").click(); // 收回变空
  await expect(page.getByTestId("gb-dismiss-0")).toBeEnabled();
  await page.getByTestId("gb-dismiss-0").click();
  // 组0 解散：原组1 顶替为索引0，现在只剩一个组（池仍 11 颗+组内）
  await expect(page.getByTestId("gb-groups").locator(".gb-group")).toHaveCount(1);
  await expect(page.getByTestId("gb-group-0")).toBeVisible();
  await expect(page.getByTestId("gb-group-count-0")).toHaveText("0");
});

// ---------- G5：直接分对 ----------
test("R09-E2E-01 (G5) 3组×4 分对 → correct=true → NEXT_TASK", async ({ page }) => {
  const [r] = await r09Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("pass"));
  await buildAndDistribute(page, 3, 4);
  await expect(page.getByTestId("gb-evaluation")).toContainText("分好啦");
  await expect(page.getByTestId("gb-pool-count")).toHaveText("0");
  const { result } = await submitAttempt(page);
  expect(result.correct).toBe(true);
  await expect(page.getByRole("button", { name: /下一题/ })).toBeVisible();
});

// ---------- G7：count 错 → 提示 → 再圈一组改对 ----------
test("R09-G7 分2组(6,6)错 → 提示 → 圈第3组重分：attempt_no=2", async ({ page }) => {
  const [r] = await r09Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("retry"));
  await buildAndDistribute(page, 2, 6);
  const first = await submitAttempt(page);
  expect(first.result.correct).toBe(false);
  await page.getByRole("button", { name: /给我一点提示/ }).click();
  await page.getByRole("button", { name: /我再想想/ }).click();
  // 状态保留：收空两组的糖（回池 12）、圈第 3 组、重发 4/4/4
  for (const j of [0, 1]) for (let i = 0; i < 6; i += 1) await page.getByTestId(`gb-take-${j}`).click();
  await page.getByTestId("gb-add-group").click(); // 现有3组
  for (let round = 0; round < 4; round += 1)
    for (let j = 0; j < 3; j += 1) await page.getByTestId(`gb-give-${j}`).click();
  const second = await submitAttempt(page);
  expect(second.result.correct).toBe(true);
  expect(second.body.attempt_no).toBe(2);
});

// ---------- E2E-07：UNDO + 双击防重入 ----------
test("R09-E2E-07 UNDO 收回最后一步；双击只 1 POST", async ({ page }) => {
  const [r] = await r09Tasks(1);
  await pinTasks(page, [r]);
  await page.goto(sessionUrl("undo"));
  await buildAndDistribute(page, 3, 4);
  // 撤销最后一步（给组2 第4颗）→ 组2=3、池=1 → EMPTY
  await page.getByTestId("gb-undo").click();
  await expect(page.getByTestId("gb-group-count-2")).toHaveText("3");
  await expect(page.getByTestId("gb-pool-count")).toHaveText("1");
  await expect(submitButton(page)).toBeDisabled();
  await page.getByTestId("gb-give-2").click();
  let posts = 0;
  page.on("request", q => {
    if (q.url().includes("/v1/learning/attempts") && q.method() === "POST") posts += 1;
  });
  await submitButton(page).dblclick();
  await page.waitForTimeout(2500);
  expect(posts).toBe(1);
});

// ---------- E2E-08：revision 切换清池 ----------
test("R09-E2E-08 下一题重置池子和组", async ({ page }) => {
  const two = await r09Tasks(2);
  const task2 = structuredClone(two[1].task);
  task2.ui_schema.ui_revision = `${two[1].task.ui_schema.ui_revision}-rev2`;
  await pinTasks(page, [two[0], { task: task2, sessionId: two[1].sessionId }]);
  await page.goto(sessionUrl("rev"));
  await buildAndDistribute(page, 3, 4);
  await submitAttempt(page);
  await page.getByRole("button", { name: /下一题/ }).click();
  await expect(card(page)).toBeVisible();
  await expect(page.getByTestId("gb-pool-count")).toHaveText("12");
  await expect(page.getByTestId("gb-groups").locator(".gb-group")).toHaveCount(0);
  await expect(submitButton(page)).toBeDisabled();
});

// ---------- 双皮肤 ----------
test("R09-E2E-10 healing 皮肤同契约", async ({ page }) => {
  test.skip(!process.env.E2E_HEALING_BASE, "需 3101 healing 实例");
  const [r] = await r09Tasks(1);
  await pinTasks(page, [r]);
  const url = new URL(sessionUrl("healing"), process.env.E2E_HEALING_BASE);
  await page.goto(url.toString());
  await expect(page.locator("[data-child-math-skin]")).toHaveAttribute("data-child-math-skin", "healing");
  await buildAndDistribute(page, 3, 4);
  const { body, result } = await submitAttempt(page);
  expect(body.response.type).toBe("grouping_board");
  expect(result.correct).toBe(true);
});
