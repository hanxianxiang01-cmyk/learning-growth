# V1.4 Trial-155 整改交付任务单（v2 批正式下发版）

- 编号：FE-1432d（任务单）
- 依据：《V1.4 Question Bank Production Contract v1.0》（docs/35，下称 PC-v1）+ Trial-155 三轮审计（docs/34）
- 性质：**不是重做一套 155 题**——按 A/B/C 三条整改路径，把现有 trial155 重新交付成可验收版本
- 题目标识纪律：v2 批**沿用 trial155 原 `question_id`**，与审计记录逐题对齐；换 ID 视为新题、按新批全流程重审

---

## 1. 本批次交付判定（总验收原则）

| 批次 | 数量 | 核心动作 | 入库条件 |
|---|---:|---|---|
| **A 类·直接沿用** | ≈45 | 保留原题语义，仅补齐 `hint_ladder` / `goal` / `diagnosis_target` | 三字段完整 + error 词表逐字命中（PC-v1 §9）+ 全部门禁通过 |
| **B 类·语义重导** | ≈77 | 按 Renderer Contract **重做答案轴/交互语义** | 重导后 config、answer、evaluator **三者一致**（验收对象是语义整体，不是 JSON 字段） |
| **C 类·数据修复** | 18 | 修复题目自身数据矛盾 | 一致性机器门通过 |
| **随附申报** | 全批 | M01–M42 映射提案 + 两道门禁报告 | 必须随包提交，缺项整包拒收 |

**分类完整性硬约束**：A+B+C 必须覆盖 155/155 且**每题恰好属于一类**。trial155 审计给出的是参考切分（≈45/77/18），交付方重交时须在 MANIFEST 中逐题给出最终归属；同时命中 B 与 C 的题**归 C 优先**（数据矛盾先修，再谈语义）。MANIFEST 出现未分类/双分类，整包拒收。

## 2. B 类卡死条款：验收对象 = 「题目语义 + config + answer + evaluator」整体

**不接受"字段转换后看起来能过"的交付。** 逐渲染器红线（对应对话中已明确的六例，其余按 PC-v1 §6/§7 同标准执行）：

- `direction-grid`：**不是**把 answer 换个字段名——必须重做为"走到终点格"玩法，答案 = 终点格编码（0-based，`row × cols + col`），路径走 Evidence
- `shape-canvas`：**不是**把形状名换成任意数字——答案必须是渲染器可评估的**面积标量**，且限定 rectangle / triangle 可评估形
- `pattern-board`：**不是**改 `evaluator_type` 字符串就结束——必须重做为 ABAB 周期延续玩法（`visible` 至少两个完整周期 + 目标位可判定）
- `sorting-board`：不允许挂着 sorting-board 的名字做分类的题。**注意：`choice-grid` 不在 V1.4 发布范围**（FE-1417 发布口径 19 项明确剔除 choice-grid/data-table/pictograph/timeline，组件保留运行但 Gate 顺延、无验收 parser）——分类题两条合法出路：① 改造为 sorting-board 数值升序玩法（answer=数字拼接）；② 换挂 `shape-gallery`（R12 已闭 Gate，分类放家计数语义，config 须给 `{target_kind, shapes:[{id,name,kind,color}…]}` 结构化对象）。选 ② 时 MANIFEST `renderer` 列照规列"换挂前→换挂后"
- `clock`：必须**重新生成**符合整点/半点两档语义的题（start/target 分针 ∈ {0, 30}）
- `estimation-canvas`：必须满足实际滑条值域与容差约束（`max ≤ 60`，tolerance 不贴值域边界）

判定手段：我方以 `audit-155-config.mjs`（真实 parser 函数直接吃题包 config）+ 金样例形状比对做 Gate 3 权威审计。字段名全对但语义轴仍错位的题，按 FAIL 处理并在报告中注明"疑似糊弄式转换"。

## 3. C 类定为 P0：一致性审计为前置门，不是附加检查

