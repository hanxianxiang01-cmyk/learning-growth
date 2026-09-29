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
