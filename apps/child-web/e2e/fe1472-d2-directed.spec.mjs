// FE-1472 DEF-D2 三题：真实页面前端层定向实测。
//
// ## 为什么是这个形态（而不是完整 E2E 提交）
//
// 本轮启动三件套后，`POST /v1/learning/sessions` 返回 500，后端日志实测：
//
//     psycopg.errors.InsufficientPrivilege:
//     permission denied for table learning_session
//
// 本机 Keychain 只有 `iqc-database-url`（`current_user = iqc_readonly`，
// `learning_session` 仅 SELECT）。**E2E 提交必须写库**，这一层本轮无法执行，
// 也不应绕过权限去做。因此本文件只测**不依赖写库**的那部分事实：
//
//   H1 未知条滑条上限 = 该条自己的 max（15/12/11），不是 visual.max_value（17/14/13）
//   H2 未知条能到「另一个人的数量」（7 / 12 / 11）——正确候选状态可达
//   H3 合计值超过单条上限会被夹住，**这是预期行为，不是缺陷**。
//      两根条分表两个人的数量，合计本应由数字答案表达；把合计塞进代表另一人的条
//      属**错误表征**。故四禁：不扩滑条上限、不加第三根条、不改答案、不改 Published。
//      注意巧合：d2-2 的 12、d2-3 的 11 既是正确未知量、又是滑条上限，
//      所以"被夹到上限"停下的值在第二、三题恰好就是正确答案，不能当半成品证据。
//   H3b 显式构造错误表征（未知条停在 15、答案填 18），验证前端**照原样**发送不一致输入。
//      只证明"前端不拦截"，**不涉后端判分**。
//   H4a `representation_required=true` 且表征存在 → 答案框**可用**，且提交体
//       **显式**携带 representation.bars，两根条值须符合题意（base=已知量、unknown=另一人）
//   H4b 表征缺失 → 答案框与提交按钮**必须禁用**（**合成负例**，生产题库无此配置，见下）
//
// H4 是判分行为的**前置条件**而非判分本身：`AnswerComposer` 的 disabled 由
// `schema.response_schema.representation_required && !response.representation`
// 决定（TaskRenderer.tsx:102/155）。它证明"表征非空"是提交的必要条件，
// 但不能证明"表征正确"也是——后者要读后端判分，本轮未做。
//
// ## 两轮补正修掉的语义问题（记账，避免再犯）
//
// 第一轮：H4 有两处"看着有、实际不断言"（`console.log(isDisabled())` 不形成断言；
// `bars ?? null` + `if (repBars)` 缺字段时静默跳过）。已改无条件断言。
//
// 第二轮（验收方指出，**更严重**）：
//   ① H3 曾把"合计 ≠ 单条未知量"当作半成品证据 —— 这是把**正确的数学关系**
//      误判成异常。合计本来就不等于任一加数，该断言恒真、零信息量。
//      且提交前未恢复正确未知量，第一题实际提交了 15（既非 7 也非 18）。
//   ② H4b 曾被表述得像生产故障复现，实际生产题库 **0 题**是该配置。
//   ③ UI-TEXT 曾把「正在判断…」断言成预期值，会让将来正确修复反而 FAIL。
// 三处均已按上述方式修正；文案缺陷移入台账（docs/qa §12.6）而不再断言。
//
// ## 数据来源
//
// ui_schema 直接取自现场 RDS 的 `resource_version`（只读取证，已核对
// `current_user=iqc_readonly`），在浏览器内通过 route 注入真实 task。
// **不改动任何生产内容**：不扩滑条上限、不加第三根条、不改答案、不改 Published。
//
// ## 提交拦截
//
// 所有 `POST /v1/learning/attempts` 被 route 拦截并返回构造的响应，
// 因此本文件**不写任何表**。拦截同时抓下实际请求体，用于核对上报的 answer 与表征。
import { test, expect } from "@playwright/test";

const CHILD = process.env.E2E_CHILD_ID ?? "00000000-0000-0000-0000-000000000099";
const ABILITY = "app_model";

