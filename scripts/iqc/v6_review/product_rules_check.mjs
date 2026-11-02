/**
 * 2026-11-01 产品规则调整的页面级判据（DOM 实测，不是看截图）。
 *
 * 覆盖四条用户明确定下的规则：
 *   R1 首页不再有「今天还可以练 N 道题」的配额条（每日 30 题硬限制已取消）
 *   R2 首页有「今天的安排」，且任务数在 2~3 之间（按证据安排，不是固定 30）
 *   R3 安排带具体理由（说明它读的是学习证据，不是随机文案）
 *   R4 真实作答数仍展示（记录保留，但不作掌握程度）
 *   R5 连续学习提醒会出现，且**不阻断**：点「我还不累，继续」能关掉并继续答题
 *   R6 换版式后首页与学习页在 1366×768 仍是一屏（本次改动没把上一轮的工作弄坏）
 *
 * 为什么不用「看页面截图」：配额条消失、安排出现、提醒出现这三件事都能用选择器
 * 断言，截图只能证明「我看了一眼」。而 R5 的「不阻断」更必须靠点击验证——
 * 一个盖满全屏、只有「去休息」一个按钮的弹窗，看起来也很「适当」。
 *
 * 用法：node scripts/iqc/v6_review/product_rules_check.mjs --base http://127.0.0.1:3108
 * 退出码：0 全过 / 1 有 FAIL / 2 服务不可达
 */
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

function arg(name, dflt) {
  const hit = process.argv.find(a => a.startsWith(`--${name}=`));
  if (hit) return hit.slice(name.length + 3);
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 && process.argv[i + 1] && !process.argv[i + 1].startsWith("--") ? process.argv[i + 1] : dflt;
}
const EXE = process.env.CHROME_BIN
  ?? `${process.env.HOME}/Library/Caches/ms-playwright/chromium-1228/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing`;
const BASE = arg("base", "http://127.0.0.1:3108").replace(/\/$/, "");
const OUT = arg("out", "output/v6_review/product_rules");
fs.mkdirSync(OUT, { recursive: true });

