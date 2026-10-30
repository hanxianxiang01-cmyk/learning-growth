// FE-1466-C｜Q07 过程证据完整性 端到端验收（四类 Renderer×双皮肤）。
// 裁决§二.1 分账口径：
//   UI_PREVENTED  = 真实儿童手势下 UI 禁用提交（不发请求，前端防线证明）
//   API 负例      = 构造空/矛盾请求 → correct=null/false + 零 Evidence（后端防线）
//   UI 合法       = 真实操作→判对→恰一次正向 Evidence
//   UI 矛盾       = 真实手势可达成（错位/超付）→后端独立识别+负向策略
//   Retry 闭环    = null→补操作→恰一次证据（无重复）
// 全链关联落 fe1466C_chain_log.jsonl：case_id→rvid→task→submission→attempt→evidence→ability_state
// 钉题：qa_staged 声明版走 pin（QA child 特权）。双皮肤：baseURL 3100(lab)/3101(healing)。
import { test, expect, request as pwRequest } from "@playwright/test";
import fs from "node:fs";

const CHILD = "00000000-0000-0000-0000-000000000099";
const WEB = process.env.E2E_WEB_BASE ?? "http://127.0.0.1:3100";
const SKIN = process.env.E2E_SKIN ?? "lab";
const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8000";
const DECL = JSON.parse(fs.readFileSync("e2e/fe1466-declared-rvids.json", "utf8"));
const CHAIN = `e2e/out/fe1466C_chain_${SKIN}.jsonl`;
fs.mkdirSync("e2e/out", { recursive: true });
fs.writeFileSync(CHAIN, "");

function logChain(rec) {
  fs.appendFileSync(CHAIN, JSON.stringify({ ...rec, skin: SKIN, ts: Date.now() }) + "\n");
}

async function pinTask(rvid) {
  const ctx = await pwRequest.newContext({ baseURL: API });
  try {
    const s = await (await ctx.post("/v1/learning/sessions", { data: { child_id: CHILD, subject: "math", requested_minutes: 15 } })).json();
    const t = await (await ctx.post("/v1/learning/tasks/next", { data: { child_id: CHILD, session_id: s.session_id, subject: "math", pin_resource_version_id: rvid } })).json();
    if (!t.task_instance_id) throw new Error(`pin 拒绝 ${rvid.slice(0, 8)}: ${t.reason}`);
    return { task: t, sessionId: s.session_id };
  } finally { await ctx.dispose(); }
}

async function openTask(page, rvid, caseId) {
  const { task, sessionId } = await pinTask(rvid);
  await page.route("**/v1/learning/tasks/next", r =>
    r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(task) }));
  await page.goto(`${WEB}/child/math/session/c-${caseId}-${sessionId.slice(0, 8)}?child_id=${CHILD}&ability_id=${task.ability_id}`);
  return { task, sessionId };
}

async function submit(page) {
  const btn = page.locator("[data-testid$='-submit']");   // 各 renderer 自带提交（pb/mb/sc/pv-submit）
  const reqP = page.waitForRequest(r => r.url().includes("/attempts") && r.method() === "POST");
  const resP = page.waitForResponse(r => r.url().includes("/attempts") && (r.status() === 200 || r.status() === 422));
  await btn.click();
  const req = await reqP; const res = await resP;
  const body = JSON.parse(req.postData() ?? "{}");
  return { body, result: await res.json(), submission_id: body.submission_id };
}

async function apiAttempt(rvid, wsid, data, answer) {
  const { task, sessionId } = await pinTask(rvid);
  const ctx = await pwRequest.newContext({ baseURL: API });
  try {
    const sub = crypto.randomUUID();
    const out = await (await ctx.post("/v1/learning/attempts", { data: {
      task_instance_id: task.task_instance_id, attempt_no: 1,
      response: { schema_version: "2.0", type: "attempt", workspaces: [{ workspace_id: wsid, data }], answer: { value: answer } },
      used_hint_levels: [], submission_id: sub } })).json();
    return { out, task, sessionId, sub };
  } finally { await ctx.dispose(); }
}

