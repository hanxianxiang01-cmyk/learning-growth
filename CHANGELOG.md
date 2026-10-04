## V1.4 Frontend P0

- Renderer Registry：number / object-counter / bar-model / number-line / unsupported。
- Workspace API：能力门控、撤销/重置、Hint 受控 action。
- TaskUISchema：renderer_id / interaction_capabilities / renderer metadata。
- Structured Response：新增 interaction_events。
- HTTP Adapter：AttemptResult / HintResponse normalizer。
- 新增 `/dev/v1.4-qa` 双皮肤契约验证页。
- 合并验收（2026-09-30）：本地补跑 `next build` 通过（交付方执行环境无法装依赖，V14-07 由 REVIEW 转 DONE）；修复 QA 页 fixture 类型标注（TaskResponseSchema）与 check-v14.mjs 非 ASCII 路径解码问题（fileURLToPath）；tsc / check-v13 / check-v14 / governance / release 全过。

# Changelog

所有重要变更统一记录在本文件。

版本规则：

```text
Major.Minor.Patch
```

- Major：架构/产品边界发生重大变化
- Minor：新增完整能力或模块
- Patch：Bug修复、文档、兼容性调整

---


# [Unreleased]

后续开发中的变更先记录在此，正式发版时移动到对应版本号下。

## Fixed（FE-1411 V1 操作题无限渲染循环——用户页面 F12 刷屏，2026-10-04）

> 用户实测发现：`/child/math/session/...`（V1 objects 题）F12 疯狂报 `Maximum update depth exceeded`（718 条/会话）。

- **根因**：`ManipulativeRenderer` 每次渲染 spread 出新的 `schema` 对象传给 `WorkspaceProvider`，而 Provider 以 `[schema]` 为 REINITIALIZE effect 依赖 → 每帧重置 workspace state → `onWorkspaceChange` 回调 → 父级 response 更新 → 再渲染……经典引用不稳定死循环。
- **引入与暴露**：provider 的 schema 重置 effect 是 FE-1401（V1.4 P0）交付引入；V1.3 时代该路径无 effect 不循环，V1 题此前 E2E/冒烟全走 V2 链，**真实用户打开 V1 操作题才暴露**——B5 E2E 10 用例拦不住，需 V1 回归专项（记 QA 待办）。
- **修复**（TaskRenderer.tsx）：`useMemo` 稳定化 `providerSchema`（依赖 [schema, rendererId]）。
- **验证**：无头探针复现 718→1 条（仅 Chrome DevTools 探测 404 噪音）；tsc 0 错；B5 E2E 10/10、check-v13/v14 PASS。

## Done（FE-1410 submission_id 落库迁移：V2 幂等契约入数据库，2026-10-04）

> 关闭 docs/frontend/29 §5-2「V2 资源下发前的后端迁移项」——V1.4 规模化前最后一笔 DDL 技术债。

- **DDL 迁移**（真实运行库已执行，幂等可重跑）：`scripts/migrate_submission_id.py` —— `attempt` 加 `submission_id uuid` 列 + partial 唯一索引 `uq_attempt_submission_id`（`WHERE submission_id IS NOT NULL`，尊重 V1 可空）。
- **双轨幂等**：`turn_service.record_attempt` 带 submission_id 走权威轨（同 ID 同内容→重放原 Attempt；同 ID 异内容→`SubmissionConflict`→API 409），无 submission_id 回落 `(task_instance_id, attempt_no)` 旧轨（**V1 行为零变化**）。API 层解析 submission_id + 409 映射（SubmissionConflict 先于 ValueError 捕获）。
- **幂等段重构**：抽 `_replay_shape()` 供双轨复用（首发/重放同外形规则，V2 完整三段判定不外发）。
- **防漂移单测** `tests/test_submission_id.py`（+3，不依赖 DB）：列可空/类型 UUID、partial unique 索引、SubmissionConflict 继承关系。后端 72→**75 passed**。
- **五轨实证**（真实后端+RDS）：A V2首发200 / B 同ID同内容重放同attempt_id / C 同ID异内容**409** / D 无submission_id旧轨200 / E DB层唯一索引拦住重复插入。
- **harness 缺陷根治**（E2E-10 暴露）：双 dev 实例共享 `.next`，皮肤 `NEXT_PUBLIC_*` 编译期内联互相覆盖 → `next.config.mjs` 加 `distDir: NEXT_DIST_DIR`，`.gitignore` +`.next-*`；双实例隔离后 B5 E2E **10/10 PASS**。
- **基线纪律**：权威 `01_schema_postgresql_v1.3.1.sql` 未改（SHA256 冻结物）；V2 挂入 = V1.4 基线立版动作（docs/29 §6）。

