# Contract Drift Register

用于记录“运行实现”与“冻结接口/Schema”之间的已知差异。

任何 Worker 遇到接口不一致时，先登记，再开发适配层。

| ID | Contract | Current Implementation | Frozen Baseline | Status | Resolution |
|---|---|---|---|---|---|
| DRIFT-001 | Session Result | Child Web V1.2 已接 `getSessionResult()`，包含 `learning_behaviors / ability_changes / next_recommendation` | `learning-core-v1.3.1` OpenAPI 尚未包含该Endpoint | 🔴 OPEN | 后端更新权威OpenAPI；前端当前以可配置Path + Normalizer过渡 |
| DRIFT-002 | Mastery Closure | 运行代码 L1→L2 无条件升级；turn_service 仅写 attempt_standard；Transfer 不足按 0 处理 | `learning-core-v1.3.1` 已冻结真实 L1→L2 / transfer_window / review_required 原则 | 🟢 RESOLVED | 四 PR 收口并激活 mastery-v1.3.1：PR-A(B1+B2+B3 #15) Atomic Evidence Truth；PR-B(B4+B5 #16) Evidence Coverage；PR-C(B6+B7 #17) Derived Evidence+L4；PR-D(B8 #18) Review→Curriculum；FE-1315(#19) QA replay 14/14 → RULE_VERSION 切 mastery-v1.3.1 |

## Rules

### OPEN
允许存在临时Adapter，但：
- 不得宣称冻结Contract已更新
- 不得把临时路径硬编码成架构真相

### RESOLVED
必须记录：
- resolved version
- commit / PR
- 新基线位置
- consumer迁移状态

Contract Drift不是Bug清单，而是**跨工作者接口真相同步清单**。
