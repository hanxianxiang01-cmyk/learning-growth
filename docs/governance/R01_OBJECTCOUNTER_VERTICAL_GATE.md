# R01 ObjectCounter Vertical Gate（FE-1414）

状态：**CLOSED**（2026-10-04）｜ 模板：B5 五件套第二实例 ｜ 上游：docs/frontend/31 SEM-1410 / Gap R01

## 1. 组件与语义

object-counter（V2 mode `count_compose`）：组内摆物（add/remove）→ 合并（compose）→ 拆分（decompose）→ 总数即答案。
- 语义边界（Gap R01）：能表达"部分-整体合成、比较增减"；不能表达位值/时间/度量（各有专组件）。
- locked 组=题目给定的堆（不可增删、可作 compose 目标——"放进盒子"合法）；自建组可增删、可拆、可并走。
- 答案唯一来源 = Σ counts；结构 PASS 判据 = 每个 expected 组 effective count（现存+已并入）≥ min_count。

## 2. 五件套对照

| 件 | 实现 | 证据 |
|---|---|---|
| mode Schema（config 字段级） | `objectCounterV2.ts` readConfig（groups/expected/max_total_count 类型守卫，非法→不可开始） | tsc 0 错 |
| 链题 | `resource_seed_v2.py` R01 金题（app_rel d1，school_objects，已 seed RDS） | API 钉题 30 轮命中 |
| Evaluator（独立前端） | `evaluateStructure` 四态（PASS/FAIL/PARTIAL/EMPTY），提交门禁=PASS∪FAIL（P0-01 口径） | R01-E2E-02/03 |
| Evidence/诊断链 | V2 envelope（type=object_count，workspaces.data.groups+total+composed_*，interaction_events UPPER_SNAKE） | R01-E2E-02 payload 合同断言 |
| 浏览器 E2E | `e2e/r01-object-counter.spec.mjs` 10 用例（G1~G7+防重入+revision 重置+事件模型+双皮肤） | 9/9 PASS + healing 1/1 PASS |

## 3. G1~G9 现状

- G1 渲染不降级 ✅（R01-E2E-09）；G2/G3 部分态不提交 ✅（E2E-03）；G4 V2 envelope 完整 ✅（E2E-02 断言 ui_revision/type/groups，无 representation 泄漏）；G5 判对→NEXT_TASK ✅（E2E-01 含 compose 记录 composed_into/composed_count）；G6 错误可提交→HINT ✅；G7 重试 attempt_no=2、单 Task 单证据 ✅；G8 幂等（submission_id）✅ API 级复测重放=409 SubmissionConflict（同 ID 异内容）；G9 V1 回归 ✅（B5-G9 全量重跑 9 passed 零破坏）。
- P1 事件模型 ✅：COUNT_ADDED/COUNT_REMOVED/GROUP_COMPOSED/GROUP_DECOMPOSED/UNDO/RESET 全部入 payload 且可追溯。
- 双皮肤 ✅：healing（3101）同契约同数据结构。

## 4. 与 B5 的差异（模板泛化验证）

1. 提交门禁从"结果位填满"泛化为"结构 engaged 且非 PARTIAL/EMPTY"——语义随组件变，**口径不变**（错误答案必须能到后端）；
2. 新增 compose/decompose 的**过程留痕字段**（composed_into/composed_count），Evidence 不再只有终态；
3. QA child（…0099）首次全程使用——RDS 中真实儿童 0001 的窗口零污染（数据卫生 R1/R3 的第二次实证）。

## 5. 遗留

- decompose 出的新组 label 固定"拆出的N"（皮肤文案待教学设计确认，不阻塞 Gate）；
- R01 金题暂为 1 道（题库天花板），Retention/Transfer 变式题属 V1.4 内容线任务；
- object-counter 的 V1 manipulative 路径（33 题存量）不受本 Gate 影响，回归由 B5-G9 + FE-1411 探针保障。

## 6. Registry 变更

`vertical_gate: "R01"` 新增枚举值（30 号包 Master 的 E 编号与 R 编号体系并存；本 Gate 用 R01 以避免 A1=place-value 撞号）。object-counter 新增 capabilities：add_object / remove_object / compose_groups / decompose_group。