## Merged（FE-1409 V1.4 Frontend Development Package：18 个 V2 Renderer 组件交付，2026-10-04）

> 交付来源：《V1.4_Frontend_Development_Package.zip》（基线=main@66f374c 含 P0-01，缺 E2E harness #39，合并时无回退）。

- 前端：`V2RendererLibrary.tsx` 统一基座（232 行：useRendererState 共享状态/事件/revision 隔离 + answer 提取）承载 **18 个 V2 组件**（choice-grid/place-value/ten-frame/array-board/grouping-board/formula-board/estimation-canvas/shape-gallery/shape-canvas/sorting-board/direction-grid/ruler/clock/timeline/money-board/data-table/pictograph/pattern-board）；每组件独立入口文件；TaskRenderer V2 路由全接线；registry 18 项 planned→implementedV2；globals.css 追加 renderer 样式（超集）。
- 后端同步：renderer_protocol 23 协议全部 implemented（附 assert 23/23）；`_v2_assignable`/`check_assignable` 职责收敛为「协议外/哨兵拒绝」；3 处测试基准同步（planned 拒绝样例改 hologram-board/unsupported）。
- 合并时修复：MoneyBoard `next` 缺索引签名（TS7053，交付方依赖层未暴露）——tsc 清零。
- check 新增：`scripts/check-v14-renderers.mjs`（23/23 协议、18 V2 + 4 复用路由/基座/入口齐检）。
- 诚实口径（写入 28 号文档）：**implemented = 前端可渲染不降级 ≠ 已过 B5 式 Vertical Gate**——各组件 mode 字段级 Schema（docs/29 §5-1）、链题、独立 Evaluator（四态）、undo/history、浏览器 E2E 按 B5 模板逐个补齐；23/23 全放行下发后，内容侧发布仍需 Vertical Gate 证据。
- 验证：tsc 0 错、next build ✓ 9 routes、check-v13/v14/fe1403-b5/v14-renderers/governance 全过、后端 72 passed。

## Closed（FE-1403 B5 Vertical Gate CLOSED：浏览器 E2E harness 落地，2026-10-04）

- 新增 Playwright E2E harness：`apps/child-web/e2e/b5-column-arithmetic.spec.mjs` + `playwright.config.mjs`（系统 Chrome，`npm run e2e`）；**10 用例全 PASS（50.6s）**——§7 场景矩阵 P0（01/02/03/07/08/09）+ P1（事件模型/双皮肤 3101）+ G9 V1 回归。
- 真实性：task 由真实后端预取（route 仅钉题重放、task_instance_id 真实），attempts/hints 全放行真实 RDS——满足「不以纯函数/Mock 替代」（原则5）。
- **harness 抓到 API 级测不出的真实环境缺陷**：后端 CORS 白名单缺 E2E 实例端口 → 浏览器拦截 attempts 响应（后端 200/RDS 落库均正常，但响应回不到页面）。修复：`app/core/config.py` cors_origins 增补 localhost/127.0.0.1 的 3100/3101（本地 dev 端口，安全边界不变）。
- G1~G9 九项全部转浏览器实证；FE-1403-P0-02~06 + P1-01 DONE；Gate 判定文档（B5_E2E_VERTICAL_GATE.md）§2/§3/§4/§6 同步收口，PROJECT_STATUS FE-1403-B5 → **Vertical Gate CLOSED**。
- 附带修复两处 harness 逻辑（非产品缺陷）：G7 撤销步骤误撤十位致第二次答错；G9 选择器从 placeholder 改稳定 `#math-answer` + 能力从 app_strat（全表征必填题）改 app_cond（6 道纯数字题，已核 repr_required=false）。
- 后端回归 72 passed（CORS 改动后）；.gitignore 补 test-results/playwright-report。
- **B5 模板成立**：纯函数层→组件双皮肤→V2Renderer 分流→链题→check/E2E→implemented 翻转——18 planned Renderer 按此批量推进。

## Fixed（FE-1403-P0-01 B5 提交门禁解除，2026-10-04）

> 依据《B5 真实页面 E2E + Workspace/Response 联调方案》§3/§14。

- **P0 缺陷修复**：ColumnArithmetic 提交按钮原 `disabled={... || evaluation.status !== "PASS"}`——错误答案（FAIL）被前端拦死、永远到不了后端，Diagnosis/Retry/Evidence 链无法验证。改为白名单：PASS/FAIL 可提交，PARTIAL/EMPTY 与 INVALID 不可（§3 门槛表）。Evaluator 降级为纯 UI 即时反馈。
- API 级闭环实证（真实后端 47+28）：attempt1 答 65 → correct=False → HINT；attempt2 答 75 → correct=True → NEXT_TASK。
- 存档 `docs/governance/B5_E2E_VERTICAL_GATE.md`：FE-1403 关闭判定基准（G1–G9 + 场景矩阵 + 任务进度）。
- 进度：P0-01/05 DONE（API 半）；G1–G9 后端纵向链 GREEN；FE-1403 Vertical Gate 关闭剩浏览器 E2E（P0-03/04/06 + P1 双皮肤）。