// 三题数值全部取自现场 DB（见本文件顶注），不凭记忆写。
const CASES = [
  {
    rvid: "421ede36-8f1b-4b10-9433-e92f039231bd",
    tag: "d2-1",
    known: 11, unknownMax: 15, maxValue: 17, answer: 18, other: 7,
    stem: "小青有11张贴纸，小雨比小青少4张。两个人一共有多少张贴纸？"
  },
  {
    rvid: "6e5395f0-def7-4060-a501-044d8e9a3764",
    tag: "d2-2",
    known: 9, unknownMax: 12, maxValue: 14, answer: 21, other: 12,
    stem: "小明有9本故事书，小红比小明多3本。两个人一共有多少本故事书？"
  },
  {
    rvid: "8981fbcc-5b92-44b6-ab89-6b8ef0e715fd",
    tag: "d2-3",
    known: 8, unknownMax: 11, maxValue: 13, answer: 19, other: 11,
    stem: "小兰有8颗糖，小杰比小兰多3颗。两个人一共有多少颗糖？"
  }
];

/** 现场 DB 的 ui_schema 原样重建（字段与 421ede36 等三题完全一致）。 */
function buildTask(c) {
  return {
    task_instance_id: `e2e-d2-${c.tag}-${c.rvid}`,
    ability_id: ABILITY,
    difficulty: 2,
    resource_version_id: c.rvid,
    goal: "能借助线段图理解比较关系并求合计",
    strategy_policy: {},
    ui_schema: {
      kind: "manipulative",
      schema_version: "1.0",
      prompt: c.stem,
      tools: ["label", "align", "undo", "reset"],
      response_schema: {
        type: "structured",
        answer_type: "number",
        representation_required: true
      },
      answer_placeholder: "输入数字",
      visual: {
        type: "bar-model",
        relationship: "compare",
        max_value: c.maxValue,
        bars: [
          { id: "base", label: "已知", min: 0, max: c.unknownMax, value: c.known },
          { id: "unknown", label: "未知", min: 0, max: c.unknownMax, unknown: true }
        ]
      }
    }
  };
}

const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET,POST,OPTIONS",
  "access-control-allow-headers": "*"
};

/** 拦截所有后端调用，一律不落到真实后端（因此不写库）。 */
async function stubBackend(page, task, captured) {
  await page.route("**/v1/learning/**", async route => {
    const req = route.request();
    const url = req.url();
    if (req.method() === "OPTIONS") {
      return route.fulfill({ status: 204, headers: CORS });
    }
    if (url.includes("/sessions") && req.method() === "POST") {
      return route.fulfill({
        status: 200, headers: { ...CORS, "content-type": "application/json" },
        body: JSON.stringify({ session_id: `sess-${task.task_instance_id}`, child_id: CHILD })
      });
    }
    if (url.includes("/tasks/next")) {
      return route.fulfill({
        status: 200, headers: { ...CORS, "content-type": "application/json" },
        body: JSON.stringify(task)
      });
    }
    if (url.includes("/attempts") && req.method() === "POST") {
      captured.body = JSON.parse(req.postData() ?? "{}");
      return route.fulfill({
        status: 200, headers: { ...CORS, "content-type": "application/json" },
        body: JSON.stringify({
          correct: true,
          next_action: { type: "NEXT_TASK" },
          diagnosis: null,
          feedback: "答对了"
        })
      });
    }
    return route.fulfill({
      status: 200, headers: { ...CORS, "content-type": "application/json" },
      body: JSON.stringify({})
    });
  });
}

function sessionUrl(tag) {
  return `/child/math/session/e2e-${tag}?child_id=${CHILD}&ability_id=${ABILITY}`;
}

const sliders = page => page.locator('[data-testid="bar-model"] input[type="range"]');

async function readSlider(loc) {
  return {
    min: Number(await loc.getAttribute("min")),
    max: Number(await loc.getAttribute("max")),
    value: Number(await loc.inputValue())
  };
}

