# B5 真实页面 E2E Vertical Gate —— 验收合同与进度

> 依据《V1.4 B5 真实页面 E2E + Workspace/Response 联调方案》（FE-1403｜column-arithmetic Vertical Slice Gate，2026-10-04）。
> 本文件是 FE-1403 关闭的判定基准。B5 缺的不是 Renderer，是「真实闭环证明」。

## 0. 核心原则（不可违背）

1. 前端可展示「完成/再检查」，但**不得替后端做能力等级判断**。
2. **错误答案必须能提交**——错误尝试本身就是 Diagnosis/Evidence 的输入。
3. Workspace 存可审计交互状态与事件；Response 负责转成稳定提交契约。
4. V2 renderer **不允许静默降级**为 V1 number-input。
5. 真实页面 E2E 是 Vertical Gate，**不以纯函数测试替代**。

## 1. P0 提交门槛（已修复 ✅）

**缺陷（指控属实）**：`ColumnArithmetic.tsx` 提交按钮原为 `disabled={disabled || evaluation.status !== "PASS"}`——FAIL 被前端拦死，错误答案永远到不了后端，Diagnosis/Retry/Evidence 链无法验证。

**修复（FE-1403-P0-01，PR #36）**：白名单口径——

| Evaluator 状态 | UI | 允许提交 |
|---|---|---|
| EMPTY / PARTIAL | 提示继续填写 | 否（`numericAnswer` 未满 → answer 空）|
| PASS | 完成 | 是 |
| FAIL | 再检查一次 | **是**（本 PR 解锁）|
| INVALID | 输入非法 | 否 |
| SUBMITTING | 禁用交互 | 否（页面级 disabled）|

第二道门槛 `isTaskResponseReady` 只看结构（answer 非空 + v2_workspaces 非空）、不看对错，无需动。

**API 级闭环实证**（真实后端 B5 题 47+28）：
- `attempt_no=1` 答 65 → `correct=False` → `next=HINT`（错误证据入库；diagnosis=None 为 FE-1406 合法 NULL）
- `attempt_no=2` 答 75 → `correct=True` → `next=NEXT_TASK`

## 2. Vertical Gate 判定标准（G1–G9）——2026-10-04 浏览器 E2E 全绿

| Gate | 必须满足 | 现状 |
|---|---|---|
| G1 Renderer | 真实页面出现 column-arithmetic，不降级 | ✅ **浏览器实证**（E2E-09 PASS）|
| G2 Workspace | 输入/进位/undo/reset 形成稳定 present | ✅ **浏览器实证**（E2E-03/P1 事件用例 PASS）|
| G3 Response | TaskResponse 每次变更同步 workspace 数据 | ✅ **浏览器实证**（payload 断言 PASS）|
| G4 Submit | V2 envelope 字段完整 | ✅ **浏览器实证**（E2E-02 内 envelope 全字段断言）|
| G5 Correct | 正确答案得到正确 AttemptResult | ✅ **浏览器实证**（E2E-01 PASS）|
| G6 Wrong | 错误答案可提交并产 diagnosis/next_action | ✅ **浏览器实证**（E2E-02 PASS：65→correct=false→HINT）|
| G7 Retry | attempt_no 递增，上一轮 evidence 不丢 | ✅ **浏览器实证**（E2E PASS：1→2 递增、correct=true）|
| G8 Revision | ui_revision 变化后 Workspace 不串题 | ✅ **浏览器实证**（E2E-08 PASS：新题空位不可提交）|
| G9 Regression | V1 number-input/object-counter/bar-model/number-line 不回归 | ✅ **浏览器实证**（G9 用例 PASS：V1 数字题正常判分）+ check-v13/v14 |

**E2E harness**：`apps/child-web/e2e/b5-column-arithmetic.spec.mjs`（Playwright + 系统 Chrome，10 用例全 PASS，50.6s）。
- 真实性：task 由真实后端预取（route 仅钉题重放，task_instance_id 真实存在）；/attempts /hints 全部放行真实后端——满足「不以纯函数/Mock 替代」原则。
- 运行前提：后端 CORS 白名单含 3100/3101（E2E 双皮肤实例，`app/core/config.py` 本轮加入）；跑法见 §5。

**harness 落地时发现并修复的环境缺陷**：E2E 实例端口不在 CORS 白名单 → 浏览器拦截 attempts 响应（POST 实发实返 200、RDS 落库成功，但响应回不到页面）。API 级验证测不出此类问题——这正是 §15「真实页面 E2E 不可替代」的实证注脚。