## Merged（FE-1408 V2Renderer 接 number-line + mock A5 同步，2026-10-03）

- numberLineV2.ts：V2 数轴纯函数层（state/applyJump/endpointAnswer/serialize），数据形态对齐 FE-1405 A5 链 E2E 已验证的 `data.jumps=[{jump_id,from,to}]`；未跳步不给答案（endpoint 空提交禁用）。
- NumberLineV2.tsx：V2 数轴组件——复用 rendererRuntime（undo/reset/events），写回 v2_workspaces + answer=终点值；刻度由 config.scale 驱动（0~50 步长5），start_marker 提供起点。
- TaskRenderer V2Renderer 加 number-line 分支（A5 链浏览器可玩，FE-1407 遗留解锁）。
- mock taskBank 插入 mock-rel-v2-line-1（与后端 resource_seed_v2 A5 题同源：20 起步每次 +5 跳 3 次 = 35，d3）；FE-1407「A5 暂不入 mock」限制随之解除。
- 验证：tsc 0 错、next build ✓、check-v13/v14/fe1403-b5 PASS。

## Merged（FE-1407 mock 同步 V2：B5 column-arithmetic 演示题，2026-10-03）

- mock taskBank 首位插入 `mock-rel-v2-column-1`：完整 V2 TaskUISchema（schema_version 2.0 / workspaces / column-arithmetic / mode addition / response_contract），与后端 resource_seed_v2 B5 链题同源（47+28=75，d4）；mock 模式可直接体验竖式 V2 渲染链。
- 零新增代码路径：复用 v2AttemptAdapter V2 信封、TaskRenderer V2 判别分流、hintUiAction V2 守卫；判分沿用 extractAnswer(answer) 口径（组件写入 answer，与后端 answer.value 语义一致）。
- 有意不做：A5 number-line 不入 mock——V2Renderer 尚未接 number-line 视图，接入会显示"开发中"卡（不用 unsupported 掩盖，契约 §24）；V2 链就绪后再同步。
- 验证：tsc 0 错、check-v13/v14/fe1403-b5 PASS、CI 四绿（PR #33）。

## Merged（FE-1403 B5 column-arithmetic 前端切片 + Gate B5 E2E，2026-10-03）

> 交付来源：《V1.4 FE-1403 Renderer Implementation Contract》+ zip（基线含 FE-1405；交付方 FE-1406 未入包，合并时 backend 诊断五文件不取，main 版本保留）。

- 前端：rendererRegistry 23 协议全注册+implemented 分层；columnArithmetic（State/Reducer/Serializer/Evaluator：PASS/PARTIAL/FAIL/INVALID）；ColumnArithmetic 竖式组件（双皮肤）；TaskRenderer V2 判别分流；V2TaskUiSchema 判别联合；v2_workspaces→MathResponse V2 信封。
- 后端：renderer_protocol column-arithmetic planned→implemented（前后端分层同步）；3 处门控测试基准同步改用 ruler/data-table；B5 链题（47+28=75 竖式 before_after d4）seed 入库。
- 合并时修复交付方 6 处 tsc 错误（重复 import / 判别守卫 / places 类型）——交付方依赖层缺失暴露，补跑清零。
- 验证：tsc 0 错、next build ✓、check-fe1403-b5/v13/v14/governance ✓、后端 72 passed；**Gate B5 真实 API E2E 5 步全 PASS**（V2下发→竖式判分→单task单证据→重试不覆盖→Mastery回写）。
- Gate 状态（§25 口径）：A5 GREEN · B5 API链路 GREEN/浏览器待人工 · D5/E4/F6 RED。

## Added（FE-1406 诊断 V2：三段判定、无证据不猜，2026-10-03）

> 评审 V0.2 步骤 3：`diagnosis.py` 移除"无证据兜底"与"第一条错因"推断（§4.1 点名问题）。

