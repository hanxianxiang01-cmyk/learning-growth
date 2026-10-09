# FE-1438：155 题批 Gate 4~7 抽样实灌底表

## 1. 范围与输入

- 题源：`155_question_bank_delivery_v2` 三轮整改终批（FE-1432i 终检 Gate 1~3 全零，main=16d0a9b 工具）
- 选样口径：任务单 §6 Gate 4~7=抽 5%（≥8 题、覆盖全部出现 renderer）→ 实际**全量覆盖**：19 renderer × 各 1 题（question_id 最小者，确定性）=19 题
- 渲染器全集：A 批含基座链（number-line/number-input/column-arithmetic/object-counter）+ 专件；终批 19 类=发布 19 Gate 全数

## 2. qa_staged 隔离通道（本轮核心设计）

未过 M→app 映射审批的交付题**不得泄入生产池**（QA_DATA_HYGIENE 精神）：

| 面 | published | qa_staged |
|---|---|---|
| v2-catalog（QA 发现端点） | ✅ 可见 | ❌ 不可见 |
| 生产选题（_published_resource_for_ability） | ✅ | ❌ |
| pin 路径（仅 QA child …0099，路由层真实 child 403） | ✅ | ✅（FE-1438 分支 `("published","qa_staged")`） |
| Resource.status | published | draft（双保险） |

- 入库器：`apps/learning-api/scripts/qa_sample_ingest.py`（幂等按 `[QA-Sample] <id>` title；content 保留 question_id/batch 溯源；难度 D1~D5→1~5）
- 隔离红线实测：catalog=20（金题）零泄漏；真实 child pin qa_staged→**403**
- 语义锁单测（test_qa_pin.py +2）：pin 放行集合含 qa_staged / catalog+生产池谓词仍只认 published（源码 inspect 级）
- 审批通过后转正式：`review_status→published`（UPDATE 即可，title 前缀随正式 seed 归档时清理）

## 3. 实灌结果

**API 链（scripts/qa_sample_e2e.py，进程内 ASGI）：19/19**
每题四段：Gate 4 pin 下发（renderer/config 正确）→ Gate 5 Judge（先错 999999=FALSE、后期望=TRUE，双态）→ Gate 6 原子证据=1 → Gate 7 错后 HINT。submission_id 确定性、attempt_no 递增、期望答案 DB 反查防泄题。

**UI 链（e2e/qa-sample-batch.spec.mjs，lab 3100）：19/19**
pinTaskByRvid（pinned-tasks.mjs 新导，直 pin 不经 catalog）→ route 拦截 session 页 → 专件根 testid 可见 + planned-renderer=0 + 交付题干关键词上屏。

## 4. 抓出缺陷（1 个，已修）

- **ObjectCounterV2 expected 形态单栈**：只认 `{group_id,min_count}` 对象数组，交付批=与 groups 平行的数字数组 `[5,3]`（语义相同）→ 拒渲空白卡。修=双形态兼容（数字按序 zip groups 成对象形）；tsc 0 错、金题对象形态回归照跑。
  教训同族：基座链"宽松能吃"（docs/34 §2.2）不等于**语义字段**能吃——R01 expected 是结构化字段不是标量。已补 CONTRACT §2.2 object-counter 行双形态说明（见本 PR）。

## 5. 结论与下一步

- 155 题批：Gate 1~7 全通过（机器门+API 实灌+UI 实灌三层）
- 待办：① M→app 映射审批（题批解耦，pin 不经能力路由不阻塞）；② 审批过 → qa_staged 样本转 published + 全量 155 走正式 ingest（QA 批工具复用）→ FE-1433 replay 作 Gate 8 收官复跑
- QA 卫生：全部 attempt/evidence 落 …0099；真实 child …0001 零触碰
