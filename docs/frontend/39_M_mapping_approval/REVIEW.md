# FE-1439：M01–M42 → app_* 能力映射审核（意见稿）

> ✅ **已批复（2026-10-10，见 APPROVAL.md）**：8 条改判采纳 5（M06/M13/M37/M38/M40）、保留 3（M12/M23/M30→app_check 保留、6 题 CONTENT_REVIEW_REQUIRED）。影响题数订正：5 改=25 题（原估约25 ✓）、8 全改=39（原稿未算）。`mapping_final.csv` 已被批复版覆盖（42 行全 APPROVED=仅映射定义批准，非内容放行）。**执行顺序按批复 §3**：PR 留痕→M30 定向修复→qa_staged 应用 final_app_id 验证→staging Gate 8→published 全量。跨批次约束：本表不自动继承 3,108（M42 68 题 is_transfer=false 须逐题复审）。

- 审核对象：`155_question_bank_delivery_v2/ability_mapping/M01-M42_app_mapping_proposal.xlsx`（42 条提案，status=TRIAL_MAPPING_PENDING_APPROVAL）
- 审核锚点：`ability_seed.py` 7 节点定义 + 20 道 V2 金题 `GOLD_RESOURCES_V2` 的 renderer→ability 先例 + 155 题逐题行为交叉
- 定稿表：`mapping_final.csv`（42 行含 verdict 列：34 ACCEPT / 8 PENDING_CHANGE）
- **状态：意见稿。PENDING_CHANGE 8 条待负责人批复后转 `APPROVED` 并执行下游（改 qa_staged ability_id→转 published→全量 ingest→Gate 8）**

## 1. 基础核验（机器比对，全过）

| 项 | 结果 |
|---|---|
| 提案 proposed_app_id vs trial_app_id 两列 | 42/42 一致，0 矛盾 |
| 155 题 `ability_id` vs 提案 trial 映射 | 155/155 一致，0 偏差 |
| M 号覆盖 | 题池用到的 M 全部在提案内，无遗漏 |
| 能力分布 | rel 60 / cond 35 / rd 19 / model 16 / check 14 / strat 8 / transfer 3 |

## 2. 审核口径说明

- 交叉审计曾标出 33 条"题行为 renderer ≠ 该 renderer 金题节点"——**不作为改判依据**：每个 renderer 金题仅 1~2 题、占一个节点，同渲染器承载多能力是设计允许（例如 number-input 可装 rd/rel/strat 类题）。
- 改判只认两种硬证据：① 技能语义与节点定义直接冲突；② 题的实际交互行为（整改裁决后）与所标能力不符。

## 3. 34 条 ACCEPT（无异议）

M01, M02, M03, M04, M05, M07, M08, M09, M10, M11, M14, M15, M16, M17, M18, M19, M20, M21, M22, M24, M25, M26, M27, M28, M29, M31, M32, M33, M34, M35, M36, M39, M41, **M42**。

- **M42→app_transfer 明确采纳**：其 3 题全部 `is_transfer=true`，即 qa_replay #7 迁移证据链题源；账记 transfer 正确（transfer 节点专用于跨情境迁移判定）。

## 4. 8 条建议改判（待拍板）

| M | 技能 | 原案 | 建议 | 硬证据 |
|---|---|---|---|---|
| M06 | 估数与数量感 | app_rel | app_model | 估算=参照量建模行为；金题 estimation-canvas=app_model |
| M12 | 加减混合 | app_rel | app_strat | 2 题走 formula-board 求未知/选符号（7+□=12 类）；金题 formula=app_strat |
| M13 | 加减关系与逆运算 | app_rel | app_strat | 3 题 formula-board 同上 |
| M23 | 乘除关系 | app_rel | app_strat | formula 求未知因数 1/4；grouping 部分留 rel 亦可（整条改 strat 为最小一刀） |
| M30 | 检验与解释 | app_check | app_model（或保留赌下批） | 6 题实际=ruler/estimation/pattern 读数题，无"回代检验"行为 |
| M37 | 时刻认识 | app_rd | app_cond | 认时刻=辨长短针职责；金题 clock=app_cond；app_rd 定义=读题面已知/所求 |
| M38 | 时间先后与经过 | app_check | app_rel | 经过时间=数量关系（3:00→4:30=90 分），非验算 |
| M40 | 总价与找零 | app_rel | app_strat | 4 题 FE-1432g 已全部改造成凑付行为；金题 money=app_strat |

改判成本：仅动 `ability_id` 一字段（题/答案/诊断链不动），约 25 题记账归属变化；**无 Gate 重跑**（G4~7 与 ability 无关；G8 只看 transfer 链，M42 不在改判列）。

## 5. 批复后的执行清单（顺序）

1. `mapping_final.csv` verdict 列转 APPROVED，本文件状态转 DONE，PR 签署留痕
2. qa_staged 19 样本 + 全量 155 正式 ingest 时按 final_app_id 落 `Resource.ability_id`（改判 8 条以新值入库）
3. `qa_staged → published`（一条 UPDATE，FE-1438 通道预留）
4. 全量 155 正式入库 → FE-1433 qa_replay 复跑（Gate 8 收官）→ 题库线闭环
5. 交付方回函：定稿映射表 + M30 若保留 check 则下批须补真检验行为题
