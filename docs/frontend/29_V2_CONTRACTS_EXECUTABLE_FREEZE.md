# FE-1404 TaskUISchema V2 + MathResponse V2 可执行契约（冻结候选 · V1.0）

> 状态：**可执行 Schema 落地，待内容/前端会签后转正式冻结**。
> 本文件是 `packages/contracts/schemas/*.json`（可执行 JSON Schema，draft 2020-12）的语义说明。
> 上游：《V1.4 P0 Architecture Contract》P0-03/04、《TaskUISchema V2 + MathResponseSchema V2 契约草案 V0.1》、评审 V0.2 §3。
> 协议枚举事实源：`docs/frontend/28_RENDERER_REGISTRY_CONTRACT.md` + `app/content/renderer_protocol.py`（CI 测试强制三处同步）。

---

## 1. 校验分层（可执行入口：`packages/contracts/contracts/validate.py`）

```
JSON Schema 结构层   task-ui-schema-v2 / math-response-v2（additionalProperties:false 全开）
     ↓
协议层               renderer ∈ R-001~R-023 kebab-case 枚举（UNKNOWN_RENDERER_ID）
     ↓
语义层               workspace_id 任务内唯一；事件 sequence 唯一；
                     下发前 is_implemented()——planned 受控拒绝，不降级
```

CI 门禁：`tests/test_v2_contracts.py`（9 用例，含五条纵向链样例、三组非法反例、enum 同步防漂移检查）。

## 2. TaskUISchema V2 字段（与草案 §2 对齐的冻结口径）

必填：`schema_version("2.0" const) / ui_revision / prompt / workspaces / response_contract`；可选 `hint_targets / accessibility`。

工作区必填 7 项：`workspace_id / renderer / renderer_version / mode / config / initial_state / capabilities`，可选 `constraints`。

| 冻结决策 | 口径 |
|---|---|
| `workspace_id` | `^[a-z][a-z0-9_-]*$` + 任务内唯一（校验函数强制，schema 层无法表达唯一性） |
| `renderer_version` | `MAJOR.MINOR` 字符串（如 `1.0`）；未知版本受控拒绝 |
| `mode` | snake_case；mode 专属 config/response Schema 由各 Registry 条目补充（评审 §3.2："该模式才允许发布资源"） |
| `capabilities` | 必须 ⊆ 该 renderer 注册表 interaction_capabilities（当前示例按矩阵口径书写；子集校验随 mode Schema 交付启用） |
| **mode 专属字段级 Schema** | ⏳ 23×mode 逐项交付，见 §5 待冻结清单——本 PR 冻结的是**公共契约**，不含 23 项模式目录 |

## 3. MathResponse V2（提交外层）

外层必填：`task_instance_id(uuid) / attempt_no(≥1) / submission_id(uuid) / response`。
`response` 必填：`schema_version("2.0") / ui_revision / type / workspaces / answer`；可选 `interaction_events`。

**架构不变量（additionalProperties:false 机器强制）**：
- ❌ 客户端不得提交 `correct / ability_level / evidence_role / diagnosis`（反例样例 `illegal_client_selfgraded.json` 验证被拒）；
- ✅ 数学错误 = 合法 Schema 的 answer（错误不拒收，进 Evaluator）；
- ✅ 缺必需结构/非法类型 = 契约错误（不进评分）。

**幂等契约（评审 §3.1 口径）**：
- `submission_id`：一次儿童明确提交生成；网络重试=同 ID 同内容 → 返回原 Attempt；同 ID 不同内容 → 409 冲突；
- `attempt_no`：服务端校验顺序号，**不充当幂等键**；
- ⚠️ 现状：后端幂等键仍是 `(task_instance_id, attempt_no)`；`submission_id` 落库 + 唯一索引 = V2 资源上线前的后端迁移项（记 §5）。

**交互事件**：`event_id / sequence(唯一) / event_type(SNAKE_UPPER) / actor(learner|hint|system) / payload / workspace_id`。actor=hint 标注提示代填；缺失事件不推断孩子不会（评分只看结构，过程证据不足单独标记——归 Evaluator 规则，不在 Schema 层）。

## 4. 五条纵向验证链（草案 §3.2）

| 链 | renderer | 样例 | 下发判定 |
|---|---|---|---|
| B5 | column-arithmetic | ui_schema/b5_valid.json（+ examples 全量 Attempt） | planned → 拒绝下发 |
| A5 | number-line | ui_schema/a5_valid.json | **implemented → 可下发**（V2 首条链） |
| D5 | shape-canvas | ui_schema/d5_valid.json | planned → 拒绝 |
| E4 | ruler | ui_schema/e4_valid.json | planned → 拒绝 |
| F6 | data-table | ui_schema/f6_valid.json | planned → 拒绝 |

A5 的验证意义：number-line 前端已实现（FE-1401），**第一条 V2 链可端到端走通**，不被其余 4 条 planned 组件阻塞。

## 5. 待冻结清单（转"正式冻结"前必须完成）

| # | 项 | 归属 |
|---|---|---|
| 1 | 23 Renderer × mode 字段级 Schema + 合法/非法样例 + Evaluator 正反例（草案 §11 冻结条件） | 内容+后端，随各 Renderer 交付 |
| 2 | submission_id 后端落库（attempts 表列 + 唯一索引）+ 409 冲突路径 | 后端迁移（V2 资源下发前） |
| 3 | capabilities ⊆ 注册表子集校验启用 | 随 mode Schema |
| 4 | 多工作区：展示型 vs 必需工作区、跨区引用规则（草案 §11） | 前后端会签 |
| 5 | V1 适配冻结：50 题 V1 schema 行为不变的承诺写进回归 | QA |
| 6 | 本 schema 挂入权威 OpenAPI（ui_schema/response 现为自由 object）+ SHA256SUMS 重算 | 需与基线 Owner 走 V1.4 基线立版 |
| 7 | TypeScript 判别联合镜像（packages/contracts 导出 TS 类型，前端消费） | 前端 |

**会签通过后**：本文件状态改 FROZEN，`packages/contracts/schemas/` 打版本标签。

## 6. 与 OpenAPI 的关系（本期不改权威 yaml 的理由）

权威 OpenAPI 是 V1.3.1 冻结基线（SHA256 管理），其中 `ui_schema`/`response` 本就是自由 object——V2 契约**不违反** V1.3.1 基线（向后兼容：V1 资源无 renderer_id 也可下发）。V2 立进权威 = V1.4 基线立版动作（含 SHA256SUMS、版本目录 learning-core-v1.4），不单方面修改冻结物。在此之前：schema 以 `packages/contracts/schemas/` 为可执行事实源，CI 防漂移测试保证与代码枚举一致。
