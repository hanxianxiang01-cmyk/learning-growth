# R09 GroupingBoard Vertical Gate（FE-1422）

状态：**CLOSED**（2026-10-07）｜ 模板：B5 五件套第九实例 ｜ 上游：docs/frontend/31 Gap R09（Batch C 第二题）

## 1. 组件语义

grouping-board（V2 mode `equal_groups`）：**平均分物**——12 颗糖分给 3 个小朋友，孩子主动建组、逐组发物、收回、解散空组。与基座"自动均分展示"根本不同：分的过程是孩子的动作，不是渲染结果。

**group structure evaluator**（R09 Evaluator P0），二分类各有金题靶（Diagnosis P0"分组数量/每组数量错误"原料）：

| error | 语义 | 触发 |
|---|---|---|
| count | 组数 ≠ 目标组数 | 2 组各 6（要 3 组） |
| unequal | 组数对但各组不均 | 3 组（5,4,3） |
| PASS | 组数对+每组相等+全发完 | 3 组（4,4,4），答案=每组 4 |

EMPTY=池里还有没发的（**分完才是一个成立的答案**——P0-01 口径下"没分完"连提交资格都没有）。

## 2. 五件套对照

| 件 | 实现 | 证据 |
|---|---|---|
| mode Schema | parseGroupingConfig（items 2~20、target≥2≤items、max_groups 守卫） | node 语义矩阵（含不尽分形态放行、三非法拒绝） |
| 链题 | R09 金题（分糖 12÷3=4，**sharing 族第二题**，app_rel 节点第四题）seed RDS | API 钉题命中 |
| Evaluator | evaluateGrouping EMPTY→count→unequal→PASS（先核组数再核均衡——两错并存时报 count） | R09-COUNT / R09-UNEQUAL |
| Evidence | data={groups[],pool_remaining,answer,target_groups,items,structure}；事件 GROUP_CREATED/REMOVED + ITEM_ADDED/REMOVED=**"分组过程"**（Gap R09 Evidence 条目） | R09-COUNT 断言事件链 |
| 浏览器 E2E | `e2e/r09-grouping-board.spec.mjs` 11 用例 | **11/11 passed**（含 healing） |

## 3. G1~G9

G1 渲染不降级（专件替换基座 GroupingBoard）✅；G2/G3 发 11/12 颗仍 EMPTY（"还有 1 颗没分出去"）✅；G4 envelope 合同（type=grouping_board、groups=[6,6]、structure.error=count、target_groups=3）✅；G5 4/4/4→判对 NEXT_TASK ✅；G6 count/unequal 双 FAIL 可提交→HINT ✅；**G7=count 错→提示→收光重圈第三组 4/4/4→attempt_no=2**（RETRY 不清板语义第 N 次复用）✅；G8 UNDO 单步（给最后一颗撤销→池回 1 变 EMPTY）、双击 1 POST ✅；G9 全量 **83 passed** 零回归 ✅。

## 4. 模板增量 / 本 Gate 独有语义

1. **防丢物约束**：有糖的组不能解散（NOT_EMPTY_GROUP 拒绝码）——必须先收回池子再拆组，物品守恒是分组题的底线（R09-DISMISS 用例）；
2. **修正路径 = 收回+补发**（R09-FIX 用例）：(5,4,3) 点组0 的−、组2 的＋ → (4,4,4)，"平均"被孩子用手做出来而不是被告知——与 R06 swap、R10 符号替换同属"过程即教学"；
3. **不尽分形态放行**：12÷5 组 config 合法，数学上恒 unequal——孩子怎么摆都暴露概念缺口，这是对的（内容线可用来诊断"平均分"理解）；
4. sharing 词表族第二题（R07 糖果袋后），族覆盖 2/7。

## 5. 遗留

- remainder **答案形态**（"每组2余2"）未支持——envelope answer 是标量；除有余数题需内容/判分线扩展（或拆分双槽），记内容线；
- drag 归组以点选替代（同前口径）；
- R09 金题 1 道。

## 6. 进度

**Vertical Gate 10/19**。Batch C 剩 EstimationCanvas（R11）。
