# FE-1432i：三题微增量终复检——155 题全批机器门（Gate 1~3）清零通过

- 复检对象：`FE1432h_3Q_MicroDelta`（3 题重交）+ `FE1432h_Reconciled155_ReviewOnly`（最终合并复审包）
- 复检时间：2026-10-09 21:21 起；仓库 main=62df97d
- **结论：Gate 1 / Gate 2（权威 v2+clock 补丁）/ Gate 3（权威 audit-155-config.mjs）三批全零违规；155 题机器门全部通过，进入 Gate 4~7 抽样 Pin E2E 资格。**

## 1. 三题整改核验（全过）

| 题 | 交付方案 | 权威复跑结果 | 语义复核 |
|---|---|---|---|
| V14-P0-077 | formula-board→number-input，`{min:0,max:200,integer_only}` ans=24 | Gate 3 PASS（基座链） | 题干"4 排×每排 6 把…填总数"承载乘法 ✓ |
| V14-P0-078 | 同上换挂，ans=4 | Gate 3 PASS | "24 张每 6 张一组…填组数"承载除法 ✓ |
| V14-P0-133 | clock `start:[3,0] target:[4,30]` ans=270 | Gate 3 PASS（R17 parser） | swap(4,30)=(6,30)≠target 自环消除 ✓ |

换挂选择（而非改加减）保留 M16/M23 乘除教学目标——能力语义无损，处置优于最小改动。

## 2. 合并复现

`apply_microdelta.py` 对上轮 reconciled_155 复跑：3 替换+152 不变，产物与分发 `FE1432h_Reconciled155_ReviewOnly` **三批逐字段一致**；A42/B86/C27=155、ID/归属保持。

## 3. 全链权威复跑（仓库 main 工具）

- Gate 2 v2（含 FE-1432h clock 数组补丁）：A **0** / B **0** / C **0**；fixtures 基线自验 gold 0 / negative 恰 4 ✓
- Gate 3：专件 PASS 120（A17+B79+C24）/ FAIL **0**；基座链 35 题（number-line/number-input/column-arithmetic/object-counter 通用 config）
- 诊断词终扫（完整 ERROR_VOCAB 19 行）：越表 **0**（077/078 换挂后 pattern 落 number-input {strategy,calc} 行内）

## 4. 状态与下一步

**155_question_bank_delivery_v2（含两轮增量）= 首个通过 Gate 1~3 全链的完整题批。**

下一步（Gate 4~7，验收方执行）：
1. 抽 5%（≥8 题、覆盖 155 出现的全部 renderer 含基座链）→ seed 到 RDS（**QA-Simulator child …0099 链路，正式入库前不落真实池**）
2. pin 下发（FE-1422a）→ 3100/3101 实灌：答题→判分→Evidence→Diagnosis 四段核验
3. 全过后进 FE-1433 qa_replay#7（Gate 8 执行器）回归，再决定正式 seed 入库
4. M01–M42→app_* 映射审批与题批解耦（映射 PENDING 不阻塞 E2E 抽样——pin 直接按 resource_version 下发，不经能力路由）

## 5. 四轮验收史小结

| 轮 | 包 | Gate 3 结果 | 根因 |
|---|---|---|---|
| FE-1432b | trial155 原始 | FAIL 114/122（93%） | 答案轴冲突（真语义错位） |
| FE-1432g | delivery_v2 首版 | FAIL 37 | 我方 §7 守卫未成文 |
| FE-1432h | 37Q+65 词增量 | FAIL 3 | 我方又两条未成文（op 值域/swap 自环） |
| FE-1432i | 3Q 微增量 | **FAIL 0** | — |

教训定版：**FE-1434 契约 FROZEN 输入必须含 parser 守卫全集**；交付方四轮纪律递进（增量制、SHA 校验、隔离副本提案、非权威如实标注），本轮起验收语言完全对齐。
