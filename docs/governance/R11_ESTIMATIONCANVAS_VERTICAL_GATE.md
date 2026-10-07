# R11 EstimationCanvas Vertical Gate 验收底表（FE-1423）

状态：**CLOSED**（2026-10-07）｜ 模板：B5 五件套第十实例 ｜ 上游：docs/frontend/31 Gap R11（Batch C 收官题）

## 1. Gap R11 条目对照

| Gap 条目 | 要求 | 落地 |
|---|---|---|
| Semantic P0 | estimate / range / reason | 滑条估算 + 近似数 range 语义 + 理由三选一 chip |
| State P0 | estimate → submit → feedback | 五态评估器 EMPTY(estimate)→EMPTY(reason)→PASS→FAIL(too_high/too_low) |
| Interaction P0 | input / selection | drag(滑条) + select(理由)，answer_input capability |
| Response P0 | expected range / target | data={estimate,reason,adjust_history,reference,answer,structure} |
| Evaluator P0 | tolerance / reasoning | evaluateEstimation：方向对 actual、close 粒度对 expected+tolerance；reason 未选=EMPTY 不可提交 |
| Evidence P0 | 估算值、调整过程 | adjust_history 三段式（E2E-06 断言 [20,35,40]）+ ESTIMATE_CHANGED/REASON_* 事件链 |
| Diagnosis P0 | 估算策略错误 | error_models=no_reference_use/too_high/too_low；structure 原料入库（判分仍后端权威） |
| Acceptance P0 | 五状态 | EMPTY×2 / PASS / FAIL(too_high) / FAIL(too_low) 各有 E2E 用例 |

## 2. 判分口径裁决（重要）

后端 `_judge` 是 float 严格相等、range 判分需要动冻结判分链——金题因此锚定小学**近似数**语义：
actual=38 → expected=40（四舍五入最近十），答案唯一；`content.answer=40` 与 config.expected
双守卫在前端 parseEstimationConfig 同式校验（expected==roundTen(actual)、actual 非整十、
expected 是整十、值域 ≤max）。

**与 R08 transpose 解耦同款**：too_high/too_low/close 是前端诊断原料走 Evidence
（correct=false 的 45 提交，structure={status:FAIL,error:too_high,close:true} 入库），
判分权仍在后端。

## 3. E2E 用例（10 例）

| 用例 | 验证 | 结果 |
|---|---|---|
| E2E-01 (G1) | 渲染不降级：滑条+参照+三理由 chip | ✅ |
| E2E-02 | EMPTY estimate 拦提交 | ✅ |
| E2E-03 | 拖了未选理由仍拦（EMPTY reason，五态之二） | ✅ |
| E2E-04 (G4/G6) | envelope 合同：type=estimation_canvas、data 五字段、ESTIMATE_CHANGED+REASON_SELECTED 事件链、无 representation 泄漏 | ✅ |
| E2E-05 | too_high FAIL 可提交 → correct=false HINT（P0-01 口径） | ✅ |
| E2E-06 | 调整过程 Evidence：三次拖动=三段历史 [20,35,40] | ✅ |
| E2E-07 (G5/G7) | 估低→改对：correct=true、NEXT_TASK、attempt_no 递增 | ✅ |
| E2E-08 | 防重入 dblclick 只 1 POST（R04-IDEM 同模式） | ✅ |
| E2E-09 | UNDO 单步回 EMPTY reason 态 | ✅ |
| E2E-10 | healing 双皮肤同链可用 | ✅ |

首跑教训：两次 `await click()` 各自 await 到响应（跨 attempt 边界）测不到防重入——
必须 `dblclick()` 一次真实双击（提交中 disabled 拦第二击）。

## 4. 金题与数据

- **V2-R11-EST-001 书架上大约有多少本书**（app_model 第三题、**shopping 族首题**——
  治理词表"启用但零覆盖"第二族开始有真实数据），已 seed 真实 RDS
- API 实证（走 FE-1422a pin 机制首抽命中）：估 35 未整十→false HINT / 估 48
  too_high 原料→false / 估 40→true NEXT_TASK / 重放同 attempt_id ✅

## 5. 回归与门禁

- 纯函数 node 语义矩阵：五态、noop/replaced 语义、越界/round、config 四守卫全过
- 全量 E2E：连续两轮（收口前）全绿零回归
- tsc 0 / 六 check PASS / 后端 95 passed（防漂移+1）

## 6. Batch C 状态

**3/3 全清**：ArrayBoard(R08) ✅ GroupingBoard(R09) ✅ EstimationCanvas(R11) ✅
（GroupingBoard 按交付方 Batch 序也在 C；C 域"数量关系/操作→结构证据"完成）

**Vertical Gate 总进度：11/19**。下一批 Batch D 几何：ShapeGallery(R12)。
