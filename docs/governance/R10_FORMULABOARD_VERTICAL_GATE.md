# R10 FormulaBoard Vertical Gate（FE-1420）

状态：**CLOSED**（2026-10-07）｜ 模板：B5 五件套第七实例 ｜ 上游：docs/frontend/31 Gap R10（Batch B 收官）

## 1. 组件语义

formula-board（V2 双 mode）：算式填空板。config.tokens 定义算式流（数字/运算符/等号/空槽），answer_slot 指认答案槽。

**equation semantic evaluator**（R10 Evaluator P0）：不是字符串匹配——把填好的算式左右两边**各自求值**核对等式成立性。错误二分类（Diagnosis P0"运算符/数量关系错误"原料，各有金题专项靶）：

| error | 语义 | 判定方法 | 金题靶 |
|---|---|---|---|
| operator | 符号选错（数字全对） | 翻转任一运算符槽可使等式成立 | 7○2=5 填＋ |
| relation | 数量关系错 | 等式不成立且翻符号救不回 | □+4=9 填 6 |

EMPTY=任一槽未填（拦提交，P0-01 口径）；PASS=等式成立。前端弱判产原料，判分后端权威（answer=槽值）。

## 2. 五件套对照

| 件 | 实现 | 证据 |
|---|---|---|
| mode Schema | `parseFormulaConfig`：token 四类校验、恰一等号、槽 1~3、answer_slot ∈ slots、两侧各≤1 运算形态守卫 | node 语义矩阵 20+ 断言（含非法 config 三连、交叉类型键拒绝） |
| 链题 | **双金题**：□+4=9（unknown_number）+ 7○2=5（unknown_operator），均 app_strat 节点，seed RDS | API 钉题双命中（mode 区分） |
| Evaluator | `evaluateFormula` EMPTY/PASS/operator/relation；数字键盘多位追加/上限拒/首位 0 拒；符号替换 flagged | R10-RELATION / R10-OPERATOR |
| Evidence | data={filled, answer, structure{status,error,equation}}；事件 SLOT_ACTIVATED/NUMBER_FILLED/NUMBER_REPLACED/OPERATOR_FILLED/OPERATOR_REPLACED/SLOT_CLEARED+UNDO/RESET——**修改顺序、替换过程**（Gap R10 Evidence 条目）即此事件序列 | R10-G7 断言 OPERATOR_REPLACED 在链上 |
| 浏览器 E2E | `e2e/r10-formula-board.spec.mjs` 9 用例 | **9/9 passed**（含 healing） |

## 3. G1~G9

G1 渲染不降级（专件替换基座 FormulaBoard）✅；G2/G3 清空退回 EMPTY、SLOT_CLEARED 留痕 ✅；G4 envelope 合同（type=formula_board、filled、structure 二分类各自断言）✅；G5 PASS→NEXT_TASK ✅；G6 FAIL（relation 与 operator 各一）可提交→HINT ✅；G7 重试 attempt_no=2 + 符号替换改对 ✅；G8 UNDO 步粒度（activate/追加各一步）、双击防重入 1 POST ✅；G9 回归 ✅——全量套件 **63 passed**（前七套 Gate 零回归）。双皮肤 healing ✅。

## 4. 模板增量

1. **V2 首个非数字答案链**：answer="-"（字符串）端到端跑通——`_judge` 文本分支、envelope numericOrText 原样透传、后端 str 比对全链路验证；
2. **双金题一 Gate**：R10 的两个错误分类各配一道靶题，E2E 把"分类提示文案→证据字段→后端判分"三层对齐断言；
3. **app_strat 节点首题**（第四个能力节点：app_rel→app_model→app_rd→app_strat）；
4. 键盘交互（activate→keypad→fill/clear）事件全留痕——"修改顺序、替换过程"从 Gap 条文变成可回放的 interaction_events。

## 5. 遗留

- 乘法算式（Gap 提 relation 广义）不在本 Gate 范围——tokens 形态守卫限"两侧各至多一个 +/−"，× 属后续内容扩展；
- comparison/多槽混合题待题库喂入时补；
- structure 判定与后端判分独立（前端原料、后端裁决）——diagnosis_v2 接线属引擎线。

## 6. 进度

**Vertical Gate 8/19**（A5/B5/R01/R02/R04/R06/R07/R10）。**Batch B 4/4 全清**（BarModel/PlaceValue/FormulaBoard + ColumnArithmetic=B5）。Batch C 起：ArrayBoard(R08)/GroupingBoard(R09)/EstimationCanvas(R11)。
