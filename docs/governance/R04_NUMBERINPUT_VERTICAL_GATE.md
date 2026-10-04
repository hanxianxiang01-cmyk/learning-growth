# R04 NumberInput Vertical Gate（FE-1415）

状态：**CLOSED**（2026-10-04）｜ 模板：B5 五件套第三实例 ｜ 上游：docs/frontend/31 SEM-1413 / Gap R04

## 1. 组件定位

number-input（V2 mode `numeric_answer`）：语义最简的数字答案 Renderer，但承担**双重验证使命**——
1. Gap R04 指认它是 **submission_id 幂等契约（FE-1410）的专项验证入口**；
2. V1→V2 双轨对照面：V1 `kind:"number"` 的 17 道存量题与 V2 number-input 走同一判分内核（content.answer 标量），是分流改造回归的标尺。

## 2. 五件套对照

| 件 | 实现 | 证据 |
|---|---|---|
| mode Schema | `parseNumberInputConfig`（min/max/integer_only 字段守卫，缺省=不设限） | tsc 0 |
| 链题 | R04 金题（app_rel d1 小鸟飞走 7-2=5，before_after，number_input，min0/max20/integer）seed RDS | API 钉题命中 |
| Evaluator | `parseAnswer`：非法/越界/小数(要求整数时)→null=EMPTY 不可提交；合法即 READY 可提交（**对错交后端**，P0-01 口径） | R04-E2E-03 |
| Evidence | envelope data={answer, input_history(尾20)}；事件 NUMBER_INPUT_CHANGED | R04-E2E-02 断言 |
| 浏览器 E2E | `e2e/r04-number-input.spec.mjs` 7 用例 | **7/7 passed**（含 healing） |

## 3. 幂等专项实证（本 Gate 核心）

API 级四连（真实后端+RDS，QA child）：
- 错误答案 3 → 200，correct=false，HINT（可达 Diagnosis 链 ✅）
- 同 submission_id 同内容重放 → **200 且 attempt_id 相同**（权威轨重放 ✅）
- 同 submission_id 异内容（答案被改）→ **409 SubmissionConflict**（契约禁止 ✅）
- attempt_no=2 改对 5 → correct=true，NEXT_TASK ✅

E2E 级：双击提交只发 1 个 POST、1 个 submission_id（按钮 disabled 重入保护）。

## 4. G1~G9

G1 渲染不降级 ✅（不再回落 V1 AnswerComposer，占位符=值域提示）；G2/G3 空/越界/小数拒提交 ✅；G4 envelope 完整（type=number_input、data.answer、input_history、事件）✅；G5 判对→下一题 ✅；G6 错误可提交→HINT ✅；G7 重试 attempt_no=2 ✅（hint→我再想想→清态重填全链真走）；G8 幂等 ✅（§3）；G9 回归 ✅——**全量套件 27 passed**（B5 9 + R01 10+1 + R04 7，零回归）。双皮肤 healing ✅。

## 5. 遗留

- input_history 只进 envelope 不落 attempt 列（response JSON 整体入库，可追溯）；
- number-input 的 V2 金题暂 1 道；V1 `kind:number` 17 题仍走 V1 轨道（正常：schema_version=1.0），两轨并存是迁移期设计而非缺陷。

## 6. 模板计数

Vertical Gate 已闭：**B5（column-arithmetic）+ R01（object-counter）+ R04（number-input）= 3 / 19**。Batch A 剩 ten-frame（R07）。
