# Gate 0：基线差异确认（R-MASTERY-CLOSURE 复核证据）

> 依据：《V1.4 评审问题与开发前置项 V0.2》§5 步骤 0——"技术负责人确认最新代码基线与 9 月 29 日快照差异；提交号、已有 Closure 证据及未合入清单；不得只用口头状态。"
>
> 本文即该步骤的书面完成证据。核对人：技术侧（WorkBuddy 代理执行，逐项附提交号与代码行号）。
> 核对日期：2026-09-30。当前 `main` HEAD：`e22ae59`。

---

## 1. 两个基线的定位

| 基线 | 提交范围 | 说明 |
|---|---|---|
| **评审依据快照**（9/29 代码包） | ≤ `b6faa4b`（PR #13，persist_mastery_state 初版） | 评审 V0.2 文中"每次 correct 非 NULL 均写 attempt_standard、L1→L2 直接升级、rule_version=mastery-v1.3、缺 Transfer 返回 0"的描述与该快照一致 |
| **当前 main** | HEAD = `e22ae59`（PR #24） | 快照之后的增量 = **PR #14 → #24**，共 11 个合入 |

快照之后的完整提交链（`git log --oneline`，旧→新）：

```text
ba7dade  #14  FE-1310 V1.3 Mastery Closure 前端对齐
55247c9  #15  FE-1311 PR-A Atomic Evidence Truth（B1+B2+B3）
650fc74  #16  FE-1312 PR-B Evidence Coverage Truth（B4+B5）
ac23176  #17  FE-1313 PR-C Derived Evidence + L4（B6+B7）
02972a3  #18  FE-1314 PR-D Mastery→Curriculum Closure（B8）
4f0b57c  #19  FE-1315 QA replay 14/14 → 激活 mastery-v1.3.1
883a170  #20  docs  DRIFT-002 关闭同步治理文档
45cde3a  #21  FE-1316 权威 OpenAPI 补 Session Result（关闭 DRIFT-001）
a78d3e9  #22  docs  V1.3 Closure Contracts
da7352e  #23  chore CI 新增 backend-tests job
e22ae59  #24  FE-1401 V1.4 Frontend P0 合并
```

---

## 2. 评审点名问题逐项复核（旧结论 → 现状 → 证据）

### 2.1 P0-1 Mastery 证据闭环（评审 §2.1 末段点名的实现缺陷）

| 评审旧结论（基于快照） | 当前状态 | 证据 |
|---|---|---|
| `turn_service.py` 对每次 correct 非 NULL 的 Attempt 均写 `attempt_standard` | ✅ **已修复**：仅该 Task 无有效原子证据时写入一次（首个可评分 Attempt）；类型按 Assignment 角色映射 | `turn_service.py:138`（ATOMIC_EVIDENCE_TYPES 查重跳过）、`:147`（EVIDENCE_ROLE_TO_TYPE）；PR #15 |
| Mastery 规则版本写 `mastery-v1.3` | ✅ **已激活** `mastery-v1.3.1`，且消除硬编码改引常量 | `education_rules.py:14`、`turn_service.py:25,158`；PR #19 |
| `mastery.py` 缺 Transfer 时返回 0 | ✅ **已修复**：coverage 不足返回 `None` + 结构化 reason（`insufficient_context_families` / `insufficient_sessions` / `no_transfer_evidence`），mastery_score 缺维=NULL 不重归一 | `mastery.py:349,357,359,365`（collect_evidence + reason codes）；PR #16 |
| L1→L2 路径存在直接升级 | ✅ **已修复**：真实 Gate（≥5 证据、≥3 资源、≥2 session、C/I/S 阈值、≥4/5 任务 hint≤2） | `mastery.py:301-330`；PR #15 |
| 冻结 DDL 无 Assignment 角色字段 | 🟡 **部分落地（应用层）**：`evidence_role`/`task_purpose` 写入 `task_instance.strategy_policy`（JSONB，免 DDL）；**DB 列级字段与唯一约束未做** | `learning.py:235-252`；PR #15/#18 |

**评审 §2.2 要求的关闭证据核对：**

| 关闭证据项 | 状态 | 位置 |
|---|---|---|
| 首错后改正确的单 Task 单证据测试 | ✅ | `tests/test_mastery.py`（27 用例）+ QA replay #5 + 生产验证（session d5177cbe：8 作答 3 证据） |
| standard/transfer/retention 三角色回放 | ✅ | QA replay #7 + 生产验证（attempt_transfer、retention_check 均已落库，rule=v1.3.1） |
| 缺证据 NULL 与 coverage | ✅ | `test_b4_transfer_single_row_is_insufficient` 等 5 个 coverage 用例（PR #16） |
| L0→L4 升级与 Review 链 | ✅ | 14/14 回放：`scripts/qa_replay_mastery.py`（PR #19）；生产：app_strat 于 16:20 按真实 Gate 升 L2 |
| 并发重试幂等 | ✅ | BUG-1315（attempt_no 递增 #12）+ 后端提交幂等（F6） |
| 生产数据脏证据清理 | ✅ | 3 条非首条原子证据已作废（valid=false），AbilityState 重算 |

### 2.2 P0-2 TaskUISchema V2 / Response V2（评审 §3）

