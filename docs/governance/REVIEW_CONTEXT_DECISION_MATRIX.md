# REVIEW 6 题语义裁决矩阵（REVIEW_CONTEXT_DECISION_MATRIX）

> 依据：《V1.4 P0 Governance Closure》§6 三态流程 + 治理原则「context_family 是 Transfer 能力标签，不是表面名词标签」。
> 前置：FE-1402 已 CLOSED（main=699ec39），6 题保持 NULL/REVIEW。
> 裁决日期：2026-10-01。裁决方法：对每题回答"孩子要迁移的**关系结构**是什么"，再看该结构在现有词表中是否有族。

## 1. 逐题裁决

| # | stem 前8位 | 能力 | 题干结构分析 | 核心迁移关系 | is before_after? | is comparison? | 裁决 |
|---|---|---|---|---|---|---|---|
| 1 | `af2cb0d1` | cond | 「4红气球、3蓝气球（+2本书干扰），红蓝一共多少」——两个**静态集合**求和，无变化事件 | 部分-部分-整体（静态合并）+ 条件筛选 | ❌ 无"原来/又/吃了"类变化 | ❌ 无差比 | **维持 REVIEW** |
| 2 | `40d0feb3` | cond | 「5汽车、3火车、2皮球，汽车+火车共几辆」——同上 | 部分-部分-整体（静态合并） | ❌ | ❌ | **维持 REVIEW** |
| 3 | `3706473c` | cond | 「6苹果、2梨、4铅笔，苹果+梨共几个」——同上 | 部分-部分-整体（静态合并） | ❌ | ❌ | **维持 REVIEW** |
| 4 | `76695c2b` | rd | 「小东7球、小西3球，问小西几个」——**无运算**，考对象定位阅读 | 信息定位（读题理解） | ❌ | ❌ | **维持 REVIEW** |
| 5 | `1ab893bf` | rel | 「3袋×每袋7珠共几颗」——等量组求总量，静态 | 等量群（乘法结构前身） | ❌ | ❌ | **维持 REVIEW** |
| 6 | `b1a30690` | transfer | 「18杯共，7蓝其余白，白杯几个」——整体−部分 | 部分-整体分解（减法结构） | ❌ | ❌ | **维持 REVIEW** |

**结论：6 题全部既非 `before_after` 也非 `comparison`**——"猜测可归 before_after/comparison"的路径经逐题检验不成立（无变化事件、无差比关系）。同时全部维持 REVIEW/NULL。

## 2. 治理发现（本次裁决暴露的真问题）

6 题不是散落的特例，而是一个**同构族**：静态"部分-整体/等量群"结构。证据是词表内部的自相矛盾：

| 结构完全相同的题 | 已裁决 | 差异 |
|---|---|---|
| 贴纸12张，5星星其余圆形（`e6f17364`） | PASS → school_objects | 物品=贴纸（学习用品）|
| 杯子18个，7蓝其余白（`b1a30690`） | REVIEW | 物品=杯子（生活物品）|
| 2盒彩笔每盒6支（`f311e9ec`） | PASS → school_objects | 物品=彩笔 |
| 3袋玻璃珠每袋7颗（`1ab893bf`） | REVIEW | 物品=玻璃珠 |

同一能力结构仅因**名词**不同而一族一 REVIEW——这正是治理原则要禁止的"按名词分类"。根因：`school_objects`（指南锚点族）本身按物品场景命名，混入了本应按能力划分的词表。

**正式提案（走 §10 扩展协议，未批准前不写入数据）：**

```
新族 candidate：part_whole
定义：静态的部分-整体关系（合并、分解、等量群），无变化事件、无差比
正例：3袋×7珠共几颗；18杯7蓝其余白；4红3蓝气球共几个
反例：「原来9块吃了3块」(变化→before_after)；「小东比小西多几支」(差比→comparison)
边界：与 before_after 的区分=有无状态变化事件；与 comparison 的区分=是否差比
重叠检查：与现有 6 族均不重叠；school_objects 中学习用品静态题迁移期可双标过渡
覆盖：现有题库 ≥6 题（本次 REVIEW 全部）+ school_objects 中约 5 题同构
```

批准流程按 §10：定义→正反例→重叠确认→覆盖确认→更新词表→更新校验→补测试→Transfer Regression→启用。**本轮不实施。**

## 3. context_family 覆盖率报告（当前权威数据）

| family | 题数 | 迁移题(td非空)覆盖 | 状态 |
|---|---|---|---|
| comparison | 18 | **2** | 启用·有迁移覆盖 |
| before_after | 16 | **2** | 启用·有迁移覆盖 |
| school_objects | 8 | 0 | 启用·静态族 |
| time_schedule | 2 | 0 | 启用·无迁移覆盖 |
| lineup_position | 0 | 0 | 启用·零覆盖 |
| shopping | 0 | 0 | 启用·零覆盖 |
| sharing | 0 | 0 | 启用·零覆盖 |
| (NULL/REVIEW) | 6 | 1(杯子题) | 待 part_whole 裁决 |

**等级可达性推论：**

| 目标 | 门槛 | 现状 | 结论 |
|---|---|---|---|
| L2→L3 | transfer ≥2 族 | comparison + before_after = **2 族已有迁移覆盖** | ✅ 可达路径已打通（FE-1402 成果）|
| L3→L4 | transfer ≥3 族 | 仅 2 族 | 🔴 **生产不可达**，需内容补第 3 族迁移题 |
| L4 requires_explanation 能力 | explanation 证据 | 无写入路径 | 🔴 封死（V1.4 讲题功能，已记 Closure Contracts）|

## 4. E9/E10 内容生产约束（由覆盖率报告推导，写入生产规范）

1. **迁移题族配比硬约束**：每个能力节点的迁移题（transfer_distance 非空）必须覆盖 **≥3 个 distinct canonical family**（对应 L3→L4 门槛），seed 时机器检查；
2. **零覆盖族优先补题序**（对齐 V1.4 五域内容计划）：`shopping`（E8/E9 人民币单元天然供给）、`sharing`（B9 除法平均分）、`lineup_position`（D7/D8 位置方向）、`time_schedule`（E5/E7 时间单元）——五域 Renderer 上线恰好解锁这四个族的场景题；
3. **新题 seed 必带 family**：迁移题 mastery_rule.context_family 为空 = REJECT（不许 NULL 蒙混进迁移池）；
4. **part_whole 裁决**（见 §2 提案）应在 E9 内容批量生产**之前**完成，否则 50 题里的 6 题 + 未来大量静态题将继续堆积 REVIEW。

## 5. 下一步（按既定顺序）

```
✅ REVIEW 6题语义裁决（本文件）
✅ context_family 覆盖率报告（§3）
✅ E9/E10 内容生产约束（§4，待并入 05_Five_Domain_Content_Production_Spec）
        ↓
FE-1403 Renderer Registry Contract（前置输入已具备：题目→mastery_rule→family→transfer→diagnosis 链路稳定）
```

FE-1403 的输入就绪声明：Renderer 层消费的是 TaskUISchema V2（renderer_id + interaction_capabilities），与 context_family 解耦（族属 Assignment/Evidence 层）——FE-1402 保证了 Evidence 侧输入稳定，FE-1403 无需等待 part_whole 裁决。
</content>