- `DiagnosisV2`：观察(observations+field_path) → 候选(candidates: tag/rule_id/rule_version/evidence_paths) → top_level_code；**NULL 是合法结论**（证据不足不冒充已判断，status=observation_only）。
- **删除 `_fallback_by_hints`**：答错但无观察支持任何资源规则 → 不再猜 E01/E05；hint 依赖度不再决定错因。
- **删除"error_models[0] 即结论"**：资源全部错因规则作为候选来源，仅当观察命中规则触发条件才形成候选（V1 建模观察=required 表征缺失；V2 观察=空工作区无过程数据）。
- `correct=None`（未评分）不判：评分故障走工程异常，不写儿童数学误解（评审判定表行4）。
- 多候选并存 → top_level_code 保持 NULL（"存在其他合理解释"不强选）。
- 对外响应只暴露有码结论（response_shape：无码时 diagnosis=None，不给儿童猜测标签）；LearningEvent 保留 V2 完整三段判定（审计 + 未来 confirmed 聚合）。幂等重放同规则。
- confirmed 状态**保留值位不启用**：判定条件（跨资源跨session+反例排除）按评审 §6 属待校准 OPEN 项。
- `session_result.py` 诊断汇总兼容 top_level_code 与 V1 历史事件 code；`/v1/diagnosis` 独立端点经兼容层。
- 测试重写 +15（NULL 合法/兜底移除实证/观察驱动/兼容外形/hint 不变），后端 71 passed；API 冒烟实证：答错无观察 diagnosis=None、V2 空工作区→E05 候选成立。
- E01~E07 语义与 LE-* 分离不变；tag→观察匹配表为保守缺省，正式标签字典待内容/教学规则审定进 ADR（评审 §6）。

## Added（FE-1405 A5 纵向链端到端打通，2026-10-02）

> V2 契约从"可执行 Schema"推进到"真实链路端到端可跑"：第一条 implemented renderer（number-line）的 V2 题完成 下发→渲染→提交→判分→幂等 全链验证。

- `app/content/resource_seed_v2.py`：V2 纵向链资源独立文件（`ui_schema_version:"2.0"` 显式声明 + context_family canonical），首批 1 题（A5 数轴跳步，d3，before_after）。
- `seed_content.py`：按 `ui_schema_version` 分流构建 V1/V2 ui_schema；`_build_ui_schema_v2` 产出经 `validate_ui_schema_v2` 契约验证（CI 单测自证）。
- `learning.py`：查询期 V2 下发门控 `_v2_assignable()`——planned renderer 受控拒绝（不降级）；V2 提交判分提取 `answer.value`（V1 标量行为不变）。
- 前端：`taskUiSchemaNormalizer` 增加 V2→渲染视图转换（number-line/object-counter 映射到现有控件，携带 ui_revision/response_type/workspace_id 元数据）；新增 `v2AttemptAdapter`（按 MathResponse V2 信封构造提交报文，含 submission_id=uuid）；`http.ts submitAttempt` 接收可选 task 分流 V1/V2 payload。
- E2E 验证（真实 RDS + API）：V2 题入库契约 PASS → 下发 PASS → 错误提交判错(HINT) → 正确提交判对 → 重放幂等 PASS。
- 测试 +7（门控 4 例、seed 产物契约 2 例、answer 标量 1 例），后端 65 passed；tsc/check-v14 PASS。
- 存量 50 题 V1 行为零变化（门控只拦 V2-planned）。

## Added（FE-1404 TaskUISchema V2 + MathResponse V2 可执行契约，2026-10-02）

> 评审 V0.2 步骤 2 后半：契约从 V0.1 草案推进为可执行 Schema（冻结候选，待会签）。

- `packages/contracts/schemas/`：draft 2020-12 可执行 JSON Schema 两份（TaskUISchema V2 / MathResponse V2，全节点 `additionalProperties:false`——客户端自评字段机器级不可提交）。
- `packages/contracts/contracts/validate.py`：三层校验（schema→FE-1403 协议枚举→语义层：workspace_id 唯一/sequence 唯一/is_implemented 下发分层，planned 受控拒绝不降级）。
- `samples/`：五条纵向链全量合法样例（B5/A5/D5/E4/F6）+ 反例3组（renderer 别名/重复 workspace_id/客户端自评）+ `examples/` 带 interaction_events 全量 Attempt。
- 测试 +9（含 schema enum 与 renderer_protocol 代码枚举防漂移同步检查），后端 58 passed。
- `docs/frontend/29`：语义口径 + submission_id 幂等契约 + 待冻结清单 7 项（mode 字段级 Schema、submission_id 落库、TS 镜像、权威 OpenAPI 挂入=V1.4 基线立版动作）。
- pyproject dev 依赖 + jsonschema。
- 本期不动权威 OpenAPI（V1.3.1 冻结基线，ui_schema/response 为自由 object，V2 向后兼容不违反）。

## Added（FE-1403 Renderer Registry Contract 协议冻结，2026-10-02）

> 依据《V1.4 P0 Architecture Contract》P0-01 + 评审 V0.2 §3.1：冻结 23 个 Renderer 的 kebab-case 协议枚举与分流规则。