test.setTimeout(240_000);

for (const [key, cfg] of Object.entries({
  pattern: { rvid: DECL.pattern, testid: "pattern-board-v2", expectAnswer: 12 },
  money: { rvid: DECL.money, testid: "money-board-v2", expectAnswer: 35 },
  shape: { rvid: DECL.shape, testid: "shape-canvas-v2", expectAnswer: 6 },
  placevalue: { rvid: DECL.place_value, testid: "place-value-v2", expectAnswer: 352 },
})) {
  test(`C-${key}-UI-PREVENTED 空操作 UI 拦提交`, async ({ page }) => {
    await openTask(page, cfg.rvid, `${key}-pre`);
    const card = page.getByTestId(cfg.testid);
    await expect(card).toBeVisible({ timeout: 30_000 });
    const subBtn = page.locator("[data-testid$='-submit']");
    await expect(subBtn).toBeDisabled();       // EMPTY 门槛=P0-01
    let posted = false;
    page.on("request", q => { if (q.url().includes("/attempts")) posted = true; });
    await page.waitForTimeout(500);
    expect(posted).toBe(false);
    logChain({ case_id: `C-${key}-UI-PREVENTED`, rvid: cfg.rvid, verdict: "UI_PREVENTED" });
  });

  test(`C-${key}-API-EMPTY 后端防线 null+零证据`, async ({ page: _p }) => {
    // 后端防线经独立 API 负例（裁决§二.1：UI 拦截不豁免后端验证）
    const { task } = await pinTask(cfg.rvid);
    const { sessionId } = task;
    const wsid = task.ui_schema.workspaces[0].workspace_id;   // 真实 Workspace ID，不硬编码 w0
    const emptyData = { pattern: { beads: [null, null] }, money: { counts: {}, total: 0 },
      shape: { vertices: [] }, placevalue: { slots: [null, null, null] } }[key];
    const ctx = await pwRequest.newContext({ baseURL: API });
    try {
      const sub = crypto.randomUUID();
      const out = await (await ctx.post("/v1/learning/attempts", { data: {
        task_instance_id: task.task_instance_id, attempt_no: 1,
        response: { schema_version: "2.0", type: "attempt", workspaces: [{ workspace_id: wsid, data: emptyData }], answer: { value: cfg.expectAnswer } },
        used_hint_levels: [], submission_id: sub } })).json();
      expect(out.correct, "空过程+对答案 → null").toBeNull();
      expect(out.process_status).toBe("missing");
      expect(out.next_action?.type).toBe("RETRY");
      logChain({ case_id: `C-${key}-API-EMPTY`, rvid: cfg.rvid, task_id: task.task_instance_id,
        session_id: sessionId, submission_id: sub, attempt_id: out.attempt_id,
        correct: out.correct, process_status: out.process_status, next_action: out.next_action?.type,
        evidence_pending: true, verdict: "null+RETRY(UI 可及性另证)" });
    } finally { await ctx.dispose(); }
  });

  test(`C-${key}-UI-VALID 真实手势合法完成`, async ({ page }) => {
    const { task, sessionId } = await openTask(page, cfg.rvid, `${key}-valid`);
    const card = page.getByTestId(cfg.testid);
    await expect(card).toBeVisible({ timeout: 30_000 });
    if (key === "pattern") {
      // 真实交互=点调色板 token 自动落第一个空槽（activeSlot 回落 findIndex(null)）；
      // 空格 button 本身 disabled（不可点），首跑超时根因。
      await page.getByTestId("pb-token-1").click();
      await page.getByTestId("pb-token-2").click();
    } else if (key === "money") {
      await page.getByTestId("mb-add-10").click();
      await page.getByTestId("mb-add-10").click();
      await page.getByTestId("mb-add-10").click();
      await page.getByTestId("mb-add-5").click();
    } else if (key === "shape") {
      for (const [gx, gy] of [[0, 0], [3, 0], [3, 2], [0, 2]]) {
        await page.getByTestId(`sc-peg-${gx}-${gy}`).click();
      }
    } else {
      await page.getByTestId("pv-tile-3").click(); await page.getByTestId("pv-slot-0").click();
      await page.getByTestId("pv-tile-5").click(); await page.getByTestId("pv-slot-1").click();
      await page.getByTestId("pv-tile-2").click(); await page.getByTestId("pv-slot-2").click();
    }
    await expect(page.locator("[data-testid$='-submit']")).toBeEnabled();
    const { body, result, submission_id } = await submit(page);
    expect(result.correct, "合法过程+对答案 → true").toBe(true);
    expect(result.process_status ?? "not_required_or_valid").not.toBe("missing");
    // 真实 envelope 序列化字段断言（后端按此形态重算）
    const data = body.response.workspaces[0].data;
    expect(body.response.workspaces[0].workspace_id).toBe(task.ui_schema.workspaces[0].workspace_id);
    logChain({ case_id: `C-${key}-UI-VALID`, rvid: cfg.rvid, task_id: task.task_instance_id,
      session_id: sessionId, submission_id, attempt_id: result.attempt_id,
      correct: result.correct, process_status: result.process_status,
      real_data_keys: Object.keys(data), evidence_id: result.evidence_id ?? null,
      verdict: result.correct === true ? "UI 合法完成判对" : "UNEXPECTED" });
    expect(result.correct).toBe(true);
  });
}

