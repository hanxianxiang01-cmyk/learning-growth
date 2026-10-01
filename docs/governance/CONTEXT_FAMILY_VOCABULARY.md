# Context Family Vocabulary（受控词表 · 唯一事实源）

> 状态：**V1.4 P0 Governance Closure — 实施中**
> 依据：《V1.4 P0 Governance Closure》§3：本文件是 context_family 词表的唯一事实源。DDL / Engine / Frontend / 题库 / Prompt 一律不得另行维护词表。
> 字段语义（§5）：`mastery_rule.context_family` = 该题在 Transfer 评估中所属的标准化场景/关系族，是 Transfer Evidence 的 canonical classification key。

---

## 0. 分类优先级规则（先于具体族定义）

对一道题按以下顺序取**第一个命中**的族（关系优先于物品场景）：

1. 题目主要数量关系是「比…多 / 比…少 / 相差」→ `comparison`
2. 题目含「数量随事件变化」事件（原来…吃了/买来/开来/上车/送来/飞来的单向或连续变化）→ `before_after`
3. 题目结构核心是「按时间定位信息 / 时间先后」→ `time_schedule`
4. 排队、位置、序数 → `lineup_position`
5. 购买、付款、找零交易 → `shopping`
6. 平均分、按份分配物品 → `sharing`
7. 其余静态物品题：物品属学习用品 → `school_objects`；属玩具/球类/水果等生活物品 → **待裁决**（见 §4 提案 `everyday_objects`）

**特别约束（照录治理文档 §2）**：
- `before_after` 不得简单理解成"所有两步题"。如"小明排队第5个"不能因存在计算步骤归入 before_after，应按结构判断。
- `school_objects` 是指南已有示例锚点，不得因题库数量少而删除。

---

## 1. V1.4 初始词表

| context_family | 定义 | 适用边界 | 正例 | 反例 | 启用状态 | 当前题库覆盖 |
|---|---|---|---|---|---|---|
| `school_objects` | 书、笔、贴纸、彩笔等学习物品场景 | 静态集合的合并/求部分/条件筛选；物品须为学习用品 | 2盒彩笔每盒6支一共几支；12张贴纸5张星星其余圆形 | 「原来9本书又买3本」(变化→before_after) | **启用** | 8 题 |
| `comparison` | 比…多、比…少等基准比较关系 | 题目主要关系是差比；含比较方向验证、语言顺序变化 | 小东8支比小西5支多几支；小芸比小康少5颗 | 「吃掉3个」(变化事件→before_after) | **启用** | 18 题 |
| `before_after` | 增加/减少形成的前后变化（单步或连续多步） | 核心是数量随事件起算变化 | 车上上来6人下去4人；原来9块饼干吃掉3块 | 「排队第5个前面4人」(位置结构) | **启用** | 16 题 |
| `lineup_position` | 排队、位置、序数等位置关系 | 序数/方位为题目核心 | （当前题库无） | 数轴跳步表示减少(变化→before_after) | 启用·**暂无覆盖** | 0 题 |
| `shopping` | 购物、付款、找零 | 交易结构为题目核心 | （当前题库无，仅个别题以"买了"作干扰项） | 干扰项含"买了铅笔"但问上午带了几张卡片(time_schedule) | 启用·**暂无覆盖** | 0 题 |
| `sharing` | 分糖果、分配物品等平均/按份分配 | 等分/按份分配动作或结构 | （当前题库无；按类别分解整体不归入此族，见 §5 裁决点） | 「18个杯子7蓝其余白」(类别分解非分配→待裁决) | 启用·**暂无覆盖** | 0 题 |
| `time_schedule` | 时间、日程、时间先后关系 | 时间信息是定位/推理主轴 | 上午画了几朵花（下午画树为干扰）；上午带卡片/中午借书/下午买铅笔 | 「上午卖出下午卖出共多少」(变化→before_after) | **已启用**（2026-10-01 Backfill 评审批准，2 题真实覆盖） | 2 题 |

> 空值语义：`context_family` 为 NULL 表示该题**尚无**有效 Transfer Family 判定；NULL 不得伪装成任何族参与 transfer 计数（Engine 端已按此实现：distinct 集合中 NULL 不计入）。

---

## 2. Seed Validation Contract（§4 落地）

入口：`app/content/context_family.py`（校验函数被 seed 脚本调用）。

```text
raw value → trim → canonical validation → Vocabulary lookup → PASS / ERROR
```

- 合法值：仅限本文件 §1 表中已启用族 ID（snake_case，全小写）。
- 非法值一律：`ERROR: UNKNOWN_CONTEXT_FAMILY`，不得进入正式 Seed。
  示例非法：`school`、`学校物品`、`School_Objects`、`buying`、`purchase`。
