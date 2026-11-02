// 临时探针：V1.4 移动端改版落地后，量两页的版式与文案。用完即删。
import { chromium } from "playwright";
const EXE = `${process.env.HOME}/Library/Caches/ms-playwright/chromium-1228/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing`;
const BASE = process.argv[2] ?? "http://127.0.0.1:3108";
const browser = await chromium.launch({ executablePath: EXE });

for (const vp of [{ w: 390, h: 844 }, { w: 768, h: 1024 }, { w: 1024, h: 768 }, { w: 1366, h: 768 }, { w: 1440, h: 900 }]) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, isMobile: vp.w <= 480, deviceScaleFactor: 2 });
  const p = await ctx.newPage();
  await p.goto(`${BASE}/child/math`, { waitUntil: "networkidle" });
  await p.waitForSelector('[data-testid="v6-home-start"]', { timeout: 30000 });
  const homeM = await p.evaluate(() => ({ h: document.documentElement.scrollHeight, w: document.documentElement.scrollWidth, vh: innerHeight, vw: innerWidth }));
  console.log(`\n=== ${vp.w}x${vp.h}`);
  console.log(`  home  内容高 ${homeM.h} / 视口 ${homeM.vh}  超出 ${Math.max(0, homeM.h - homeM.vh)}px  文档宽 ${homeM.w}`);
  const homeText = (await p.locator("body").innerText()).replace(/\s+/g, " ");
  console.log(`  首页文案: ${homeText.slice(0, 190)}`);
  const tiles = await p.$$eval(".v6-task-tile", els => els.map(e => { const r = e.getBoundingClientRect(); return { t: e.innerText.replace(/\s+/g, ""), x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) }; }));
  console.log(`  磁贴 ${tiles.length} 个: ` + tiles.map(t => `${t.t}@(${t.x},${t.y})${t.w}x${t.h}`).join(" | "));
  const empty = await p.locator('[data-testid="v6-home-empty"]').count();
  console.log(`  空状态卡 ${empty}`);

  await p.goto(`${BASE}/child/math/growth`, { waitUntil: "networkidle" });
  await p.waitForSelector('[data-testid="v6-growth-abilities"]', { timeout: 30000 });
  await p.waitForTimeout(500);
  const gM = await p.evaluate(() => ({ h: document.documentElement.scrollHeight, w: document.documentElement.scrollWidth, vh: innerHeight, vw: innerWidth }));
  console.log(`  growth 内容高 ${gM.h} / 视口 ${gM.vh}  超出 ${Math.max(0, gM.h - gM.vh)}px  文档宽 ${gM.w}`);
  const g = await p.evaluate(() => ({
    summary: document.querySelector('[data-testid="v6-growth-summary"]')?.innerText.replace(/\s+/g, " ") ?? "(无)",
    rows: document.querySelectorAll(".v6-ability-row").length,
    expanded: document.querySelectorAll('.v6-ability-row[aria-expanded="true"]').length,
    tags: [...document.querySelectorAll(".v6-explore-tag")].map(e => e.textContent),
    rowH: [...document.querySelectorAll(".v6-ability-row")].map(e => Math.round(e.getBoundingClientRect().height)),
    body: document.body.innerText.replace(/\s+/g, " "),
    placeholder: !!document.querySelector('[data-testid="v6-detail-placeholder"]'),
  }));
  console.log(`  摘要: ${g.summary}`);
  console.log(`  行数 ${g.rows} 已展开 ${g.expanded} 行高 ${[...new Set(g.rowH)].join("/")} 占位面板 ${g.placeholder}`);
  console.log(`  标签: ${[...new Set(g.tags)].join(" / ")}`);
  console.log(`  含旧空态措辞: ${["待了解", "暂无数据", "暂无记录", "尚待了解"].filter(t => g.body.includes(t)).join("/") || "无"}`);
  await p.screenshot({ path: `/tmp/shot-${vp.w}x${vp.h}-growth.png`, fullPage: true });

  if (vp.w === 390 || vp.w === 1366) {
    await p.locator(".v6-ability-row").first().click();
    await p.waitForTimeout(400);
    const after = await p.evaluate(() => ({ h: document.documentElement.scrollHeight, detail: !!document.querySelector('[data-testid="v6-ability-detail"]') }));
    console.log(`  点开第一项后: 详情 ${after.detail} 内容高 ${after.h}`);
    await p.screenshot({ path: `/tmp/shot-${vp.w}-growth-open.png`, fullPage: true });
  }
  await p.goto(`${BASE}/child/math`, { waitUntil: "networkidle" });
  await p.waitForTimeout(400);
  await p.screenshot({ path: `/tmp/shot-${vp.w}x${vp.h}-home.png`, fullPage: true });
  await ctx.close();
}
await browser.close();
