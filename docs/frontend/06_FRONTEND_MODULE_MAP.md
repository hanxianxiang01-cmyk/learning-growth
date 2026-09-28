# 06｜前端模块地图

> 本文用于帮助新接手的前端、产品、架构和 AI 工程师快速理解当前 `Math_Sprint3_Frontend` 已经完成什么、各模块能做什么、状态如何、依赖哪些 API。

---

# 一、前端总体模块

| 模块 | 当前职责 | 当前状态 |
|---|---|---|
| 数学首页 | 今日目标、任务入口、成长入口、创建 Session | ✅ 可用 |
| 数学学习页 | 题目、数学表征、答题、Hint、Retry、Next | ✅ 主流程可用 |
| 学习状态机 | 控制答题全过程状态流转 | ✅ 已实现 |
| 结果页 | 学习行为、用时、Hint、能力状态 | ✅ 正式Session Result API驱动；本地快照仅fallback |
| 成长地图 | 展示能力等级、趋势、证据数量 | ✅ 展示可用 |
| Learning Engine API | Profile、Abilities、Session、Task、Attempt、Hint | ✅ Mock/HTTP 双模式 |
| 皮肤系统 | healing / math-lab 两套系统内置皮肤 | ✅ 可用，当前全局配置 |
| Dev UI Kit | 18组件 × 2皮肤 = 36小样 | ✅ 可用 |

---

# 二、数学首页

## Route

```text
/child/math
```

## 核心文件

```text
src/screens/MathHomeScreen.tsx
```

## 功能清单

| 功能 | 当前能力 | 状态 |
|---|---|---|
| 获取儿童 Profile | 年级、观察信息、发展能力 | ✅ |
| 获取能力状态 | level / confidence / trend / evidence_count | ✅ |
| 今日学习目标 | 优先取 developing 能力 | ✅ |
| 今日任务卡 | 展示学习入口 | ✅ |
| 创建 Learning Session | POST sessions | ✅ |
| 跳转学习页 | 带 sessionId 进入 | ✅ |
| 成长地图入口 | 跳转能力页 | ✅ |
| 个性化学习计划 | 真正按 Learning Plan 动态生成 | 🟡 待开发 |

## 当前行为

```text
进入首页
 ↓
读取 Profile + Abilities
 ↓
选择 developing ability
 ↓
展示今日目标
 ↓
点击任务
 ↓
Create Session
 ↓
进入学习页
```

## 边界

目前首页多个任务卡最终都调用同一个 `createSession()`。
任务的真正选择仍由 Learning Engine 决定。

后续若要实现：
- 指定能力训练
- 指定任务类型
- 指定 Learning Plan

需要扩展 Session / Plan Contract。

---

# 三、数学学习页

## Route

```text
/child/math/session/[sessionId]
```

## 核心结构

```text
LearningTopBar
├── MathQuestionCard
├── MathWorkspace
├── AnswerComposer
├── ManipulativeToolbar
└── CoachPanel
```

## 功能清单

| 能力 | 当前实现 | 状态 |
|---|---|---|
| 拉取下一题 | `/learning/tasks/next` | ✅ |
| 显示题干 | `ui_schema.prompt` | ✅ |
| 显示学习目标 | `task.goal` | ✅ |
| 数量可视化 | objects / rows | ✅ |
| 输入答案 | 文本/数字输入 | ✅ |
| 提交 Attempt | `/learning/attempts` | ✅ |
| 对错反馈 | Learning Engine 驱动 | ✅ |
| 请求 Hint | `/learning/hints` | ✅ |
| Hint 1–4 | 支持 | ✅ |
| Retry | attempt_no 递增 | ✅ |
| Next Task | `NEXT_TASK` | ✅ |
| Complete | `COMPLETE` | ✅ |
| 进度点 | 当前基于 Mock 3任务逻辑 | 🟡 |
| 画一画 | 工具入口 | 🟡 |
| 摆一摆 | 工具入口 | 🟡 |
| 数一数 | 工具入口 | 🟡 |
| 真正自由画布 | 未实现 | ❌ |
| 真正拖拽积木 | 未实现 | ❌ |
| 数轴交互 | 未实现 | ❌ |
| Bar Model 交互 | 未实现 | ❌ |