- DDL 保持 `context_family varchar(64)`，**不加** CHECK 约束（§9 决策：类型约束归 DDL，值域归词表，入口归 Validation，消费归 Engine）。

## 3. Engine 消费契约（§8）

- Engine 只消费 canonical ID，不解释 Family 语义；代码中禁止出现 `if family == "shopping"` 之类分支。
- Transfer 判定：L2→L3 = ≥2 distinct family + ≥2 sessions；L3→L4 = ≥3 distinct family（+节点 gate）。
- **现状核验（2026-10-01）**：`mastery.py` 仅做 distinct 计数、无族名硬编码 —— AC-06 已满足。

## 4. 待裁决项（Backfill 评审，对应 §6 REVIEW 状态）

**REVIEW-A：新增族 `everyday_objects`？**
玩具（气球/皮球/玩具车/玻璃珠）、球类、餐桌物品等**生活物品**的静态集合题，按 §0 规则落到第 7 档，现无对应族。候选方案：
- (a) 正式按 §10 扩展协议新增 `everyday_objects`（定义：儿童日常玩具与生活物品场景；正例：红蓝气球一共几个；反例：吃掉3个橘子=before_after）；
- (b) 强行并入 `school_objects`（破坏其"学习物品"定义，不建议）；
- (c) 保持 REVIEW，context_family 留 NULL，待 V1.4 内容扩容再裁决（这 6 题将不计入 transfer diversity，但不影响现有 L2→L3 解锁，见 §6）。

涉及题目（6 题）：`af2cb0d1`(气球合)、`40d0feb3`(玩具车合)、`3706473c`(苹果梨合)、`76695c2b`(球·定位)、`1ab893bf`(玻璃珠等组)、`b1a30690`(杯子类别分解·迁移题td=1)。

**REVIEW-B：`time_schedule` 是否正式启用**——有 2 题真实覆盖（`0da1d340`、`aba8131f`），提案：启用。

## 5. 类别分解题说明

「总数=A类+其余」的按类别分解题（彩纸红黄、贴纸星星圆、书故事科普），物品为学习用品时按 §0 第 7 档 PASS `school_objects`；物品为生活物品时随 REVIEW-A（如杯子题）。不引入 `sharing`（sharing 语义为"分配动作/等分"，非类别分解）。

## 6. 回填结果摘要（AC-04 过程记录）

| 指标 | 数值 |
|---|---|
| 总题数 | 50 |
| PASS（含 3 族确认 + time_schedule 2 题待启用确认） | **44** |
| REVIEW（待裁决，ctx 暂 NULL） | 6 |
| REJECT | 0 |
| invalid_context_family（启用后应校验） | 0（目标） |

**Transfer 覆盖检查（§7 硬性）**：5 道迁移题中已确定族 = comparison ×2、before_after ×2、REVIEW ×1 →
**已存在 ≥2 distinct family 的迁移覆盖** → 待 §1 回填执行后，L2→L3 的 transfer 多样性门槛（≥2 family + ≥2 session）在生产数据下即具备可达路径。`lineup_position / shopping / sharing` 启用但零覆盖——按 §7 如实记录，需要内容侧补题，不伪装覆盖。

## 7. Vocabulary Extension Protocol（§10 固化）

新增族必须依序：提出新增 → 定义语义边界 → 正例 → 反例 → 与现有族不重叠确认 → 题库实际覆盖确认 → 更新本文件 → 更新 Seed Validation → 补充测试 → 重跑 Transfer Regression → 批准启用。
**禁止**先往数据库写新值再补词表（顺序必须：Vocabulary → Validation → Data）。

---

## 附录：50 题分类明细（回填 Review 清单）

> PASS = 可明确归族；REVIEW = 两族皆合理/待词表裁决；ctx 值在回填脚本执行后写入 `resource_version.mastery_rule.context_family`。