- `docs/frontend/28_RENDERER_REGISTRY_CONTRACT.md`：协议冻结文档——23 枚举（R-001~R-023，含来源/实现状态分层）、V1/V2 分流规则、V2 硬约束清单、unsupported 哨兵不入协议面、Registry 12 字段交付节奏。
- `app/content/renderer_protocol.py`：机器可读镜像 + `validate_renderer_id()`（UNKNOWN_RENDERER_ID 拒绝）+ `is_implemented()`（协议合法≠可下发，planned 受控拒绝）。
- 测试 +5（枚举冻结23/命名映射自检/非法拒绝/哨兵排除/implemented 分层），后端 49 passed。
- 前端 `rendererRegistry.ts` 补注释锚定协议事实源（行为零改动）。

## Added（V1.4 P0 Governance Closure：context_family 受控词表 + 50题回填，2026-10-01）

> 依据《V1.4 P0 Governance Closure》与《V1.3评审》§7：把 context_family 从自由文本升级为「受控词表 + 数据入口校验 + Engine 消费契约」。同时关闭 Gate 0 残留前置之一（L2→L3 生产可达性）。

- `docs/governance/CONTEXT_FAMILY_VOCABULARY.md`：受控词表唯一事实源（AC-01）——6 启用族（school_objects/comparison/before_after/lineup_position/shopping/time_schedule）+ 定义/正反例/分类优先级规则 + 扩展协议（§10）+ 50 题分类明细。
- `app/content/context_family.py`：Seed Validation（AC-02）——trim→canonical→lookup，非法值 `UNKNOWN_CONTEXT_FAMILY` 拒绝；`everyday_objects` 未批准前亦拒。
- `app/content/context_family_map.py`：50 题 stem→family 映射（AC-04）——PASS 44 / REVIEW 6（日常物品无 canonical 族，留 NULL 不硬猜）/ REJECT 0。
- `seed_content.py`：mastery_rule 从写死 None 改为按映射生成（入口强校验）；`turn_service` 写证据时从 `resource_version.mastery_rule.context_family` 读取并写入证据列（唯一来源冻结）。
- 存量回填执行：50 题 mastery_rule 已回写 + 31 条历史原子证据 context_family 已补齐（幂等脚本）。
- 硬性检查（§7）：迁移题覆盖 comparison×2 + before_after×2 → **L2→L3 transfer diversity（≥2族）生产可达路径打通**；lineup/shopping/sharing 启用但零覆盖如实记录（待内容补题）。
- Transfer Regression（AC-05）：同族×2→insufficient、异族×2→数值，引擎判定按 canonical 计数验证通过。
- Engine Decoupling（AC-06）：核验 mastery.py 无族名分支，仅 distinct 计数——已满足。
- DDL 不变（§9）：varchar(64) 保持、不加 CHECK；职责四分离。
- 测试：新增词表校验 3 用例（拒绝非法值/50题覆盖/迁移族数），后端 44 passed。

### 待裁决（REVIEW 6 题，需产品/内容确认）

- 是否按 §10 扩展协议正式新增 `everyday_objects` 族（气球/玩具车/水果/球/玻璃珠/杯子 6 题）；批准前其 context_family 保持 NULL，不参与 transfer 计数。

## Added（Session Result 契约写入权威 OpenAPI，2026-09-30）

> DRIFT-001 收口：权威 OpenAPI 此前缺少 Session Result endpoint，前端一直靠可配置 Path + Normalizer 过渡。

- 权威 `02_openapi_v1.3.1.yaml` 补 `GET /v1/learning/sessions/{session_id}/result` 及 `SessionResult` / `AbilityChange` / `LearningBehavior` / `NextRecommendation` / `DiagnosisSummaryItem` schema。
- 顺带补齐 `MasteryDecision.decision` 枚举：`collect_evidence` / `recovering`（后端已在用，此前 yaml 漏同步）。
- 前端 `config.ts` 默认 path 已与权威路由一致，注释更新；`SHA256SUMS` 同步重算。
- `CONTRACT_DRIFT_REGISTER` 将 DRIFT-001 标为 RESOLVED。

## Added（V1.3 Mastery Closure 后端收口，2026-09-30）

> DRIFT-002 完整闭环：运行实现此前只接「半条链」（证据落库但从不消化成能力等级、L1→L2 空壳秒升、L2+ 因缺 transfer 证据不可达）。分四个 PR 收口后 QA replay 全绿，正式激活 `mastery-v1.3.1`。

- **FE-1311（PR-A Atomic Evidence Truth，#15）**
  - B1：L1→L2 补真实 Gate（非空壳）——eligible standard/retention ≥5、resource_version ≥3、session ≥2、C≥0.80/I≥0.50/S≥0.50，外加非补偿门槛「≥4/5 任务 hint≤2」；不足返回 `collect_evidence`。
  - B2：`evidence_role` 落到 Task Assignment——`task_instance.strategy_policy` 写 `evidence_role`(standard/transfer/retention) + `task_purpose`；`turn_service` 按 role 决定 evidence_type，不再硬编码 `attempt_standard`。
  - B3：单 Task 单证据——首个可评分 Attempt 为唯一 Mastery 原子证据，后续 Retry 仅写 Attempt/Event，不覆盖能力测量。
