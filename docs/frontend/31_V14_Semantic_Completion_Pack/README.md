# V1.4 Semantic Completion Pack 消费索引（31 号交付）

交付物（原件 + 无损文本抽取）：
- `V1.4 Renderer Semantic Completion Matrix（19 Renderer）.docx`（sem_matrix.txt，1311 行）——六维 Completion Contract + VG-01~05 底表 + A~E 五类验收路径
- `V1.4 Renderer Semantic Completion → Development Gap Matrix.docx`（gap_matrix.txt，1017 行）——R01~R19 逐组件 Development Gap
- `V1.4 Renderer Development Task Breakdown.docx`（task_breakdown.txt，1035 行）——FE-1401~1437 任务拆解 + Batch A~E + DoD
- `开发任务表.xlsx`（task_table.txt）——37 行任务总表（含依赖/验收标准列）

## 1. 交付方基线判定（重要）

交付方工作快照 ≈ **FE-1408 前后**，不掌握此后我们合入的六件事，其状态列大面积过时：

| 交付断言 | 仓库真实状态 | 判定 |
|---|---|---|
| "已有 Runtime Component 4/23" | FE-1409 已交付 23/23 implemented（21 组件文件 + 基座） | ❌ 过时 |
| "submission_id 幂等未完全闭环" | FE-1410 已闭环：真实 RDS DDL + 双轨幂等 + 409 + 防漂移单测 | ❌ 过时 |
| "Vertical E2E 约 40%，B5 未闭环" | B5 Vertical Gate **CLOSED**（G1~G9 浏览器 E2E 10/10，B5_E2E_VERTICAL_GATE.md） | ❌ 过时 |
| "V2 Schema/OpenAPI 未完全冻结" | docs/frontend/29 可执行契约已立（待会签转 FROZEN，口径一致） | 🟡 一致 |
| "现在不能进入单纯 QA，先 Semantic Completion" | 与我们 FE-1409 的诚实口径相同（implemented≠Gate PASS） | ✅ 一致 |

## 2. 编号冲突裁决（治理硬约束）

交付方重新占用 **FE-1401~FE-1437**，与我们已消费的编号**语义完全错开**（如他们的 FE-1410=ObjectCounter，我们的 FE-1410=submission_id 迁移；FE-1414=ColumnArithmetic vs 我们 FE-1411=热修）。**本仓库不采纳其编号**：
- 交付方任务引用一律加前缀映射：`SEM-<他们的号>`（登记、讨论用），执行以我们自有 FE 序列（下一号 FE-1413）立项；
- 交付方的组件任务等价物 = 我们的"B5 五件套模板逐组件打 Vertical Gate"（18 个剩余组件）；
- 交付方框架任务（SEM-1401~1409、1429~1437）多数已有实现或部分实现，见 §3 映射表。

## 3. 交付任务 → 仓库现状映射

| 交付任务 | 我们的对应物 | 状态 |
|---|---|---|
| SEM-1401 Runtime Contract | docs/frontend/26 + contracts.ts + renderer_protocol.py | 🟡 有骨架，按其"8 件套"清单补 RendererDefinition 字段核对 |
| SEM-1402 State Contract | B5 六态（INITIAL→…→RETRY）已在 ColumnArithmetic | 🟡 13 态枚举待推广 |
| SEM-1403 Registry Runtime | 28 号 Registry Contract（23/23） | ✅ DONE |
| SEM-1404/1405 Semantic Event + Adapter | V2 UPPER_SNAKE 事件（docs/29 §…）+ B5 adapter | 🟡 B5 有，其余 18 组件待 |
| SEM-1406 Response V2 Adapter | taskUiSchemaNormalizer V2 分流 | ✅ 基本在 |
| SEM-1407 Evaluator Framework | B5 Evaluator（PASS/FAIL/PARTIAL/EMPTY）仅 1 个 | 🔴 18 个待建 |
| SEM-1408 Evidence Contract | interaction_events 已进 attempt payload（后端） | 🟡 前端证据语义待规范 |
| SEM-1409 Diagnosis Adapter | FE-1406 后端三段判定 DONE；前端消费路径 | 🟡 半 |
| SEM-1410~1428（19 组件 Completion） | B5=其 SEM-1414 **已 CLOSED**；其余 18 按模板打 | 🔴 主战场 |
| SEM-1429/1430 Workspace/Schema→Renderer | TaskRenderer 分流 + registry 路由 | ✅ 基本在 |
| SEM-1431 Submission Contract | FE-1410 | ✅ DONE |
| SEM-1432~1436 VG-01~05 | B5 已实证 VG-01/02/03 半区；VG-04/05 后端链已通 | 🟡 模板升级 |
| SEM-1437 Contract Test（19×11 场景） | 无 | 🔴 待建 |

## 4. Scope 差异：19 vs 23

交付把 Release Scope 收敛为 19，剔除 `choice-grid / data-table / pictograph / timeline`（差集核验：其 19 全在我们 23 协议内）。**裁决建议**：Registry 保持 23（冻结协议枚举不缩）；P0 批次按交付 19 执行，被剔除 4 协议组件已存在、Gate 顺延（不阻塞 V1.4 立版）。

## 5. 有效增量（采纳进治理）

1. **19×6=114 Completion Checkpoints** + A~E 五路径验收 → 把 B5 五件套模板升级为正式底表（G1~G9 与之互补：G 管联调缺陷，Checkpoint 管语义完备）；
2. **Batch A~E 分批**（基础数量→结构运算→关系→几何→生活数学）→ 采纳为执行顺序，但**Batch A 起手工改为与交付协商**（见下轮讨论）；
3. **禁止条款 20.1~20.4**（Component 不 fetch / 不自判 Diagnosis / 不改 AbilityState / DOM Event≠Semantic Event）→ 写入 review checklist；
4. **开发顺序不可倒置**（Contract→Runtime→Event→Response→Evaluator→Evidence→Diagnosis→Renderer→Acceptance）→ 与 B5 实践一致，确认。

## 6. 消费动作

登记入仓（本目录），不触发批量开发。执行立项按自有 FE 序列走 PR 流程；`qa_replay #7` 等已知项口径不变。
