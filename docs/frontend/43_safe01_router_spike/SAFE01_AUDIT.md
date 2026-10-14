# SAFE-01｜标准答案出站路径审计与候选净化（基于用户最新仓库）

**状态：SPIKE/候选修复，未合并远端、未部署；不等于生产 SAFE-01 全闭环。**

## 1. 输入事实

- 最新 ZIP：`learning-growth-main (3).zip`，SHA256 `b2a925b76358fdda4164da663599ffeeb4ddb44e3225b90b19fe5b7d12c7f401`，443个文件。
- 与此前V6全量迁移包（529文件）不同：最新ZIP未包含此前的V6皮肤组件、素材及测试，不能将旧包默默混入新基线。
- 当前冻结 `packages/contracts/schemas/math-response-v2.schema.json` 明确写明**客户端不得提交正确率／能力等级／证据角色／诊断结果**；workspace.data 的结构为开放对象。

## 2. 已证实的数据流

`TaskRenderer` 通过 `TaskResponse.v2_workspaces` → `HttpLearningApi.submitAttempt()` → `buildAttemptPayload()` → `enrichWorkspaceData()` → HTTP JSON → FastAPI `/v1/learning/attempts` → `learning.submit_attempt()` → `turn_service.record_attempt(response=...)`。

- 原版 `enrichWorkspaceData()` 调用 `getRendererEvaluator()`，并在 `workspace.data.evaluation` 附带本地评价结果。
- 配置中不存在 `expected_answer` / `answer` 时，评价为 `NOT_EVALUATED`，出站无标准答案。
- **当 Workspace `config.expected_answer` 存在时，原版可重现：`response.workspaces[0].data.evaluation.expected_answer`。** 原版同时出站本地 `status`、`score`。
- 后端 `learning.py::submit_attempt()` 从 `ResourceVersion.content.get('answer')` 取标准答案，读取 `response.answer.value` 为用户答案，**没有使用客户端 evaluation 作最终 Judge**。
- `turn_service.record_attempt` 接收完整 `response` 并保存到 `Attempt.response`；因此标准答案可在条件成立时进入作答记录存储路径。未在真实数据库完成插入核验。
- 源码内 `app/content/resource_seed_v2.py` 中未检出 `expected_answer` 字面量。这个结论**不能代替真实已发布资源表的全量配置扫描**。

## 3. 实测

| 场景 | 原版 | 候选修复后 |
|---|---|---|
| config 不带标准答案 | `evaluation.status=NOT_EVALUATED`、无预期答案 | 不再出站 `evaluation` |
| config 含 `expected_answer=63` | 出站 `evaluation.expected_answer="63"`、分数及本地状态 | 出站 `evaluation` 消失，标准答案路径消失 |
| 请求通过 `HttpLearningApi` | 截取的 `fetch` JSON 明确包含预期答案 | 截取请求不含 `evaluation` |
| 服务端收到伪造客户端评价 | 最终 `correct` 仍按数据库答案与用户答案计算 | 后端未改，权威规则不变 |

> 测试技术：运行真实TS适配器（仅用TypeScript转译的 CJS，在 fetch Stub 截取HTTP序列化报文）；Python导入真实 `submit_attempt()` 用假DB和 `record_attempt` Stub 复现Judge入参。没有生产网络、数据库、账户或儿童数据。

## 4. 候选修复

修改 `apps/child-web/src/lib/api/v2AttemptAdapter.ts`：

- 保留 `evidence`、`runtime_status`、用户作答与必要的工作区状态；
- **移除 transport 阶段注入的整个 `evaluation`**；若已有工作区 data.evaluation，亦不向后端转发；
- 不改 `Response.answer`、`submission_id` 的生成逻辑、服务端 `Judge`、题目内容或冻结的数学语义；
- 修复只能切断当前已复现的 **出站评价字段路径**，不是把 `config.expected_answer` 从客户端题目下发中清除。若线上资源配置真的含标准答案，入站配置暴露仍需独立处理。

## 5. 新发现的发布阻断：跨版本幂等冲突

**已独立复现：同一 Task/attempt/revision 的旧版与新版 `submission_id` 相同，JSON响应体不同。** 后端 `turn_service.record_attempt` 同 ID、不同内容会抛 `SubmissionConflict(409)`。

因此，在实际发布这个候选修复前：

1. 必须确认是否有未完成的旧版提交或可能跨部署重新发出的请求；
2. 通过不可变首次出站请求快照（包括复用原 `submission_id`）或经审核的迁移/排空方案保证重试内容稳定；
3. 在真实 QA 数据库复现“服务端已保存，客户端丢响应 → 部署切换 → 同次重试”，并明确预期结果；
4. 验证 Attempt 存储、日志链路与监控中的敏感评价字段；
5. 真实线上资源 `ui_schema` 的入站字段核查需独立审计，不把源码默认种子等同数据库事实。

**SAFE-01裁决：出站风险真实、候选净化有效，但生产启用 BLOCKED（真实DB、跨部署幂等、已发布内容扫描均待验）。**

## 6. 证据

`evidence/safe01_baseline.json`、`evidence/safe01_candidate.json`、`evidence/safe01_backend.json`、`evidence/safe01_idempotency.json`。测试程序在仓库 `tests/spikes/`，不含真实答案库、凭据或儿童数据。
