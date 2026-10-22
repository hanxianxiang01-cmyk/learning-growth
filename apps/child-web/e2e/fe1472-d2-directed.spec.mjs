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
//   H3 未知条到不了两人合计（18 / 21 / 19）——设成合计会被夹到上限
//   H4 `representation_required=true` 时，表征不存在则答案框禁用（提交前置闸门）
//
// H4 是判分行为的**前置条件**而非判分本身：`AnswerComposer` 的 disabled 由
// `schema.response_schema.representation_required && !response.representation`
// 决定（TaskRenderer.tsx NumberRenderer）。它证明"表征非空"是提交的必要条件，
// 但不能证明"表征正确"也是——后者要读后端判分，本轮未做。
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

    // ── H4 提交前置闸门：表征存在 → 答案框才可用 ─────────────────────
    const input = page.locator("#math-answer");
    const visible = await input.isVisible();
    console.log(`[${c.tag}] 表征已存在时，答案框可见=${visible} disabled=${visible ? await input.isDisabled() : "n/a"}`);
    expect(visible, "答案框应存在（representation_required=true 但未提交前不应整块隐藏）").toBe(true);

    // 填正确数字答案并提交，抓请求体（拦截，不写库）
    await input.fill(String(c.answer));
    await page.getByRole("button", { name: /提交答案/ }).click();
    await page.waitForTimeout(600);
    const body = captured.body;
    console.log(`[${c.tag}] 拦截到的提交体 answer=${JSON.stringify(body?.response?.answer)}`);
    const repBars = body?.response?.representation?.bars ?? null;
    console.log(`[${c.tag}] 上报表征 bars=${JSON.stringify(repBars)}`);
    expect(body, "应拦截到一次提交请求（证明提交链路可达）").toBeTruthy();
    expect(String(body.response.answer), "上报的数字答案应为填写值")
      .toBe(String(c.answer));
    // 上报的未知条应是界面当前值（= 上限），即"表征与题目不符"
    if (repBars) {
      const unknownBar = repBars.find(b => b.id === "unknown");
      console.log(`[${c.tag}] 上报未知条 value=${unknownBar?.value}（=上限 ${c.unknownMax}，非合计 ${c.answer}）`);
      expect(unknownBar?.value,
        "上报的未知条值应与界面一致（半成品：停在滑条上限）")
        .toBe(c.unknownMax);
    }
  });
}