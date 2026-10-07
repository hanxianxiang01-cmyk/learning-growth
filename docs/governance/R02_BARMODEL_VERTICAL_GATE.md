# R02 BarModel Vertical Gate（FE-1418）

状态：**CLOSED**（2026-10-07）｜ 模板：B5 五件套第五实例 ｜ 上游：docs/frontend/31 Gap R02（Batch B 先锋）

## 1. 组件语义

bar-model（V2 mode `part_whole`；`comparison` 纯函数层已支持、链题待补）：条形模型——三根条（部分/部分/整体 或 大/小/差），config 声明两根"读题已知条" + 一根"答案条"。

**本 Gate 的核心卖点 = 模型结构 evaluator（R02 P0"Diagnosis=结构错误分类证据"条目）**。判分不只核答案数字，三根条整体核对，错误分三类且各自 E2E 可达：

| error | 语义 | 触发实例（金题 5+3=8） |
|---|---|---|
| modeling | 已知条没照题摆（读题/建模错） | a 摆 6 → "和题目说的不一样" |
| relation | 结构不成立（整体不比部分长/差不比大条短）——数学上不存在的模型 | c=4 < a=5 → "长短关系不对" |
| calc | 结构成立但数不对（模型搭对算错） | c=9 → "数字再检查检查" |

三类错误序列化进 Evidence `data.structure={status,error,relation}`，后端判分仍权威看 answer——结构证据是给诊断链的原料（前端弱判不越权）。

## 2. 五件套对照

| 件 | 实现 | 证据 |
|---|---|---|
| mode Schema | `parseBarModelConfig`：mode∈{part_whole,comparison}、答案条不许在 known 里、known 恰好两根各≥1、答案可解性守卫（comparison 差≥1）、max_blocks 下限=solved+1 | node 语义矩阵 13 断言全过 |
| 链题 | R02 金题（**app_model 节点首题**，星星 5+3=，school_objects）seed RDS | API 钉题命中（abilities 路由生效） |
| Evaluator | `evaluateBarModel` 三分类优先级 modeling→relation→calc；EMPTY=答案条未碰 | R02-STRUCT 双负例 + calc |
| Evidence | data={bars:{a,b,c}, answer_bar, answer, structure}；事件 BAR_BLOCK_ADDED/REMOVED | R02-E2E-02 全断言 |
| 浏览器 E2E | `e2e/r02-bar-model.spec.mjs` 10 用例 | **10/10 passed**（含 healing） |

## 3. G1~G9

G1 渲染不降级（专件替换基座 BarModel 路由）✅；G2/G3 EMPTY 门禁=答案条没碰不算答案（摆满已知条也不可提交）✅；G4 envelope 合同（type=bar_model、bars 三值、structure.error=calc 留痕、事件齐）✅；G5 判对→NEXT_TASK（PASS 结构证据同报）✅；G6 FAIL 可提交→HINT ✅；G7 重试 attempt_no=2（RETRY 不清模型——减一格改对，R07 同款语义）✅；G8 UNDO 回退一格 + 双击防重入 1 POST ✅；G9 回归 ✅——**全量套件 45 passed**（B5 10 + R01 10+1 + R04 7 + R07 8 + R02 10 零回归）。双皮肤 healing ✅。

## 4. 模板增量

1. **app_model 能力节点首次接入**：R02 是第一条非 app_rel 的 V2 链题——tasks/next 按 ability 路由验证通过，app_model 的 mastery 轨自此有了第一份真实证据；
2. **结构证据 ≠ 判分** 的边界做实：answer 错→correct=false 走后端；结构证据只进 Evidence。前端三分法是"原料"不是"裁决"；
3. comparison 模式的解析/求值/结构规则已进纯函数层并有 node 断言，链题待补（不阻塞 Gate——Gate 验收对象是组件闭环）。

## 5. 遗留

- comparison 金题待补（建议 D2 难度"多几个"情境，与 part_whole 成对）；
- drag/resize 交互（Gap R02 Interaction 条目提到）以 +/− 步进实现替代——儿童端点按比拖拽可靠，事件语义等价（BAR_BLOCK_ADDED/REMOVED）；
- R02 金题暂 1 道，retention/transfer 变式属内容线。

## 6. 进度

**Vertical Gate 6/19**（A5/B5/R01/R02/R04/R07）。Batch B 进行中：下一站 PlaceValue（R06），后 FormulaBoard（R10）。
