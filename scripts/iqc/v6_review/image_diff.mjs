/**
 * FE-1445 复审：两组截图的逐像素比对（迁移前 vs 迁移后）。
 *
 * 为什么不用 ImageMagick/PIL：本机都没有（实测 `magick`/`PIL` 均缺失）。
 * 浏览器本来就在手边，用 canvas 读像素即可——不引新依赖，也不把「装个工具」
 * 变成结论成立的前提。
 *
 * 判据：
 *   D01 两版同尺寸（尺寸变了说明布局变了）
 *   D02 差异像素数为 0（任何一处像素不同都算「有视觉变化」，逐条列出待人工判定）
 *
 * 用法：node scripts/iqc/v6_review/image_diff.mjs \
 *         --a output/v6_review/visual --b output/v6_review/visual-head \
 *         --out output/v6_review/visual_diff.json
 */
import { chromium } from "playwright-core";
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { basename, dirname, resolve } from "node:path";

const EXEC = process.env.CHROME_HEADLESS_SHELL
  ?? "/Users/hanxianxiang/Library/Caches/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell";

function arg(name, dflt) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : dflt;
}
const A = resolve(arg("a", "output/v6_review/visual"));
const B = resolve(arg("b", "output/v6_review/visual-head"));
const OUT = resolve(arg("out", "output/v6_review/visual_diff.json"));

const browser = await chromium.launch({ executablePath: EXEC });
const page = await browser.newPage();

async function diff(pa, pb) {
  const a64 = readFileSync(pa).toString("base64");
  const b64 = readFileSync(pb).toString("base64");
  return page.evaluate(async ([a, b]) => {
    const load = src => new Promise((ok, bad) => {
      const img = new Image();
      img.onload = () => ok(img);
      img.onerror = () => bad(new Error("decode failed"));
      img.src = `data:image/png;base64,${src}`;
    });
    const [ia, ib] = await Promise.all([load(a), load(b)]);
    if (ia.width !== ib.width || ia.height !== ib.height) {
      return { sameSize: false, aSize: [ia.width, ia.height], bSize: [ib.width, ib.height], diffPixels: -1 };
    }
    const draw = img => {
      const c = document.createElement("canvas");
      c.width = img.width; c.height = img.height;
      c.getContext("2d").drawImage(img, 0, 0);
      return c.getContext("2d").getImageData(0, 0, img.width, img.height).data;
    };
    const da = draw(ia), db = draw(ib);
    let diffPixels = 0, maxDelta = 0;
    let minX = Infinity, minY = Infinity, maxX = -1, maxY = -1;
    for (let i = 0; i < da.length; i += 4) {
      const d = Math.max(
        Math.abs(da[i] - db[i]),
        Math.abs(da[i + 1] - db[i + 1]),
        Math.abs(da[i + 2] - db[i + 2]),
        Math.abs(da[i + 3] - db[i + 3])
      );
      if (d > 0) {
        diffPixels += 1;
        if (d > maxDelta) maxDelta = d;
        const p = i / 4, x = p % ia.width, y = Math.floor(p / ia.width);
        if (x < minX) minX = x;
        if (y < minY) minY = y;
        if (x > maxX) maxX = x;
        if (y > maxY) maxY = y;
      }
    }
    return {
      sameSize: true,
      width: ia.width,
      height: ia.height,
      totalPixels: ia.width * ia.height,
      diffPixels,
      maxDelta,
      bbox: diffPixels ? [minX, minY, maxX, maxY] : null
    };
  }, [a64, b64]);
}

const checks = [];
const rows = [];
const check = (label, ok, detail = "") => {
  checks.push({ label, ok: !!ok, detail: String(detail) });
  console.log(`[${ok ? "PASS" : "FAIL"}] ${label}${detail ? " — " + detail : ""}`);
};

try {
  if (!existsSync(A) || !existsSync(B)) {
    check("两组截图目录均存在", false, `${A} / ${B}`);
  } else {
    const skins = readdirSync(A).filter(d => !d.includes("."));
    for (const skin of skins) {
      const dirA = resolve(A, skin);
      const dirB = resolve(B, skin);
      if (!existsSync(dirB)) { check(`${skin} 对照组存在`, false); continue; }
      const files = readdirSync(dirA).filter(f => f.endsWith(".png")).sort();
      for (const f of files) {
        const pb = resolve(dirB, f);
        if (!existsSync(pb)) { check(`${skin}/${basename(f, ".png")} 对照组有同名截图`, false); continue; }
        const d = await diff(resolve(dirA, f), pb);
        rows.push({ skin, renderer: basename(f, ".png"), ...d });
        check(`${skin}/${basename(f, ".png")} 尺寸一致`, d.sameSize,
              d.sameSize ? `${d.width}x${d.height}` : `${d.aSize} vs ${d.bSize}`);
        check(`${skin}/${basename(f, ".png")} 像素无差异`, d.diffPixels === 0,
              d.diffPixels === 0 ? "0/变化" : `${d.diffPixels}/${d.totalPixels}px 不同，最大通道差 ${d.maxDelta}，bbox ${d.bbox}`);
      }
    }
  }
} finally {
  await browser.close();
}

mkdirSync(dirname(OUT), { recursive: true });
const failed = checks.filter(c => !c.ok);
writeFileSync(OUT, JSON.stringify({
  generatedAt: new Date().toISOString(), a: A, b: B, rows, checks,
  result: failed.length ? "FAIL" : "PASS"
}, null, 2));
console.log(`\n${checks.length - failed.length}/${checks.length} PASS -> ${failed.length ? "FAIL" : "PASS"}  (${OUT})`);
process.exitCode = failed.length ? 1 : 0;
