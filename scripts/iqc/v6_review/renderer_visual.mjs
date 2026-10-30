/**
 * FE-1445 复审：19 类 Renderer × 两套皮肤的视觉采集与结构断言。
 *
 * 只判定「有没有回归」这类可机器判定的东西：
 *   V01 19 个渲染器都渲染出来（不是降级成 unsupported 占位）
 *   V02 每个渲染器都有实际可见尺寸（宽高 > 0，防白屏）
 *   V03 画布没有横向溢出（防布局撑破）
 *   V04 皮肤确实生效（--cm-app / --v6-theme 两套皮肤不同）
 *   V05 V6 主行动色为统一 token（两皮肤相同，这是 V6 的设计口径，不是缺陷；
 *       这里把它测出来并记录，避免下次有人误以为是「按钮不跟皮肤」）
 *
 * 样本来自生产题库（dump_renderer_fixtures.py 只读导出），不写进仓库。
 *
 * 用法：
 *   node scripts/iqc/v6_review/renderer_visual.mjs \
 *     --fixtures output/v6_review/fixtures.json --out output/v6_review/visual
 */
import { chromium } from "playwright-core";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const EXEC = process.env.CHROME_HEADLESS_SHELL
  ?? "/Users/hanxianxiang/Library/Caches/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell";

function arg(name, dflt) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : dflt;
}
const BASE = arg("base", "http://127.0.0.1:3102");
const FIXTURES = resolve(arg("fixtures", "output/v6_review/fixtures.json"));
const OUT = resolve(arg("out", "output/v6_review/visual"));

const fixtures = Object.values(JSON.parse(readFileSync(FIXTURES, "utf8")));
const checks = [];
const check = (id, label, ok, detail = "") => {
  checks.push({ id, label, ok: !!ok, detail: String(detail) });
  console.log(`[${ok ? "PASS" : "FAIL"}] ${id} ${label}${detail ? " — " + detail : ""}`);
};

const skins = ["exploration-lab", "healing"];
const tokensBySkin = {};

const browser = await chromium.launch({ executablePath: EXEC });
try {
  for (const skin of skins) {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 });
    await ctx.addInitScript(items => { window.__GALLERY_FIXTURES__ = items; }, fixtures);
    const page = await ctx.newPage();
    const errors = [];
    page.on("pageerror", e => errors.push(String(e)));
    await page.goto(`${BASE}/dev/renderer-gallery?skin=${skin}`, { waitUntil: "networkidle" });
    await page.waitForSelector("[data-gallery-root]", { timeout: 30000 });
    await page.waitForTimeout(1200);

    const dir = resolve(OUT, skin);
    mkdirSync(dir, { recursive: true });

    // 皮肤 token：证明皮肤真的应用上了
    tokensBySkin[skin] = await page.evaluate(() => {
      const root = document.querySelector("[data-gallery-root]");
      const cs = getComputedStyle(root);
      return {
        cmApp: cs.getPropertyValue("--cm-app").trim(),
        cmPrimary: cs.getPropertyValue("--cm-primary").trim(),
        v6Action: cs.getPropertyValue("--v6-action").trim(),
        v6Theme: cs.getPropertyValue("--v6-theme").trim()
      };
    });

    for (const item of fixtures) {
      const r = item.renderer;
      const canvas = page.locator(`[data-gallery-canvas="${r}"]`);
      const exists = await canvas.count() === 1;
      let box = null;
      if (exists) {
        box = await canvas.boundingBox();
        await page.locator(`[data-gallery-renderer="${r}"]`).screenshot({ path: resolve(dir, `${r}.png`) });
      }
      const fallback = exists ? await canvas.evaluate(el =>
        !!el.querySelector('[data-testid="planned-renderer"]')
        || /还在开发中|暂时需要新的学习工具/.test(el.textContent || "")) : true;
      const overflow = exists ? await canvas.evaluate(el => el.scrollWidth - el.clientWidth) : -1;

      // 每个渲染器三条：存在且有尺寸 / 不降级 / 不横向溢出
      check(`V${r}`, `${skin}/${r} 渲染出现且可见`, exists && !!box && box.height > 20 && box.width > 20,
            box ? `${Math.round(box.width)}x${Math.round(box.height)}` : "无画布");
      check(`V${r}b`, `${skin}/${r} 未降级为占位`, !fallback, fallback ? "命中降级占位" : "ok");
      check(`V${r}c`, `${skin}/${r} 无横向溢出`, overflow <= 1, `overflow=${overflow}px`);
    }

    check(`VE${skin}`, `${skin} 无页面级 JS 异常`, errors.length === 0, errors.slice(0, 2).join(" | ") || "0");
    await ctx.close();
  }

  // 皮肤差异：背景/主题必须不同；主行动色在 V6 下应为统一 token
  const [a, b] = [tokensBySkin["exploration-lab"], tokensBySkin["healing"]];
  check("V04", "两套皮肤的应用色确实不同", !!a && !!b && a.cmApp !== b.cmApp && a.v6Theme !== b.v6Theme,
        `app ${a?.cmApp} vs ${b?.cmApp}; theme ${a?.v6Theme} vs ${b?.v6Theme}`);
  check("V05", "V6 主行动色为统一 token（两皮肤一致，设计口径）", !!a && !!b && a.v6Action === b.v6Action,
        `${a?.v6Action} vs ${b?.v6Action}`);

  const report = {
    generatedAt: new Date().toISOString(),
    base: BASE,
    fixtures: fixtures.map(f => ({ renderer: f.renderer, rvid: f.resource_version_id })),
    tokensBySkin,
    checks
  };
  mkdirSync(OUT, { recursive: true });
  writeFileSync(resolve(OUT, "report.json"), JSON.stringify(report, null, 2));

  const failed = checks.filter(c => !c.ok);
  console.log(`\n${checks.length - failed.length}/${checks.length} PASS -> ${failed.length ? "FAIL" : "PASS"}`);
  process.exitCode = failed.length ? 1 : 0;
} finally {
  await browser.close();
}
