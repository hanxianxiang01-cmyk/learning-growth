# V1.3 Closure Contracts —— 版本边界收口约定

> 目的：把 V1.3 与 V1.4 的边界钉死，避免 V1.4 接动态化时背上架构债。
>
> 原则：**V1.3 = 闭环成立；V1.4 = 闭环智能化。**
>
> 本文档记录三份契约的字段语义、当前代码落点、V1.3 待改项、V1.4 扩展方向。
> 它不是 Bug 清单，而是「跨版本接口 / 数据模型真相同步清单」。

---

## Contract ① — Session & Task Goal（会话目标契约）

### 语义定义

```text
requested_minutes = 本次学习的「时间预算」（是预算，不是精确计时）
SESSION_TASK_GOAL = 一次 session 的「默认任务数」（是默认值，不是产品规则）
Task             = 一道任务实体（可能带多次作答 Attempt）
Question         = 题目内容（Task 的载体）

关键区分：Task ≠ Question。一 Task 可能多次作答，但只产生一条能力证据。
```

### 当前代码落点（事实）

| 项 | 位置 | 现状 |
|---|---|---|
| `SESSION_TASK_GOAL = 3` | `apps/learning-api/app/services/learning.py:29` | 散落硬编码，注释标「MVP 约定」 |
| `requested_minutes` | 后端 `start_session` / `assign_next_task` | **接收但完全未使用**，也不持久化 |
| `requested_minutes` 字段 | `LearningSession` 模型 | **不存在该字段**（`models/__init__.py:204-210`） |
| 前端进度点 `total={3}` | `apps/child-web/src/screens/MathLearningScreen.tsx:57-58` | 硬编码，不读后端 |
| 前端 mock 目标数 | `apps/child-web/src/lib/api/mock.ts:371` | 硬编码 `SESSION_TASK_GOAL = 3` |

### V1.3 待改项

1. `SESSION_TASK_GOAL` 从 `learning.py` 收进 `education_rules.py`，语义标注「默认值，非产品规则」。✅ 已完成（本次）
2. `LearningSession` 增加 `requested_minutes`（可空）字段并持久化 —— 即使暂不驱动题量，先留下「时间预算」的接口空间。⚠️ 本次**暂缓**：属 DDL 迁移（基线 SQL 无此列 + `migrations/versions/` 为空 + 需 ALTER 真实 RDS + 重算 SHA256），留作 V1.3 收口后的独立迁移项。
3. 前端 `total` 改为读后端返回的 goal，不再硬编码。⏳ 待做（前端改动，无迁移风险）。

### V1.4 扩展方向

- `requested_minutes` 推导动态任务数（不固定 3 题）。
- 10 / 15 / 20 分钟模式。
- 动态难度、动态 Session 延长 / 缩短。
- 注意题库天花板：每个能力当前最多 5~11 题，动态题量 > 5 会触发重复出题，须配合扩容题库或跨能力轮换。

---

## Contract ② — Home Projection（首页投影契约）

### 语义定义

```text
首页卡片 = 对「今日计划 / 推荐任务」的一个「投影」，不是对固定能力的硬绑定。

HomeCard 抽象模型：
  card_type               # 卡片类型（recommend / continue / challenge ...）
  ability_id              # 目标能力（可空，后端自选时为空）
  task_id                 # 目标任务（可空）
  recommendation_reason   # 推荐理由（驱动标题 / 文案）
  action                  # 点击动作（启动 session 的参数）
```

### 当前代码落点（事实）

| 项 | 位置 | 现状 |
|---|---|---|
| 首页卡片 | `MathHomeScreen.tsx:99-116` | **写死两个 `MathTaskCard`**（🔢数量关系 / 🧩策略） |
| 能力映射 | `lib/challengeMapping.ts` | 关键词反查（`quantity→数量关系`、`strategy→策略`），半抽象 |
| 数据源 | 硬编码 props | 不从后端推荐列表 `map` 渲染 |

### V1.3 待改项

1. 首页卡片改为「由推荐列表 `map` 驱动渲染」，接受 `HomeCard[]` 而非固定两个组件实例。
2. `app_rel` / `app_strat` 明确为「当前数据」，非「架构绑定」，卡片字段可用 `HomeCard` 契约填充。

### V1.4 扩展方向

- 42 / 49 能力动态注入首页。
- Renderer Matrix / Ability Matrix 两套逻辑合一，不再为「固定两卡片」分开处理。

---

## Contract ③ — Minimum Learning Loop（最小学习闭环契约）

### 语义定义

```text
这条链路每一步都要回答「谁决定、为什么出现、完成后发生什么」：

  今日目标 (Goal)
     ↓  谁选能力？凭 level/evidence/依赖链？
  创建 Session
     ↓
  完成 Task
     ↓
  记录 Result（Session Result API）
     ↓
  更新学习结果（AbilityState / mastery_evidence）
     ↓
  生成下一步推荐 (Next Recommendation)
     ↓  这个推荐是否回灌首页？
  （回到 今日目标，闭环）
```

### 当前代码落点（事实）

| 项 | 位置 | 现状 |
|---|---|---|
| 今日目标判定 | `profile.py:55-62` | level ≥3 判强项，<3 判发展中，按依赖链排序取 `developing[0]` |
| 结果聚合 | `session_result.py` | 已输出 `next_recommendation` |
| **断点** | `MathHomeScreen` | 「今日目标」推荐的能力 **不参与选题**；`next_recommendation` **不回灌首页** |

### V1.3 待改项

1. 明确「今日目标」推荐的能力 = 进入 session 的默认能力（打通 Goal → Session 的入口对齐）。
2. `next_recommendation` 回灌首页「今日目标」卡片，让「做完这次」和「下次做什么」接上。

### V1.4 扩展方向

- 今日计划由能力状态 + 近期证据 + 历史共同决定（Adaptive Today Plan）。
- Next Best Task 真正由当前表现驱动（Adaptive Next Task）。

---

## 版本边界一句话

| | V1.3（收口） | V1.4（增强） |
|---|---|---|
| ① 题量/时长 | 定默认值 + 字段语义 + 接口空间 | 动态任务数、时间预算 |
| ② 首页 | 定 HomeCard 投影契约，卡片数据驱动 | 42/49 能力动态注入 |
| ③ 今日目标 | 打通 Goal → Session → Next 最小闭环 | 能力状态 + 证据 + 历史智能推荐 |

**优先级：③ > ② > ①**（③ 是闭环是否成立的根本，② 是架构债高发点，① 最易、只需定默认值）。