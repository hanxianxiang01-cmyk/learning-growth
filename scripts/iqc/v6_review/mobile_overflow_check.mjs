// 手机端横向溢出判据（学习页）：只有「真实落在视口外、且没有任何视口内裁剪容器拦住」才算溢出。
// 判据刻意区分两件事：
//   1) 内容被 overflow-x:auto/scroll/hidden/clip 的祖先裁在视口内  -> 不算溢出（但会单独报「需要横向滚动」）
//   2) 元素右边界超出视口、且没有视口内的裁剪祖先               -> 真溢出（会被 .v6-page 的 overflow-x:clip 直接切掉，孩子无法触及）
// 用法：node scripts/iqc/v6_review/mobile_overflow_check.mjs <baseUrl> [--shot] [--all-tasks]
import { chromium } from "playwright";
import fs from "node:fs";

const exe = `${process.env.HOME}/Library/Caches/ms-playwright/chromium-1228/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing`;
const BASE = (process.argv[2] ?? "http://127.0.0.1:3106").replace(/\/$/, "");
const SHOT = process.argv.includes("--shot");
const ALL_TASKS = process.argv.includes("--all-tasks");
const OUT = "output/v6_review/mobile_fit";
fs.mkdirSync(OUT, { recursive: true });

const VIEWPORTS = [
  { name: "iPhone 14 390x844", width: 390, height: 844 },
  { name: "iPhone SE 375x667", width: 375, height: 667 },
  { name: "老安卓 360x760", width: 360, height: 760 },
  { name: "窄屏 320x568", width: 320, height: 568 },
];

const MEASURE = () => {
  const vw = window.innerWidth;
  const desc = (el) => {
    const cls = (el.className && typeof el.className === "string" ? el.className : "")
      .split(/\s+/).filter(Boolean).slice(0, 3).join(".");
    const tid = el.dataset?.testid ? `[${el.dataset.testid}]` : "";
    return `${el.tagName.toLowerCase()}${tid}${cls ? "." + cls : ""}`;
  };
  // 只有「真的能横向滑动」的容器才算合理收留溢出内容。
  // overflow-x:hidden/clip 的祖先（含全页的 .v6-page / .v6-learning）不算：
  // 它把内容藏起来、孩子永远够不到，正是要抓的缺陷。否则判据会被全页 clip 挡成永远 PASS。
  const clippedBy = (el) => {
    let cur = el.parentElement;
    while (cur && cur !== document.documentElement) {
      const cs = getComputedStyle(cur);
      if (/auto|scroll/.test(cs.overflowX) && cur.scrollWidth > cur.clientWidth + 1) {
        const r = cur.getBoundingClientRect();
        if (r.right <= vw + 0.5 && r.left >= -0.5) return desc(cur);
      }
      cur = cur.parentElement;
    }
    return null;
  };
  const all = [...document.querySelectorAll("body *")];
  const real = [];
  const scrollers = [];
  for (const el of all) {
    const cs = getComputedStyle(el);
    if (cs.position === "fixed" || cs.visibility === "hidden") continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    if (r.right > vw + 0.5 && !clippedBy(el)) {
      real.push({ node: desc(el), right: Math.round(r.right), w: Math.round(r.width), cs: { minW: cs.minWidth, overflowX: cs.overflowX }, text: (el.textContent || "").trim().slice(0, 20) });
    }
    if (el.scrollWidth > el.clientWidth + 1 && el.clientWidth > 0 && /auto|scroll/.test(cs.overflowX)) {
      scrollers.push({ node: desc(el), scrollW: el.scrollWidth, clientW: el.clientWidth });
    }
  }
  real.sort((a, b) => b.right - a.right);
  // 只看最外层：去掉祖先也在列表里的（它们同属一个溢出块）
  const nodes = new Set(real.map((r) => r.node));
  const textClipped = [];
  for (const el of document.querySelectorAll(".question-text, p, strong, small, h1, h2, span")) {
    const cs = getComputedStyle(el);
    if (cs.overflow === "visible" && cs.whiteSpace === "nowrap" && el.scrollWidth > el.clientWidth + 1) {
      textClipped.push({ node: desc(el), scrollW: el.scrollWidth, clientW: el.clientWidth, ws: cs.whiteSpace });
    }
  }
  return {
    vw,
    docScrollW: document.documentElement.scrollWidth,
    hasTask: !!document.querySelector(".v6-task-content"),
    brand: (document.querySelector(".v6-renderer")?.getAttribute("data-testid")) || "",
    taskIds: [...document.querySelectorAll("[data-testid]")].map((e) => e.dataset.testid).filter((t) => /renderer|number-line|ten-frame|bar-model|column-arithmetic|clock|answer/.test(t)).slice(0, 6),
    realOverflow: real.slice(0, 10),
    realCount: real.length,
    scrollers: scrollers.slice(0, 6),
    textClipped: textClipped.slice(0, 6),
    _nodes: nodes.size,
  };
};

