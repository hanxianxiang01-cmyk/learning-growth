// FE-1422a：QA 确定性钉题（替代"循环抽题碰 band 运气"的旧 buildTaskPool）。
//
// 流程（docs/governance/QA_PINNED_TASK_PROPOSAL.md 方案 A）：
//   1. GET /v1/content/v2-catalog → 按 renderer 找到 published V2 资源的 resource_version_id；
//   2. 每个需要的 task：新 session + POST /tasks/next { pin_resource_version_id }
//      —— 服务端硬校验仅 QA child 可用，绕过 fit_band/session 排除，确定性 100%；
//   3. 返回 [{ task, sessionId }]，task_instance_id 真实存在，提交/判分链路与生产一致。
//
// 旧机制作废原因：QA child 每轮 E2E 写 attempt → mastery 引擎推 level → band 漂移，
// 抽题命中 = f(band 历史轨迹)，不可复现（2026-10-07 全量回归大面积超时实锤）。
import { request as pwRequest } from "@playwright/test";

let catalogCache = null; // { [renderer]: [resource_version_id, ...] }

/** 查 V2 目录（模块级缓存，一整轮 Playwright 只打一次）。
 *  key = `${renderer}#${mode ?? ""}` —— 同 renderer 多 mode（R10 双金题）可分别定位。 */
export async function loadV2Catalog(api) {
  if (catalogCache) return catalogCache;
  const ctx = await pwRequest.newContext({ baseURL: api });
  try {
    const resp = await ctx.get("/v1/content/v2-catalog");
    if (!resp.ok()) throw new Error(`v2-catalog ${resp.status()}`);
    const items = (await resp.json()).items || [];
    const byKey = {};
    for (const it of items) {
      const key = `${it.renderer}#${it.mode ?? ""}`;
      (byKey[key] ??= []).push(it);
      // 兼容不带 mode 的旧调用：裸 renderer key 聚合所有 mode
      (byKey[it.renderer] ??= []).push(it);
    }
    catalogCache = byKey;
    return byKey;
  } finally {
    await ctx.dispose();
  }
}

/**
 * 确定性取 n 个 V2 task（同一 renderer[+mode]）。
 * @param {string} [mode] 指定 workspace mode（R10 unknown_number / unknown_operator）
 * @returns {Promise<Array<{task:object, sessionId:string, pinned:object}>>}
 */
export async function fetchPinnedTasks({ api, child, renderer, mode, count, catalogIndex = 0 }) {
  const catalog = await loadV2Catalog(api);
  const key = mode ? `${renderer}#${mode}` : renderer;
  const candidates = catalog[key];
  if (!candidates || candidates.length === 0) {
    throw new Error(`v2-catalog 无 renderer=${renderer}${mode ? " mode=" + mode : ""} 的 published V2 资源（先跑 seed_content.py）`);
  }
  const pinned = candidates[catalogIndex % candidates.length];
  const ctx = await pwRequest.newContext({ baseURL: api });
  const tasks = [];
  try {
    for (let i = 0; i < count; i += 1) {
      const session = await ctx.post("/v1/learning/sessions", {
        data: { child_id: child, subject: "math", requested_minutes: 15 }
      });
      const sid = (await session.json()).session_id;
      const resp = await ctx.post("/v1/learning/tasks/next", {
        data: {
          child_id: child,
          session_id: sid,
          subject: "math",
          requested_minutes: 15,
          pin_resource_version_id: pinned.resource_version_id
        }
      });
      const t = await resp.json();
      const ui = t.ui_schema || {};
      const ws = (ui.workspaces || [])[0] || {};
      if (ui.schema_version !== "2.0" || ws.renderer !== renderer || (mode && ws.mode !== mode)) {
        throw new Error(`pin 钉题失败：期望 ${renderer}${mode ? "/" + mode : ""} V2，实得 ${ws.renderer ?? ui.kind ?? "null"}`);
      }
      tasks.push({ task: t, sessionId: sid, pinned });
    }
  } finally {
    await ctx.dispose();
  }
  return tasks;
}

/**
 * FE-1438：直接按 resource_version_id 钉题（绕过 catalog——qa_staged 抽样批不进
 * 公开目录，见 scripts/qa_sample_ingest.py 隔离设计；服务端 pin 路径放行 published+qa_staged）。
 */
export async function pinTaskByRvid({ api, child, rvid }) {
  const ctx = await pwRequest.newContext({ baseURL: api });
  try {
    const session = await ctx.post("/v1/learning/sessions", {
      data: { child_id: child, subject: "math", requested_minutes: 15 }
    });
    const sid = (await session.json()).session_id;
    const resp = await ctx.post("/v1/learning/tasks/next", {
      data: { child_id: child, session_id: sid, subject: "math", pin_resource_version_id: rvid }
    });
    const t = await resp.json();
    if (!t.task_instance_id) throw new Error(`pin 落题失败: ${JSON.stringify(t).slice(0, 200)}`);
    return { task: t, sessionId: sid };
  } finally {
    await ctx.dispose();
  }
}