## 3. E2E 场景矩阵（§7）关键用例——浏览器全部 PASS

| ID | 场景 | 期望 | 级别 | 状态 |
|---|---|---|---|---|
| B5-E2E-01 | 正确 75 提交 | POST 成功 correct=true → NEXT_TASK | P0 | ✅ 浏览器 |
| B5-E2E-02 | 错误 65 提交 | POST 成功 correct=false → HINT | P0 | ✅ 浏览器 |
| B5-E2E-03 | 只填个位 5 | 不可提交、不生成 attempt | P0 | ✅ 浏览器 |
| B5-E2E-07 | 提交后快速重点 | 仅一个 attempt（防重入）| P0 | ✅ 浏览器 |
| B5-E2E-08 | ui_revision 变化 | Workspace 重置不串题 | P0 | ✅ 浏览器 |
| B5-E2E-09 | 下发 column-arithmetic V2 | 渲染 B5 不出现 number-input | P0 | ✅ 浏览器 |
| B5-E2E-04/05/06/10 | 进位事件/撤销/重置/双皮肤 | 结构一致仅视觉不同 | P1 | ✅ 浏览器（事件用例 + 3101 healing 实例）|

## 4. 任务拆分与进度

| 任务 | 内容 | 优先级 | 状态 |
|---|---|---|---|
| FE-1403-P0-01 | 修复 B5 提交门禁（FAIL 可提交）| P0 | ✅ **DONE（#36）** |
| FE-1403-P0-02 | 固定 B5 V2 fixture + HTTP 拦截 | P0 | ✅ DONE（真实后端预取 + route 钉题重放）|
| FE-1403-P0-03 | 真实 MathLearningScreen E2E | P0 | ✅ DONE（10 用例浏览器全 PASS，50.6s）|
| FE-1403-P0-04 | Workspace→TaskResponse→HTTP body 校验 | P0 | ✅ DONE（E2E-02 envelope 全字段断言 PASS）|
| FE-1403-P0-05 | 错误 attempt→diagnosis→retry 校验 | P0 | ✅ DONE（E2E-02 + G7 浏览器 PASS）|
| FE-1403-P0-06 | ui_revision reset / no stale | P0 | ✅ DONE（E2E-08 浏览器 PASS）|
| FE-1403-P1-01 | undo/reset/双皮肤回归 | P1 | ✅ DONE（事件用例 + 3101 healing 实例 PASS）|
| FE-1403-GATE | 更新状态、关闭 Vertical Gate | P0 | ✅ **CLOSED**（10 用例浏览器全 PASS）|

## 5. 本轮明确不做（§13）

不扩其余 18 个 planned Renderer / 前端不做能力等级·诊断码·mastery / 不把 B5 判断逻辑前置到 UI 权威 / 不为 E2E 改协议 ID / 不新增字段绕过 TaskResponse→MathResponse V2 适配层。

## 4.1 运行方式（E2E harness）

```bash
# 前置：后端 :8000 运行（CORS 白名单需含 3100/3101）
cd apps/child-web
# 双实例（exploration-lab 默认 + healing）：
#   NEXT_PUBLIC_CHILD_MATH_SKIN=exploration-lab npx next dev -p 3100
#   NEXT_PUBLIC_CHILD_MATH_SKIN=healing         npx next dev -p 3101
E2E_WEB_BASE=http://127.0.0.1:3100 E2E_HEALING_BASE=http://127.0.0.1:3101 npm run e2e
```

## 6. 结论

**FE-1403 B5 Vertical Gate：CLOSED（2026-10-04）**。10 个浏览器 E2E 用例（含 §3 全部 P0 + P1 事件/双皮肤）全 PASS，G1~G9 九项全部转为浏览器实证。运行前提：后端 CORS 白名单含 E2E 双实例端口（本轮加入）。

**harness 落地抓到的真实缺陷**（API 级验证测不出）：E2E 实例端口不在 CORS 白名单 → 浏览器拦截 attempts 响应（后端实际返回 200、RDS 落库成功，但响应回不到页面）。这正是方案 §15「真实页面 E2E 不可替代」的实证注脚。

**B5 模板成立**：纯函数层 → 组件（双皮肤）→ V2Renderer 分流 → seed/mock 链题 → check/E2E 脚本 → implemented 前后端同步翻转——18 个 planned Renderer 可按此模板批量推进。
