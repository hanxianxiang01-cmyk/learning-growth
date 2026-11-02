/**
 * 全站页面「装得下吗」审计（横向越界 / 被裁 / 页面可横向拖动 / 触控目标）。
 *
 * 为什么单独写一个：`mobile_overflow_check.mjs` 只盯学习页的 5 个入口，
 * 首页与成长地图没被任何判据覆盖过 —— 成长地图在手机上横向撑破就是这么漏掉的。
 *
 * 判据（任何一条失败都计入退出码，屏幕 FAIL 而 rc=0 是不允许的）：
 *   P0 页面真的渲染出来了：目标地标存在、且没落在错误态上
 *      —— 没有这条，报错页只有一张错误卡，P1~P4 全 PASS，等于判据在空跑。
 *      第一版就是这么假绿的：直接打开成长页没 cookie → 401 → 错误卡 → 「装得下」。
 *   P1 页面不可横向拖动：documentElement.scrollWidth <= innerWidth，且 scrollTo 后 scrollX 仍为 0
 *   P2 无「露在外面」的越界元素：右边界 > 视口 + 0.5，且祖先里没有能横滑的容器
 *   P3 无「被裁掉」的越界元素：右边界 > 视口，但祖先用 overflow-x:hidden/clip 把它藏了
 *      —— 藏起来等于孩子永远够不到，与露在外面同等严重（形态 56：全页 clip 会让 P2 永远 PASS）
 *   P4 无左侧越界：元素左边界 < -0.5（居中内容被推到视口外同样够不到）
 * 附：横向可滑容器、nowrap 文字截断、<44px 触控目标只报「观察项」，不参与退出码。
 *
 * 三种模式：
 *   （默认）视口矩阵：10 个视口 × 页面，每页先走首页签发身份，再进内页
 *   --flow          真实路径：首页 5 张挑战卡逐个点进去量学习页，再量小结页（含结果版式）
 *   --sweep         宽度扫描：一次加载后 320→1600 每 10px 量一遍，专抓断点缝隙
 *   --rich          用网络层伪造 abilities（L3/12 条证据）覆盖「有数据」的版式，不写库
 *
 * 用法：
 *   node scripts/iqc/v6_review/page_fit_audit.mjs --base http://127.0.0.1:3108 [--shot] [--pages=/child/math,/child/math/growth]
 *   node scripts/iqc/v6_review/page_fit_audit.mjs --base http://127.0.0.1:3108 --flow --sweep
 *   node scripts/iqc/v6_review/page_fit_audit.mjs --base http://child.beizengkeji.cn --shot --out output/v6_review/page_fit
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
const BASE = (arg("base", "http://127.0.0.1:3108")).replace(/\/$/, "");
const OUT = arg("out", "output/v6_review/page_fit");
const SHOT = process.argv.includes("--shot");
const FLOW = process.argv.includes("--flow");
const SWEEP = process.argv.includes("--sweep");
fs.mkdirSync(OUT, { recursive: true });

const VIEWPORTS = [
  { name: "320x568 窄屏", width: 320, height: 568 },
  { name: "360x760 老安卓", width: 360, height: 760 },
  { name: "375x667 SE", width: 375, height: 667 },
  { name: "390x844 iPhone", width: 390, height: 844 },
  { name: "414x896 大手机", width: 414, height: 896 },
  { name: "768x1024 pad 竖", width: 768, height: 1024 },
  { name: "1024x768 pad 横", width: 1024, height: 768 },
  { name: "1366x768 笔记本", width: 1366, height: 768 },
  { name: "1440x900", width: 1440, height: 900 },
  { name: "1920x1080", width: 1920, height: 1080 },
];
const SWEEP_WIDTHS = Array.from({ length: Math.floor((1600 - 320) / 10) + 1 }, (_, i) => 320 + i * 10);

// 一次跑满 10 个视口 × 全部页面在这台机器上会被杀掉（内存），分批用 --vps=1440x900,1366x768 跑。
// --vps 里的 WxH 不必是预设：任意尺寸都接受（反证时要故意造一个更矮的视口）。
// 关键：写错或写空的 --vps 一旦筛出 0 个视口，本脚本会跑 0 条记录然后打印 PASS ——
// 那是最典型的假绿，所以这里直接按用法错误退出（rc=2），绝不让空集过关。
const VP_FILTER = arg("vps", "");
const VP_LIST = VP_FILTER
  ? VP_FILTER.split(",").map(s => s.trim()).filter(Boolean).map(tok => {
      const hit = VIEWPORTS.find(v => `${v.width}x${v.height}` === tok);
      if (hit) return hit;
      const m = /^(\d{2,4})x(\d{2,4})$/.exec(tok);
      return m ? { name: `${tok} 临时`, width: Number(m[1]), height: Number(m[2]) } : null;
    }).filter(Boolean)
  : VIEWPORTS;
if (VP_LIST.length === 0) {
  console.error(`✗ --vps="${VP_FILTER}" 没有解析出任何视口，什么都没跑。用法：--vps=1366x768,1440x900`);
  process.exit(2);
}

const MEASURE = () => {
  const vw = window.innerWidth;
  const desc = (el) => {
    const cls = (typeof el.className === "string" ? el.className : "").split(/\s+/).filter(Boolean).slice(0, 3).join(".");
    const tid = el.dataset?.testid ? `[${el.dataset.testid}]` : "";
    return `${el.tagName.toLowerCase()}${tid}${cls ? "." + cls : ""}`;
  };
  const inView = (r) => r.left >= -0.5 && r.right <= vw + 0.5;
  // 只有「真能横滑」的容器才算合理收留：overflow-x:auto|scroll 且内容比容器宽。
  const hScroller = (el) => {
    let cur = el.parentElement;
    while (cur && cur !== document.documentElement) {
      const cs = getComputedStyle(cur);
      if (/auto|scroll/.test(cs.overflowX) && cur.scrollWidth > cur.clientWidth + 1 && inView(cur.getBoundingClientRect())) return desc(cur);
      cur = cur.parentElement;
    }
    return null;
  };
  // overflow-x:hidden|clip 的祖先只是把内容藏了 —— 单独记，不算「没问题」。
  const clipper = (el) => {
    let cur = el.parentElement;
    while (cur && cur !== document.documentElement) {
      const cs = getComputedStyle(cur);
      if (/hidden|clip/.test(cs.overflowX)) return desc(cur);
      cur = cur.parentElement;
    }
    return null;
  };

  const over = [];
  const scrollables = [];
  for (const el of document.querySelectorAll("body *")) {
    const cs = getComputedStyle(el);
    if (cs.position === "fixed" || cs.visibility === "hidden" || cs.display === "none") continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    if (r.right > vw + 0.5 || r.left < -0.5) {
      const sc = hScroller(el);
      over.push({
        el, node: desc(el), right: Math.round(r.right), left: Math.round(r.left), w: Math.round(r.width),
        kind: sc ? "scrollable" : (clipper(el) ? "clipped" : "exposed"),
        by: sc ?? clipper(el) ?? "", text: (el.textContent || "").trim().slice(0, 24),
      });
    }
    if (cs.overflowX !== "visible" && el.scrollWidth > el.clientWidth + 1 && el.clientWidth > 0) {
      scrollables.push({ node: desc(el), scrollW: el.scrollWidth, clientW: el.clientWidth });
    }
  }
  // 只留最外层：祖先也越界时，子树里的条目是同一个块的碎片，报出来只是噪音。
  const set = new Set(over.map(o => o.el));
  const keep = over.filter((o) => {
    let cur = o.el.parentElement;
    while (cur) { if (set.has(cur)) return false; cur = cur.parentElement; }
    return true;
  });
  const strip = (o) => ({ node: o.node, right: o.right, left: o.left, w: o.w, kind: o.kind, by: o.by, text: o.text });

  const htmlCs = getComputedStyle(document.documentElement);
  const bodyCs = getComputedStyle(document.body);
  // 真的能不能拖动：滚一下看 scrollX 有没有变（clip 会挡住，但 clip 本身就是 P3 的缺陷）
  const before = window.scrollX;
  window.scrollTo(9999, window.scrollY);
  const dragged = window.scrollX;
  window.scrollTo(before, window.scrollY);

  const nowrap = [];
  for (const el of document.querySelectorAll("p,span,strong,small,h1,h2,h3,a,button,li")) {
    const cs = getComputedStyle(el);
    if (cs.whiteSpace === "nowrap" && cs.overflow === "visible" && el.scrollWidth > el.clientWidth + 1) {
      nowrap.push({ node: desc(el), scrollW: el.scrollWidth, clientW: el.clientWidth, text: (el.textContent || "").trim().slice(0, 18) });
    }
  }
  const small = [];
  for (const el of document.querySelectorAll("button,a,[role=button]")) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    if (r.width < 44 || r.height < 44) small.push({ node: desc(el), w: Math.round(r.width), h: Math.round(r.height) });
  }
  return {
    vw,
    docScrollW: document.documentElement.scrollWidth,
    docScrollH: document.documentElement.scrollHeight,
    vh: window.innerHeight,
    bodyScrollW: document.body.scrollWidth,
    htmlOverflowX: htmlCs.overflowX,
    bodyOverflowX: bodyCs.overflowX,
    draggedX: dragged,
    over: keep.filter(o => o.kind !== "scrollable").map(strip),
    scrollableOver: keep.filter(o => o.kind === "scrollable").map(strip).slice(0, 6),
    scrollables: scrollables.slice(0, 6),
    nowrap: nowrap.slice(0, 6),
    small: small.slice(0, 8),
    markers: {
      task: !!document.querySelector(".v6-task-content"),
      growth: !!document.querySelector(".v6-ability-map"),
      detail: !!document.querySelector(".v6-ability-detail"),
      result: !!document.querySelector(".v6-result-stats"),
    },
    errorText: (() => {
      const hit = [...document.querySelectorAll('[role="alert"], .v6-page-state, .surface-card')]
        .map(e => (e.textContent || "").replace(/\s+/g, " ").trim())
        .find(t => /没加载成功|加载失败|出错了|暂时没有|加载不成功/.test(t));
      return hit ? hit.slice(0, 60) : "";
    })(),
  };
};

/** 每个页面「渲染成功」的地标：没有它，量到的可能只是错误卡。 */
const EXPECT = {
  "/child/math": ".v6-task-grid",
  "/child/math/growth": ".v6-ability-map",
  "/session": '[data-testid="v6-learning-screen"] .v6-task-content',
  "/result": ".v6-result-stats",
};