async function setSlider(loc, value) {
  await loc.evaluate((el, v) => {
    const setter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype, "value").set;
    setter.call(el, String(v));
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }, value);
}

for (const c of CASES) {
  test(`DEF-D2 ${c.tag} ${c.rvid.slice(0, 8)} 未知条可达范围与提交前置闸门`, async ({ page }) => {
    const task = buildTask(c);
    const captured = { body: null };
    await stubBackend(page, task, captured);

    await page.goto(sessionUrl(c.tag));
    await expect(page.getByTestId("bar-model")).toBeVisible({ timeout: 60_000 });

    const n = await sliders(page).count();
    const unknown = sliders(page).nth(n - 1);
    console.log(`\n[${c.tag}] 滑条数=${n}（期望 2：已知条 + 未知条）`);
    expect(n, "bar-model 应为每根条一个滑条").toBe(2);

    // ── H1 上限口径 ────────────────────────────────────────────────────
    const s0 = await readSlider(unknown);
    console.log(`[${c.tag}] 未知条 min=${s0.min} max=${s0.max} 初值=${s0.value}`);
    console.log(`[${c.tag}] 该条 max=${c.unknownMax} / visual.max_value=${c.maxValue}`);
    expect(s0.max,
      `未知条滑条上限应等于该条自己的 max=${c.unknownMax}，而不是 visual.max_value=${c.maxValue}`)
      .toBe(c.unknownMax);
    expect(s0.max, "上限不应恰好等于 visual.max_value（否则两种口径无法区分）")
      .not.toBe(c.maxValue);

    // ── H2 正确候选可达 ───────────────────────────────────────────────
    await setSlider(unknown, c.other);
    const afterOther = await readSlider(unknown);
    console.log(`[${c.tag}] 摆到 ${c.other}（另一个人的数量）→ 滑条读数 ${afterOther.value}`);
    expect(afterOther.value, `未知条应能摆到 ${c.other}`).toBe(c.other);

    // ── H3 合计值超过单条上限：是预期行为，不是缺陷 ─────────────────────
    // **H3 的正确表述**：两根条分别表示两个人的数量，合计本应由**数字答案**表达，
    // 不该塞进任何一根条。所以"合计到不了单条上限"是**正确设计**，不是缺陷。
    // 此前版本把"合计被夹住"当作半成品证据，是把正确的数学关系误判成异常。
    //
    // 另有一个极易踩的巧合（验收方指出）：d2-2 的 12、d2-3 的 11 既是**正确未知量**、
    // 又恰好是该条**滑条上限**。所以"设成合计后被夹到上限"停下来的值，
    // 在第二、三题上**正好就是正确答案**——不能据此说"停在半成品"。
    expect(c.answer, `前置：本题合计 ${c.answer} 应大于未知条上限 ${c.unknownMax}`)
      .toBeGreaterThan(c.unknownMax);
    await setSlider(unknown, c.answer);
    const afterTotal = await readSlider(unknown);
    console.log(`[${c.tag}] 尝试设成合计 ${c.answer} → 实际被夹到 ${afterTotal.value}（预期行为，非缺陷）`);
    expect(afterTotal.value, "设成合计会被浏览器夹到该条上限（预期行为）").toBe(c.unknownMax);
    expect(afterTotal.value, "合计不等于任何一根条的值（数学恒等，不是缺陷证据）")
      .not.toBe(c.answer);

    // ── H2b 提交前恢复正确未知量，并核对两根条符合题意 ──────────────────
    // 关键：**必须显式恢复到正确值再提交**，否则提交的是"停在合计被夹住后的值"，
    // 那不是正确答案（第一题 15≠7；第二、三题虽巧合相等，但语义上并未验证正确性）。
    await setSlider(unknown, c.other);
    const restored = await readSlider(unknown);
    console.log(`[${c.tag}] 提交前恢复正确未知量 ${c.other} → 读数 ${restored.value}`);
    expect(restored.value, `提交前应恢复到正确未知量 ${c.other}`).toBe(c.other);

    // ── H4 提交前置闸门 ────────────────────────────────────────────────
    // H4a 正向：表征存在 → 答案框必须**可用**。
    // 原版只 `console.log(isDisabled())` 不形成断言，等于"H4 是否成立取决于日志里
    // 那行字"，`disabled` 为 true 时测试照样 PASS。改为断言。
    const input = page.locator("#math-answer");
    await expect(input, "答案框应存在（representation_required=true 不应整块隐藏）").toBeVisible();
    console.log(`[${c.tag}] 表征已存在 → 答案框 disabled=${await input.isDisabled()}`);
    await expect(input, "表征已存在时答案框必须可用（disabled 应为 false）").toBeEnabled();

    // 填正确数字答案并提交，抓请求体（拦截，不写库）
    await input.fill(String(c.answer));
    await page.getByRole("button", { name: /提交答案/ }).click();
    await page.waitForFunction(() => true); // 让 route 回调先行落地
    await expect
      .poll(() => captured.body, { message: "应拦截到一次提交请求（证明提交链路可达）", timeout: 10_000 })
      .toBeTruthy();
    const body = captured.body;
    console.log(`[${c.tag}] 拦截到的提交体 answer=${JSON.stringify(body.response.answer)}`);

    // H4a 正向续：提交体必须**显式**携带 representation 与预期 bars。
    // 原版写 `body?.response?.representation?.bars ?? null` 后再 `if (repBars)`，
    // 字段缺失时整段断言被静默跳过——缺字段反而 PASS，属空转。改为无条件断言。
    expect(body.response.representation, "提交体必须携带 representation；缺失即失败（原版在此静默跳过）")
      .toBeTruthy();
    expect(body.response.representation.type, "上报表征类型应为 bar-model").toBe("bar-model");
    expect(Array.isArray(body.response.representation.bars), "上报表征 bars 必须是数组").toBe(true);
    expect(body.response.representation.bars.length, "bar-model 应上报 2 根条").toBe(2);

    // 两根条的值必须**符合题意**：已知条=已知量，未知条=另一个人的数量。
    // 这是"正确表征"的定义，而不是"与答案不相等"这种恒真条件。
    const baseBar = body.response.representation.bars.find(b => b.id === "base");
    const unknownBar = body.response.representation.bars.find(b => b.id === "unknown");
    expect(baseBar, "上报表征必须包含 id=base 的条").toBeTruthy();
    expect(unknownBar, "上报表征必须包含 id=unknown 的条（原版 find 失败时静默跳过）").toBeTruthy();
    console.log(`[${c.tag}] 上报表征 base=${baseBar.value}（应=${c.known}） unknown=${unknownBar.value}（应=${c.other}）`);
    expect(baseBar.value, `已知条应等于题面已知量 ${c.known}`).toBe(c.known);
    expect(unknownBar.value, `未知条应等于正确未知量（另一个人的数量）${c.other}`).toBe(c.other);

    // 正确表征下，两根条之和 = 合计答案。这条才是有意义的自洽性检查，
    // 它同时证明"合计由数字答案表达、两根条各表一人"这个语义没被弄错。
    expect(baseBar.value + unknownBar.value,
      `正确表征下两根条之和应等于合计 ${c.answer}`)
      .toBe(c.answer);
    expect(String(body.response.answer), "上报的数字答案应为填写值").toBe(String(c.answer));
  });
}

