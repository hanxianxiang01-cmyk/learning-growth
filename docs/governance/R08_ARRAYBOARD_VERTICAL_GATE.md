# R08 ArrayBoard Vertical Gate（FE-1421）

状态：**CLOSED**（2026-10-07）｜ 模板：B5 五件套第八实例 ｜ 上游：docs/frontend/31 Gap R08（Batch C 起手）

## 1. 组件语义

array-board（V2 mode `array_structure`）：rows × columns / repeated addition——行列建阵列表征乘法。动作四个：加/减行、加/减列；答案=行×列的积。

**product/structure 解耦是本 Gate 的数学点**：
- 摆 4×3（目标 3×4）：积仍 12——**乘法交换律，后端判对**；但 structure evaluator 报 `transpose`（行列概念互换）留痕 Evidence；
- 诊断链由此区分"懂交换律但行列语义混"与"真不会"——Gap R08 Diagnosis P0"行列概念错误"的原料；
- count：行列至少一维数错且不构成转置；EMPTY：没摆（任一行/列为 0）。
- 方阵（target 行列相等）时"转置"即正确摆法——evaluator 先判 exact 再判 transpose，语义自动兼容。

## 2. 五件套对照

| 件 | 实现 | 证据 |
|---|---|---|
| mode Schema | `parseArrayBoardConfig`：target 1~9 整数、max≥target 否则回退 9（保证可达）| node 语义矩阵（含 fallback 语义、双非法拒绝） |
| 链题 | R08 金题（app_model 节点第二题，排队做操 3×4=12，**lineup_position 词表族首题**）seed RDS | API 钉题命中 |
| Evaluator | `evaluateArray` EMPTY→PASS→transpose→count；product 与 structure 独立 | R08-TRANSPOSE/COUNT 双专项 |
| Evidence | data={rows,columns,product,answer,target_structure,structure}；事件 ARRAY_ROW/COL_ADDED/REMOVED（**行列调整轨迹**=Gap R08 Evidence 条目）+ UNDO/RESET | R08-TRANSPOSE envelope 全断言 |
| 浏览器 E2E | `e2e/r08-array-board.spec.mjs` 9 用例 | **9/9 passed**（含 healing） |

## 3. G1~G9

G1 渲染不降级（专件替换基座 ArrayBoard）✅；G2/G3 只加行不加列=积 0 仍 EMPTY ✅；G4 envelope 合同（rows/columns/target_structure/structure.error）✅；G5 3×4→PASS NEXT_TASK ✅；**G6-变体（本 Gate 独有）：transpose 态 FAIL 可提交且后端 correct=true**——解耦端到端实锤 ✅；count 2×5→correct=false HINT ✅；G7 提示后行+1列−1 改对 attempt_no=2 ✅；G8 max=8 越界按钮 disabled、UNDO 一步、RESET、双击 1 POST ✅；G9 全量 **72 passed** 零回归 ✅。双皮肤 ✅。

## 4. 模板增量

1. **"判对但留诊断原料"首个实例**：此前 FAIL 态都伴随 correct=false；R08 的 transpose 是 correct=true **同时** structure.error 非空——证明前端结构判定与后端判分是两条独立可信通道（不互相污染）；
2. **lineup_position 族首题**：治理词表七族里第五族开始有真实覆盖（此前如实记录"启用但零覆盖"的三族之一）；
3. app_model 节点第二题（R02 条形 + R08 阵列——同节点跨 renderer 多样性开始形成）。

## 5. 遗留

- repeated addition 显式化（"3个4"语言标注）可作 hint_ladder 增强——内容线；
- 行/列点击直接定位（现 +/− 步进，同前例替代 drag 口径）；
- R08 金题 1 道；方阵变式（如 4×4）留给题库喂入。

## 6. 进度

**Vertical Gate 9/19**。Batch C 剩 GroupingBoard（R09）/ EstimationCanvas（R11）。