## 当前定位

当前 `MathWorkspace` 是：

> 数学视觉化工作区 V1

还不是：

> 完整数学 Manipulative Engine

---

# 四、学习交互状态机

## 文件

```text
src/features/learning/machine.ts
src/features/learning/useLearningSession.ts
```

## 状态

```text
idle
loading_task
answering
submitting
hint_available
hint_loading
hint_active
retry
correct
completed
error
```

## 主流程

```text
idle
 ↓
loading_task
 ↓
answering
 ↓ submit
submitting
 ├─ correct + NEXT_TASK → correct → loading_task
 ├─ correct + COMPLETE  → completed → result
 ├─ wrong + HINT/TEACH  → hint_available
 │                         ↓
 │                       hint_loading
 │                         ↓
 │                       hint_active
 │                         ↓
 │                       retry
 │                         ↓
 │                       answering
 └─ error               → error
```

## 当前控制变量

```text
task
answer
attemptNo
lastAttempt
hint
usedHintLevels
error
status
```

## 规则

- 第一次错误不直接显示答案
- Hint 1–4 由 Learning Engine 控制
- E01~E07 属于教育诊断码
- 前端不计算 Mastery
- 前端不自行做 Diagnosis
- 前端只根据 `next_action.type` 驱动交互

---

# 五、AI / Hint 模块

## 核心组件

```text
CoachPanel
```

## 定位

AI 不是聊天机器人，而是：

> 状态驱动的学习助手

## 状态表现

| 状态 | 行为 |
|---|---|
| answering | 鼓励先自己思考 |
| hint_available | 可请求提示 |
| hint_loading | 提示加载 |
| hint_active | 展示提示 |
| retry | 引导再尝试 |
| correct | 进入下一任务 |
| completed | 本轮完成 |
| error | 友好错误提示 |

## Hint 类型

```text
Level 1 → QUESTION
Level 2 → STRUCTURE_HINT
Level 3 → STEP_HINT
Level 4 → TEACH
```

## 尚未实现

- AI 流式输出
- TTS
- Voice
- Chat History
- 前端直接调用 DeepTutor

当前正确调用链：

```text
Child UI
 ↓
Learning Engine
 ↓
DeepTutor / LLM
```

---

# 六、结果页

## Route

```text
/child/math/result/[sessionId]
```

## 页面组成

```text
CompletionHero
├── LearningBehaviorChecklist
├── AbilityGrowthCard
├── SessionStats
└── NextTaskCard
```

## 当前展示

```text
完成情况
错误后是否继续尝试
Hint使用情况
是否完成最终任务
本次用时
作答次数
对应能力Level
能力Trend
```

## 数据来源

### 正式主数据源

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

### 本地快照

```text
sessionStorage
```

只在 Result API 异常时作为临时兜底，并在UI明确标记“临时记录”。

## 边界

V1.2开始，结果页不再根据前端Attempt数量推断教育行为。
教育判断由 Learning Engine / Session Result 返回。

---

# 七、成长地图

## Route

```text
/child/math/growth
```

## 当前展示

```text
ability_id
name
level
confidence
evidence_count
trend
fit_band
```

## UI表现

```text
数量关系       ━━━━━━━━░░   L2
近期上升 · 6条证据
```

## 当前状态

已完成：

- Ability Overview
- Level
- Trend
- Evidence Count

尚未实现：

- 能力详情页
- 学习证据详情
- 历史曲线
- “为什么判断为 L2”
- 最近任务明细

---

# 八、Learning Engine API

## 目录

```text
src/lib/api/
├── contracts.ts
├── http.ts
├── mock.ts
└── index.ts
```