/**
 * 首页 6 个入口的 testid。第一版按 `[data-testid^="v6-task-entry"]` 去找 —— 那个前缀
 * 在这版首页根本不存在，选择器实际只匹到 `v6-home-start` 一个按钮，
 * 于是「5 张卡逐个进去量」变成了「同一个入口点 5 次」，5 个 renderer 一条都没覆盖到。
 * 判据要证明覆盖，就得先把入口名字钉死，再把每次进到的 renderer 记进报告。
 */
const CARD_SEL = [
  '[data-testid="v6-home-start"]',
  '[data-testid="v6-home-quantity"]',
  '[data-testid="v6-home-modeling"]',
  '[data-testid="v6-home-reading"]',
  '[data-testid="v6-home-conditions"]',
  '[data-testid="v6-home-strategy"]',
].join(", ");

const PAGES = (arg("pages", "/child/math,/child/math/growth")).split(",").map(s => s.trim()).filter(Boolean);
// 空数据页面最窄，但真实用户是**有数据**的：等级 L3、12 条证据会把文案撑长。
// --rich 只在网络层替换 abilities 响应，不改页面、不改库，用来覆盖「有数据」这一版式。
const RICH = process.argv.includes("--rich");
const RICH_BODY = JSON.stringify(
  ["app_rel", "app_check", "app_rd", "app_transfer", "app_model", "app_cond", "app_strat"]
    .map(id => ({ ability_id: id, level: 3, confidence: 0.72, evidence_count: 12, trend: "stable", fit_band: { min: 2, max: 4 } }))
);