const browser = await chromium.launch({ executablePath: exe });
let failed = 0;
const report = [];

for (const vp of VIEWPORTS) {
  const cards = ALL_TASKS ? 5 : 1;
  for (let card = 0; card < cards; card++) {
    const ctx = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
      isMobile: true, hasTouch: true, deviceScaleFactor: 2,
    });
    const page = await ctx.newPage();
    const errs = [];
    page.on("pageerror", (e) => errs.push(String(e).slice(0, 100)));

    await page.goto(`${BASE}/child/math`, { waitUntil: "networkidle" });
    await page.waitForTimeout(600);

    const entries = await page.$$('[data-testid^="v6-task-entry"], [data-testid="v6-home-start"]');
    if (entries.length === 0) { console.log(`!! ${vp.name} 首页没有可点入口`); await ctx.close(); continue; }
    const target = entries[Math.min(card, entries.length - 1)];
    const label = (await target.evaluate((e) => (e.textContent || "").trim().slice(0, 14))) || `entry${card}`;
    await target.click();
    await page.waitForTimeout(2600);

    const m = await page.evaluate(MEASURE);
    const tag = `${vp.name} · ${label}`;
    const bad = m.realCount > 0;
    if (bad) failed++;
    report.push({ viewport: vp.name, entry: label, ...m });

    console.log(`\n=== ${tag}`);
    console.log(`  视口 ${m.vw} / 文档 scrollWidth ${m.docScrollW} / 任务 ${m.taskIds.join(",") || "?"}  ${bad ? "✗ 真溢出 " + m.realCount : "✔ 无真溢出"}`);
    if (!m.hasTask) console.log("  ⚠ 未进入学习页");
    for (const o of m.realOverflow) {
      console.log(`  ✗ ${o.node}  右边界 ${o.right} (超 ${o.right - m.vw}px)  宽${o.w}  minWidth=${o.cs.minW} overflowX=${o.cs.overflowX}  文案「${o.text}」`);
    }
    if (m.scrollers.length) {
      console.log(`  ⓘ 需要横向滚动的内容（被裁在视口内，不算溢出但体验需评估）:`);
      for (const s of m.scrollers) console.log(`     ${s.node}  ${s.scrollW} > ${s.clientW}`);
    }
    if (m.textClipped.length) {
      console.log(`  ⓘ 不换行的文字:`);
      for (const t of m.textClipped) console.log(`     ${t.node}  ${t.scrollW} > ${t.clientW} whiteSpace=${t.ws}`);
    }
    if (errs.length) console.log(`  页面错误: ${errs.join(" | ")}`);
    if (SHOT) await page.screenshot({ path: `${OUT}/${vp.width}x${vp.height}-${card}-${label.replace(/[^\w\u4e00-\u9fa5]/g, "")}.png` });
    await ctx.close();
  }
}

await browser.close();
fs.writeFileSync(`${OUT}/report.json`, JSON.stringify(report, null, 1), "utf8");
console.log(`\n${failed === 0 ? "✔ 全部视口 × 任务无横向溢出 -> PASS" : "✗ " + failed + " 组存在真溢出 -> FAIL"}`);
process.exit(failed === 0 ? 0 : 1);