## 已接能力

| API | 使用位置 | 状态 |
|---|---|---|
| getProfile | 首页 | ✅ |
| getAbilities | 首页 / 结果 / 成长 | ✅ |
| createSession | 首页 | ✅ |
| getNextTask | 学习页 | ✅ |
| submitAttempt | 学习页 | ✅ |
| requestHint | 学习页 | ✅ |
| getSessionResult | 结果页 | ✅ V1.2新增 |

## Mock Mode

```env
NEXT_PUBLIC_LEARNING_API_MODE=mock
```

允许后端未启动时完整跑通主流程。

## HTTP Mode

```env
NEXT_PUBLIC_LEARNING_API_MODE=http
```

调用 FastAPI Learning Engine。

---

# 九、Task Renderer 能力

## Contract 已预留

```text
number
single-choice
formula
drag
```

以及：

```text
objects
bar-model
number-line
grid
```

## 当前真正实现

| Renderer | 状态 |
|---|---|
| number / text input | ✅ |
| objects展示 | ✅ |
| bar-model | 🟡 基础展示 |
| formula | 🟡 仅输入能力 |
| single-choice | ❌ |
| drag | ❌ |
| number-line interaction | ❌ |
| grid drawing | ❌ |

---

# 十、皮肤系统

## 文件

```text
src/theme/
├── skins.ts
└── ChildSkinProvider.tsx
```

## 系统内置皮肤

```text
healing
math-lab
```

默认：

```text
math-lab
```

## 当前能力

| 能力 | 状态 |
|---|---|
| 内置皮肤定义 | ✅ |
| CSS变量驱动 | ✅ |
| 两套组件视觉 | ✅ |
| 孩子端换肤 | ❌ |
| 按 child_id 存储皮肤 | ❌ |
| 家长端管理 | ❌ |
| Skin Engine | ❌ |
| AI自定义皮肤 | ❌ |

当前皮肤来源：

```text
NEXT_PUBLIC_CHILD_MATH_SKIN
```

后续计划：

```text
child_id
 ↓
Skin Resolver
 ↓
Resolved Skin
 ↓
ChildSkinProvider
```

---

# 十一、Session Runtime

## 文件

```text
src/lib/runtime/sessionStore.ts
```

## 当前记录

```text
childId
sessionId
startedAt
completedAt
tasksCompleted
correctTasks
totalAttempts
hintsUsed
lastAbilityId
diagnosisCodes
```

## 当前作用

在正式 Session Result API 尚未接入前，为结果页提供最小数据闭环。

## 当前边界

- 使用 sessionStorage
- 非正式持久化
- 不应替代后端 Learning Event / Session 数据

---

# 十二、18个核心组件

## UI
1. PrimaryButton
2. SurfaceCard
3. ProgressDots
4. AbilityBadge

## 首页
5. TodayGoalCard
6. MathTaskCard
7. GrowthEntryCard

## 学习
8. MathQuestionCard
9. MathWorkspace
10. ManipulativeToolbar
11. AnswerComposer
12. CoachPanel

## 结果
13. CompletionHero
14. LearningBehaviorChecklist
15. AbilityGrowthCard
16. SessionStats
17. NextTaskCard

## 成长
18. AbilityMap

全部均为真实 `.tsx` 组件。

---

# 十三、Dev UI Kit

## Route

```text
/dev/ui-kit
```

## 用途

开发 / 产品 / 设计验收。

```text
18 Healing
+
18 Math Lab
=
36 实际组件样例
```

不是孩子端产品功能。

---

# 十四、当前完成度

## 已具备

```text
页面框架
双内置皮肤
组件体系
Session创建
Next Task
Answer
Attempt
Diagnosis
Hint
Retry
Next
Complete
Result
Ability Overview
Mock API
HTTP Adapter
```

## 下一阶段重点

```text
MathWorkspace + Task Renderer
```

这是当前最优先的产品能力建设方向。
