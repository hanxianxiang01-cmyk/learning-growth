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

## 2. Vertical Gate 判定标准（G1–G9）

| Gate | 必须满足 | 现状 |
|---|---|---|
| G1 Renderer | 真实页面出现 column-arithmetic，不降级 | ✅ TaskRenderer V2 分流 + 后端 `_v2_assignable` 门控 |
| G2 Workspace | 输入/进位/undo/reset 形成稳定 present | ✅ rendererRuntime 已具备，待浏览器点击复核 |
| G3 Response | TaskResponse 每次变更同步 workspace 数据 | ✅ onResponseChange 链路在，待 payload 断言 |
| G4 Submit | V2 envelope 字段完整 | ✅ v2AttemptAdapter，待联调复核 |
| G5 Correct | 正确答案得到正确 AttemptResult | ✅ API 实证通过 |
| G6 Wrong | 错误答案可提交并产 diagnosis/next_action | ✅ **API 实证通过（P0 必须）** |
| G7 Retry | attempt_no 递增，上一轮 evidence 不丢 | ✅ API 实证：attempt 1→2，单Task单证据不覆盖 |
| G8 Revision | ui_revision 变化后 Workspace 不串题 | ✅ 组件有 RESET effect，待浏览器复核 |
| G9 Regression | V1 number-input/object-counter/bar-model/number-line 不回归 | ✅ check-v13/v14 PASS，50 题 V1 零变化 |

## 3. E2E 场景矩阵（§7）关键用例

| ID | 场景 | 期望 | 级别 | 状态 |
|---|---|---|---|---|
| B5-E2E-01 | 正确 75 提交 | POST 成功 correct=true → COMPLETE/NEXT | P0 | ✅ API 级 |
| B5-E2E-02 | 错误 65 提交 | POST 成功 correct=false → RETRY/HINT | P0 | ✅ API 级（门禁解除后可达）|
| B5-E2E-03 | 只填个位 5 | 不可提交、不生成 attempt | P0 | 待浏览器 |
| B5-E2E-07 | 提交后快速重点 | 仅一个 attempt（防重入）| P0 | 待浏览器 |
| B5-E2E-08 | ui_revision 变化 | Workspace 重置不串题 | P0 | 待浏览器 |
| B5-E2E-09 | 下发 column-arithmetic V2 | 渲染 B5 不出现 number-input | P0 | ✅ 组件+门控 |
| B5-E2E-04/05/06/10 | 进位事件/撤销/重置/双皮肤 | 结构一致仅视觉不同 | P1 | 待浏览器 |

## 4. 任务拆分与进度

| 任务 | 内容 | 优先级 | 状态 |
|---|---|---|---|
| FE-1403-P0-01 | 修复 B5 提交门禁（FAIL 可提交）| P0 | ✅ **DONE（#36）** |
| FE-1403-P0-02 | 固定 B5 V2 fixture + HTTP 拦截 | P0 | mock 已有 mock-rel-v2-column-1；E2E harness 待建 |
| FE-1403-P0-03 | 真实 MathLearningScreen E2E | P0 | ⬜ 待浏览器 harness |
| FE-1403-P0-04 | Workspace→TaskResponse→HTTP body 校验 | P0 | 🟡 API 级已过；浏览器 payload 断言待做 |
| FE-1403-P0-05 | 错误 attempt→diagnosis→retry 校验 | P0 | ✅ API 级（B5-E2E-02/07 后端半）|
| FE-1403-P0-06 | ui_revision reset / no stale | P0 | ⬜ 待浏览器 |
| FE-1403-P1-01 | undo/reset/双皮肤回归 | P1 | ⬜ 待浏览器 |
| FE-1403-GATE | 更新状态、关闭 Vertical Gate | P0 | 🟡 API 链路 GREEN；浏览器 E2E 通过后 CLOSED |

## 5. 本轮明确不做（§13）

不扩其余 18 个 planned Renderer / 前端不做能力等级·诊断码·mastery / 不把 B5 判断逻辑前置到 UI 权威 / 不为 E2E 改协议 ID / 不新增字段绕过 TaskResponse→MathResponse V2 适配层。

## 6. 结论

B5 后端纵向链（G1–G9 的 API 半）已 GREEN，P0 提交门槛已解除。**FE-1403 Vertical Gate 关闭的最后条件**：真实浏览器 E2E（P0-03/04/06 + 双皮肤 P1）跑通。方案 §15 认同：先停止扩 Renderer 数量，把这一个纵向切片用浏览器 E2E 钉死，B5 才具备作为其余 Renderer 扩展模板的资格。
