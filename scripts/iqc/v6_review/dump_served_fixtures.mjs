/**
 * FE-1445 复审：导出「服务端实际下发」的 19 类 Renderer 任务样本。
 *
 * 为什么要走接口而不是直接读库：库里的 `ui_schema` 是**未补齐**的原始内容，
 * 服务端在 `/tasks/next` 响应里才补 `renderer_version` / `capabilities` 等字段。
 * 第一版直接拿库里的 ui_schema 喂渲染器，14 个报
 * 「Workspace main requires renderer_version」——那是我取错了事实源，
 * 不是渲染器的问题。视觉复核必须看用户真正收到的那份 payload。
 *
 * 数据卫生：钉题只对 QA 池 child（…0099）开放，本脚本走
 * POST /v1/guest/qa-session 取 QA 会话后 pin，绝不写真实 child 的数据。
 * 需要后端以 SELECTION_TRACE_ENABLED=true 启动（生产默认关闭）。
 *
 * 用法：
 *   node scripts/iqc/v6_review/dump_served_fixtures.mjs --out output/v6_review/fixtures.json
 */
import { request as pwRequest } from "playwright-core";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

function arg(name, dflt) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : dflt;
}
const API = arg("api", "http://127.0.0.1:8000");
const OUT = resolve(arg("out", "output/v6_review/fixtures.json"));
const QA_CHILD = "00000000-0000-0000-0000-000000000099";

const RELEASE_RENDERERS = [
  "object-counter", "bar-model", "number-line", "number-input",
  "column-arithmetic", "place-value", "ten-frame", "array-board",
  "grouping-board", "formula-board", "estimation-canvas", "shape-gallery",
  "shape-canvas", "sorting-board", "direction-grid", "ruler", "clock",
  "money-board", "pattern-board"
];

const ctx = await pwRequest.newContext({ baseURL: API });

// QA 会话（仅 …0099 可签发；别的 child 会被 403）
const qa = await ctx.post(`/v1/guest/qa-session?child_id=${QA_CHILD}`);
if (!qa.ok()) {
  console.error(`FATAL: qa-session ${qa.status()} —— 后端需以 SELECTION_TRACE_ENABLED=true 启动`);
  process.exit(2);
}

const cat = await ctx.get("/v1/content/v2-catalog");
if (!cat.ok()) {
  console.error(`FATAL: v2-catalog ${cat.status()}`);
  process.exit(2);
}
const items = (await cat.json()).items || [];
const byRenderer = {};
for (const it of items) (byRenderer[it.renderer] ??= []).push(it);

const fixtures = {};
const missing = [];
for (const renderer of RELEASE_RENDERERS) {
  const candidates = byRenderer[renderer] || [];
  if (!candidates.length) { missing.push(renderer); continue; }
  const picked = candidates[0];

  const s = await ctx.post("/v1/learning/sessions", {
    data: { child_id: QA_CHILD, subject: "math", requested_minutes: 15 }
  });
  const sid = (await s.json()).session_id;
  const t = await ctx.post("/v1/learning/tasks/next", {
    data: {
      child_id: QA_CHILD, session_id: sid, subject: "math", requested_minutes: 15,
      pin_resource_version_id: picked.resource_version_id
    }
  });
  if (!t.ok()) { missing.push(`${renderer}(${t.status()})`); continue; }
  const task = await t.json();
  const ws = (task.ui_schema?.workspaces || [])[0] || {};
  if (ws.renderer !== renderer) { missing.push(`${renderer}(got ${ws.renderer})`); continue; }

  fixtures[renderer] = {
    renderer,
    resource_version_id: task.resource_version_id ?? picked.resource_version_id,
    difficulty: task.difficulty,
    goal: task.goal ?? "",
    ui_schema: task.ui_schema
  };
  console.log(`[OK]   ${renderer.padEnd(20)} mode=${String(ws.mode ?? "-").padEnd(16)} rv=${ws.renderer_version ?? "?"} rvid=${fixtures[renderer].resource_version_id}`);
}
await ctx.dispose();

mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, JSON.stringify(fixtures, null, 2));
console.log(`\n覆盖 ${Object.keys(fixtures).length}/${RELEASE_RENDERERS.length} -> ${OUT}`);
if (missing.length) {
  console.error(`FAIL: 缺 ${missing.join(", ")}`);
  process.exit(1);
}
