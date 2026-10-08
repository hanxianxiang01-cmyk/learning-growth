# R19 PatternBoard Vertical Gate 验收底表（FE-1436）

状态：**CLOSED**（2026-10-08）｜ 模板：B5 五件套第十八实例 ｜ 上游：docs/frontend/31 Gap R19（Batch E 收官题）

## 1. Gap R19 条目对照

| Gap 条目 | 要求 | 落地 |
|---|---|---|
| Semantic P0 | sequence / rule / prediction | ABAB 花边（黄蓝黄蓝…）识别周期并预测后续 2 颗 |
| State P0 | pattern construction | beads（空格现值，null=空）+ attempt_history |
| Interaction P0 | select / extend / construct | 调色板点颜色=填第一个空格；点珠两次=选中→抠掉；替换留痕 |
| Response P0 | expected pattern rule | data={visible,beads,pattern_text,period,attempt_history,answer,structure}；answer=空格 token 拼接（12） |
| Evaluator P0 | pattern evaluator | inferPeriod（p∈2..3 最小周期）+ evaluatePattern：EMPTY→PASS(changed_once)→phase_shift→rule_ignored→wrong_sequence |
| Evidence P0 | **尝试顺序、修改过程** | attempt_history=[[slot,from,to]…] 全链（含替换/抠除），E2E-04/07 断言 |
| Diagnosis P0 | **规律识别错误** | rule_ignored（全摆末颗=没找规律）+ phase_shift（周期读对但从末颗重新数）——两种典型"规律识别错"精确分诊 |
| Acceptance P0 | E2E | 11 用例全过（见 §4） |

## 2. 解耦的第九次运用（Gap 原文直接给了原料字段）

Gap R19 Evidence=「**尝试顺序、修改过程**」——这条原料与"答案对不对"正交：
孩子可以试错（摆错→抠掉→改对），最终 beads=[1,2] 答案 12 判对，
但 `structure.changed_once=true`（attempt 次数 > blanks）如实记录"这是一路试出来的"。
**判对+过程留痕**（R08/R15/R16/R18 同形态），E2E-07 双断言实证。
教学含义：一次对 vs 试错后对，对掌握度都算"会了"，但对"策略稳定性"的诊断价值不同——
原料不丢，交给后端观察匹配。

**判错侧双子靶（R14/R15/R17 同形态）**：
- `phase_shift`：[2,1]=整体后移一位——周期读对了但**从上一颗重新数**（真实高频错法）；
- `rule_ignored`：[2,2]=全末颗——完全没看规律的颜色惯性。
parser 三守卫保互斥可达：period 必须存在（p∈2..3）、shifted≠expected（回文退化拒）、
全末颗≠expected（period≥2 自动成立，显式双保险）。

## 3. 与 Gap 原文差异（如实记录）

- token 限 1..5 一位整数 → 答案=拼接整数无歧义（同 R14 数值卡口径）；
  Gap"expected pattern rule"未要求显式规则表达式，规律以 period+beads 结构承载。
- 调色板点选+双点抠除替代拖拽（儿童可靠性口径，同 R07~R18）。
- `pattern_text` 原料用数字串（"1 2 1 2 1 2"）——可读中文名（黄蓝…）由组件渲染层负责，
  Evidence 保持机器口径。
- 原基座 PatternBoard（input 填数）保留在 V2RendererLibrary 作参考；专件已替换路由分支。

## 4. E2E 用例（11 例，首跑全绿）

| 用例 | 验证 | 结果 |
|---|---|---|
| E2E-01 (G1) | 4 固定珠+2 空格+两色调色板 | ✅ |
| E2E-02 (G2) | 没填满拦提交（EMPTY，"还差 1 颗"） | ✅ |
| E2E-03 | 正解黄蓝填满→PASS+toHaveCSS 底色断言 | ✅ |
| E2E-04 (G4/G6) | envelope：type=pattern_board、answer={value:12}、beads=[1,2]、attempt_history=[[0,null,1],[1,null,2]]、changed_once=false、PATTERN_BEAD_PLACED×2、无泄漏 | ✅ |
| E2E-05 | rule_ignored 专项：[蓝蓝]→false+HINT+"全摆成一种颜色" | ✅ |
| E2E-06 | phase_shift 专项：[蓝黄]→false+"从上一颗重新数" | ✅ |
| E2E-07 | **解耦靶**：摆错→双点抠除→改对→correct=true + changed_once=true + attempt>2 | ✅ |
| E2E-08 (G5/G7) | 修正路径：rule_ignored→换→phase_shift→再换→PASS→NEXT_TASK | ✅ |
| E2E-09 | RESET 回全空+拦提交 | ✅ |
| E2E-10 | dblclick 防重入=1 attempt | ✅ |
| E2E-11 | healing 皮肤同链判对 | ✅ |

## 5. API 实证记录（pin=1723d78a-44c9-419d-82d4-7a9f6a48520a）

① pin 下发 pattern-board；② rule_ignored 22→false+HINT；③a 重放同 attempt_id；
③b 异内容 409；④ PASS 12（changed_once=true 形态）→true+NEXT_TASK；⑤ phase_shift 21→false。

## 6. Batch E 收官 + V1.4 Renderer 全清

**4/4**：Ruler(R16) ✅ Clock(R17) ✅ MoneyBoard(R18) ✅ **PatternBoard(R19) ✅**。
**Vertical Gate 总进度 19/19 —— V1.4 全部 19 个 Renderer 竖切闭环完成。**
进入 V1.4 收官四件套：FE-1432 题库入库 → FE-1433 qa_replay#7 → FE-1434 契约 FROZEN → FE-1435 立版。
