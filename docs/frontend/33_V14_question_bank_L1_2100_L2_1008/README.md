# 消费索引：V1.4_Question_Bank_L1_2100_L2_1008_Package（FE-1432 核对轮，2026-10-08）

**结论：不入库。** 本包为"结构骨架齐、内容层空转"的 production-draft，
四道闸全不过（详见判定表）。原件（JSON + README）已存档本目录作追溯基线。
与旧包 `V1.4_Complete_Question_Bank_Package`（210 题）同源同病、且覆盖更大——
判定口径不变：**逐题有真文本、有答案、过词表，才谈入库**。

## 包概况（实测）

| 断言 | 实测 |
|---|---|
| L1 Core 2,100（42 能力 × D1-D5 × 10 变式） | ✅ 条数一致（`L1_Core` 2100） |
| L2 Dynamic 1,008（42 × 24） | ✅ 条数一致（`L2_Dynamic` 1008） |
| 合计 3,108 | ✅ |
| 每题 20 字段结构 | ✅ 3108 题字段数全一致 |
| status | `production-draft`（README 自declare需逐题 QA 后才可 live seeding） |

## 判定表（交付断言 vs 仓库事实）

| # | 交付声明 | 核对结果 | 判定 |
|---|---|---|---|
| 1 | 已加入 renderer_id / TaskUISchema v2 / Response / Evaluator / Diagnosis / Evidence 字段 | 字段**名**在，值全是套话：`task_ui_schema_version:"v2"`（无 schema 实体）、`diagnosis_target:"E01-E07"`（3108 题一字不差）、`expected_evidence:"interaction_event + submission + evaluator_result"`（模板串） | ❌ 有字段无契约实体 |
| 2 | 题目内容 | **3108/3108 prompt 全为模板占位句**（`围绕「X」完成N层任务；题型Y。要求独立完成并提交可验证结果。`，2100 条去重后仅按能力×难度×题型组合） | 🔴 无一真题 |
| 3 | 答案 | **0/3108 含 answer 字段**——判分链无法建立 | 🔴 致命 |
| 4 | context_family | 10 个自造值（error_detection/strategy_choice/transfer_context/multi_representation/explanation_check/direct_numeric/visual_representation/missing_value/inverse_relation/context_problem）——**全部不在我方受控词表 7 词**（CONTEXT_FAMILY_VOCABULARY：school_objects/comparison/before_after/lineup_position/shopping/sharing/time_schedule）。这 10 值语义是"题型维度"不是"情境族"，概念错位 | ❌ 词表闸不过 + 语义轴混用 |
| 5 | M01–M42 能力映射 | 42 个 provisional ID，未映射 canonical 7 节点（app_rd/cond/rel/model/strat/check/transfer）；README 自declare"正式 Ability ID 尚未冻结" | ❌ 映射闸不过 |
| 6 | "19 renderer 覆盖" | 实测 **17 类**（PascalCase 未归一 kebab）；**缺 ten-frame、estimation-canvas**——我方已闭 Gate 的 R07/R11 两组件在包内零覆盖 | ❌ 覆盖断言不实 |
| 7 | question_role / variant_group_id / retry_of | BASE/VARIANT/RETRY/TRANSFER/CHALLENGE/PRACTICE/REVIEW/DIAGNOSIS 八角色 + 84 条 retry_of 非空 + variant_group 分组——**语义与我方复习调度/重试链吻合** | ✅ **本次唯一净增量，采纳进治理口径** |
| 8 | NumberInput 承载 M25 | M25→number-input 映射存在，但 number-input 已闭 Gate（R04），可承接 | 🟡 可用（前提是有真题） |

## 与旧 210 题包的关系

同一交付方的迭代版：从 210 → 3,108 是**矩阵展开**（42 能力 × 难度 × 题型 × 变式的笛卡尔壳），
不是内容扩充。旧包四道闸（M01-42 映射/词表批准/缺 config/文本答案混形态）在新包上一条没解，
反而新增两个缺口（renderer 覆盖谎报、diagnosis 常量套话）。**"Gate 打完一道喂一道"口径维持不变**：
现在 19/19 Gate 已全清，喂题的技术前提就绪，但**题库本身还没到可喂的状态**。

## 采纳项登记

1. `question_role` 八角色体系（BASE/VARIANT/RETRY/TRANSFER/CHALLENGE/PRACTICE/REVIEW/DIAGNOSIS）
   → 与 FE-1433 qa_replay / 复习调度设计对齐时作为输入语义参考；
2. `variant_group_id` 分组 + `retry_of` 链 → 正式题库入库时的溯源字段格式参考；
3. 42 能力命名清单（M01-M42 ability_name）→ 后续 M→app_* 映射表的原料。

## 下一步建议（FE-1432 重定义）

原计划"210 题入库"与本轮 3,108 包入库**同因搁置**：内容层未就绪。
FE-1432 改口径为——**等待交付方补齐四件套后启动**：
① 真题文本（非模板句）② 逐题 answer ③ config（V2 renderer 参数实体）④ context_family 按我方词表重标（或走 §10 词表批准协议新增族）。
补齐前 V1.4 收官链不阻塞：FE-1433 qa_replay#7、FE-1434 契约 FROZEN、FE-1435 立版
均可基于现有 20 道金题推进。