const browser = await chromium.launch({ executablePath: EXE });
const rows = [];
let failGroups = 0;

const newContext = (vp) => browser.newContext({
  viewport: { width: vp.width, height: vp.height },
  isMobile: vp.width <= 480, hasTouch: vp.width <= 480, deviceScaleFactor: 2,
});

async function newPage(ctx) {
  const page = await ctx.newPage();
  if (RICH) {
    await page.route("**/v1/children/*/abilities", r => r.fulfill({
      status: 200, contentType: "application/json",
      headers: { "access-control-allow-origin": "*" }, body: RICH_BODY,
    }));
  }
  return page;
}

/** 游客身份在首页签发：先走首页再进内页，否则内页 401（这本身是产品缺陷，见报告）。 */
async function gotoWarm(page, url) {
  await page.goto(`${BASE}/child/math`, { waitUntil: "networkidle" });
  await page.waitForTimeout(600);
  if (url !== "/child/math") {
    await page.goto(`${BASE}${url}`, { waitUntil: "networkidle" });
    await page.waitForTimeout(800);
  }
}

function judge(page, m, expectKey, label, vp) {
  const vpName = vp.name;
  const problems = [];
  const expectSel = EXPECT[expectKey];
  if (expectSel) {
    const rendered = page.evaluate(s => !!document.querySelector(s), expectSel);
    return rendered.then(ok => {
      if (!ok) problems.push(`P0 未渲染出 ${expectSel}（量到的可能只是错误卡/骨架）`);
      return finish(problems);
    });
  }
  return Promise.resolve(finish(problems));

  function finish(list) {
    if (m.errorText) list.push(`P0 页面处于错误态:「${m.errorText}」`);
    if (m.docScrollW > m.vw + 1) list.push(`P1 页面可横向拖动 scrollWidth ${m.docScrollW} > ${m.vw}（html overflow-x=${m.htmlOverflowX}）`);
    if (m.draggedX > 0) list.push(`P1b 右滑真的移动了 ${m.draggedX}px`);
    const exposed = m.over.filter(o => o.kind === "exposed");
    const clipped = m.over.filter(o => o.kind === "clipped");
    if (exposed.length) list.push(`P2 ${exposed.length} 个越界元素露在视口外`);
    if (clipped.length) list.push(`P3 ${clipped.length} 个越界元素被裁掉（孩子够不到）`);
    if (m.over.some(o => o.left < -0.5)) list.push("P4 有元素左侧越界");
    // P6 一屏：pad/PC 上页面不得需要上下滚动。手机（<768）不参与——单列内容本身就长，
    // 那是另一种版式决定，不该在这里被静默判成 PASS 或 FAIL。
    if (vp && vp.width >= 768 && m.docScrollH > m.vh + 1) {
      list.push(`P6 要上下滚 ${m.docScrollH - m.vh}px（内容 ${m.docScrollH} / 视口 ${m.vh}）`);
    }
    // 手机档（<768）允许纵向滚动是产品决策（2026-10-31 用户确认），但超出量必须打出来，
    // 否则报告只剩一个 "✔ 装得下"，读的人会以为手机也一屏——那是判据在替决策撒谎。
    const phoneVOver = (vp && vp.width < 768) ? Math.max(0, m.docScrollH - m.vh) : 0;
    const bad = list.length > 0;
    if (bad) failGroups++;
    rows.push({ viewport: vpName, page: label, problems: list, phoneVOver, ...m });
    console.log(`\n=== ${vpName} · ${label}`);
    console.log(`  文档 ${m.docScrollW} / 视口 ${m.vw} / html overflow-x=${m.htmlOverflowX}  ${bad ? "✗ " + list.join(" | ") : "✔ 装得下"}`);
    if (phoneVOver > 0) {
      console.log(`  ⓘ 手机档按决策允许纵向滚动：超出 ${phoneVOver}px（内容 ${m.docScrollH} / 视口 ${m.vh}），不计入失败`);
    }
    for (const o of [...exposed, ...clipped].slice(0, 8)) {
      console.log(`  ✗ [${o.kind}] ${o.node} 右${o.right}(超${o.right - m.vw}) 宽${o.w} ${o.by ? "被" + o.by : ""} 「${o.text}」`);
    }
    if (m.scrollableOver.length) {
      console.log(`  ⓘ 需横滑的内容（收在能滑的容器里）:`);
      for (const s of m.scrollableOver) console.log(`     ${s.node} 右${s.right} ← ${s.by}`);
    }
    if (m.nowrap.length) {
      console.log(`  ⓘ nowrap 文字截断:`);
      for (const t of m.nowrap) console.log(`     ${t.node} ${t.scrollW}>${t.clientW} 「${t.text}」`);
    }
    return bad;
  }
}