C 类问题的本质：**Schema 能通过，但实际运行时答案错误**（money `paid − price ≠ answer`、direction 坐标 1 起越界、分针 `:15` 等 18 题实证）。因此本批起验收流水线顺序固定为：

```
Schema（Gate 1）
  → Consistency Audit（Gate 2，PC-v1 §10 六类逐题机器校验）
    → audit-155-config.mjs（Gate 3 Config×Parser）
      → 才允许进入后续 Pin E2E / Judge / Evidence / Diagnosis（Gate 4~7）
        → qa_replay（Gate 8）
```

顺序与 §6 收货动作及 PC-v1 §11 编号**对齐为唯一权威口径**（Gate 2=一致性、Gate 3=Parser）。一致性脚本**不得作为附加检查后置**。两道机器门任一未过的批，后续 E2E 不执行、直接退包。

## 4. 工具归属与判定权

- **Gate 3**：权威判定工具 = 我方仓库内 `apps/child-web/scripts/audit-155-config.mjs`（依赖我方渲染器 parser 源文件，交付环境不可独立运行）。交付方**自检报告可随包附**，但入库判定以我方复跑为准。
- **Consistency Audit**：我方将 PC-v1 §10 六类规则打包独立 Python 脚本（`consistency_audit.py`）随任务单一并发出，交付方可在交付前自跑；我方复跑为终判。
- 两份报告（audit_report / consistency_report）为**随包必备**，缺失即"随附申报未齐"。

## 5. 最终交付包结构（固定，不得增删顶层目录）

```text
155_question_bank_delivery_v2/
├── A_direct_reuse/
│   ├── questions.json
│   └── audit_report.md
├── B_semantic_regeneration/
│   ├── questions.json
│   └── audit_report.md
├── C_data_fix/
│   ├── questions.json
│   └── consistency_report.md
├── ability_mapping/
│   └── M01-M42_app_mapping_proposal.xlsx
├── reports/
│   ├── audit-155-config-report.md
│   └── consistency-audit-report.md
└── DELIVERY_MANIFEST.md
```

### DELIVERY_MANIFEST.md 必填列（逐题 155 行）

| 列 | 说明 |
|---|---|
| `question_id` | 沿用 trial155 原 ID |
| `class` | A / B / C（恰好一类） |
| `renderer` | 归一后 kebab-case；换挂题须列**换挂前→换挂后** |
| `regenerated` | 是否语义重导（bool） |
| `gate3_parser_pass` | Config×Parser 机器门（交付方自检值，我方复跑为准） |
| `consistency_pass` | 一致性机器门（同上） |
| `fail_reason` | 未过题必须给原因；已过题留空 |

## 6. 我方收货动作（对应 PC-v1 §11 8-Gate 链）

1. MANIFEST 完整性检查（155 行、单分类覆盖）——不齐即退，不进入 Gate 1
2. Gate 1~2：Schema + Consistency（我方脚本复跑）
3. Gate 3：`audit-155-config.mjs` 我方权威复跑
4. Gate 4~7：抽 5%（≥8 题、覆盖全部出现过的 renderer）用 pin 机制（FE-1422a）在 3100 实灌 seed→下发→答题→判分→Evidence→Diagnosis 全链
5. Gate 8：qa_replay（FE-1433 产物）
6. 通过部分按批 seed 入库，question_id 与 MANIFEST 对齐归档

**下一轮验收不再人工逐题看 155 题**：Contract → 分类 → 两道机器门 → 抽样 E2E。

## 7. 挂起项提醒

- `hint_ladder` 4 级、首级不得泄露答案（PC-v1 §8）——A 类补齐时同样适用
- `context_family` 只允许受控词表 7 值（trial155 已零越表，保持）
- M→app 映射允许继续标 `TRIAL_MAPPING_PENDING_APPROVAL`，但提案表必须随包；正式入库前须过映射审批
