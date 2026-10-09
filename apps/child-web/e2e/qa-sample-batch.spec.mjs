// FE-1438：155 题批 Gate 4~7 UI 抽样实灌（qa_staged 隔离批，QA child …0099）。
// 语义：交付方整改题（每 renderer 1 题×19）经 pin(qa_staged) 在真实前端渲染 + 交互 + 提交判分。
// 隔离：qa_staged 不进 catalog/生产池（scripts/qa_sample_ingest.py），pin 路径放行（FE-1438 分支）。
// 依赖：后端 8000 + lab 3100；rvid 映射=e2e/qa-sample-rvids.mjs（ingest 后导出）。
import { test, expect } from "@playwright/test";
import { pinTaskByRvid } from "./pinned-tasks.mjs";
import { QA_SAMPLE_RVIDS } from "./qa-sample-rvids.mjs";

const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8000";
const CHILD = process.env.E2E_CHILD_ID ?? "00000000-0000-0000-0000-000000000099";

// question_id → 根 testid + 一个题面关键词（渲染不降级 + 题面来自交付数据）
const SAMPLES = [
  { qid: "V14-P0-001", renderer: "object-counter",  root: "object-counter-v2",   kw: "积木" },
  { qid: "V14-P0-009", renderer: "bar-model",       root: "bar-model-v2",        kw: "书架" },
  { qid: "V14-P0-017", renderer: "number-line",     root: "number-line-v2",      kw: "数轴" },
  { qid: "V14-P0-025", renderer: "number-input",    root: "number-input-v2",     kw: "个十" },
  { qid: "V14-P0-033", renderer: "place-value",     root: "place-value-v2",      kw: "位值" },
  { qid: "V14-P0-041", renderer: "ten-frame",       root: "ten-frame-v2",        kw: "圆点" },
  { qid: "V14-P0-049", renderer: "column-arithmetic", root: "column-arithmetic", kw: "竖式" },
  { qid: "V14-P0-057", renderer: "array-board",     root: "array-board-v2",      kw: "棋子" },
  { qid: "V14-P0-065", renderer: "grouping-board",  root: "grouping-board-v2",   kw: "玻璃珠" },
  { qid: "V14-P0-073", renderer: "formula-board",   root: "formula-board-v2",    kw: "7" },
  { qid: "V14-P0-081", renderer: "estimation-canvas", root: "estimation-canvas-v2", kw: "散点" },
  { qid: "V14-P0-089", renderer: "shape-gallery",   root: "shape-gallery-v2",    kw: "三角形" },
  { qid: "V14-P0-097", renderer: "shape-canvas",    root: "shape-canvas-v2",     kw: "长方形" },
  { qid: "V14-P0-105", renderer: "sorting-board",   root: "sorting-board-v2",    kw: "数字卡" },
  { qid: "V14-P0-113", renderer: "direction-grid",  root: "direction-grid-v2",   kw: "棋子从" },
  { qid: "V14-P0-121", renderer: "ruler",           root: "ruler-v2",            kw: "刻度" },
  { qid: "V14-P0-129", renderer: "clock",           root: "clock-v2",            kw: "钟面" },
  { qid: "V14-P0-137", renderer: "money-board",     root: "money-board-v2",      kw: "文具" },
  { qid: "V14-P0-145", renderer: "pattern-board",   root: "pattern-board-v2",    kw: "规律" },
];

test.beforeEach(async ({ page }) => {
  page.setDefaultTimeout(180_000);
});

for (const s of SAMPLES) {
  test(`QA-SAMPLE ${s.qid} (${s.renderer}) pin 渲染不降级`, async ({ page }) => {
    const rvid = QA_SAMPLE_RVIDS[s.qid];
    expect(rvid, `qa_staged rvid 缺失（先跑 qa_sample_ingest.py）`).toBeTruthy();
    const { task, sessionId } = await pinTaskByRvid({ api: API, child: CHILD, rvid });
    // Gate 4：pin 下发 = 该题 ui_schema（renderer 正确、config 来自交付数据）
    expect(task.ui_schema.workspaces[0].renderer).toBe(s.renderer);

    // UI 实灌：拦截 tasks/next 让 session 页吃到 pin 的题
    await page.route("**/v1/learning/tasks/next", route =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(task) }));
    await page.goto(`/child/math/session/qa-${sessionId}?child_id=${CHILD}`);

    // 渲染专件（不降级到 planned-renderer/通用壳）
    await expect(page.getByTestId(s.root)).toBeVisible();
    await expect(page.getByTestId("planned-renderer")).toHaveCount(0);
    // 题面来自交付 prompt
    await expect(page.getByText(new RegExp(s.kw)).first()).toBeVisible();
  });
}