| # | rv_id 前8位 | 能力 | d | 题干要点 | family | 状态 |
|---|---|---|---|---|---|---|
| 1 | 079a7e47 | check | 2 | 6红笔+4蓝笔=10 验证 | school_objects | PASS |
| 2 | dd1147dc | check | 2 | 8苹果吃掉3 验证 | before_after | PASS |
| 3 | 2dd5be20 | check | 3 | 13珠比弟多5 方向验证 | comparison | PASS |
| 4 | 237f47fc | check | 3 | 停车场12-5+2 两步验证 | before_after | PASS |
| 5 | 8d0f2b86 | check | 4 | 9+3=12再+9 比较推导验证 | comparison | PASS |
| 6 | af2cb0d1 | cond | 1 | 红蓝气球合(书干扰) | everyday_objects? | REVIEW |
| 7 | 40d0feb3 | cond | 1 | 玩具汽车+火车合 | everyday_objects? | REVIEW |
| 8 | 3706473c | cond | 1 | 苹果+梨合(笔干扰) | everyday_objects? | REVIEW |
| 9 | 6857ba8d | cond | 2 | 橘子吃掉4(苹果干扰) | before_after | PASS |
| 10 | 623b7f19 | cond | 2 | 贴纸送3(练习册干扰) | before_after | PASS |
| 11 | 76ce803c | cond | 3 | 糖+5-3(饼干干扰) | before_after | PASS |
| 12 | 7acb4a38 | model | 1 | 积木左6右4多几块 | comparison | PASS |
| 13 | 240ff07b | model | 2 | 彩纸13张红5其余黄 | school_objects | PASS |
| 14 | 103ddd46 | model | 2 | 数轴11左移3格 | before_after | PASS |
| 15 | 8b121389 | model | 2 | 6本书多4本 | comparison | PASS |
| 16 | ed97b114 | model | 3 | 比小康少5星星 | comparison | PASS |
| 17 | 8981fbcc | model | 3 | 多3颗再求合 | comparison | PASS |
| 18 | e02a5afe | model | 4 | 公交上6下4 | before_after | PASS |
| 19 | bf475e65 | rd | 1 | 定位红笔数 | school_objects | PASS |
| 20 | 462ce951 | rd | 1 | 定位书本数(橘子干扰) | school_objects | PASS |
| 21 | 76695c2b | rd | 1 | 定位小西的球 | everyday_objects? | REVIEW |
| 22 | 3fd4f402 | rd | 2 | 定位小亮棋子 | school_objects | PASS |
| 23 | 0da1d340 | rd | 2 | 上午画几朵花 | time_schedule | PASS·待启用 |
| 24 | aba8131f | rd | 3 | 上午带几张卡片 | time_schedule | PASS·待启用 |
| 25 | 0c494f3e | rel | 1 | 饼干吃3剩几 | before_after | PASS |
| 26 | 6fad3a13 | rel | 1 | 气球+3蓝共几 | before_after | PASS |
| 27 | a7719043 | rel | 1 | 鸟飞来2只 | before_after | PASS |
| 28 | eaa828b3 | rel | 1 | 彩笔多几支 | comparison | PASS |
| 29 | e6f17364 | rel | 2 | 贴纸星星/圆形分解 | school_objects | PASS |
| 30 | f311e9ec | rel | 2 | 2盒彩笔等组合 | school_objects | PASS |
| 31 | 3ea61fc9 | rel | 2 | 珠子比弟弟多5 | comparison | PASS |
| 32 | e5c13ef5 | rel | 2 | 故事书多4本 | comparison | PASS |
| 33 | 7f22076d | rel | 3 | 棋子少6颗 | comparison | PASS |
| 34 | 1ab893bf | rel | 3 | 3袋玻璃珠等组 | everyday_objects? | REVIEW |
| 35 | 421ede36 | rel | 4 | 贴纸少4再求合 | comparison | PASS |
| 36 | 0176dc73 | strat | 1 | 铅笔+3支 | before_after | PASS |
| 37 | dc1f2a1c | strat | 1 | 饼干吃4剩几 | before_after | PASS |
| 38 | cfc971b4 | strat | 1 | 花多几朵 | comparison | PASS |
| 39 | c07482bb | strat | 2 | 卡片多4张 | comparison | PASS |
| 40 | 8612589b | strat | 2 | 贝壳多5个 | comparison | PASS |
| 41 | f5fb6594 | strat | 2 | 15本书故事6其余科普 | school_objects | PASS |
| 42 | 79acf485 | strat | 3 | 送3张剩8反推原数 | before_after | PASS |
| 43 | 04f97cb0 | strat | 3 | 卡片少4逆向 | comparison | PASS |
| 44 | 6e5395f0 | strat | 4 | 故事书多3求合 | comparison | PASS |
| 45 | a7fc3314 | strat | 4 | 停车场+5-4 | before_after | PASS |
| 46 | 8f603745 | transfer | 3 | 跑圈多几圈 **td=1** | comparison | PASS |
| 47 | a5ea2487 | transfer | 3 | 椅子搬来4 **td=1** | before_after | PASS |
| 48 | c88410f2 | transfer | 4 | 千步多4千 **td=1** | comparison | PASS |
| 49 | b1a30690 | transfer | 4 | 杯子蓝白分解 **td=1** | everyday_objects? | REVIEW |
| 50 | 05a2649f | transfer | 5 | 书架+5本借4 **td=1** | before_after | PASS |

族分布：comparison 18 · before_after 16 · school_objects 8 · time_schedule 2 · REVIEW 6 · REJECT 0。
迁移题族：comparison ×2 + before_after ×2（+1 REVIEW）→ transfer diversity ≥2 可达 ✅
</content>