// ── H3b 错误表征：显式构造错误状态，验证前端是否照原样发送 ─────────────────
//
// 验收方要求：若还要测"错误表征能提交"，必须**另设明确的错误状态**，
// 而不是拿"合计被夹住"充数。
//
// 本题（d2-1，11/7，合计 18，未知条上限 15）显式构造两种错误：
//   ① 未知条停在 15（既不是正确的 7，也不是合计 18——是无意义值）
//   ② 数字答案填 18（正确合计）
// 预期：前端**照原样**把两者都发出去（不做一致性拦截）。
//
// **本用例只证明"前端允许发送不一致输入"**，不证明后端会判对/判错。
// 本文件拦截了真实后端并对 `correct:true` 只作构造值，故后端行为**未验证**。
test("DEF-D2 H3b 错误表征：前端照原样发送不一致输入（不涉后端判分）", async ({ page }) => {
  const c = CASES[0]; // d2-1：11 / 正确未知 7 / 合计 18 / 上限 15
  // 显式声明错误状态的期望值，避免"看起来不一致就算错"的模糊判定
  const WRONG_UNKNOWN = c.unknownMax; // 15，既非正确答案 7，也非合计 18
  expect(WRONG_UNKNOWN, "前置：错误值必须既不是正确未知量，也不是合计")
    .not.toBe(c.other);
  expect(WRONG_UNKNOWN, "前置：错误值必须既不是正确未知量，也不是合计")
    .not.toBe(c.answer);

  const task = buildTask(c);
  const captured = { body: null };
  await stubBackend(page, task, captured);

  await page.goto(sessionUrl(`${c.tag}-wrong`));
  await expect(page.getByTestId("bar-model")).toBeVisible({ timeout: 60_000 });

  const n = await sliders(page).count();
  const unknown = sliders(page).nth(n - 1);
  await setSlider(unknown, WRONG_UNKNOWN);
  const shown = await readSlider(unknown);
  console.log(`\n[h3b] 未知条显式置于错误值 ${shown.value}（正确应为 ${c.other}，合计 ${c.answer}）`);
  expect(shown.value, "滑条应先到达该错误值").toBe(WRONG_UNKNOWN);

  const input = page.locator("#math-answer");
  await expect(input, "表征存在（虽是错误表征）→ 答案框应可用").toBeEnabled();
  await input.fill(String(c.answer));
  await page.getByRole("button", { name: /提交答案/ }).click();
  await page.waitForFunction(() => true);
  await expect
    .poll(() => captured.body, { message: "前端应放行并发送", timeout: 10_000 })
    .toBeTruthy();

  const bars = captured.body.response.representation.bars;
  const unknownBar = bars.find(b => b.id === "unknown");
  console.log(`[h3b] 实际发送 answer=${JSON.stringify(captured.body.response.answer)} unknown=${unknownBar.value}`);

  // 前端把错误表征**原样**发出（这就是要记录的观察）
  expect(unknownBar.value, "前端应原样发送错误的未知条值（不做一致性拦截）").toBe(WRONG_UNKNOWN);
  expect(String(captured.body.response.answer), "数字答案应原样发送").toBe(String(c.answer));
  expect(unknownBar.value + bars.find(b => b.id === "base").value,
    "错误表征下两根条之和 ≠ 合计（这正是错误所在）")
    .not.toBe(c.answer);

  // 后端判分明确标为未验证：拦截返回的 correct:true 是构造值
  console.log("[h3b] 后端判分：未验证（本文件拦截后端，correct:true 为构造值，非真实 Judge 结果）");
});