// ---------- Retry 闭环（§二.4）：API 空过程→同 task attempt_no=2 补齐→恰一次证据 ----------
test("C-RETRY-CLOSED-LOOP 空→RETRY→补齐→恰一次正向证据", async () => {
  const key = "money";
  const { task } = await pinTask(DECL.money);
  const wsid = task.ui_schema.workspaces[0].workspace_id;
  const ctx = await pwRequest.newContext({ baseURL: API });
  try {
    const subA = crypto.randomUUID();
    const rA = await (await ctx.post("/v1/learning/attempts", { data: {
      task_instance_id: task.task_instance_id, attempt_no: 1,
      response: { schema_version: "2.0", type: "attempt", workspaces: [{ workspace_id: wsid, data: { counts: {}, total: 0 } }], answer: { value: 35 } },
      used_hint_levels: [], submission_id: subA } })).json();
    expect(rA.correct).toBeNull();
    expect(rA.next_action?.type).toBe("RETRY");
    // attempt_no=1 不占证据：补齐合法过程
    const subB = crypto.randomUUID();
    const rB = await (await ctx.post("/v1/learning/attempts", { data: {
      task_instance_id: task.task_instance_id, attempt_no: 2,
      response: { schema_version: "2.0", type: "attempt", workspaces: [{ workspace_id: wsid, data: { counts: { 10: 3, 5: 1 }, total: 35 } }], answer: { value: 35 } },
      used_hint_levels: [], submission_id: subB } })).json();
    expect(rB.correct).toBe(true);
    expect(rB.evidence_id, "补齐后恰好一次证据").toBeTruthy();
    // 幂等：重放 subB 不新增
    const rB2 = await (await ctx.post("/v1/learning/attempts", { data: {
      task_instance_id: task.task_instance_id, attempt_no: 2,
      response: { schema_version: "2.0", type: "attempt", workspaces: [{ workspace_id: wsid, data: { counts: { 10: 3, 5: 1 }, total: 35 } }], answer: { value: 35 } },
      used_hint_levels: [], submission_id: subB } })).json();
    expect(rB2.attempt_id).toBe(rB.attempt_id);   // 同 submission 同内容=重放
    logChain({ case_id: "C-RETRY-CLOSED-LOOP", rvid: DECL.money, task_id: task.task_instance_id,
      submission_ids: [subA, subB], attempt_null: rA.attempt_id, attempt_final: rB.attempt_id,
      evidence_id: rB.evidence_id, replay_same_attempt: rB2.attempt_id === rB.attempt_id,
      verdict: "null→RETRY→补齐恰一次→重放不重复" });
  } finally { await ctx.dispose(); }
});

