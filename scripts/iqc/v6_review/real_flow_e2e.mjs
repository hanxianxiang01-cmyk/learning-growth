/**
 * FE-1445 复审：V6 前端 + 真实题库后端的真实数据端到端。
 *
 * 与 `e2e/*.spec.mjs` 的区别：那些 spec 用 page.route 把 `/tasks/next` 换成钉住的题，
 * 只验证渲染；本脚本**不拦截任何请求**，走真实选题、真实判分，用来回答
 * 「V6 迁移后还能不能真的学」。
 *
 * 判据（每条都参与退出码，屏幕 FAIL 而 rc=0 是不允许的）：
 *   C01 首页只发 1 次 bootstrap（StrictMode 双挂载下也不能多）
 *   C02 cookie 是 HttpOnly 且值与 child_id 不同（token 不得是明文 id）
 *   C03 全流程不出现默认身份 …0001 / QA 池 …0099（数据串用）
 *   C04 profile/abilities 用的是刚刚签发的那个游客 id
 *   C05 创建 session 201，且 body 的 child_id = 游客 id
 *   C06 /tasks/next 200，task 来自已发布题库（真值从库里取，见 db_answer.py）
 *   C07 作答提交 200 且 correct=true（判分与题库真值一致）
 *   C08 只提交了 1 次 /attempts（无重复提交）
 *   C09 提交后 /guest/me 的当日配额已计入（解包/计数正确）
 *   C10 反馈区进入 correct 态（前端正确消费判分结果）
 *   C11 全流程无 4xx/5xx（401/403/404/429 都不允许出现在正常路径上）
 *   C17 首页**显示**每日剩余题数，且数字 = 后端 quota.remaining（DOM × API 双源互核）
 *       —— 只看 API 有 quota 查不出「拿到了却没渲染」，此条专治该缺口
 *
 * 用法：
 *   export DATABASE_URL="postgresql://..."     # 给 db_answer.py 取真值用
 *   node scripts/iqc/v6_review/real_flow_e2e.mjs --base http://127.0.0.1:3102 \
 *        --out output/v6_review/real_flow_run.json
 */
import { chromium } from "playwright-core";
import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

const EXEC = process.env.CHROME_HEADLESS_SHELL
  ?? "/Users/hanxianxiang/Library/Caches/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell";
const PY = process.env.REVIEW_PYTHON
  ?? "/Users/hanxianxiang/.workbuddy/binaries/python/envs/learning-engine/bin/python";

function arg(name, dflt) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : dflt;
}
const BASE = arg("base", "http://127.0.0.1:3102");
const OUT = resolve(arg("out", "output/v6_review/real_flow_run.json"));
const API = arg("api", "http://127.0.0.1:8000");
const CARD = arg("card", "quantity");
const EXPECT_SKIN = process.env.EXPECT_SKIN ?? "exploration-lab";

const DEFAULT_CHILD = "00000000-0000-0000-0000-000000000001";
const QA_CHILD = "00000000-0000-0000-0000-000000000099";

const checks = [];
function check(id, label, cond, detail = "") {
  checks.push({ id, label, ok: !!cond, detail: String(detail) });
  console.log(`[${cond ? "PASS" : "FAIL"}] ${id} ${label}${detail ? " — " + detail : ""}`);
}

const api = [];       // { method, path, status, body }
const problems = [];  // 任何异常请求
const sent = [];      // 请求体（csrf/子身份核对用）

const browser = await chromium.launch({ executablePath: EXEC });
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await ctx.newPage();

page.on("response", async r => {
  const url = r.url();
  if (!url.startsWith(API)) return;
  let body = null;
  try { body = await r.json(); } catch { /* 非 JSON 响应不解析 */ }
  const rec = { method: r.request().method(), path: url.slice(API.length), status: r.status(), body };
  api.push(rec);
  if (r.status() >= 400) problems.push(rec);
});
page.on("request", r => {
  const url = r.url();
  if (!url.startsWith(API) || r.method() !== "POST") return;
  let payload = null;
  try { payload = JSON.parse(r.postData() ?? "null"); } catch { payload = r.postData(); }
  sent.push({ path: url.slice(API.length), payload });
});
page.on("requestfailed", r => {
  if (r.url().startsWith(API)) problems.push({ method: r.method(), path: r.url().slice(API.length), status: "failed" });
});