// ── H4b 负例：表征缺失 → 答案框必须禁用（**合成负例**）─────────────────────
//
// ## 性质声明（重要，防止冒充生产故障复现）
//
// 本用例是**前端防御逻辑的合成负例**，不是生产题目故障的复现。
// 现场 RDS 实测：`representation_required=true` 的题目共 **37 题，全部
// `kind=manipulative`**，`kind="number"` 为 **0 题**——即**当前生产题库不存在
// 该配置组合**。故它验证的是"闸门表达式在表征缺失时确实会禁用"，
// **不能表述为"已复现一条生产题目不可作答的故障"**，也不需要据此改生产题目。
//
// ## 为什么必须用独立用例而不是在 D2 三题上关掉表征
//
// `createInitialRepresentation()`（math-workspace/model.ts:18-66）对
// objects / bar-model / number-line 三种 visual **都无条件返回非空对象**，
// 且 `WorkspaceProvider` 挂载后立即经 `onWorkspaceChange` 回填 `present`。
// `RESET` 把 `present` 复位成 `state.initial`（同样非空），`UNDO` 在无历史时
// 直接 return state。**因此在 manipulative 题上，「表征缺失」状态在真实 UI 里
// 根本不可达**——若强行在 D2 三题上"构造"该状态，只能靠改写组件内部 state 伪造，
// 那是假证据，不是浏览器实测。
//
// 故负例改用**真实可达**的渲染路径：`schema_version=1.0` + `kind="number"` 走
// `NumberRenderer`（TaskRenderer.tsx:76-108），它**不挂载 WorkspaceProvider**，
// 而 `createEmptyTaskResponse()`（:46-48）不含 `representation` 字段 →
// `representation_required && !response.representation` 恒真 → 答案框应禁用。
// 这条断言检验的正是 `AnswerComposer` 的 disabled 表达式本身。
//
// ## 顺带记录的出题陷阱（写入缺陷台账，不在此处断言文案）
//
// `kind="number"` 一旦配上 `representation_required=true`，因为永远无法挂载
// 工作区，答案框会永久禁用、题目不可作答。当前 0 题踩到，但出题侧应避开。
test("DEF-D2 H4b 合成负例：表征缺失时答案框与提交按钮必须禁用", async ({ page }) => {
  const task = {
    task_instance_id: "e2e-d2-h4b-negative",
    ability_id: ABILITY,
    difficulty: 2,
    resource_version_id: "e2e-d2-h4b-negative",
    goal: "H4 合成负例：representation_required=true 且无工作区可挂载",
    strategy_policy: {},
    ui_schema: {
      kind: "number",
      schema_version: "1.0",
      prompt: "H4 合成负例：这道题要求表征，但没有任何工作区可用。",
      response_schema: {
        type: "structured",
        answer_type: "number",
        representation_required: true
      },
      answer_placeholder: "输入数字"
    }
  };
  const captured = { body: null };
  await stubBackend(page, task, captured);

  await page.goto(sessionUrl("h4b"));
  const input = page.locator("#math-answer");
  await expect(input, "答案框应存在（禁用≠隐藏，便于孩子看见但不误提交）").toBeVisible({ timeout: 60_000 });

  const disabled = await input.isDisabled();
  console.log(`\n[h4b] 表征缺失（无工作区）→ 答案框 disabled=${disabled}`);
  await expect(input, "表征缺失时答案框必须禁用（disabled=true）").toBeDisabled();

  // 提交按钮同样必须禁用，否则键盘/点击仍可绕过。
  // **不按文案定位**：disabled 时文案会变（见台账 DEF-D2-UI-TEXT），
  // 用结构定位 `.answer-composer button`，避免测试与文案耦合。
  const submit = page.locator(".answer-composer button");
  await expect(submit, "答案区应有提交按钮").toHaveCount(1);
  const submitDisabled = await submit.isDisabled();
  const submitText = (await submit.textContent())?.trim() ?? "";
  console.log(`[h4b] 提交按钮 disabled=${submitDisabled}，当前文案=${JSON.stringify(submitText)}`);
  await expect(submit, "表征缺失时提交按钮必须禁用").toBeDisabled();

  // 文案缺陷**只记录不断言**（验收方指正：锁定错误文案会让将来正确修复反而失败）。
  // 台账：docs/qa/FE1469_FE1470_Q03_BATCHES.md §12.6 DEF-D2-UI-TEXT。
  console.log("[h4b] 注：当前 disabled 文案沿用了「正在判断…」，已记入缺陷台账 " +
              "DEF-D2-UI-TEXT（disabled 语义混用）；本用例不断言该文案，修复后应无需改测试");
  // 但"文案不得误导"这一事实可以留一条**弱**信息：不为空即可，
  // 避免出现无文案的按钮（那是另一个可用性缺陷）。
  expect(submitText.length, "提交按钮应有可见文案（空文案属另一类可用性缺陷）").toBeGreaterThan(0);

  console.log(`[h4b] 拦截到的提交请求=${captured.body === null ? "无" : "有"}`);
  expect(captured.body, "禁用状态下不应产生任何提交请求").toBeNull();
});