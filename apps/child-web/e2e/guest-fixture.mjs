// V1.4 游客模式：E2E 全局夹具。
//
// ## 为什么需要它
//
// 游客模式把身份来源从 `?child_id=` 改成 HttpOnly Cookie。25 个 E2E spec
// 都写着 `?child_id=…0099` —— 那个参数现在**只是被忽略的残留**，身份实际
// 由 Cookie 决定。若不先建立 QA 会话，每个 spec 都会被当成「一个匿名新游客」：
// 数据写进随机新建的身份，`docs/governance/QA_DATA_HYGIENE.md` R1 的
// 「测试流量必须落在 …0099」当场失效，且失败表现是「页面上找不到刚才的题」
// 这种毫无指向性的样子。
//
// ## 做法
//
// 每个测试前调一次 `POST /v1/guest/qa-session`，让后端签发 QA 池会话，
// 浏览器随后所有同域请求都自动带上该 Cookie。spec 里原有的 `?child_id=`
// 保持不动（既不改 25 个文件，也不至于让读代码的人以为身份还在 URL 里，
// 那些注释会在本轮的交付说明里点明）。
//
// ## 前提
//
// 后端必须 `SELECTION_TRACE_ENABLED=true`（qa-session 与 selection-trace
// 共用同一运维开关，生产默认关闭）。E2E 环境本来就需要 trace 端点，
// 故不额外增加配置负担。
import { test as base, request as pwRequest } from "@playwright/test";

const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8000";
export const E2E_CHILD = process.env.E2E_CHILD_ID ?? "00000000-0000-0000-0000-000000000099";

export const test = base.extend({
  // 用 storageState 让 Cookie 在两个端口间共享（3100 页面 / 8000 API
  // 同属 127.0.0.1，Cookie 按 host 匹配、不区分端口，故一次即可）
  storageState: async ({}, use) => {
    const ctx = await pwRequest.newContext();
    const res = await ctx.post(`${API}/v1/guest/qa-session?child_id=${E2E_CHILD}`);
    if (!res.ok()) {
      const body = await res.text();
      throw new Error(
        `QA 会话签发失败（${res.status()}）。请确认后端已设 ` +
          `SELECTION_TRACE_ENABLED=true 且可访问 ${API}。响应：${body}`
      );
    }
    const state = await ctx.storageState();
    await ctx.dispose();
    await use(state);
  }
});

export { expect } from "@playwright/test";