const count = re => api.filter(x => x.method === "POST" && re.test(x.path)).length;

let run = { base: BASE, startedAt: new Date().toISOString() };
try {
  // ---------- 1. 首页：身份初始化 ----------
  await page.goto(`${BASE}/child/math`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2500);

  // 皮肤核对：必须**导航之后**再读属性，否则 DOM 还是空的（第一版就栽在这里）
  const skinAttr = await page.locator("[data-child-math-skin]").first().getAttribute("data-child-math-skin").catch(() => null);
  run.skin = skinAttr;
  check("C16", `皮肤为 ${EXPECT_SKIN}`, skinAttr === EXPECT_SKIN, `页面实际=${skinAttr}`);

  const bootstraps = api.filter(x => x.path === "/v1/guest/bootstrap");
  check("C01", "首页只发 1 次 bootstrap", bootstraps.length === 1, `实际 ${bootstraps.length} 次`);
  const boot = bootstraps[0];
  check("C01b", "bootstrap 返回 200 且 is_new=true", boot?.status === 200 && boot?.body?.is_new === true,
        `status=${boot?.status} is_new=${boot?.body?.is_new}`);
  const guestId = boot?.body?.child_id;
  run.guestId = guestId;
  run.bootstrapQuota = boot?.body?.quota;

  // C17：配额必须**在页面上可见**，且数字与后端返回的真实值一致。
  // 这一条专治「拿到了 g.quota 却没渲染」——只看 API body 有 quota 查不出这个缺口。
  // 两个事实源互核：DOM 文本 vs bootstrap body 的 quota.remaining（形态 42）。
  const quotaText = await page.locator('[data-testid="v6-home-quota"]').first().textContent().catch(() => null);
  const quotaRemaining = boot?.body?.quota?.remaining;
  check("C17", "首页显示每日剩余题数且与后端 quota.remaining 一致",
        !!quotaText && Number.isFinite(quotaRemaining) && quotaText.includes(String(quotaRemaining)),
        `页面="${(quotaText ?? "").trim()}" 后端 remaining=${quotaRemaining}`);

  const cookies = await ctx.cookies();
  const ck = cookies.find(c => c.name === "guest_session");
  check("C02", "guest_session 为 HttpOnly 且 token≠child_id",
        !!ck && ck.httpOnly === true && !!guestId && ck.value !== guestId,
        `httpOnly=${ck?.httpOnly} token==id? ${ck?.value === guestId}`);

  // ---------- 2. 数据串用：默认身份 / QA 池 ----------
  const bodies = JSON.stringify(api);
  const pageHtml = await page.content();
  const leaks = [DEFAULT_CHILD, QA_CHILD].filter(id => bodies.includes(id) || pageHtml.includes(id));
  check("C03", "未出现默认身份 …0001 / QA 池 …0099", leaks.length === 0, leaks.join(",") || "0 处");

  // ---------- 3. profile / abilities 归属于本游客 ----------
  const prof = api.find(x => x.path.startsWith("/v1/children/") && x.path.endsWith("/profile"));
  const abil = api.find(x => x.path.startsWith("/v1/children/") && x.path.endsWith("/abilities"));
  const pathId = prof?.path.split("/")[3];
  check("C04", "profile/abilities 使用刚签发的游客 id",
        prof?.status === 200 && abil?.status === 200 && pathId === guestId,
        `path=${pathId} guest=${guestId}`);

  // ---------- 4. 开始学习 ----------
  await page.getByTestId(
    CARD === "start" ? "v6-home-start" : `v6-home-${CARD}`
  ).click();

  // 注意取值时机：必须先等响应到齐再 find，否则拿到的是 undefined
  // （第一版就栽在这里——屏幕 FAIL 但流程其实正常，属判据自身的错）。
  await page.waitForTimeout(1500);
  const sess = api.find(x => x.path === "/v1/learning/sessions");
  const sessStatus = sess?.status;
  run.sessionId = sess?.body?.session_id;
  const sessSent = sent.find(x => x.path === "/v1/learning/sessions");
  run.sessionRequestChildId = sessSent?.payload?.child_id;
  check("C05", "创建 session 返回 201 且 body 的 child_id = 游客 id",
        sessStatus === 201 && sessSent?.payload?.child_id === guestId,
        `status=${sessStatus} body.child_id=${sessSent?.payload?.child_id}`);
  // ---------- 5. 取题 ----------
  await page.waitForFunction(() => document.querySelector('[data-testid="v6-learning-screen"]') !== null, null, { timeout: 60000 });
  await page.waitForTimeout(1500);
  const nextTask = api.find(x => x.path === "/v1/learning/tasks/next");
  const task = nextTask?.body;
  const ws = task?.ui_schema?.workspaces?.[0];
  const rvid = task?.resource_version_id;
  run.taskInstanceId = task?.task_instance_id;
  run.resourceVersionId = rvid;
  run.renderer = ws?.renderer
    ?? task?.ui_schema?.renderer_id
    ?? (task?.ui_schema?.visual?.type === "objects" ? "object-counter"
      : task?.ui_schema?.visual?.type === "bar-model" ? "bar-model"
      : task?.ui_schema?.visual?.type === "number-line" ? "number-line"
      : task?.ui_schema?.kind);
  run.schemaVersion = task?.ui_schema?.schema_version;
  check("C06", "取到任务且来自真实题库", nextTask?.status === 200 && !!task?.task_instance_id && !!rvid,
        `status=${nextTask?.status} renderer=${run.renderer} rvid=${rvid}`);

  // 真值：从库里读（独立事实源，不用被测系统自己算）
  const truth = JSON.parse(execFileSync(PY, [resolve("scripts/iqc/v6_review/db_answer.py"), rvid], {
    env: { ...process.env }, encoding: "utf8"
  }).trim());
  run.truth = truth;
  check("C06b", "题目在库中为 published 且有标准答案", truth.review_status === "published" && truth.answer !== undefined,
        `status=${truth.review_status} answer=${JSON.stringify(truth.answer)}`);

  // ---------- 6. 作答 ----------
  // 表示法必填的题要先产生表示；object-counter 用「一一对齐」一次性生成
  const align = page.getByRole("button", { name: "一一对齐" });
  if (await align.count()) { await align.first().click(); await page.waitForTimeout(600); }

  const input = page.locator("input[placeholder='输入数字'], input[type='text'], input[type='number']").first();
  await input.fill(String(truth.answer));
  await page.waitForTimeout(300);

  const submitBtn = page.locator("button").filter({ hasText: /提交答案|提交/ }).first();
  const submitEnabled = await submitBtn.isEnabled();
  check("C07a", "填答后提交按钮可用", submitEnabled, `enabled=${submitEnabled}`);

  const attemptsBefore = count(/^\/v1\/learning\/attempts$/);
  await submitBtn.click();
  await page.waitForTimeout(2500);
  const attempts = api.filter(x => x.method === "POST" && x.path === "/v1/learning/attempts");
  const attempt = attempts[attempts.length - 1];
  run.attempt = attempt?.body ? { correct: attempt.body.correct, attemptNo: attempt.body.attempt_no } : null;

  check("C07", "提交返回 200 且判分与真值一致（correct=true）",
        attempt?.status === 200 && attempt?.body?.correct === true,
        `status=${attempt?.status} correct=${attempt?.body?.correct}`);
  check("C08", "只提交了 1 次 /attempts", attempts.length - attemptsBefore === 1,
        `本次新增 ${attempts.length - attemptsBefore} 次`);

  // ---------- 7. 配额计入 ----------
  // 必须**在提交之后重新问一次**：/guest/me 只在页面挂载时被调用过，
  // 直接从已有响应里找只会读到提交前的快照（第一版就栽在这里）。
  const quotaBefore = boot?.body?.quota;
  const me = await page.evaluate(async url => {
    const r = await fetch(url, { credentials: "include" });
    return { status: r.status, body: await r.json() };
  }, `${API}/v1/guest/me`);
  const q = me?.body?.quota;
  run.quotaBefore = quotaBefore;
  run.quotaAfter = q;
  check("C09", "提交后当日配额已计入（used 由 0 变 1）",
        q?.used === 1 && quotaBefore?.used === 0,
        `before.used=${quotaBefore?.used} after.used=${q?.used} limit=${q?.limit} remaining=${q?.remaining}`);

  // ---------- 8. 前端反馈态 ----------
  const fb = page.getByTestId("v6-learning-feedback");
  const fbState = await fb.count() ? await fb.getAttribute("data-feedback-state") : null;
  check("C10", "反馈区进入 correct 态", fbState === "correct", `data-feedback-state=${fbState}`);

  // 截图留证（视觉复核会用同目录产物）
  mkdirSync(dirname(OUT), { recursive: true });
  await page.screenshot({ path: OUT.replace(/\.json$/, "-session.png"), fullPage: true });

  // ---------- 9. 小结页（真实 session 数据） ----------
  await page.goto(`${BASE}/child/math/result/${run.sessionId}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2500);
  const resultCall = api.filter(x => x.path === `/v1/learning/sessions/${run.sessionId}/result`).pop();
  const resultText = (await page.locator("main").first().innerText()).replace(/\s+/g, " ").slice(0, 400);
  run.resultStatus = resultCall?.status;
  run.resultText = resultText;
  check("C12", "小结页拿到 session result（200）", resultCall?.status === 200, `status=${resultCall?.status}`);
  const badResult = /没加载成功|暂时没|出错了|加载失败/.test(resultText);
  check("C13", "小结页无错误态", !badResult && resultText.length > 20, badResult ? "命中错误文案" : `${resultText.length} 字`);
  await page.screenshot({ path: OUT.replace(/\.json$/, "-result.png"), fullPage: true });

  // ---------- 10. 成长页（真实成长状态） ----------
  // 注意：成长页的数据源是 GET /v1/children/{id}/abilities（能力状态），
  // 不是 /v1/growth/monthly（月度报告是另一条链路）。
  await page.goto(`${BASE}/child/math/growth`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2500);
  const abilityCalls = api.filter(x => x.path === `/v1/children/${run.guestId}/abilities`);
  const growthText = (await page.locator("main").first().innerText()).replace(/\s+/g, " ").slice(0, 600);
  run.growthCalls = abilityCalls.map(x => x.status);
  run.growthText = growthText;
  // 与库对账：本次作答应推动「数量关系 app_rel」到 L1、证据 1 条
  const expectsL1 = /\bL1\b/.test(growthText) && /1\s*条证据/.test(growthText);
  check("C14", "成长页数据 200 且与库一致（数量关系 L1 / 1 条证据）",
        abilityCalls.some(x => x.status === 200) && expectsL1,
        `status=${abilityCalls.map(x => x.status).join(",")} L1&1条证据=${expectsL1}`);
  const badGrowth = /没加载成功|暂时没|出错了|加载失败/.test(growthText);
  check("C15", "成长页无错误态", !badGrowth && growthText.length > 20, badGrowth ? "命中错误文案" : `${growthText.length} 字`);
  await page.screenshot({ path: OUT.replace(/\.json$/, "-growth.png"), fullPage: true });

  // ---------- 最后：全流程响应码 ----------
  check("C11", "全流程 API 无 4xx/5xx", problems.length === 0,
        problems.map(p => `${p.method} ${p.path} ${p.status}`).join("; ") || "0 个异常响应");

} catch (err) {
  check("C00", "脚本执行未抛异常", false, err instanceof Error ? err.message : String(err));
  try { await page.screenshot({ path: OUT.replace(/\.json$/, "-error.png"), fullPage: true }); } catch { /* ignore */ }
} finally {
  await browser.close();
}

run.finishedAt = new Date().toISOString();
run.apiCalls = api.map(x => `${x.method} ${x.path} ${x.status}`);
run.checks = checks;
const failed = checks.filter(c => !c.ok);
run.result = failed.length === 0 ? "PASS" : "FAIL";

mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, JSON.stringify(run, null, 2));
console.log(`\n${checks.filter(c => c.ok).length}/${checks.length} PASS -> ${run.result}  (产物: ${OUT})`);
process.exit(failed.length === 0 ? 0 : 1);