| 评审旧结论 | 当前状态 | 证据 |
|---|---|---|
| V2 任务界面与作答契约未接线 | 🟡 **前端 P0 底座已合入，V2 契约未冻结**：Renderer Registry（5 renderer + 安全降级）、Workspace API（can()/capability 门控）、`renderer_id`/`interaction_capabilities` 判别字段、`interaction_events`、AttemptResult/Hint normalizer | PR #24（e22ae59）；`src/features/task-renderer/rendererRegistry.ts`、`math-workspace/workspaceApi.ts`、`contracts.ts` |
| 23 项 Renderer ID 注册表 + kebab-case 协议枚举 | 🔴 **未做**（前端注册表当前 5 个 renderer；R-001~R-023 全量枚举、可执行 JSON Schema、OpenAPI 同步均待冻结） | 见 §3 未合入清单 |
| submission_id 幂等 | 🔴 **未做**（当前幂等键仍是 (task_instance_id, attempt_no)） | 见 §3 |

### 2.3 P0-3 诊断兜底（评审 §4.1 末段）

| 评审旧结论 | 当前状态 | 证据 |
|---|---|---|
| `diagnosis.py` 按 error_model 或 hint 等级兜底给 E01/E05 | 🔴 **仍未改造**（V1 语义与冻结 E01~E07 契约一致，但"无证据兜底"正是评审点名要移除的） | `diagnosis.py:50,55`（`_fallback_by_hints` 仍在）——**属实，未修** |
| `learning.py` 对任何错误可选资源第一条 error_model | 🔴 **仍存在**（`turn_service`/`learning` 中 error_models[0] 选取逻辑未变） | PR #15~#19 未触碰该文件；**属实，未修** |
| top_level_code 可为 NULL、observation/candidate/confirmed 三段 | 🔴 **未实现**（属 V1.4 诊断 V2 改造，评审自身也定位为"步骤 3"） | 未合入，见 §3 |

> 注：评审文档把诊断 V2 列为开发前置步骤 3（V1.4 范围内动作），**不是** V1.3 Closure 的欠账。此处如实标注"未修"是划归 V1.4，不构成 R-MASTERY-CLOSURE 阻塞。

---

## 3. 未合入清单（评审要求列明）

| # | 欠账 | 归属 | 说明 |
|---|---|---|---|
| 1 | **context_family 数据回填** | V1.3 遗留（缺口 1） | 50 题 `mastery_rule` 全 None（seed 写死）→ transfer 覆盖恒 insufficient → **L2→L3 生产不可达**（代码/单测已就绪）。含词表冻结、打标、seed 改造、`turn_service` 补写 ctx 列、存量回灌 |
| 2 | **DB 唯一约束**：valid 原子证据 (task_instance_id) 部分唯一索引 | V1.3 收口 | 评审 §2.1"数据库约束建议"；当前仅应用层查重。需迁移评审定 DDL |
| 3 | **explanation 证据写入路径** | V1.4 | 无"讲题"交互与 role 分配，requires_explanation 能力 L4 封死（已记 Closure Contracts） |
| 4 | **V2 契约冻结包**：R-001~R-023 枚举、判别联合可执行 Schema、OpenAPI/ADR 同步 | V1.4 步骤 2 | 前端 P0 底座已就位，协议冻结待前后端+内容会签 |
| 5 | **submission_id 幂等** | V1.4 步骤 2 | 替换/并存现 attempt_no 幂等，评审 §3.1 已有设计 |
| 6 | **Assignment 字段列化**（evidence_role/task_purpose 从 JSONB 提升为列） | V1.4 步骤 1 收尾 | 评审 §2.1"Task Assignment 必须保存…"——JSONB 已承载，列化+索引+约束待迁移评审 |
| 7 | **诊断 V2 改造**（移除兜底、三段判定、misconception tags） | V1.4 步骤 3 | §2.3 所述 |
| 8 | 调度前置图 DAG / 试运行参数 / QA 执行矩阵执行 | V1.4 步骤 4/5 | 草案态，未执行属正常 |
| 9 | Theme 迁移 math-lab→explorer | V1.4（已冻结决策） | 纯前端机械重构，可并行 |

---

## 4. Gate 结论

**R-MASTERY-CLOSURE 代码级证据：齐备。**
评审 §2.2 列出的六类关闭证据（单Task单证据、三角色、NULL/coverage、L0→L4+Review、幂等、回放）全部有提交号、测试与生产数据背书；`mastery-v1.3.1` 已 ACTIVE（PR #19），CI 门禁含后端 41 测试（PR #23）。

**R-MASTERY-CLOSURE 完整 GREEN 的两个残留前置**（§3 表 #1、#2）：

1. context_family 回填——不阻塞"闭环机制正确"，但阻塞"五域能真实走 L2→L3 以上"。**建议列为步骤 1 的最后收尾项**；
2. DB 唯一约束——防脏数据兜底从"应用自觉"升级为"数据库强制"。需一次轻量迁移评审。

**五域正式 Mastery 业务接线（步骤 1 → 完成后才可启动）**：以本文件 + PR #15~#19/#23 合入记录为前置 Gate 证据，待 §3 #1 #2 关闭后可宣布 R-MASTERY-CLOSURE = GREEN。

---

## 附：核对方法记录

- 提交链：`git log --oneline main`（本地与 origin/main 一致，HEAD=e22ae59）
- 代码行号引用均出自当前 main 工作区文件（非快照记忆）
- 生产数据验证记录：见 2026-09-30 工作日志（session d5177cbe / e56058a0 / f7796256 轨迹回放）
- QA 回放脚本：`scripts/qa_replay_mastery.py`（14/14，可复跑）
