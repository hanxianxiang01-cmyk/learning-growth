# SAFE-01 真实库终查、风险定级与发布兼容性裁决（审计收官 · 2026-10-13）

**性质**：本文件是 `SAFE01_AUDIT.md` 的证据补充与风险重新定级记录，并入 docs/43 审计线，不另立新文档、不变更 V1.2 架构基线。
**核验人**：我方复审（真实 RDS + d0c172c 源码交叉核验，2026-10-12~13）。

## 1. 审计结论（最终记录）

| 审计项 | 最终结论 |
|---|---|
| 发布题库 | 175 题 published；`workspace.config.expected_answer` 与 `workspace.config.answer` **jsonpath 精确双键扫描均 = 0**（原审计仅查 `expected_answer`，本轮补齐 `answer` 分支——原版 `getRendererEvaluator` 实际取 `config.expected_answer ?? config.answer`） |
| 历史 Attempt | **1879/1879 条 response 均携带 `evaluation` 字段，全部 `status=NOT_EVALUATED`**（无任何一条含标准答案值） |
| 标准答案暴露 | 已检查数据面（发布配置+历史报文+源码种子）中**未发现已发生的答案回传实例**；风险=条件性触发路径，未来入库携带该键即活 |
| Judge 权威性 | `submit_attempt` 判分= `ResourceVersion.content.answer` × `response.answer.value`（DB 源）；客户端 evaluation 不参与最终 correct——源码与假 DB 双确认 |
| SAFE-01 定级 | **P2 纵深防御**（不再按事故处理）；出站净化方向批准，独立小 PR 实施，不阻断其他研发 |
| 幂等兼容 | **零泄漏 ≠ 零兼容**：净化删的是整条 evaluation 字段、1879 条历史全量携带 → 新旧版本提交 body 必然不同 → 同 `submission_id` 跨版本重试可触发 409（`api/learning.py` L97-99 SubmissionConflict 属实）。发生仍需"旧版已落库→响应丢失→升级后重试"特定时序，**低频发布兼容风险，非数据事故** |
| Router（双实现） | 设计前置**验收通过**：per-renderer flag（默认全 legacy）+ `TaskRendererImplementationBoundary` 任务生命周期锁定=V1.2 批复要求的单 Renderer 回滚机制兑现；R04=number-input 试点。**正式运行验收未完成**：其余 18 个未接第二实现、真实 React18/Next14 切换、刷新任务恢复、已运行 Kernel 任务的部署回滚均待 E1/E2 验证。**不另造 Router** |

## 2. 修复任务与审计结论的完成边界（不得混标）

**审计已完成（可标 PASS）**：发布配置双键精确扫描；历史 Attempt 字段核验；Judge 数据源确认；409 机制源码核验；契约检查脚本冲突定位（`check-v14-contracts.mjs` L25 断言 `adapter.includes("getRendererEvaluator")`——净化 PR 必炸该检查，属**待淘汰行为的存量锁**；CI 四门禁不含此脚本，独立 `v1.4:contracts:check`）。

**仍需开发及验收（不得因评审批示而标 PASS）**：
- 契约检查 L25 改目标（保 `buildRendererEvidence`/`stableSubmissionId`/attempt_no 依赖即 L26/L27 不动；新断言=保 Evidence+RuntimeStatus、禁注入判分声明与答案字段），加**真实序列化正反例**（不再源码字符串搜索）；
- 异常路径统一净化：`if (!declared) return w` 与 `catch { return w }` 两处直返可绕过剥离——安全字段剔除移到全分支公共路径，配一条故意触发异常分支的测试；
- 跨版本同 `submission_id` 重试回归（真实 QA 库时序复现）；
- 发布规程：**遇 409 不得丢弃提交、不得盲目重发**——先核实原提交是否已落库（GET attempts/session result），防止儿童重复作答或学习记录丢失；排空窗口内保留旧版出站行为。

## 3. 原 SAFE01_AUDIT「BLOCKED」状态更新

原 §5 生产启用 BLOCKED 的前置 1/2（快照平台）**降级取消**，代之以轻量排空纪律（上表规程）；前置 3（真实 QA 复现重试）与前置 4/5（存储与入站扫描）**本轮已由 §1 双键+历史核验闭环覆盖**。净化 PR 本身无生产泄漏面（175 题双键=0），合入即常规 P2 修复，**无需等 MIK K 批**。

## 4. 正式批复记录

> SAFE-01／Renderer Router 技术 Spike **有条件通过**。
>
> SAFE-01 经真实数据库核验（175 题发布配置双键零命中、1879 条历史全量 NOT_EVALUATED），未发现已发生的标准答案字段暴露实例，风险定级调整为 **P2 纵深防御**。出站净化补丁批准作为独立修复实施，合入前须完成：异常分支公共路径净化、`check-v14-contracts.mjs` L25 改目标+真实序列化断言、跨版本同 ID 重试回归与 409 处置规程。
>
> Renderer 双实现路由**设计前置验收通过**，R04 试点保留；其余 18 个 Renderer 不据此视为迁移完成，正式运行验收（真实切换/任务恢复/部署回滚）待 E1/E2。K1 进入正式集成以 **FE-1445 工程基线 PASS** 为前置条件。
>
> **V1.2 继续为 Math Interaction Kernel 与 19 Renderer 一体化改造的正式实施基线，不升 V1.3。**

## 5. 执行顺序（裁决定版）

1. **SAFE-01 独立 PR**（净化收口+检查更新+回归）——P2，不阻断他线；
2. **FE-1445 工程基线**——锁定依赖 Typecheck / Build / 真实 QA 学习链路（当前最大阻碍）；
3. **Router 运行验收**——真实 React 双实现切换、任务锁定、回滚；
4. **K1 正式合入**——前置=FE-1445 PASS + Kernel 集成测试。
