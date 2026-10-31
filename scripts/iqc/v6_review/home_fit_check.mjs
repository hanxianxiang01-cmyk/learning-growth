import { chromium } from "playwright";
import fs from "node:fs";

const BASE = process.argv[2] || "http://127.0.0.1:3105";
const CANDIDATES = [
  process.env.CHROME_PATH,
  `${process.env.HOME}/Library/Caches/ms-playwright/chromium-1228/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing`,
].filter(Boolean);
const exe = CANDIDATES.find((p) => fs.existsSync(p));

const VIEWPORTS = [
  { name: "PC 1920x1080", w: 1920, h: 1080 },
  { name: "PC 1440x900", w: 1440, h: 900 },
  { name: "PC 1366x768", w: 1366, h: 768 },
  { name: "Pad 1024x768 横屏", w: 1024, h: 768 },
  { name: "Pad 768x1024 竖屏", w: 768, h: 1024 },
  { name: "Phone 390x844", w: 390, h: 844 },
];

const OUT = "output/v6_review/home_fit";
fs.mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ executablePath: exe });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();
const errors = [];
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
page.on("pageerror", (e) => errors.push(String(e)));

const report = [];
for (const vp of VIEWPORTS) {
  await page.setViewportSize({ width: vp.w, height: vp.h });
  await page.goto(BASE + "/child/math", { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(900);

  const m = await page.evaluate(() => {
    const q = (sel) => document.querySelector(sel);
    const rect = (el) => (el ? Math.round(el.getBoundingClientRect().height) : null);
    const total = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight);
    const cards = [...document.querySelectorAll(".v6-task-entry")];
    const overflow = [];
    for (const c of cards) {
      const cRect = c.getBoundingClientRect();
      for (const el of c.querySelectorAll("strong,small,.v6-task-estimate")) {
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) continue; // display:none 的元素不算越界
        if (getComputedStyle(el).visibility === "hidden") continue;
        if (r.right > cRect.right + 0.5 || r.left < cRect.left - 0.5) {
          overflow.push(`${c.dataset.testid}:${el.className || el.tagName} 越界`);
        }
        if (el.scrollWidth > el.clientWidth + 1) {
          overflow.push(`${c.dataset.testid}:${el.className || el.tagName} 文字溢出 ${el.scrollWidth}>${el.clientWidth}`);
        }
      }
    }
    // 真「一屏」的直接判据：最后一个内容块的底边必须落在视口内（scrollHeight 最小等于视口高，会骗人）。
    const columnsEl = q(".v6-home-columns");
    const contentBottom = columnsEl ? Math.round(columnsEl.getBoundingClientRect().bottom) : null;
    return {
      total,
      contentBottom,
      header: rect(q(".v6-learning-header")),
      hero: rect(q(".v6-home-hero")),
      quota: rect(q(".v6-home-quota")),
      columns: rect(q(".v6-home-columns")),
      records: rect(q(".v6-home-records")),
      tasks: rect(q(".v6-home-tasks")),
      taskList: (() => {
        const el = q(".v6-task-list");
        if (!el) return null;
        return getComputedStyle(el).gridTemplateColumns;
      })(),
      cardHeights: cards.map((c) => Math.round(c.getBoundingClientRect().height)),
      cardWidths: cards.map((c) => Math.round(c.getBoundingClientRect().width)),
      smallLines: cards.map((c) => {
        const s = c.querySelector("small");
        if (!s) return null;
        const lh = parseFloat(getComputedStyle(s).lineHeight);
        return Math.round(s.getBoundingClientRect().height / lh);
      }),
      estimateVisible: cards.map((c) => {
        const e = c.querySelector(".v6-task-estimate");
        return !!(e && getComputedStyle(e).display !== "none");
      }),
      minTap: Math.min(...[...document.querySelectorAll(".v6-task-entry, .v6-home-hero button, .v6-learning-header nav a")]
        .map((el) => Math.round(el.getBoundingClientRect().height))),
      mapEntry: !!q(".v6-map-entry"),
      navHasMap: [...document.querySelectorAll(".v6-learning-header nav a")].some((a) => a.textContent.includes("成长地图")),
      overflow,
      hOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
    };
  });

  const over = m.total - vp.h;
  report.push({ viewport: vp.name, w: vp.w, h: vp.h, over, ...m });
  console.log(`\n${"=".repeat(76)}\n${vp.name}  视口高 ${vp.h}`);
  console.log(`  总内容高 ${m.total}   超高 ${over > 0 ? over : 0}   ${over <= 0 ? "✔ 一屏" : "✗ 需滚动"}`);
  console.log(`  最后一个内容块底边 y=${m.contentBottom} / 视口高 ${vp.h}  ${m.contentBottom !== null && m.contentBottom <= vp.h ? "✔ 全可见" : "✗ 有内容在屏幕外"}`);
  console.log(`  header ${m.header} | hero ${m.hero} | quota ${m.quota} | columns ${m.columns} (records ${m.records} / tasks ${m.tasks})`);
  console.log(`  task-list 列宽: ${m.taskList}`);
  console.log(`  卡片高: ${m.cardHeights.join(",")}  宽: ${m.cardWidths.join(",")}`);
  console.log(`  描述行数: ${m.smallLines.join(",")}   时长可见: ${m.estimateVisible.map((v) => (v ? "Y" : "n")).join(",")}`);
  console.log(`  最小触控目标高 ${m.minTap}  横向溢出 ${m.hOverflow}  底部重复成长卡 ${m.mapEntry}  页头成长入口 ${m.navHasMap}`);
  if (m.overflow.length) console.log(`  ⚠ 文字越界/溢出: ${m.overflow.slice(0, 6).join(" | ")}`);

  await page.screenshot({ path: `${OUT}/${vp.w}x${vp.h}.png`, fullPage: false });
}

fs.writeFileSync(`${OUT}/report.json`, JSON.stringify({ report, errors }, null, 2));
console.log(`\n控制台错误 ${errors.length} 条`);
if (errors.length) console.log(errors.slice(0, 5).join("\n"));
await browser.close();