- **FE-1312（PR-B Evidence Coverage Truth，#16）**
  - B4：四维指标改 Optional——coverage 不足返回 `None` 而非 `0.0`（区分「没测」vs「测了不会」）；`mastery_score` 任一维度缺失 = `None`，不重归一化、不把缺当 0。
  - B5：多样性约束严格执行——C/I 需 ≥3 resource + ≥2 session；S 需 ≥3 resource + ≥2 session；T 需 ≥2 rows + ≥2 context + ≥2 session。
- **FE-1313（PR-C Derived Evidence + L4，#17）**
  - B6：`stability_window`/`transfer_window` 派生证据落库，带 `source_evidence_ids` 可追溯 + `window_signature` sha1 幂等。
  - B7：L3→L4 完整 Gate——T≥0.80 + transfer 证据≥3 + context≥3 + 节点级 `level_schema.l4_gate`（禁用 if-else 硬编码）。
- **FE-1314（PR-D Mastery→Curriculum Closure，#18）**
  - B8：review 状态机——`decide_review` 纯函数；单次失败不降级、窗口内 ≥2 失败 review_required、≥3 全失败最多降 1 级；trend 综合语义(up/down_review/watch/stable)；Curriculum 按 evidence need 选 role（儿童端仅见 NEXT_TASK）。
- **FE-1315（激活，#19）**
  - `scripts/qa_replay_mastery.py` 回放后端指南 §14 全部 14 条必测用例，14/14 通过。
  - `RULE_VERSION` 由 `mastery-v1.3` 激活为 `mastery-v1.3.1`（models 默认值同步），消除 `turn_service` 硬编码 `rule_version`。
  - 历史数据按 v1.3.1 重算回灌。

相关文档新增：`docs/backend/01_V13_MASTERY_CLOSURE_IMPLEMENTATION.md`、`docs/frontend/23_MASTERY_CLOSURE_FRONTEND_CONTRACT.md`、`docs/frontend/24_MASTERY_FRONTEND_BACKEND_INTEGRATION.md`。

## Changed（V1.3 Mastery Closure 前端对齐，2026-09-30）

- FE-1310：能力趋势统一转换为儿童可理解文案（有进步 / 很稳定 / 继续积累 / 正在巩固），不暴露 review/downgrade 内部术语。
- FE-1310：结果页从“只显示第一项 ability_change”改为完整渲染一次 Session 的全部能力变化。
- FE-1310：Session Result Normalizer 兼容 `old_level/new_level` 与 MasteryDecision `decision` 迁移字段。
- QA-1311：V1.3 静态 QA 增加 Mastery UI 边界校验，防止儿童端重新引入复核术语或只渲染单能力。
- Mock：补充 up / stable / down_review 三种能力状态，用于结果页和成长地图回归。


## Fixed（Sprint 3 联调阶段修复，2026-09-28）

> 以下 6 处修复在`前后端真实联调`中暴露，均为「mock 模式测不出、接真后端才会踩到」的契约/bug。
> 事前已通过「前后端 API 对齐评审」+ 真实 RDS 端到端验证逐一确认。

### F1. 前端 next_action 空值兜底
- **文件**：`apps/child-web/src/features/learning/machine.ts`
- **根因**：后端 `record_attempt` 答错时返回 `next_action`，答对时返回 `null`；前端 `getNextActionCode` 无条件读 `result.next_action.type`，答对时崩 `Cannot read properties of null (reading 'type')`。
- **修复**：改为 `result.next_action?.type ?? "NEXT_TASK"`，加空值兜底。
- **影响**：修复答对即崩溃。

### F2. 前端提交防重入锁
- **文件**：`apps/child-web/src/features/learning/useLearningSession.ts`
- **根因**：快速连点「提交」/ 连按 Enter，导致同一 `(task_instance_id, attempt_no)` 提交两次，撞后端唯一约束 `attempt_task_instance_id_attempt_no_key` → 500。
- **修复**：新增 `submittingRef`（`useRef`），提交中禁止再次触发，`try/finally` 保证解锁。
- **影响**：修复重复提交导致的 500。