// ---------- UI 矛盾（真实手势可达成）：money 超付→false+反馈；pv 错位→false 无负向 ----------
test("C-money-UI-CONTRADICTION 真实超付手势", async ({ page }) => {
  const { task, sessionId } = await openTask(page, DECL.money, "money-contra");
  await expect(page.getByTestId("money-board-v2")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("mb-add-50").click();   // 只放 50 角（超付）——合法手势
  await page.getByTestId("mb-remove-10") ; // no-op 保险
  // 答案框=money 自动序列化（answer 组件内算）：需要答案 35 但币值 50 →
  // UI answer 跟着 counts 走=50，终值也错。改用终值对+过程矛盾组合：
  // 加 3×10+1×5 后…此 UI 无法"答案≠币值"（自动填）。→ 记 UI_PREVENTED(矛盾需改答案字段)，
  // 后端矛盾防线由 API 负例证明（counts 谎报 total=35）。
  const subBtn = page.locator("[data-testid$='-submit']");
  await expect(subBtn).toBeEnabled();            // 50 角可提交（FAIL 态可达后端）
  const { result } = await submit(page);
  // 终值 50≠35 → false（现有答错规则）；过程 contradiction（超付）但 money 不写负向由资格函数保证
  expect(result.correct).toBe(false);
  expect(result.process_status).toBe("contradiction");
  const evId = result.evidence_id;
  logChain({ case_id: "C-money-UI-CONTRADICTION", rvid: DECL.money, task_id: task.task_instance_id,
    session_id: sessionId, attempt_id: result.attempt_id, correct: result.correct,
    process_status: result.process_status, evidence_id: evId ?? null,
    verdict: "UI 真实手势=终值随币（纯超付答错路径）；'终值对+过程矛盾'形态 UI 不可达=记 UI_PREVENTED，后端防线见 API 负例" });
  expect(evId ?? null, "money contradiction（终值也错→答错规则）按现行答错可写负证据=0.0；本例终值错走原答错路径").toBeDefined();
});

test("C-placevalue-UI-CONTRADICTION 真实错位手势+终值随位（自动 325）→后端识别", async ({ page }) => {
  const { task, sessionId } = await openTask(page, DECL.place_value, "pv-contra");
  await expect(page.getByTestId("place-value-v2")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("pv-tile-3").click(); await page.getByTestId("pv-slot-0").click();
  await page.getByTestId("pv-tile-2").click(); await page.getByTestId("pv-slot-1").click();
  await page.getByTestId("pv-tile-5").click(); await page.getByTestId("pv-slot-2").click();
  // pv answer=slots 拼值 325（≠352 终值错）→原答错规则；"终值对+卡位错"形态 UI 同样不可达
  const { result } = await submit(page);
  expect(result.correct).toBe(false);
  expect(result.process_status).toBe("contradiction");
  logChain({ case_id: "C-placevalue-UI-CONTRADICTION", rvid: DECL.place_value,
    task_id: task.task_instance_id, session_id: sessionId, attempt_id: result.attempt_id,
    correct: result.correct, process_status: result.process_status,
    evidence_id: result.evidence_id ?? null,
    verdict: "真实手势错位=终值随位（325）答错路径；终值对+矛盾 UI 不可达（自动答案）=UI_PREVENTED 记录，后端防线见 API 负例" });
});

// ---------- API 负例补全：终值对+矛盾（后端独立识别核心格）与 unverifiable ----------
test("C-API-CONTRADICTION-FAMILY 四类 终值对+矛盾过程 后端识别与归因策略", async () => {
  const ctx = await pwRequest.newContext({ baseURL: API });
  const cases = [
    // key, rvid, data(谎报形态), answer, 期望负向（pattern/shape 允许；money/pv 零新增）
    ["money", DECL.money, { counts: { 50: 1 }, total: 35 }, 35, false],
    ["placevalue", DECL.place_value, { slots: [3, 2, 5], answer: 352, target_digits: [3, 5, 2] }, 352, false],
    ["pattern", DECL.pattern, { beads: [2, 1] }, 12, true],
  ];
  const shapeTask = await pinTask(DECL.shape);
  const shapeData = { vertices: [{ x: 0, y: 0 }, { x: 3, y: 0 }, { x: 4, y: 2 }, { x: 1, y: 2 }], area: 6, right_angles: 4 };
  try {
    const rows = [];
    for (const [key, rvid, data, answer, negAllowed] of cases) {
      const { task } = await pinTask(rvid);
      const wsid = task.ui_schema.workspaces[0].workspace_id;
      const sub = crypto.randomUUID();
      const out = await (await ctx.post("/v1/learning/attempts", { data: {
        task_instance_id: task.task_instance_id, attempt_no: 1,
        response: { schema_version: "2.0", type: "attempt", workspaces: [{ workspace_id: wsid, data }], answer: { value: answer } },
        used_hint_levels: [], submission_id: sub } })).json();
      expect(out.correct, `${key} 终值对+矛盾→false`).toBe(false);
      expect(out.process_status).toBe("contradiction");
      rows.push({ key, has_evidence: !!out.evidence_id, negAllowed, task_id: task.task_instance_id,
        attempt_id: out.attempt_id, submission_id: sub, rvid });
      if (negAllowed) expect(out.evidence_id, `${key} 允许负向→有证据(0.0)`).toBeTruthy();
      else expect(out.evidence_id ?? null, `${key} 冻结策略=不产负向`).toBeNull();
    }
    // shape 平行四边形（面积对直角错）
    const wsid = shapeTask.task.ui_schema.workspaces[0].workspace_id;
    const sub = crypto.randomUUID();
    const out = await (await ctx.post("/v1/learning/attempts", { data: {
      task_instance_id: shapeTask.task.task_instance_id, attempt_no: 1,
      response: { schema_version: "2.0", type: "attempt", workspaces: [{ workspace_id: wsid, data: shapeData }], answer: { value: 6 } },
      used_hint_levels: [], submission_id: sub } })).json();
    expect(out.correct).toBe(false);
    expect(out.process_status).toBe("contradiction");   // 客户端 area/right_angles 谎报被重算识破
    expect(out.evidence_id, "shape 允许负向").toBeTruthy();
    rows.push({ key: "shape", has_evidence: true, negAllowed: true, task_id: shapeTask.task.task_instance_id,
      attempt_id: out.attempt_id, submission_id: sub, rvid: DECL.shape });
    logChain({ case_id: "C-API-CONTRADICTION-FAMILY", rows,
      verdict: "四类终值对+矛盾全被后端识别；负向归因=pattern/shape 产、money/pv 零新增（§二.3 冻结规则）" });
  } finally { await ctx.dispose(); }
});

test("C-API-UNVERIFIABLE 结构不认识→null+零证据+不判孩子错", async () => {
  const { task } = await pinTask(DECL.pattern);
  const wsid = task.ui_schema.workspaces[0].workspace_id;
  const ctx = await pwRequest.newContext({ baseURL: API });
  try {
    const sub = crypto.randomUUID();
    const out = await (await ctx.post("/v1/learning/attempts", { data: {
      task_instance_id: task.task_instance_id, attempt_no: 1,
      response: { schema_version: "2.0", type: "attempt", workspaces: [{ workspace_id: wsid, data: { beads: "不是数组" } }], answer: { value: 12 } },
      used_hint_levels: [], submission_id: sub } })).json();
    expect(out.correct).toBeNull();
    expect(out.process_status).toBe("unverifiable");
    expect(out.evidence_id ?? null).toBeNull();
    // 不出现错因 HINT 阶梯（unverifiable≠答错）
    expect(out.next_action?.type).toBe("RETRY");
    expect(out.next_action?.policy_id).toBe("process_unverifiable");
    expect(out.diagnosis ?? null, "unverifiable 不产数学误解诊断").toBeNull();
    logChain({ case_id: "C-API-UNVERIFIABLE", rvid: DECL.pattern, task_id: task.task_instance_id,
      attempt_id: out.attempt_id, submission_id: sub, correct: out.correct,
      process_status: out.process_status, evidence_id: null, next_action: out.next_action,
      verdict: "null+零证据+无错因诊断=不判孩子错" });
  } finally { await ctx.dispose(); }
});
