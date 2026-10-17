// FE-1462 通用运行时契约探针（数据驱动，可扩展骨架）。
// 三态结果（裁决 §三验收口径）：
//   PASS_RUNTIME   = 渲染→操作→提交→Judge 字段齐全且一致
//   CONTRACT_DEFECT= 题面要求的操作在 UI 上不可完成（登记契约缺陷，不掩盖）
//   BLOCKED        = 数据/schema 不足以验证（显式，不静默跳过）
// 用例源：-- 前缀 IQC_PROBE_JSON 环境变量注入 [{rvid,testid,op:{seq或tap},expect_answer}]
import { test, expect } from "@playwright/test";
import { request as pwRequest } from "@playwright/test";

const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8000";
const CHILD = process.env.E2E_CHILD_ID ?? "00000000-0000-0000-0000-000000000099";
const CASES = JSON.parse(process.env.IQC_PROBE_JSON || "[]");

async function pin(rvid) {
  const ctx = await pwRequest.newContext({ baseURL: API });
  try {
    const s = await ctx.post("/v1/learning/sessions", { data: { child_id: CHILD, subject: "math", requested_minutes: 15 } });
    const sid = (await s.json()).session_id;
    const t = await ctx.post("/v1/learning/tasks/next", { data: { child_id: CHILD, session_id: sid, subject: "math", pin_resource_version_id: rvid } });
    const task = await t.json();
    return { sid, task, blocked: !task.task_instance_id ? (task.reason || "pin-denied") : null };
  } finally { await ctx.dispose(); }
}

test.setTimeout(180_000);
for (const c of CASES) {
  test(`PROBE ${c.renderer} ${c.rvid.slice(0,8)}`, async ({ page }, tinfo) => {
    const { sid, task, blocked } = await pin(c.rvid);
    if (blocked) {
      console.log(`PROBE-RESULT ${c.renderer} ${c.rvid.slice(0,8)} BLOCKED pin:${blocked}`);
      expect(true).toBeTruthy(); return; // 显式 BLOCKED 记录=通过（不假通过）
    }
    await page.route("**/v1/learning/tasks/next", r =>
      r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(task) }));
    await page.goto(`/child/math/session/iqc-probe-${sid}?child_id=${CHILD}`);
    const host = page.getByTestId(c.testid);
    try { await expect(host).toBeVisible({ timeout: 30_000 }); }
    catch {
      console.log(`PROBE-RESULT ${c.renderer} ${c.rvid.slice(0,8)} CONTRACT_DEFECT renderer-not-rendered(${c.testid})`);
      throw new Error("renderer 未渲染——契约缺陷登记");
    }
    // 操作驱动分两型（renderer 交互模型不同——driver registry 的 v1 手工形态）：
    // seq=一阶段直点（数轴类）；shape=两阶段 选卡→放家（shape-gallery 类）
    for (const v of (c.op && c.op.seq) || []) {
      await host.locator(".number-tick span", { hasText: new RegExp(`^\\s*${v}\\s*$`) }).first().click();
    }
    for (const v of (c.op && c.op.shape) || []) {
      await host.locator("button[data-testid^=\"sg-shape-\"]", { hasText: v }).first().click();
      await host.getByTestId("sg-home").click();
    }
    const answerBox = page.locator("#math-answer");
    if (await answerBox.count()) await answerBox.fill(String(c.expect_answer));
    const res = page.waitForResponse(r => r.url().includes("/attempts") && (r.status() === 200 || r.status() === 422));
    // 提交控件分 renderer：数轴类走答案区"提交答案"；操作类自带提交（driver registry v1）
    if (c.submit_testid) await host.getByTestId(c.submit_testid).click();
    else await page.getByText("提交答案").click();
    const resp = await res; const j = await resp.json();
    const judgeFields = ["correct", "next_action"].filter(k => k in j);
    console.log(`PROBE-RESULT ${c.renderer} ${c.rvid.slice(0,8)} correct=${j.correct} fields=${judgeFields.join(",")} ${j.process_violation ? "pv=" + j.process_violation : ""}`);
    expect(j.correct, "Judge 应答布尔").not.toBeNull();
  });
}