async function shot(page, name) {
  if (!SHOT) return;
  await page.screenshot({ path: path.join(OUT, `${name}`.replace(/[^\w\u4e00-\u9fa5.-]/g, "") + ".png"), fullPage: true });
}

async function runStatic(ctx, vp, url, label, interact) {
  const page = await newPage(ctx);
  const errs = [];
  page.on("pageerror", e => errs.push(String(e).slice(0, 120)));
  await gotoWarm(page, url);
  if (interact) await interact(page);
  const m = await page.evaluate(MEASURE);
  await judge(page, m, url, label, vp);
  if (errs.length) console.log(`  ⚠ 页面错误: ${errs.join(" | ")}`);
  await shot(page, `${vp.width}x${vp.height}-${label}`);
  await page.close();
}

/** 学习页 + 小结页：从首页真实点进去，量完学习页再量这一节的总结页。 */
async function runFlow(ctx, vp, cardIndex) {
  const page = await newPage(ctx);
  const errs = [];
  page.on("pageerror", e => errs.push(String(e).slice(0, 120)));
  await page.goto(`${BASE}/child/math`, { waitUntil: "networkidle" });
  await page.waitForTimeout(900);
  const entries = await page.$$(CARD_SEL);
  if (!entries.length) { console.log(`!! ${vp.name} 首页没有可点入口`); await page.close(); return; }
  // 入口少一个就意味着有一整个题型没被量到：这是覆盖缺口，不能当「点了就行」
  if (entries.length < 6) console.log(`  ⚠ 首页只找到 ${entries.length} 个入口（期望 6），卡片覆盖不全`);
  const target = entries[Math.min(cardIndex, entries.length - 1)];
  const label = ((await target.evaluate(e => (e.textContent || "").trim().slice(0, 12))) || `entry${cardIndex}`);
  await target.click();
  await page.waitForFunction(() => document.querySelector('.v6-task-content') !== null, null, { timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(1800);
  const m = await page.evaluate(MEASURE);
  await judge(page, m, "/session", `session-${cardIndex + 1}-${label}`, vp);
  await shot(page, `${vp.width}x${vp.height}-session-${cardIndex + 1}`);
  const sid = (page.url().match(/session\/([^/?#]+)/) ?? [])[1];
  if (sid) {
    await page.goto(`${BASE}/child/math/result/${sid}`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1500);
    const rm = await page.evaluate(MEASURE);
    await judge(page, rm, "/result", `result-${cardIndex + 1}-${label}`, vp);
    await shot(page, `${vp.width}x${vp.height}-result-${cardIndex + 1}`);
  }
  if (errs.length) console.log(`  ⚠ 页面错误: ${errs.join(" | ")}`);
  await page.close();
}

/** 一次加载后扫全部宽度：断点之间的缝隙只有扫出来才看得见。 */
async function sweep(ctx, label, setup, expectKey) {
  const page = await newPage(ctx);
  await setup(page);
  // 扫描前先确认「扫的是那个页面」：setup 里点卡片失败会停在首页，
  // 之后的 129 个宽度全在量首页 —— 又是一次判据空跑。
  const expectSel = EXPECT[expectKey];
  const ok = expectSel ? await page.evaluate(s => !!document.querySelector(s), expectSel) : true;
  const m0 = await page.evaluate(MEASURE);
  if (!ok || m0.errorText) {
    failGroups++;
    const why = !ok ? `未渲染出 ${expectSel}` : `处于错误态「${m0.errorText}」`;
    console.log(`\n✗ 扫描 ${label} 失败：${why}（不扫了——扫出来也是别的页面）`);
    rows.push({ sweep: label, bad: [{ why }] });
    await page.close();
    return;
  }
  const meta = await page.evaluate(() => {
    const r = document.querySelector('[data-testid^="renderer"]');
    const t = document.querySelector(".v6-task-title, .v6-question-text, h1");
    return { renderer: r ? r.dataset.testid : "", title: (t?.textContent || "").trim().slice(0, 20) };
  });
  const bad = [];
  let firstShot = true;
  for (const w of SWEEP_WIDTHS) {
    await page.setViewportSize({ width: w, height: 800 });
    await page.waitForTimeout(45);
    const m = await page.evaluate(MEASURE);
    const exposed = m.over.filter(o => o.kind === "exposed");
    const clipped = m.over.filter(o => o.kind === "clipped");
    if (m.docScrollW > m.vw + 1 || m.draggedX > 0 || exposed.length || clipped.length || m.over.some(o => o.left < -0.5)) {
      bad.push({ w, sw: m.docScrollW, nodes: [...exposed, ...clipped].slice(0, 3).map(o => `${o.kind}:${o.node}@${o.right}`) });
      if (SHOT && firstShot) { await shot(page, `sweep-${label}-${w}`); firstShot = false; }
    }
  }
  if (bad.length) {
    failGroups++;
    console.log(`\n✗ 扫描 ${label}: ${bad.length} 个宽度溢出`);
    for (const b of bad.slice(0, 12)) console.log(`   ${b.w}px scrollWidth=${b.sw} ${b.nodes.join(" ")}`);
  } else {
    console.log(`\n✔ 扫描 ${label}${meta.renderer ? ` [${meta.renderer}]` : ""}: 320–1600 每 10px 均无横向溢出`);
  }
  rows.push({ sweep: label, renderer: meta.renderer, title: meta.title, bad });
  await page.close();
}

const sweepCtx = await browser.newContext({ viewport: { width: 390, height: 800 } });

if (SWEEP) {
  for (const p of PAGES) {
    await sweep(sweepCtx, p === "/" ? "根路径" : p.replace(/^\//, "").replace(/\//g, "-"), async (page) => {
      await gotoWarm(page, p);
    }, p);
    if (p.includes("/growth")) {
      await sweep(sweepCtx, "growth-展开节点", async (page) => {
        await gotoWarm(page, p);
        const n = page.locator(".v6-ability-row").first();
        if (!(await n.count())) throw new Error("没有能力行可点，展开态扫不到");
        await n.click();
        await page.waitForTimeout(600);
        if (!(await page.evaluate(() => !!document.querySelector('[data-testid="v6-ability-detail"]')))) {
          throw new Error("点了能力行没展开详情");
        }
      }, p);
    }
  }
  if (FLOW) {
    const cards = (arg("cards", "1,2,3,4,5,6")).split(",").map(s => Number(s.trim())).filter(n => n >= 1 && n <= 6);
    for (const i of cards) {
      await sweep(sweepCtx, `session-${i}`, async (page) => {
        await page.goto(`${BASE}/child/math`, { waitUntil: "networkidle" });
        await page.waitForTimeout(800);
        const entries = await page.$$(CARD_SEL);
        if (!entries.length) throw new Error("首页无可点入口");
        await (entries[Math.min(i - 1, entries.length - 1)]).click();
        await page.waitForFunction(() => document.querySelector('.v6-task-content') !== null, null, { timeout: 45000 }).catch(() => {});
        await page.waitForTimeout(1500);
      }, "/session");
    }
    if (cards.includes(1)) await sweep(sweepCtx, "result", async (page) => {
      await page.goto(`${BASE}/child/math`, { waitUntil: "networkidle" });
      await page.waitForTimeout(800);
      const first = (await page.$$(CARD_SEL))[0];
      await first.click();
      await page.waitForTimeout(2500);
      const sid = (page.url().match(/session\/([^/?#]+)/) ?? [])[1];
      await page.goto(`${BASE}/child/math/result/${sid}`, { waitUntil: "networkidle" });
      await page.waitForTimeout(1500);
    }, "/result");
  }
  await sweepCtx.close();
} else {
  for (const vp of VP_LIST) {
    const ctx = await newContext(vp);
    for (const p of PAGES) {
      await runStatic(ctx, vp, p, p === "/" ? "根路径" : p.replace(/^\//, "").replace(/\//g, "-"), null);
      if (p.includes("/growth")) {
        // 手机上点开节点会展开详情卡（.v6-mobile-node-detail），版式与收起时不同，必须单独量。
        // V1.4 起「节点」改成了「能力行」：原来按 `v6-node-` 前缀找按钮，改名后一个都找不到，
        // count=0 时静默跳过 —— 于是「展开态」量到的其实还是收起态（1053 == 1053），
        // 判据看起来 PASS，实际什么都没测。现在找不到行、点了没展开，都记一条 FAIL。
        await runStatic(ctx, vp, p, "growth-展开节点", async (page) => {
          const n = page.locator(".v6-ability-row").first();
          if (!(await n.count())) {
            rows.push({ viewport: vp.name, page: "growth-展开节点", problems: ["P0 没有任何能力行可点，展开态无从测量"], phoneVOver: 0 });
            failGroups++;
            return;
          }
          await n.click();
          await page.waitForTimeout(700);
          const opened = await page.evaluate(() => !!document.querySelector('[data-testid="v6-ability-detail"]'));
          if (!opened) {
            rows.push({ viewport: vp.name, page: "growth-展开节点", problems: ["P0 点了能力行但没有展开详情（展开态等于没测）"], phoneVOver: 0 });
            failGroups++;
          }
        });
      }
    }
    if (FLOW) for (let i = 0; i < 6; i++) await runFlow(ctx, vp, i);
    await ctx.close();
  }
  await sweepCtx.close();
}

await browser.close();
fs.writeFileSync(path.join(OUT, "report.json"), JSON.stringify(rows, null, 1), "utf8");
// 一条记录都没有 = 什么都没验，这时说 PASS 等于替空集合背书。
if (rows.length === 0) {
  console.error(`✗ 0 条测量记录：页面根本没被量到，不能判 PASS`);
  process.exit(1);
}
console.log(`\n${failGroups === 0 ? "✔ 全部页面 × 视口装得下 -> PASS" : "✗ " + failGroups + " 组有问题 -> FAIL"}  (报告 ${path.join(OUT, "report.json")})`);
process.exit(failGroups === 0 ? 0 : 1);
