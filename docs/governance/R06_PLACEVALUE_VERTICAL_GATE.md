# R06 PlaceValue Vertical Gate（FE-1419）

状态：**CLOSED**（2026-10-07）｜ 模板：B5 五件套第六实例 ｜ 上游：docs/frontend/31 Gap R06（Batch B 第二题）

## 1. 组件语义

place-value（V2 mode `place_value_build`）：数位/位值/组成——**数字卡放位值框**（digit movement）。
- config：target（10~999）+ 牌堆 pool=target 各位数字的一种排列（**parser 强制 multiset 相等**——孩子只可能"站错位置"，这正是 R06 Diagnosis P0"位值混淆"的靶）；
- 交互三动作：pick（选牌）→ place（进空框）/ swap（与框内牌对调）/ return（点框收回），另有 UNDO/RESET；
- 答案 = 三框拼出的数；structure evaluator：EMPTY（没放满）→ PASS / **FAIL+place_confusion**（放满但位置错）——混淆分类序列化进 Evidence 供后端诊断原料，判分仍后端权威。

## 2. 五件套对照

| 件 | 实现 | 证据 |
|---|---|---|
| mode Schema | `parsePlaceValueConfig`：target 值域/位数自适应（个十个百）、pool multiset 守卫 | node 语义矩阵全过（含非法 config 双负例） |
| 链题 | R06 金题（**app_rd 能力节点首题**，数字卡回家 352、pool=[2,5,3]，school_objects）seed RDS | API 钉题命中 |
| Evaluator | `evaluatePlaceValue` EMPTY/PASS/place_confusion；swap 语义（框牌回堆、新牌进框） | R06-CONFUSE / R06-SWAP |
| Evidence | data={slots, pool_remaining, answer, target_digits, structure}；事件 DIGIT_PICKED/UNPICKED/PLACED/SWAPPED/RETURNED + UNDO/RESET | R06-CONFUSE envelope 断言（error=place_confusion 入库） |
| 浏览器 E2E | `e2e/r06-place-value.spec.mjs` 9 用例 | **9/9 passed**（含 healing） |

## 3. G1~G9

G1 渲染不降级（专件替换基座 PlaceValue 路由）✅；G2/G3 放两张不第三张仍 EMPTY 不可提交 ✅；G4 envelope 合同（type=place_value、slots=[3,2,5]、structure.error=place_confusion、target_digits=[3,5,2]、PICKED+PLACED 事件齐）✅；G5 全对→NEXT_TASK ✅；G6 混淆 325 可提交→HINT ✅；G7 重试 attempt_no=2（混淆→提示→**swap 修正**→判对）✅；G8 UNDO（pick+place 两步历史）+ 双击防重入 1 POST ✅；G9 回归 ✅——全量套件 **54 passed**（前六套 Gate+B5/R01/R02/R04/R06/R07 零回归）。双皮肤 healing ✅。

## 4. 模板增量

1. **swap 作为修正路径**（R06 独有交互语义）：E2E-SWAP 用例把"站错位的两张对调回来"做成验收动作——牌堆/框双向流动，pool_remaining 归零即结构闭合；
2. **app_rd 节点首题**：继 app_rel（R01/R04/R07）、app_model（R02）后第三个能力节点接入 V2 链；
3. **UNDO 粒度教训**：pick 与 place 各是一步 history（reducer 不感知操作对）——UNDO 用例需按"两步撤销"设计（写进 skill 坑清单）；
4. 新事件词五连（DIGIT_PICKED/UNPICKED/PLACED/SWAPPED/RETURNED）进 contracts 枚举；select 能力已在名单，零新词。

## 5. 遗留

- 两位数/四位数（10~99、1000~9999）：config 自适应已支持（places 按 target 位数生成），链题未配；
- 拖拽（Gap R06 "drag"）以点选两步替代（儿童端可靠性口径，同 R02 步进替代）；
- R06 金题暂 1 道，retention/transfer 变式属内容线。

## 6. 进度

**Vertical Gate 7/19**（A5/B5/R01/R02/R04/R06/R07）。Batch B 剩 FormulaBoard（R10）。