### F3. 前端 response 契约对齐（object 而非 string）
- **文件**：`apps/child-web/src/features/learning/useLearningSession.ts` + `apps/child-web/src/lib/api/contracts.ts` + `apps/child-web/src/lib/api/mock.ts`
- **根因**：OpenAPI 明确 `AttemptRequest.response` 是 `object`，但前端传的是字符串 `state.answer`，后端 `response.get("answer")` 会取不到答案，http 模式判分失效。
- **修复**：`response` 改为 `{ answer: state.answer }`；`contracts.ts` 类型收紧为 `Record<string, unknown>`；`mock.ts` 判分改为取 `.answer`。
- **影响**：修复 http 模式判分失效。

### F4. dev ui-kit 组件 prop 对齐
- **文件**：`apps/child-web/app/dev/ui-kit/page.tsx`
- **根因**：`AbilityGrowthCard` 在 V1.2 已把 prop 从 `level` 改为 `afterLevel`，但 ui-kit 仍用旧 `level`，导致 typecheck 报错。
- **修复**：`level={2}` → `afterLevel={2}`。
- **影响**：修复 typecheck 失败。

### F5. 首页「今日目标」措辞与能力排序
- **文件**：`apps/child-web/src/screens/MathHomeScreen.tsx` + `apps/learning-api/app/services/profile.py`
- **根因**：后端 `profile` 的 `developing` 按数据库无序返回，导致「今日目标」误推链末环能力（如「检查验算」）给零基础孩子；措辞「继续练习」对从未开始的孩子不准确。
- **修复**：后端 `developing` 按能力依赖链 `_CANONICAL_ORDER` 排序（读题理解→…→迁移变式）；前端 `level===0` 显示「开始练习」而非「继续练习」。
- **影响**：首页推荐能力更符合教学顺序，零基础措辞准确。

### F6. 后端提交幂等
- **文件**：`apps/learning-api/app/services/turn_service.py`
- **根因**：与 F2 同源，前端防重入是缓解，后端幂等才是根治。
- **修复**：`record_attempt` 提交前查已有 `(task_instance_id, attempt_no)`，存在则直接返回第一次结果（不重复写 attempt/event/evidence）。
- **影响**：即使前端漏防，同一 attempt 重复提交也返回 200 + 相同 attempt_id，不再 500。

## Added（V1.3 Math Interaction Foundation，待正式发版）

> 来自 `Math_Sprint3_Frontend_V1.3` 交付包的三方合并；开发期间不升版本号，仍保持 `1.2.0`。

- FE-1301 Task Renderer V1：学习页改由 `TaskRenderer` 统一渲染（number / manipulative / unsupported 三分支）
- FE-1302 隔离的 Workspace State：`math-workspace` 状态与学习状态机解耦（`WorkspaceProvider` + `workspaceReducer`）
- FE-1303 交互式 Object Counter（一一对应摆一摆）
- FE-1304 交互式 Bar Model（线段图）
- FE-1305 交互式 Number Line（数轴跳跃）
- API-1306 TaskUISchema V1：`contracts.ts` 引入判別联合 schema + `taskUiSchemaNormalizer` 兼容旧 schema
- API-1307 Structured Response：attempt 提交 `TaskResponse { answer, representation }`
- API-1308 Workspace-aware Hint：`HintResponse.ui_action` 驱动图示高亮/聚焦
- QA-1312 `/dev/v1.3-qa` 双皮肤（healing / math-lab）QA 页

## Changed（与 FE-1300 三方合并）

- `math-workspace` / `task-renderer` 全新目录，`manipulatives` 3 个交互组件
- `MathLearningScreen` 用 `TaskRenderer` 替代旧的 `MathQuestionCard + MathWorkspace`
- `machine.ts`：`answer: string` → `response: TaskResponse`，`SET_ANSWER` → `SET_RESPONSE`
- `config.ts`：`apiBaseUrl` 默认去掉 `/api` 后缀（对齐后端实际 `/v1/...` 前缀）

---

# [1.2.0] - 2026-09-28

**Release Name:** Learning Result Closure

## Added

### Session Result 正式前端契约
新增：
- `SessionResult`
- `LearningBehavior`
- `AbilityChange`
- `NextRecommendation`

文件：

```text
src/lib/api/contracts.ts
```

### Session Result API
新增：

```text
LearningApi.getSessionResult(sessionId)
```

实现：
- `HttpLearningApi`
- `MockLearningApi`

### Session Result Normalizer
新增：

```text
src/lib/api/sessionResultNormalizer.ts
```

用途：
- 将当前后端结果Payload统一转为前端Canonical Contract
- 隔离后端Schema演进
- 等权威OpenAPI补齐SessionResult后再收紧别名兼容

### 结果页正式后端驱动
`MathResultScreen` 不再把 `sessionStore` 作为主要数据源。

结果页现在由：

```text
Session Result API
├── learning_behaviors
├── ability_changes
├── duration_ms
├── task_count
├── attempt_count
├── hint_usage
└── next_recommendation
```

直接驱动。