const rows = [];
let failed = 0;
function rec(name, ok, detail = "") {
  if (!ok) failed++;
  rows.push({ name, ok, detail });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? `  — ${detail}` : ""}`);
}

function todayKey() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

const browser = await chromium.launch({ executablePath: EXE });

// ---------- 首页：配额条没了，今日安排在 ----------
const homeCtx = await browser.newContext({ viewport: { width: 1366, height: 768 } });
const home = await homeCtx.newPage();
let reachable = true;
try {
  await home.goto(`${BASE}/child/math`, { waitUntil: "networkidle", timeout: 30000 });
} catch {
  reachable = false;
}
if (!reachable) {
  console.log("✗ 服务不可达，什么都没验");
  await browser.close();
  process.exit(2);
}
await home.waitForSelector('[data-testid="v6-home-start"]', { timeout: 30000 });

const quotaCount = await home.locator('[data-testid="v6-home-quota"]').count();
rec("R1 首页没有配额条（今天还可以练 N 道题）", quotaCount === 0, `count=${quotaCount}`);

const bodyText = await home.locator("body").innerText();
const quotaWording = ["还可以练", "道题已经完成", "明天再来吧"].filter(t => bodyText.includes(t));
rec("R1b 页面文案里不再出现配额措辞", quotaWording.length === 0, quotaWording.length ? `命中=${quotaWording.join("/")}` : "无");

const plan = home.locator('[data-testid="v6-home-plan"]');
const planCount = await plan.count();
const planText = planCount ? (await plan.innerText()).replace(/\s+/g, " ").trim() : "";
const taskMatch = /(\d+)\s*个小任务/.exec(planText);
const taskCount = taskMatch ? Number(taskMatch[1]) : -1;
rec("R2 首页有「今天的安排」", planCount === 1, planText.slice(0, 60));
// 安排的任务数必须等于后端会话目标：写 30 固然不对，写 2 而实际要做 3 也是错的。
// 只判「2~3」会放过后者，所以直接读后端常量比对。
const backendGoal = Number(
  /^SESSION_TASK_GOAL\s*=\s*(\d+)/m.exec(
    fs.readFileSync(new URL("../../../apps/learning-api/app/core/education_rules.py", import.meta.url), "utf8")
  )?.[1]
);
rec(
  "R2b 安排的任务数等于后端会话目标（不是 30，也不是随口一个数）",
  taskCount === backendGoal && Number.isInteger(backendGoal),
  `taskCount=${taskCount} 后端=${backendGoal}`
);
rec("R3 安排带具体理由", /先把它练扎实|从它开始最合适|再多看几种情况|保持手感/.test(planText), planText.slice(-40));

// 标题与安排必须指向同一项能力：同一屏两个重点等于没有重点
const planAbility = /先练「(.+?)」/.exec(planText)?.[1] ?? "";
const heroTitle = (await home.locator(".v6-home-hero h1").innerText()).replace(/\s+/g, "");
rec(
  "R3b 主标题与今日安排指向同一项能力",
  planAbility.length > 0 && heroTitle.includes(planAbility),
  `title=${heroTitle} plan=${planAbility}`
);

const answered = home.locator('[data-testid="v6-home-answered"]');
rec("R4 真实作答数仍有展示位（记录保留）", (await answered.count()) === 1, await answered.innerText().catch(() => ""));

// R4b：只验「展示位存在」等于没验渲染分支（answered_today=0 时这段文案根本不出现）。
// 种子一条今天的作答记录，首页必须把数字说出来。
{
  const seeded = await browser.newContext({ viewport: { width: 1366, height: 768 } });
  const today = new Date().toISOString().slice(0, 10);
  await seeded.addInitScript(payload => {
    window.localStorage.setItem("iqc:mock-answered", JSON.stringify(payload));
  }, { date: today, taskIds: ["seed-task-1"] });
  const sp = await seeded.newPage();
  await sp.goto(`${BASE}/child/math`, { waitUntil: "networkidle" });
  await sp.waitForSelector('[data-testid="v6-home-answered"]', { timeout: 30000 });
  const note = (await sp.locator('[data-testid="v6-home-answered"]').innerText()).replace(/\s+/g, " ");
  rec(
    "R4b 有作答记录时首页真的显示「今天已经答了 N 道题」",
    /今天已经答了\s*1\s*道题/.test(note),
    note.trim()
  );
  await seeded.close();
}

// 首页仍一屏
const homeFit = await home.evaluate(() => ({ h: document.documentElement.scrollHeight, vh: innerHeight }));
rec("R6 首页 1366×768 仍是一屏", homeFit.h <= homeFit.vh + 1, `内容 ${homeFit.h} / 视口 ${homeFit.vh}`);

// 五个挑战入口是「3 + 2」磁贴：上一行三个、下一行两个。
// 只断言「5 个按钮存在」是不够的——上一版是 5 行列表，同样有 5 个。
{
  const tiles = await home.$$eval(".v6-task-tile", els => els.map(e => {
    const r = e.getBoundingClientRect();
    return { y: Math.round(r.y), x: Math.round(r.x), w: Math.round(r.width), name: e.innerText.replace(/\s+/g, "") };
  }));
  const rows = [...new Set(tiles.map(t => t.y))].sort((a, b) => a - b);
  const firstRow = tiles.filter(t => t.y === rows[0]).length;
  const secondRow = tiles.filter(t => t.y === rows[1]).length;
  rec(
    "R9 五个挑战入口排成 3 + 2（不是五行列表）",
    tiles.length === 5 && rows.length === 2 && firstRow === 3 && secondRow === 2,
    `共 ${tiles.length} 个 / 两行 ${firstRow}+${secondRow}`
  );
  const wantNames = ["数量关系", "建模表征", "读题理解", "条件识别", "策略挑战"];
  const gotNames = tiles.map(t => t.name.replace(/(发现数量的联系|用图、表等表达|读清题意与信息|找出关键条件|尝试不同方法)$/, ""));
  rec("R9b 磁贴名称与设计一致（不带「挑战」后缀，也不改名）", JSON.stringify(gotNames) === JSON.stringify(wantNames), gotNames.join("/"));
}

// 产品不宣称年级。
// 上一版 R10 断言的是「必须写二年级、不能写 2年级」——但它只在 mock 数据（grade="2"）下成立。
// 真实库里 child.grade 存的是中文全称（游客还被写死成「一年级」），
// 拼出来是「一年级年级数学」；而题库根本没有年级字段、选题也不按年级过滤。
// 所以正确的判据不是「写对年级」，而是「不要宣称年级」——这一条与数据形态无关，
// 同时用 R10b 钉住「整行没被删掉」，避免空集假绿。
{
  const body = await home.locator("body").innerText();
  const note = await home.locator(".v6-home-record-note").innerText();
  const hit = body.match(/.{0,6}年级.{0,6}/);
  rec("R10 首页不宣称年级（页面无「X年级数学」）", !/年级数学/.test(body), hit ? hit[0] : "(无)");
  rec("R10b 学习时长提示仍在（不是把整行删掉）", /建议每次学习/.test(note), note.replace(/\s+/g, " ").slice(0, 40));
}

await home.screenshot({ path: path.join(OUT, "home-1366.png") });
await homeCtx.close();

// ---------- 成长地图：摘要与七项列表 ----------
// 上一版是「节点地图 + 右侧详情」，默认就把第一项点亮。V1.4 改成
// 「真实计数摘要 + 七行列表 + 默认不选中」，这几条都能用 DOM 断言，不必看图。
{
  const gctx = await browser.newContext({ viewport: { width: 1366, height: 768 } });
  const g = await gctx.newPage();
  await g.goto(`${BASE}/child/math`, { waitUntil: "networkidle" });
  await g.waitForTimeout(400);
  await g.goto(`${BASE}/child/math/growth`, { waitUntil: "networkidle" });
  await g.waitForSelector('[data-testid="v6-growth-abilities"]', { timeout: 30000 });
  await g.waitForTimeout(400);

  const summary = (await g.locator('[data-testid="v6-growth-summary"]').innerText()).replace(/\s+/g, " ");
  const explored = Number(/已探索\s*(\d+)\s*项能力/.exec(summary)?.[1] ?? -1);
  const rows = await g.$$eval(".v6-ability-row", els => els.map(e => ({
    label: e.querySelector(".v6-row-copy>strong")?.textContent?.trim() ?? "",
    tag: e.querySelector(".v6-explore-tag")?.textContent?.trim() ?? "",
    expanded: e.getAttribute("aria-expanded") === "true",
  })));
  const recorded = rows.filter(r => r.tag !== "尚待探索").length;
  rec("R8 成长页有「已探索 N 项能力」摘要", explored >= 0, summary.slice(0, 60));
  // 摘要与列表必须来自同一个事实：数字说 3 项、列表里有 4 行有记录，就是两个真相。
  rec("R8b 摘要数字等于列表里有记录的行数", explored === recorded, `摘要 ${explored} / 列表 ${recorded}`);
  // 七项、顺序固定、且一个不少——「七项能力」写死编号会让这条空跑，所以按名称全列。
  const wantOrder = ["数量关系", "检查验算", "读题理解", "迁移变式", "建模表征", "条件识别", "策略选择"];
  rec("R8c 七项能力齐全且顺序与能力定义一致", JSON.stringify(rows.map(r => r.label)) === JSON.stringify(wantOrder), rows.map(r => r.label).join("/"));
  rec("R8d 默认不展开任何一项（不替孩子选第一项）", rows.length > 0 && rows.every(r => !r.expanded), `展开 ${rows.filter(r => r.expanded).length} 项`);
  rec("R8e 宽屏右栏是「请先选一项」占位，不是默认展示第一项", (await g.locator('[data-testid="v6-detail-placeholder"]').count()) === 1, "");

  const body = await g.locator("body").innerText();
  const legacy = ["待了解", "尚待了解", "暂无数据", "暂无记录"].filter(t => body.includes(t));
  rec("R8f 空态只说「尚待探索」，不再四套措辞并存", legacy.length === 0, legacy.length ? `命中=${legacy.join("/")}` : "无");
  // 有记录的行只能显示「真趋势词」。这里不抄一份词表（抄了就和实现一起漂移），
  // 直接读 abilityStatus.ts 里的 label 全集来比对。
  const trendLabels = [...fs.readFileSync(
    new URL("../../../apps/child-web/src/lib/presentation/abilityStatus.ts", import.meta.url), "utf8"
  ).matchAll(/label:\s*"([^"]+)"/g)].map(m => m[1]);
  const badTag = rows.filter(r => r.tag !== "尚待探索" && !trendLabels.includes(r.tag));
  rec(
    "R8g 行内标签要么是「尚待探索」，要么是趋势源文件里的真实标签",
    trendLabels.length >= 4 && badTag.length === 0,
    badTag.length ? badTag.map(r => r.tag).join("/") : `趋势词 ${trendLabels.join("/")}`
  );

  // 点开一项：这一行展开、详情出现在右栏、其它行不受影响。
  await g.locator(".v6-ability-row").nth(2).click();
  await g.waitForTimeout(300);
  const after = await g.evaluate(() => ({
    expanded: [...document.querySelectorAll(".v6-ability-row")].map(e => e.getAttribute("aria-expanded") === "true"),
    detail: !!document.querySelector('[data-testid="v6-ability-detail"]'),
    placeholder: !!document.querySelector('[data-testid="v6-detail-placeholder"]'),
    title: document.querySelector('[data-testid="v6-ability-detail"] h2')?.textContent?.trim() ?? "",
  }));
  rec(
    "R8h 点开第三项：只这一行展开、右栏换成它的详情",
    after.expanded.filter(Boolean).length === 1 && after.expanded[2] && after.detail && !after.placeholder && after.title === wantOrder[2],
    `展开=${after.expanded.indexOf(true)} 详情=${after.title || "无"} 占位=${after.placeholder}`
  );

  const gFit = await g.evaluate(() => ({ h: document.documentElement.scrollHeight, vh: innerHeight }));
  rec("R8i 成长页 1366×768 仍是一屏（展开详情后也不许滚）", gFit.h <= gFit.vh + 1, `内容 ${gFit.h} / 视口 ${gFit.vh}`);
  await g.screenshot({ path: path.join(OUT, "growth-1366.png") });
  await gctx.close();
}

// ---------- 学习页：休息提醒出现且不阻断 ----------
const ctx = await browser.newContext({ viewport: { width: 1366, height: 768 } });
// 种一个「已经连做 5 题」的状态：等提醒出现不必真答 5 题（那要靠 5 次真实提交，
// 与提醒逻辑无关，只会让判据变慢变脆）。跨天标记用当天的 key，否则会被 normalize 清零。
await ctx.addInitScript(key => {
  window.localStorage.setItem(
    "iqc:break-nudge",
    JSON.stringify({ date: key, startedAt: Date.now(), tasksSinceNudge: 5, lastNudgeAt: 0 })
  );
}, todayKey());
const learn = await ctx.newPage();
await learn.goto(`${BASE}/child/math`, { waitUntil: "networkidle" });
await learn.waitForSelector('[data-testid="v6-home-start"]', { timeout: 30000 });
await learn.click('[data-testid="v6-home-start"]');
await learn.waitForSelector(".v6-task-content", { timeout: 45000 });
await learn.waitForSelector('[data-testid="v6-break-nudge"]', { timeout: 15000 }).catch(() => {});

const nudge = learn.locator('[data-testid="v6-break-nudge"]');
const nudgeCount = await nudge.count();
const nudgeText = nudgeCount ? (await nudge.innerText()).replace(/\s+/g, " ") : "";
rec("R5 连续学久了会出现休息提醒", nudgeCount === 1, nudgeText.slice(0, 60));
rec(
  "R5b 提醒里有「继续」出口（不是只剩「去休息」）",
  nudgeCount === 1 && (await learn.locator('[data-testid="v6-break-continue"]').count()) === 1,
  ""
);

// 不阻断：提醒出现时，答题控件仍然可用；点「继续」后提醒消失、还能接着答。
// 注意别拿「提交按钮」当判据——它本来就随作答状态禁用，拿它验会得到假失败
// （而假失败会让人去改根本不该改的地方）。这里只看「有没有可用的输入控件」。
const inputState = await learn.evaluate(() => {
  // 题型的交互控件形态不一（有的用 input，有的用选项按钮），所以统一按
  // 「可交互且未禁用」计数，而不是只数 input——只数 input 会在按钮型题上假失败。
  const inputs = Array.from(document.querySelectorAll(
    '.v6-task-content button, .v6-task-content input, .v6-task-content textarea, .v6-task-content [role="button"]'
  ));
  const enabled = inputs.filter(el => !el.disabled && el.getAttribute("aria-disabled") !== "true");
  const nudgeEl = document.querySelector('[data-testid="v6-break-nudge"]');
  const box = nudgeEl ? nudgeEl.getBoundingClientRect() : null;
  // 遮挡判据：浮条矩形与「提醒之外的可交互控件」是否相交。
  // 只量占视口比例是不够的——5% 面积的浮层照样能正好压在提交按钮上，
  // 而「必须先点掉提醒才能交作业」就是变相禁止，正是这条产品规则要防的事。
  const covered = box
    ? inputs
        .filter(el => !nudgeEl.contains(el))
        .filter(el => {
          const b = el.getBoundingClientRect();
          return b.width > 0 && b.height > 0 &&
            b.bottom > box.top && b.top < box.bottom &&
            b.right > box.left && b.left < box.right;
        })
        .map(el => (el.innerText || el.getAttribute("aria-label") || el.tagName).replace(/\s+/g, "").slice(0, 16))
    : [];
  return {
    inputs: inputs.length,
    enabled: enabled.length,
    areaRatio: box ? (box.width * box.height) / (innerWidth * innerHeight) : 1,
    covered
  };
});
rec(
  "R5c 提醒出现时答题控件仍可交互",
  inputState.enabled > 0,
  `控件 ${inputState.inputs} 个，可用 ${inputState.enabled} 个`
);
rec(
  "R5f 提醒不遮挡任何答题控件（挡住的「继续」不是真继续）",
  inputState.areaRatio < 0.15 && inputState.covered.length === 0,
  `占视口 ${(inputState.areaRatio * 100).toFixed(1)}%，遮挡 ${inputState.covered.length} 个` +
    (inputState.covered.length ? `：${inputState.covered.join("/")}` : "")
);

if (nudgeCount === 1) {
  await learn.click('[data-testid="v6-break-continue"]');
  await learn.waitForTimeout(300);
  const gone = (await learn.locator('[data-testid="v6-break-nudge"]').count()) === 0;
  rec("R5d 点「我还不累，继续」后提醒关闭", gone, gone ? "" : "仍在");
  const stillLearning = (await learn.locator(".v6-task-content").count()) === 1;
  rec("R5e 关闭提醒后人还在学习页（没有被踢走）", stillLearning, "");
}

const learnFit = await learn.evaluate(() => ({ h: document.documentElement.scrollHeight, vh: innerHeight }));
rec("R6b 学习页 1366×768 仍是一屏", learnFit.h <= learnFit.vh + 1, `内容 ${learnFit.h} / 视口 ${learnFit.vh}`);
await learn.screenshot({ path: path.join(OUT, "session-break-1366.png") });
await ctx.close();

// ---------- 手机档：提醒不能把窄屏撑出横向滚动 ----------
// 1366 放得下不等于 390 放得下。浮层用 min(760px, 100vw-32px)，
// 但「按公式算得出」不等于「浏览器里真的没溢出」——按钮换行、字号撑宽都可能超。
{
  const phone = await browser.newContext({ viewport: { width: 390, height: 844 } });
  await phone.addInitScript(key => {
    window.localStorage.setItem(
      "iqc:break-nudge",
      JSON.stringify({ date: key, startedAt: Date.now(), tasksSinceNudge: 5, lastNudgeAt: 0 })
    );
  }, todayKey());
  const p = await phone.newPage();
  await p.goto(`${BASE}/child/math`, { waitUntil: "networkidle" });
  await p.waitForSelector('[data-testid="v6-home-start"]', { timeout: 30000 });
  await p.click('[data-testid="v6-home-start"]');
  await p.waitForSelector('[data-testid="v6-break-nudge"]', { timeout: 45000 }).catch(() => {});
  const box = await p.evaluate(() => {
    const el = document.querySelector('[data-testid="v6-break-nudge"]');
    if (!el) return null;
    const r = el.getBoundingClientRect();
    const btn = el.querySelector('[data-testid="v6-break-continue"]');
    const br = btn ? btn.getBoundingClientRect() : null;
    // 排除提醒自身的按钮。注意别写 `!el.contains(el)`——节点必然包含自身，
    // 那样写会把候选集清空，遮挡检查永远 0，看起来全绿其实什么都没查。
    const ctrls = Array.from(document.querySelectorAll('button, input, textarea, [role="button"]'))
      .filter(el => !el.closest('[data-testid="v6-break-nudge"]'));
    const covered = ctrls.filter(el => {
      const b = el.getBoundingClientRect();
      return b.width > 0 && b.height > 0 &&
        b.bottom > r.top && b.top < r.bottom && b.right > r.left && b.left < r.right;
    }).map(el => (el.innerText || el.getAttribute("aria-label") || el.tagName).replace(/\s+/g, "").slice(0, 16));
    return {
      left: Math.round(r.left), right: Math.round(r.right), vw: innerWidth,
      docW: document.documentElement.scrollWidth,
      btnH: br ? Math.round(br.height) : 0,
      covered
    };
  });
  rec(
    "R7 手机 390 宽下休息提醒完整在视口内（左右不越界）",
    !!box && box.left >= 0 && box.right <= box.vw && box.docW <= box.vw + 1,
    box ? `left=${box.left} right=${box.right} vw=${box.vw} docW=${box.docW}` : "提醒没出现"
  );
  rec(
    "R7b 手机档按钮高度 ≥ 44px（手指点得到）",
    !!box && box.btnH >= 44,
    box ? `按钮高 ${box.btnH}px` : "提醒没出现"
  );
  rec(
    "R7c 手机档提醒不遮挡任何答题控件（含提交按钮）",
    !!box && box.covered.length === 0,
    box ? `遮挡 ${box.covered.length} 个${box.covered.length ? "：" + box.covered.join("/") : ""}` : "提醒没出现"
  );
  await p.screenshot({ path: path.join(OUT, "session-break-390.png") });
  await phone.close();
}

await browser.close();
fs.writeFileSync(path.join(OUT, "report.json"), JSON.stringify(rows, null, 1), "utf8");
console.log(`\n${failed === 0 ? "✔ 产品规则判据全过" : `✗ ${failed} 项未通过`}  (${rows.length} 项，报告 ${path.join(OUT, "report.json")})`);
process.exit(failed === 0 ? 0 : 1);
