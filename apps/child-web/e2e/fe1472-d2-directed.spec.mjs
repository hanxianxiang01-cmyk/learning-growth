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
//   H3 未知条到不了两人合计（18 / 21 / 19）——设成合计会被夹到上限。
//      **注意：这不是缺陷**。两根条分表两个人的数量，合计本应由数字答案表达；
//      把合计塞进代表另一人的条属**错误表征**。故四禁：不扩滑条上限、
//      不加第三根条、不改答案、不改 Published。
//   H4a `representation_required=true` 且表征存在 → 答案框**可用**，且提交体
//       **显式**携带 representation.bars（断言，不是日志）
//   H4b 表征缺失 → 答案框与提交按钮**必须禁用**（独立负例用例，见下方注释）
//
// H4 是判分行为的**前置条件**而非判分本身：`AnswerComposer` 的 disabled 由
// `schema.response_schema.representation_required && !response.representation`
// 决定（TaskRenderer.tsx:102/155）。它证明"表征非空"是提交的必要条件，
// 但不能证明"表征正确"也是——后者要读后端判分，本轮未做。
//
// ## 本轮（H4 补正）修正的两处空转
//
// 原版 H4 有两处"看着有、实际不断言"：
//   ① `console.log(await input.isDisabled())` —— 只记录，`disabled=true` 时测试照样 PASS
//   ② `body?.response?.representation?.bars ?? null` + `if (repBars)` ——
//      字段缺失时整段断言被静默跳过，**缺字段反而 PASS**
// 两处都已改成无条件断言。补正不需要可写凭证，也不改任何题目内容。
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

    // ── H3 合计不可达 ─────────────────────────────────────────────────
    expect(c.answer, `前置：本题合计 ${c.answer} 应大于未知条上限 ${c.unknownMax}`)
      .toBeGreaterThan(c.unknownMax);
    await setSlider(unknown, c.answer);
    const afterTotal = await readSlider(unknown);
    console.log(`[${c.tag}] 尝试设成合计 ${c.answer} → 实际被夹到 ${afterTotal.value}`);
    expect(afterTotal.value, "设成合计会被浏览器夹到上限").toBe(c.unknownMax);
    expect(afterTotal.value, "未知条不接受合计值").not.toBe(c.answer);

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

    const unknownBar = body.response.representation.bars.find(b => b.id === "unknown");
    expect(unknownBar, "上报表征必须包含 id=unknown 的条（原版 find 失败时静默跳过）").toBeTruthy();
    console.log(`[${c.tag}] 上报未知条 value=${unknownBar.value}（=上限 ${c.unknownMax}，非合计 ${c.answer}）`);
    expect(unknownBar.value,
      "上报的未知条值应与界面一致（半成品：停在滑条上限）")
      .toBe(c.unknownMax);

    // 「表征与答案不自洽」这条**前端观察**保留：数字答对（18/21/19），
    // 而表征停在另一人的数量上限。此处只断言前端确实把不一致的体提交出去，
    // **不对后端判分下结论**——本文件拦截了后端，`correct:true` 是构造值。
    expect(String(body.response.answer), "上报的数字答案应为填写值").toBe(String(c.answer));
    expect(String(body.response.answer), "数字答案与表征未知条值不一致（本题即半成品形态）")
      .not.toBe(String(unknownBar.value));
  });
}

// ── H4b 负例：表征缺失 → 答案框必须禁用 ─────────────────────────────────
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
// ## 该负例同时暴露一个内容层陷阱（本轮新发现，登记不修）
//
// `kind="number"` 一旦配上 `representation_required=true`，因为永远无法挂载
// 工作区，答案框会**永久禁用**、题目不可作答。现场 RDS 实测：`representation_required=true`
// 的题目共 **37 题，全部是 `kind=manipulative`**，`kind=number` 为 **0 题**，
// 所以当前无活体受害；但这是后续出题必须避开的一种死配置。
test("DEF-D2 H4b 负例：表征缺失时答案框必须禁用（kind=number 真实可达路径）", async ({ page }) => {
  const task = {
    task_instance_id: "e2e-d2-h4b-negative",
    ability_id: ABILITY,
    difficulty: 2,
    resource_version_id: "e2e-d2-h4b-negative",
    goal: "H4 负例：representation_required=true 且无工作区可挂载",
    strategy_policy: {},
    ui_schema: {
      kind: "number",
      schema_version: "1.0",
      prompt: "H4 负例：这道题要求表征，但没有任何工作区可用。",
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
  // **不能按文案 "提交答案" 定位**：见下方 UI-TEXT 观察项，disabled 时文案会变。
  const submit = page.locator(".answer-composer button");
  await expect(submit, "答案区应有提交按钮").toHaveCount(1);
  const submitDisabled = await submit.isDisabled();
  const submitText = (await submit.textContent())?.trim() ?? "";
  console.log(`[h4b] 提交按钮 disabled=${submitDisabled}，文案=${JSON.stringify(submitText)}`);
  await expect(submit, "表征缺失时提交按钮必须禁用").toBeDisabled();

  // ── 观察项 UI-TEXT（不改变本用例 verdict，属产品缺陷登记）──────
  // `AnswerComposer.tsx:34` 写的是 `{disabled ? "正在判断…" : "提交答案"}`：
  // `disabled` 这一个 prop 同时承担了两种语义——
  //   ① 正在提交/判分中（此时"正在判断…"是恰当的）
  //   ② 前置闸门未满足（表征缺失，此时"正在判断…"是**错的**，会让孩子以为系统在判分）
  // 实测确认：表征缺失时按钮文案确为"正在判断…"。这不是本用例要验的 H4 行为，
  // 但必须留证，否则"按钮禁用"这件事会被误读为体验正常。
  expect(submitText,
    "观察项 UI-TEXT：表征缺失时按钮文案为「正在判断…」——disabled 语义混用，" +
    "会把「还差表征」误告成「正在判分」。此处断言当前实现以留证，不代表认可该文案")
    .toBe("正在判断…");

  console.log(`[h4b] 拦截到的提交请求=${captured.body === null ? "无" : "有"}`);
  expect(captured.body, "禁用状态下不应产生任何提交请求").toBeNull();
});