### 结果页状态
新增：
- loading
- success
- fallback
- error
- retry

### 版本管理
新增：
- `VERSION`
- `releases/1.2.0.json`
- `docs/10_RELEASE_NOTES_V1.2.md`
- `docs/11_SESSION_RESULT_INTEGRATION.md`
- `docs/12_VERSION_MANAGEMENT.md`
- `docs/13_MIGRATION_V1.1_TO_V1.2.md`
- `docs/14_KNOWN_ISSUES_V1.2.md`
- `docs/15_RELEASE_CHECKLIST.md`

## Changed

### sessionStore职责调整
V1.1：

```text
sessionStore → Result Page主要数据源
```

V1.2：

```text
Session Result API → Result Page主要数据源
sessionStore → 仅异常兜底 / 临时缓存
```

### LearningBehaviorChecklist
由后端：

```text
learning_behaviors
```

直接驱动，不再由前端根据 attempt/hint 数量推断教育行为。

### NextTaskCard
由后端：

```text
next_recommendation
```

驱动标题与描述。

### AbilityGrowthCard
优先使用：

```text
ability_changes
```

可展示：
- before_level
- after_level
- trend
- evidence_delta

### SessionStats
正式使用 Session Result：
- duration
- task_count
- attempt_count
- hint_usage

## Compatibility

- 无破坏性页面路由变化
- 现有 Session / Task / Attempt / Hint API 不变
- Mock 模式保持完整可跑
- 结果页正式数据源发生变化

## Known Constraint

当前本地冻结的 `02_openapi_v1.3.yaml` 尚未包含新 Session Result 路径，因此 V1.2 使用：

```env
NEXT_PUBLIC_SESSION_RESULT_PATH_TEMPLATE
```

作为接口路径适配层。

正式后端 OpenAPI 更新后，应以权威路径替换环境变量并收紧 Normalizer。

---

# [1.1.0] - 2026-09-28

## Added

### 项目接手文档
新增：

```text
docs/06_FRONTEND_MODULE_MAP.md
```

内容包括：
- 前端8大模块
- 各页面功能清单
- 当前能力
- 状态
- API依赖
- 功能边界
- 已完成/待完成

### 后续开发路线图
新增：

```text
docs/07_NEXT_DEVELOPMENT_ROADMAP.md
```

明确：
- P0 / P1 / P2
- Math Manipulative Engine
- Task Renderer
- Session Result API
- Ability Detail
- Evidence
- Learning Plan
- Skin Resolver
- Parent Dashboard
- Skin Engine
- Voice/TTS

### 接手指南
新增：

```text
docs/08_HANDOVER_GUIDE.md
```

用于新开发人员快速上手。

### Changelog
新增根目录：

```text
CHANGELOG.md
```

后续所有版本必须更新本文件。

## Changed

- README 增加“项目当前完成度 / 下一步开发 / 版本记录”入口
- package version 从 `1.0.0` 升为 `1.1.0`
- handoff metadata 增加版本和变更记录要求

## Code Changes

本版本主要为文档治理与工程交接增强。

核心业务代码、Learning Engine API、状态机逻辑未改变。

---

# [1.0.0] - 2026-09-28

## Added

### 可运行 Next.js 工程
新增：
- App Router
- TypeScript
- npm scripts
- Mock / HTTP 双模式

### 页面
新增：
- `/child/math`
- `/child/math/session/[sessionId]`
- `/child/math/result/[sessionId]`
- `/child/math/growth`
- `/dev/ui-kit`

### 18个核心组件
完成：
- 4个基础UI组件
- 3个首页组件
- 5个学习组件
- 5个结果组件
- 1个成长组件

### 系统内置皮肤
完成：
- healing
- math-lab
- 默认 math-lab

### Learning Flow
完成：
- Create Session
- Next Task
- Submit Attempt
- Diagnosis
- Hint
- Retry
- Next Task
- Complete

### Learning Engine API
完成：
- Profile
- Abilities
- Session
- Task
- Attempt
- Hint

### Mock Engine
新增完整本地Mock闭环。

### Session Runtime
新增前端 Session Snapshot，用于正式 Session Result API 尚未接入时支撑结果页。

## Known Limitations

- 无正式 Session Result API
- MathWorkspace 仅为视觉/基础操作区
- 无完整 Manipulative Engine
- 无家长端
- 无 Learning Plan 页面
- 无 Skin Engine
- 无 Voice/TTS

---

# 历史前置资产

在 Sprint 3 前端之前，存在：

```text
Math_Child_UI_BuiltIn_Skins_V1.0
```

该包属于：

> 视觉规范 + Built-in Skin Runtime 骨架

Sprint 3 Frontend V1.0 在此基础上补齐了：
- 组件实现
- 页面组装
- 学习状态机
- API接线
