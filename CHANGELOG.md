## V1.4 Frontend P0

- Renderer Registry：number / object-counter / bar-model / number-line / unsupported。
- Workspace API：能力门控、撤销/重置、Hint 受控 action。
- TaskUISchema：renderer_id / interaction_capabilities / renderer metadata。
- Structured Response：新增 interaction_events。
- HTTP Adapter：AttemptResult / HintResponse normalizer。
- 新增 `/dev/v1.4-qa` 双皮肤契约验证页。
- 合并验收（2026-09-30）：本地补跑 `next build` 通过（交付方执行环境无法装依赖，V14-07 由 REVIEW 转 DONE）；修复 QA 页 fixture 类型标注（TaskResponseSchema）与 check-v14.mjs 非 ASCII 路径解码问题（fileURLToPath）；tsc / check-v13 / check-v14 / governance / release 全过。

# Changelog

所有重要变更统一记录在本文件。

版本规则：

```text
Major.Minor.Patch
```

- Major：架构/产品边界发生重大变化
- Minor：新增完整能力或模块
- Patch：Bug修复、文档、兼容性调整

---


# [Unreleased]

后续开发中的变更先记录在此，正式发版时移动到对应版本号下。

## Done（FE-1423 R11 EstimationCanvas Vertical Gate：B5 模板第十组件，近似数估算+理由，Batch C 全清，2026-10-07）

> Batch C 收官（Gap R11）。estimation-canvas=滑条估算+理由 chip：**判分锚定小学近似数语义**（38≈最接近整十=40，答案唯一，后端 float 相等判分不动冻结链）；tolerance evaluator 的 too_high/too_low+close 粒度是**诊断原料走 Evidence**（R08 transpose 解耦同款口径——方向对情境真值 actual、close 对目标 expected）。Gap"五状态"落地：EMPTY(estimate)→EMPTY(reason)→PASS→FAIL(too_high/too_low) 各有 E2E 靶。

- **纯函数层** `estimationCanvasV2.ts`：parseEstimationConfig（expected==roundTen(actual)、actual 非整十、值域守卫）+ applyEstimate（同值 no-op 不记史）+ applyReason（noop/replaced 语义分明）+ evaluateEstimation 五态 + serialize（estimate/reason/adjust_history/reference/answer/structure）；node 语义矩阵全过。
- **组件** `EstimationCanvasV2.tsx`：滑条+参照+理由三 chip；ESTIMATE_CHANGED/REASON_SELECTED/REASON_REPLACED 事件链，**adjust_history=Gap"调整过程"可回放 Evidence**；未选理由不可提交（"先想再估"纪律）；专件替换基座路由。
- **链题**：R11 金题（书架估书 38≈40，**shopping 族首题**——词表"启用但零覆盖"第二族开始有真实数据；app_model 第三题）seed RDS；防漂移单测+1（后端 94→**95 passed**）。
- **API 实证**（走 FE-1422a pin 机制首抽命中）：估 35 未整十→false HINT；估 48 too_high 原料→false；估 40→true NEXT_TASK；重放同 attempt_id。
- **E2E** `e2e/r11-estimation-canvas.spec.mjs` 10/10（EMPTY×2、五字段 envelope、调整历史 [20,35,40] 断言、G7 估低改对、dblclick 防重入、UNDO 单步、healing）。全量套件 **93 passed** 零回归。
- 底表 `docs/governance/R11_ESTIMATIONCANVAS_VERTICAL_GATE.md`。**Vertical Gate 进度 11/19；Batch C 3/3 全清**。

## Done（FE-1422a QA 确定性钉题：pin + v2-catalog，E2E 永别 band 掷骰子，2026-10-07）

> 背景：R09 收口时全量回归大面积超时，根因=QA child 每轮 E2E 写 attempt → mastery band 漂移 → 旧 buildTaskPool 抽题命中=f(band 历史轨迹)不可复现（docs/governance/QA_PINNED_TASK_PROPOSAL.md 方案 A）。

- **后端**：`app/core/qa.py`（QA_CHILD_ID/is_qa_child）+ `GET /v1/content/v2-catalog`（published+V2 门控同口径，应用层过滤避免方言）+ `tasks/next` 可选 `pin_resource_version_id`——**路由层硬校验仅 QA child（真实 child 403）**，命中直接落题绕过 band/排除，strategy_policy 带 `pinned:true` 审计标记；pin 缺省路径比特级不变。
- **契约**：openapi.yaml 入 spec（catalog 路径 + pin 参数 + 403）；`tests/test_qa_pin.py` 6 用例（守卫在触库前短路，db=None 安全）；后端 89→**94 passed**。
- **E2E**：共享模块 `e2e/pinned-tasks.mjs`（catalog 模块级缓存、每 task 独立 session+pin、renderer#mode 键定位）；**9 个 spec 旧 buildTaskPool/fetchTasks 全数替换**——钉题确定性 100%。
- **QA 池**：`scripts/qa_child_setup.py --reset-bands`（7 能力回 level0/conf0/band(1,1)，仅动 …0099）。
- **验收**：全量 E2E **连续 2 次 83/83 全绿**（第二轮为 band 重置后跑，实证不再依赖运气）。

## Done（FE-1422 R09 GroupingBoard Vertical Gate：B5 模板第九组件，主动建组平均分物，2026-10-07）

> Batch C 第二题（Gap R09）。grouping-board=平均分物：孩子**主动建组、逐组发糖、收回、解散空组**——分的过程是动作不是渲染结果。structure evaluator 二分类各有靶：**count**（组数≠目标：2组×6）/**unequal**（组数对但不均：3组 5,4,3）；EMPTY=池里还有没发的（"分完才是一个成立的答案"）。

- **纯函数层** `groupingBoardV2.ts`：parseGroupingConfig（items 2~20/target≥2≤items/max 守卫、**不尽分形态放行**——12÷5组恒 unequal 数学自洽）+ applyAddGroup/RemoveGroup（**防丢物：有糖组不可解散**）/addItem/removeItem（POOL_EMPTY 拒）+ evaluateGrouping EMPTY→count→unequal→PASS + serialize（groups[]/pool_remaining/answer/target_groups/items/structure）。node 语义矩阵全过。
- **组件** `GroupingBoardV2.tsx`：池子可视化+逐组＋/−/解散按钮；GROUP_CREATED/REMOVED+ITEM_ADDED/REMOVED=Gap"分组过程"事件链；专件替换基座路由。
- **链题**：R09 金题（12糖分3人=每人4，**sharing 族第二题**、app_rel 第四题）seed RDS；防漂移单测+1（后端 88→**89 passed**）。
- **API 实证**：(6,6) count→false HINT；(5,4,3) unequal→false；(4,4,4)→true NEXT_TASK；重放同 attempt_id。
- **E2E** `e2e/r09-grouping-board.spec.mjs` 11/11（**R09-FIX 收回+补发修正路径**、R09-DISMISS 防丢物约束、G7 收光重圈第三组 attempt_no=2、发11/12仍EMPTY、UNDO 单步回 EMPTY、healing）。全量套件 **83 passed** 零回归。
- 底表 `docs/governance/R09_GROUPINGBOARD_VERTICAL_GATE.md`。**Vertical Gate 进度 10/19**。

## Done（FE-1421 R08 ArrayBoard Vertical Gate：B5 模板第八组件，product/structure 解耦首例，2026-10-07）

> Batch C 起手（Gap R08）。array-board=行列建阵列表征乘法；本 Gate 的数学点=**积对≠摆对**：摆 4×3（目标 3×4）时乘法交换律让答案 12 仍**判对**，但 structure evaluator 报 `transpose` 留痕 Evidence——前端结构通道与后端判分通道独立可信、互不污染（**首个"判对但带诊断原料"实例**，R08 Diagnosis P0"行列概念错误"落地）。

- **纯函数层** `arrayBoardV2.ts`：parseArrayBoardConfig（target 1~9 整数、max≥target 否则回退 9 保可达）+ applyRow/ColDelta 钳制 + `evaluateArray` EMPTY→PASS→transpose→count（方阵转置=PASS 自动兼容）+ serializeArrayBoardV2（rows/columns/product/target_structure/structure）。node 语义矩阵含 fallback 语义与双非法拒绝全过。
- **组件** `ArrayBoardV2.tsx`：行/列 +/− 双控 + 实时点阵预览（grid 12 dot 断言）；ARRAY_ROW/COL_ADDED/REMOVED=Gap"行列调整轨迹"；专件替换基座 ArrayBoard 路由。
- **链题**：R08 金题（排队做操 3×4=12）seed 真实 RDS——**app_model 节点第二题 + lineup_position 词表族首题**（治理文档"启用但零覆盖"三族之一开始有真实数据）；防漂移单测 +1（后端 87→**88 passed**，含"非方阵守卫"断言）。
- **API 实证**：**transpose→correct:true**（解耦端到端实锤）；count 2×5→false HINT；PASS→NEXT_TASK；重放同 attempt_id。
- **E2E** `e2e/r08-array-board.spec.mjs` 9/9（TRANSPOSE 专项双断言 correct=true+structure.error、只加行仍 EMPTY、G7 行+1列−1 改对、max 越界 disabled、UNDO/RESET、healing）。**全量套件 72 passed** 零回归。
- contracts 事件枚举补 ARRAY_ROW/COL_*；registry vertical_gate "R08" + add/remove_object。
- 底表 `docs/governance/R08_ARRAYBOARD_VERTICAL_GATE.md`。**Vertical Gate 进度 9/19**。

## Done（FE-1420 R10 FormulaBoard Vertical Gate：B5 模板第七组件，Batch B 全清，2026-10-07）

> Batch B 收官（Gap R10）。formula-board=算式填空板（token 流+空槽），核心=**equation semantic evaluator**：左右两边各自求值核对等式，错误二分类各有金题靶——**operator**（翻符号可救=数对符号错）/**relation**（翻符号救不回=数量关系错）。**V2 首个非数字答案链**（answer="-"）端到端跑通（_judge 文本分支/numericOrText 透传/后端 str 比对全链路验证）。

- **纯函数层** `formulaBoardV2.ts`：parseFormulaConfig（token 四类校验、恰一等号、槽 1~3、answer_slot 存在性、两侧各≤1 运算形态守卫）+ applyActivate/applyNumberKey（多位追加/上限/首位 0 拒）/applyOperatorKey（替换 flagged）/applyClear + evaluateFormula EMPTY/PASS/operator/relation + serializeFormulaBoardV2。node 语义矩阵 20+ 断言全过。
- **组件** `FormulaBoardV2.tsx`：点亮空圈→弹对应键盘（数字盘/＋－大盘）、SLOT_ACTIVATED/NUMBER_FILLED/**NUMBER_REPLACED**/OPERATOR_FILLED/**OPERATOR_REPLACED**/SLOT_CLEARED 事件链——Gap R10 Evidence"修改顺序、替换过程"成为可回放事件序列；专件替换基座路由。
- **链题**：**双金题一 Gate**（□+4=9 unknown_number + 7○2=5 unknown_operator），均 **app_strat 节点首题**（第四能力节点），seed 真实 RDS；防漂移单测 +2（后端 85→**87 passed**）。
- **API 实证**：填 6→relation 证据 correct=false HINT；填 5→PASS NEXT_TASK；选＋→**operator** 证据 correct=false；选−→**字符串答案 correct=true**（V2 首例）；重放同 attempt_id。
- **E2E** `e2e/r10-formula-board.spec.mjs` 9/9（G2/G3 清空退 EMPTY、RELATION/OPERATOR 双分类专项、G7 符号替换改对断言 OPERATOR_REPLACED、键盘越界拒绝+UNDO 步粒度、healing）。全量套件 **63 passed** 零回归。
- contracts 事件枚举补 SLOT_*/NUMBER_*/OPERATOR_* 六连；registry vertical_gate "R10"。
- 环境：Playwright 启动清 test-results 撞 safe-delete bulk 阈值 → **--output=/tmp/…** 绕开（skill 已补）。
- 底表 `docs/governance/R10_FORMULABOARD_VERTICAL_GATE.md`。**Vertical Gate 进度 8/19；Batch B 4/4 全清**。

## Done（FE-1419 R06 PlaceValue Vertical Gate：B5 模板第六组件，位值混淆诊断专项，2026-10-07）

> Batch B 第二题（Gap R06）。place-value=数字卡放位值框（digit movement）；**牌堆 multiset 守卫让孩子只可能"站错位置"**——structure evaluator 产出 place_confusion 原料（R06 Diagnosis P0"位值混淆"落地）。

- **纯函数层** `placeValueV2.ts`：parsePlaceValueConfig（target 10~999 位数自适应 places、pool multiset 强制相等、非法拒绝双负例）+ applyPick/applySlot 三动作（place/swap/return）+ evaluatePlaceValue EMPTY/PASS/place_confusion + serializePlaceValueV2（slots/pool_remaining/answer/target_digits/structure）。node 语义矩阵全过（含 swap 对调回堆）。
- **组件** `PlaceValueV2.tsx`：框/牌堆点选两步交互（儿童可靠性口径替代 drag，Gap 语义等价）、选中态高亮、DIGIT_PICKED/UNPICKED/PLACED/SWAPPED/RETURNED 事件、revision 清态；专件替换基座 PlaceValue 路由。
- **链题**：R06 金题（**app_rd 能力节点首题**，数字卡回家 352，pool=[2,5,3] 乱序，school_objects）seed 真实 RDS；防漂移单测 +1（后端 84→**85 passed**）。
- **API 实证**：混淆拼 325→correct=false HINT（place_confusion 证据入库）；答对 352→NEXT_TASK；重放同 attempt_id；异内容 409。
- **E2E** `e2e/r06-place-value.spec.mjs` 9/9（EMPTY 部分放置负例、CONFUSE 专项断言 structure.error、**SWAP 修正路径**（站错两张对调改对）、G7 混淆→提示→swap→attempt_no=2、UNDO 双步历史、防重入、清态、healing）。全量套件 **54 passed** 零回归。
- contracts 事件枚举补 DIGIT_PICKED/UNPICKED/PLACED/SWAPPED/RETURNED；registry vertical_gate "R06"+select。
- **UNDO 粒度教训**：pick 与 place 各是一步 history，撤销回"牌未拿起"需两步（skill 坑清单已补）。
- 底表 `docs/governance/R06_PLACEVALUE_VERTICAL_GATE.md`。**Vertical Gate 进度 7/19**。

## Done（FE-1418 R02 BarModel Vertical Gate：B5 模板第五组件，模型结构 evaluator 三分法，2026-10-07）

> Batch B 先锋（Gap R02）。bar-model 的独有价值=**结构错误分类证据**：modeling（已知条读错）/relation（模型不成立）/calc（数算错）三类各自 E2E 可达，序列化进 Evidence 供后端诊断原料；前端弱判不越权，判分仍后端权威。

- **纯函数层** `barModelV2.ts`：parseBarModelConfig（part_whole/comparison、known 恰好两根、答案可解性守卫）+ applyBarDelta（钳制）+ solveExpected + `evaluateBarModel` 三分法（优先级 modeling→relation→calc）+ serializeBarModelV2（bars 三值+structure 证据）。node 语义矩阵 13 断言全过。
- **组件** `BarModelV2.tsx`：三行条（+/− 步进、答案条高亮）、结构提示文案按错误分类呈现、BAR_BLOCK_ADDED/REMOVED 事件、revision 清态；专件替换基座 BarModel 路由（TaskRenderer 251 行，V1 路径 318 行保留）。
- **链题**：R02 金题（**app_model 能力节点首题**，星星 5+3=8，school_objects）seed 真实 RDS；防漂移单测 +1（后端 83→**84 passed**）。
- **API 实证**：结构错答 9→correct=false HINT（calc 证据入库）；答对 8→NEXT_TASK；重放同 attempt_id；异内容 409。
- **E2E** `e2e/r02-bar-model.spec.mjs` 10/10（G1/G2G3 答案条 EMPTY 门禁/relation+modeling 双负例专项/G4 envelope structure 断言/G5/G7 减格改对/UNDO/防重入/清态/healing）。**全量套件 45 passed**（前四 Gate 零回归）。
- contracts 事件枚举补 BAR_BLOCK_ADDED/REMOVED；registry vertical_gate "R02"。
- 底表 `docs/governance/R02_BARMODEL_VERTICAL_GATE.md`。**Vertical Gate 进度 6/19**。

## Merged（FE-1417 消费《V1.4 Renderer Completed Pack》交付快照：框架层收编 + 2 个致命缺陷修复，2026-10-06）

> 交付方按 docs/frontend/31 Step 1-10 实际改码后回传整仓快照（zip，315 文件）+ 完成度报告，自称 Contract QA 19/19 全绿但**无 node_modules、未跑 build/E2E**。逐项核对：**其基线=main@83a0e94（FE-1411）**——FE-1412~1416 六件事全部不在其视野，测试脚本大面积回退。只摘框架层增量，绝不整包合并。

- **三方 diff 定基线**（base 候选×交付×当前 main 逐文件核）：qa_replay（明文密码+真实 child）/integration-smoke/b5 spec（真实 child）/CHANGELOG/治理文档/R01·R04·R07 专件——全部 ❌ 拒绝回退，保留我们的。zip 原件**不入仓**（内含 FE-1412 已根治的 RDS 明文密码，存仓=凭据重新进 git 历史）。
- **✅ 采纳框架层**（我们此前缺失的地基）：`rendererContract.ts`（13 态状态机+canTransition+语义事件工厂+evidence builder）、`evaluatorRegistry.ts`（23 evaluator 表，generic 弱判 NOT_EVALUATED 不猜）、`diagnosisAdapter.ts`/`nextTaskAdapter.ts`（后端权威边界）、`V2_RELEASE_RENDERER_IDS` 19 口径入代码、contracts.ts V2 UPPER_SNAKE 事件枚举收编、InteractionEvent 元数据（session/attempt/sequence_no）、QA 页 VG-01~05 看板、check-v14-contracts/release.mjs 两脚本（npm scripts 挂接）。
- **⚠️ 修掉交付方 3 个自测未发现的缺陷**：**A（致命）**stable submission_id 用冒号串 `task:attempt:rev`——后端 `uuid.UUID()` 直接 ValueError→404，所有 V2 提交全灭（其无 E2E 故未暴露；我们全量首跑 4 分钟超时实锤后定位）→ 重写为确定性哈希输出严格 8-4-4-4-12 UUID 形状，同 (task,attempt,revision) 恒定命中幂等轨、attempt_no 变则 ID 变；**B** evidence/evaluation 注入在其 TaskRenderer handleResponseChange（attempt_no 恒=1 且每次 change 重建 runtime）→ 移至 adapter 提交时刻取真实 attempt_no；**C** 其事件枚举混入 13 个状态名（READY/INTERACTING…属状态机不属事件）→ 剔除并注释划界。rendererContract 模块自身也有未跑 tsc 的类型错误（event_type: string 不收窄）→ 一并修。
- **"19/19" 口径澄清（写入消费索引 docs/frontend/32 README）**：交付的 19/19 是 Contract 结构层；真正打过浏览器 Vertical Gate 的仍只有 5 个（A5/B5/R01/R04/R07），其余 14 个="契约就绪、语义待完成"——与我们 FE-1409 的诚实口径一致，不随交付方升级完成度声明。
- **验证**：tsc 0（含交付模块修正）；check-v14 四脚本（含新收编 contracts/release）全 PASS；governance+hygiene PASS；**全量 Playwright E2E 35/35 passed**（B5 10+R01 11+R04 7+R07 7 双皮肤零回归——stable submission_id 重写后幂等轨端到端实锤）。

## Done（FE-1416 R07 TenFrame Vertical Gate：B5 模板第四组件，Batch A 全清，2026-10-04）

> Batch A 收尾（SEM-1416 / Gap R07）。ten-frame 语义=20 以内"十与一"结构；**补十打包（MAKE_TEN_COMPLETED）是本 Gate 独有的过程语义**。

- **纯函数层** `tenFrameV2.ts`：连续填充（点第 i 格=填到 i+1/收缩到 i，禁跳格留洞——模板首个"拒绝式交互"负例）、make-ten 打包（满10冻结成袋、tens+1 计数转第二框）、break-ten 反向拆袋、`evaluateQuantity` 三态对 target。
- **组件** `TenFrameV2.tsx`：NumberLineV2 runtime 装配模式；事件 COUNTER_ADDED/REMOVED + MAKE_TEN_COMPLETED + TEN_BROKEN + UNDO/RESET；专件替换基座 TenFrame 路由（基座保留作参考）。
- **链题**：R07 金题（app_rel d2 糖果装袋 13=1袋+3散，**sharing 族首题**——词表覆盖再+1）seed 真实 RDS；防漂移单测 +1（后端 82→**83 passed**）。
- **API 级**：错位 1袋+2=12 → correct=false HINT（FAIL 可达后端）；正确 1袋+3=13 → NEXT_TASK。
- **E2E** `e2e/r07-ten-frame.spec.mjs` 8/8（G1 空态/G2 连续填充/G5 make-ten 全链含 tens=1+count=3 结构断言/G6 错位可提交/G7 补格改对 attempt_no=2/UNDO 回退/revision 清态/healing）。**全量套件 35 passed 零回归**（B5+R01+R04+R07）。
- 新能力词 fill/grouping 进 InteractionCapability+KNOWN 名单（名单机制第二次拦漂移）。
- 底表 `docs/governance/R07_TENFRAME_VERTICAL_GATE.md`。**Vertical Gate 进度 5/19**；**Batch A（NumberLine/ObjectCounter/NumberInput/TenFrame）4/4 全清**。

## Done（FE-1415 R04 NumberInput Vertical Gate：B5 模板第三组件 + submission_id 幂等专项，2026-10-04）

> Batch A 第三个（SEM-1413 / Gap R04）。number-input 语义最简，但它是 FE-1410 幂等契约的指定验证入口，本次把双轨幂等钉到真实页面级。

- **组件** `NumberInputV2.tsx`：parseNumberInputConfig（min/max/integer_only 字段守卫）+ parseAnswer（非法/越界/小数→EMPTY 拦提交；合法即 READY 可提交，对错交后端=P0-01 口径）+ serializeNumberInputV2（answer + input_history 尾20）；NUMBER_INPUT_CHANGED 事件；revision 清态。TaskRenderer V2 分流接线；registry vertical_gate "R04"。
- **链题**：R04 金题（app_rel d1 小鸟飞走 7-2=5，before_after，number_input，0~20 整数）已 seed 真实 RDS；防漂移单测 +1（后端 81→**82 passed**）。
- **幂等四连（API 级实证）**：错误答案 3→200 correct=false HINT（可达诊断链）；同 submission_id 同内容重放→**200 同 attempt_id**；同 ID 异内容→**409**；attempt_no=2 改对→correct=true NEXT_TASK。E2E 级：双击只发 1 POST/1 submission_id。
- **浏览器 E2E** `e2e/r04-number-input.spec.mjs` 7 用例全过（G1 不降级/G2G3 空越界小数拒提/G6G4 envelope 合同/G7 重试链/E2E-08 清态/healing 双皮肤）。**全量套件 27 passed**（B5 9 + R01 11 + R04 7，零回归）。
- 治理：`docs/governance/R04_NUMBERINPUT_VERTICAL_GATE.md`；Vertical Gate 进度 **3/19**（Batch A 剩 ten-frame）。

## Done（FE-1414 R01 ObjectCounter Vertical Gate：B5 模板第二个组件闭环，2026-10-04）

> 用户裁决采纳交付方 Batch 顺序（docs/frontend/31 SEM-1410 / Gap R01），ObjectCounter 作为 Batch A 第一个打完整 Vertical Gate。

- **纯函数层** `objectCounterV2.ts`：add/remove（locked 组不可增删）、compose（并走记录 composed_into/composed_count——Evidence 首次含过程留痕）、decompose（拆 k 出新组继承 symbol）、答案=Σcounts、`evaluateStructure` 四态结构判定（effective=count+composed_count）。
- **组件** `ObjectCounterV2.tsx`：复刻 NumberLineV2 runtime 装配模式（rendererWorkspaceReducer + buildRendererEvent，UPPER_SNAKE 事件）；提交门禁=B5/P0-01 同口径（PASS∪FAIL 可提交，错误答案必须到后端）。
- **链题**：`resource_seed_v2.py` R01 金题（app_rel d1 合气球 4+3=7，context_family=school_objects，response_type=object_count，已 seed 真实 RDS）；TaskRenderer V2 分流接线；registry capabilities 扩 4（add_object/remove_object/compose_groups/decompose_group）+ vertical_gate "R01"（避 A1=place-value 撞号）；KNOWN_CAPABILITY_IDS 名单落地（防能力静默过滤漂移）。
- **API 级实证**：下发 2.0/count_compose → 提交 correct=true → NEXT_TASK；submission_id 异内容重放 **409**（幂等权威轨在 R01 上再证）。
- **浏览器 E2E** `e2e/r01-object-counter.spec.mjs` 10 用例：G1 不降级 / G2G3 PARTIAL 拦提交 / G6G4 错答案(4+2报6) envelope 完整→HINT / G5 摆对+compose 判对（data.groups[0].composed_into=g2、composed_count=4）/ G7 重试 attempt_no=2 / 防重入 / revision 重置不串题 / 事件模型六类 / COUNT_REMOVED 独立 / 双皮肤 healing。全量套件 **20/20 passed**（B5 零回归 + R01 全过 + healing 双皮肤）。
- **治理**：`docs/governance/R01_OBJECTCOUNTER_VERTICAL_GATE.md`（G1~G9 对照 + 模板泛化差异 + 遗留）；数据卫生全程生效——E2E 证据全进 QA child …0099。
- 验证：tsc 0 / check-v13·v14·renderers·fe1403-b5 全 PASS / 后端 75→**81 passed**（新增防漂移单测 test_v2_gold_resources.py ×6，不连库）。

## Merged（FE-1413 消费《V1.4 Renderer Semantic Completion Pack》4 份交付，2026-10-04）

> 交付=Semantic Completion Matrix（19 Renderer 六维）+ Gap Matrix + Task Breakdown（SEM-1401~1437）+ 开发任务表 xlsx。存档 docs/frontend/31 + 无损文本抽取。

- **基线判定**：交付方工作快照≈FE-1408 前——"4/23 组件 / submission_id 未闭环 / B5 未闭环 / E2E 40%"四项断言均过时（现 23/23 implemented、FE-1410 幂等闭环、B5 Vertical Gate CLOSED）。其核心主张"implemented≠Semantic Complete 现在不能进单纯 QA"与我们 FE-1409 诚实口径一致，采纳。
- **编号冲突裁决**：交付重占 FE-1401~1437 且语义与已用序列错位（其 1410=ObjectCounter vs 我们 1410=submission_id）→ 不采纳，引用一律 `SEM-<n>` 前缀，执行按自有序列立项。
- **Scope 差异**：交付 Release Scope 19（剔 choice-grid/data-table/pictograph/timeline）；裁决 Registry 保持 23（冻结枚举不缩），P0 批次按 19 执行、被剔 4 组件 Gate 顺延。
- **有效增量**：19×6=114 Completion Checkpoints + A~E 五路径验收 → B5 五件套模板升级为正式底表；Batch A~E 分批顺序采纳；禁止条款 20.1~20.4（组件不 fetch/不自判 Diagnosis/不改 AbilityState/DOM Event≠Semantic Event）入 review checklist。
- 只登记不开发（与 30 号 18 Renderers Pack 同一纪律）；主战场=SEM-1410~1428（除已 CLOSED 的 ColumnArithmetic）等价"逐组件 Vertical Gate"。

## Done（FE-1412 QA 数据卫生治理：测试流量分池 + 存量污染清理 + 凭据根治，2026-10-04）

> 用户实测触发：真实 session 3 题全对，但 app_rel 停 L1 conf=0——108 条证据大半是 QA 重放/E2E 模拟数据，压住 CI 窗口（最近 8 条），真实水平永远测不准。同期发现 `qa_replay_mastery.py` 把真实 RDS 密码硬编码进了 git（PR #19 引入）。

- **R1 分池（治本）**：新建 QA-Simulator child `…0099`（`scripts/qa_child_setup.py`，幂等，含 7 能力初始 state）。`qa_replay_mastery.py` / `integration-smoke.mts` / `b5-column-arithmetic.spec.mjs` 统一切 QA child（`E2E_CHILD_ID`/`QA_CHILD_ID` 可覆盖）。ability_state 主键含 child_id，分池零 DDL。
- **R2 凭据根治**：qa_replay 的硬编码 DB_URL 删除，改 `os.environ["DATABASE_URL"]` 必填。（密码已在 git 历史，**RDS 控制台轮换由用户执行**。）
- **治理文档**：`docs/governance/QA_DATA_HYGIENE.md`（R1 真实数据只能由人产生 / R2 凭据只走 env / R3 新组件 E2E 继承 / R4 污染只标废不删除）。
- **CI 门禁**：`scripts/check-data-hygiene.mjs`——静态扫描测试流量目录的真实 child 字面量（R1）与 RDS host/带密连接串（R2）；挂入 `governance:check`（CI governance job 覆盖）。正负样本验证：植入违例 FAIL、清态 PASS。
- **B 存量清理**：确定性指纹 T1（999 答案整 task）/T2（60s 窗口 ≥5 session 批量簇）/T3（client_elapsed_ms<2000 亚秒提交）命中 **77 条**证据标 `valid=false`（metadata 记 invalidated_reason，可追溯可回滚）；陈旧派生窗口 1 条作废；重算走生产路径 `persist_mastery_state`。app_rel conf **0→0.75**（真实 41 条证据归位）；用户 13:41 真实 session 3 条证据复核完好。14 条 SUSPECT 经行为指纹复核（elapsed_ms 同 session 内累计递增=联调期手工快测特征，非真实学习节奏）+ 用户裁决，追加软删 12 条 → 累计 **89 条作废 + 39 条真实保留**；app_rel conf 0.75→0.50（去伪后真实值）。
- **副产物（诚实记录）**：qa_replay #7 转 FAIL——其断言此前一直靠脏数据（自己造的 transfer 证据）自证，清理后暴露系统本无真实 transfer 证据。待 V1.4 真实链题后重写该用例。
- **验证**：后端 75 passed；governance+hygiene PASS；B5 E2E 9 passed/1 skipped（3101 未起）——E2E 新证据 7 条全进 QA child，真实 child 近 5 分钟新增 **0**（分池实证）。

## Fixed（FE-1411 V1 操作题无限渲染循环——用户页面 F12 刷屏，2026-10-04）

> 用户实测发现：`/child/math/session/...`（V1 objects 题）F12 疯狂报 `Maximum update depth exceeded`（718 条/会话）。

- **根因**：`ManipulativeRenderer` 每次渲染 spread 出新的 `schema` 对象传给 `WorkspaceProvider`，而 Provider 以 `[schema]` 为 REINITIALIZE effect 依赖 → 每帧重置 workspace state → `onWorkspaceChange` 回调 → 父级 response 更新 → 再渲染……经典引用不稳定死循环。
- **引入与暴露**：provider 的 schema 重置 effect 是 FE-1401（V1.4 P0）交付引入；V1.3 时代该路径无 effect 不循环，V1 题此前 E2E/冒烟全走 V2 链，**真实用户打开 V1 操作题才暴露**——B5 E2E 10 用例拦不住，需 V1 回归专项（记 QA 待办）。
- **修复**（TaskRenderer.tsx）：`useMemo` 稳定化 `providerSchema`（依赖 [schema, rendererId]）。
- **验证**：无头探针复现 718→1 条（仅 Chrome DevTools 探测 404 噪音）；tsc 0 错；B5 E2E 10/10、check-v13/v14 PASS。

## Done（FE-1410 submission_id 落库迁移：V2 幂等契约入数据库，2026-10-04）

> 关闭 docs/frontend/29 §5-2「V2 资源下发前的后端迁移项」——V1.4 规模化前最后一笔 DDL 技术债。

- **DDL 迁移**（真实运行库已执行，幂等可重跑）：`scripts/migrate_submission_id.py` —— `attempt` 加 `submission_id uuid` 列 + partial 唯一索引 `uq_attempt_submission_id`（`WHERE submission_id IS NOT NULL`，尊重 V1 可空）。
- **双轨幂等**：`turn_service.record_attempt` 带 submission_id 走权威轨（同 ID 同内容→重放原 Attempt；同 ID 异内容→`SubmissionConflict`→API 409），无 submission_id 回落 `(task_instance_id, attempt_no)` 旧轨（**V1 行为零变化**）。API 层解析 submission_id + 409 映射（SubmissionConflict 先于 ValueError 捕获）。
- **幂等段重构**：抽 `_replay_shape()` 供双轨复用（首发/重放同外形规则，V2 完整三段判定不外发）。
- **防漂移单测** `tests/test_submission_id.py`（+3，不依赖 DB）：列可空/类型 UUID、partial unique 索引、SubmissionConflict 继承关系。后端 72→**75 passed**。
- **五轨实证**（真实后端+RDS）：A V2首发200 / B 同ID同内容重放同attempt_id / C 同ID异内容**409** / D 无submission_id旧轨200 / E DB层唯一索引拦住重复插入。
- **harness 缺陷根治**（E2E-10 暴露）：双 dev 实例共享 `.next`，皮肤 `NEXT_PUBLIC_*` 编译期内联互相覆盖 → `next.config.mjs` 加 `distDir: NEXT_DIST_DIR`，`.gitignore` +`.next-*`；双实例隔离后 B5 E2E **10/10 PASS**。
- **基线纪律**：权威 `01_schema_postgresql_v1.3.1.sql` 未改（SHA256 冻结物）；V2 挂入 = V1.4 基线立版动作（docs/29 §6）。

## Merged（FE-1409 V1.4 Frontend Development Package：18 个 V2 Renderer 组件交付，2026-10-04）

> 交付来源：《V1.4_Frontend_Development_Package.zip》（基线=main@66f374c 含 P0-01，缺 E2E harness #39，合并时无回退）。

- 前端：`V2RendererLibrary.tsx` 统一基座（232 行：useRendererState 共享状态/事件/revision 隔离 + answer 提取）承载 **18 个 V2 组件**（choice-grid/place-value/ten-frame/array-board/grouping-board/formula-board/estimation-canvas/shape-gallery/shape-canvas/sorting-board/direction-grid/ruler/clock/timeline/money-board/data-table/pictograph/pattern-board）；每组件独立入口文件；TaskRenderer V2 路由全接线；registry 18 项 planned→implementedV2；globals.css 追加 renderer 样式（超集）。
- 后端同步：renderer_protocol 23 协议全部 implemented（附 assert 23/23）；`_v2_assignable`/`check_assignable` 职责收敛为「协议外/哨兵拒绝」；3 处测试基准同步（planned 拒绝样例改 hologram-board/unsupported）。
- 合并时修复：MoneyBoard `next` 缺索引签名（TS7053，交付方依赖层未暴露）——tsc 清零。
- check 新增：`scripts/check-v14-renderers.mjs`（23/23 协议、18 V2 + 4 复用路由/基座/入口齐检）。
- 诚实口径（写入 28 号文档）：**implemented = 前端可渲染不降级 ≠ 已过 B5 式 Vertical Gate**——各组件 mode 字段级 Schema（docs/29 §5-1）、链题、独立 Evaluator（四态）、undo/history、浏览器 E2E 按 B5 模板逐个补齐；23/23 全放行下发后，内容侧发布仍需 Vertical Gate 证据。
- 验证：tsc 0 错、next build ✓ 9 routes、check-v13/v14/fe1403-b5/v14-renderers/governance 全过、后端 72 passed。

## Closed（FE-1403 B5 Vertical Gate CLOSED：浏览器 E2E harness 落地，2026-10-04）

- 新增 Playwright E2E harness：`apps/child-web/e2e/b5-column-arithmetic.spec.mjs` + `playwright.config.mjs`（系统 Chrome，`npm run e2e`）；**10 用例全 PASS（50.6s）**——§7 场景矩阵 P0（01/02/03/07/08/09）+ P1（事件模型/双皮肤 3101）+ G9 V1 回归。
- 真实性：task 由真实后端预取（route 仅钉题重放、task_instance_id 真实），attempts/hints 全放行真实 RDS——满足「不以纯函数/Mock 替代」（原则5）。
- **harness 抓到 API 级测不出的真实环境缺陷**：后端 CORS 白名单缺 E2E 实例端口 → 浏览器拦截 attempts 响应（后端 200/RDS 落库均正常，但响应回不到页面）。修复：`app/core/config.py` cors_origins 增补 localhost/127.0.0.1 的 3100/3101（本地 dev 端口，安全边界不变）。
- G1~G9 九项全部转浏览器实证；FE-1403-P0-02~06 + P1-01 DONE；Gate 判定文档（B5_E2E_VERTICAL_GATE.md）§2/§3/§4/§6 同步收口，PROJECT_STATUS FE-1403-B5 → **Vertical Gate CLOSED**。
- 附带修复两处 harness 逻辑（非产品缺陷）：G7 撤销步骤误撤十位致第二次答错；G9 选择器从 placeholder 改稳定 `#math-answer` + 能力从 app_strat（全表征必填题）改 app_cond（6 道纯数字题，已核 repr_required=false）。
- 后端回归 72 passed（CORS 改动后）；.gitignore 补 test-results/playwright-report。
- **B5 模板成立**：纯函数层→组件双皮肤→V2Renderer 分流→链题→check/E2E→implemented 翻转——18 planned Renderer 按此批量推进。

## Fixed（FE-1403-P0-01 B5 提交门禁解除，2026-10-04）

> 依据《B5 真实页面 E2E + Workspace/Response 联调方案》§3/§14。

- **P0 缺陷修复**：ColumnArithmetic 提交按钮原 `disabled={... || evaluation.status !== "PASS"}`——错误答案（FAIL）被前端拦死、永远到不了后端，Diagnosis/Retry/Evidence 链无法验证。改为白名单：PASS/FAIL 可提交，PARTIAL/EMPTY 与 INVALID 不可（§3 门槛表）。Evaluator 降级为纯 UI 即时反馈。
- API 级闭环实证（真实后端 47+28）：attempt1 答 65 → correct=False → HINT；attempt2 答 75 → correct=True → NEXT_TASK。
- 存档 `docs/governance/B5_E2E_VERTICAL_GATE.md`：FE-1403 关闭判定基准（G1–G9 + 场景矩阵 + 任务进度）。
- 进度：P0-01/05 DONE（API 半）；G1–G9 后端纵向链 GREEN；FE-1403 Vertical Gate 关闭剩浏览器 E2E（P0-03/04/06 + P1 双皮肤）。

## Merged（FE-1408 V2Renderer 接 number-line + mock A5 同步，2026-10-03）

- numberLineV2.ts：V2 数轴纯函数层（state/applyJump/endpointAnswer/serialize），数据形态对齐 FE-1405 A5 链 E2E 已验证的 `data.jumps=[{jump_id,from,to}]`；未跳步不给答案（endpoint 空提交禁用）。
- NumberLineV2.tsx：V2 数轴组件——复用 rendererRuntime（undo/reset/events），写回 v2_workspaces + answer=终点值；刻度由 config.scale 驱动（0~50 步长5），start_marker 提供起点。
- TaskRenderer V2Renderer 加 number-line 分支（A5 链浏览器可玩，FE-1407 遗留解锁）。
- mock taskBank 插入 mock-rel-v2-line-1（与后端 resource_seed_v2 A5 题同源：20 起步每次 +5 跳 3 次 = 35，d3）；FE-1407「A5 暂不入 mock」限制随之解除。
- 验证：tsc 0 错、next build ✓、check-v13/v14/fe1403-b5 PASS。

## Merged（FE-1407 mock 同步 V2：B5 column-arithmetic 演示题，2026-10-03）

- mock taskBank 首位插入 `mock-rel-v2-column-1`：完整 V2 TaskUISchema（schema_version 2.0 / workspaces / column-arithmetic / mode addition / response_contract），与后端 resource_seed_v2 B5 链题同源（47+28=75，d4）；mock 模式可直接体验竖式 V2 渲染链。
- 零新增代码路径：复用 v2AttemptAdapter V2 信封、TaskRenderer V2 判别分流、hintUiAction V2 守卫；判分沿用 extractAnswer(answer) 口径（组件写入 answer，与后端 answer.value 语义一致）。
- 有意不做：A5 number-line 不入 mock——V2Renderer 尚未接 number-line 视图，接入会显示"开发中"卡（不用 unsupported 掩盖，契约 §24）；V2 链就绪后再同步。
- 验证：tsc 0 错、check-v13/v14/fe1403-b5 PASS、CI 四绿（PR #33）。

## Merged（FE-1403 B5 column-arithmetic 前端切片 + Gate B5 E2E，2026-10-03）

> 交付来源：《V1.4 FE-1403 Renderer Implementation Contract》+ zip（基线含 FE-1405；交付方 FE-1406 未入包，合并时 backend 诊断五文件不取，main 版本保留）。

- 前端：rendererRegistry 23 协议全注册+implemented 分层；columnArithmetic（State/Reducer/Serializer/Evaluator：PASS/PARTIAL/FAIL/INVALID）；ColumnArithmetic 竖式组件（双皮肤）；TaskRenderer V2 判别分流；V2TaskUiSchema 判别联合；v2_workspaces→MathResponse V2 信封。
- 后端：renderer_protocol column-arithmetic planned→implemented（前后端分层同步）；3 处门控测试基准同步改用 ruler/data-table；B5 链题（47+28=75 竖式 before_after d4）seed 入库。
- 合并时修复交付方 6 处 tsc 错误（重复 import / 判别守卫 / places 类型）——交付方依赖层缺失暴露，补跑清零。
- 验证：tsc 0 错、next build ✓、check-fe1403-b5/v13/v14/governance ✓、后端 72 passed；**Gate B5 真实 API E2E 5 步全 PASS**（V2下发→竖式判分→单task单证据→重试不覆盖→Mastery回写）。
- Gate 状态（§25 口径）：A5 GREEN · B5 API链路 GREEN/浏览器待人工 · D5/E4/F6 RED。

## Added（FE-1406 诊断 V2：三段判定、无证据不猜，2026-10-03）

> 评审 V0.2 步骤 3：`diagnosis.py` 移除"无证据兜底"与"第一条错因"推断（§4.1 点名问题）。

- `DiagnosisV2`：观察(observations+field_path) → 候选(candidates: tag/rule_id/rule_version/evidence_paths) → top_level_code；**NULL 是合法结论**（证据不足不冒充已判断，status=observation_only）。
- **删除 `_fallback_by_hints`**：答错但无观察支持任何资源规则 → 不再猜 E01/E05；hint 依赖度不再决定错因。
- **删除"error_models[0] 即结论"**：资源全部错因规则作为候选来源，仅当观察命中规则触发条件才形成候选（V1 建模观察=required 表征缺失；V2 观察=空工作区无过程数据）。
- `correct=None`（未评分）不判：评分故障走工程异常，不写儿童数学误解（评审判定表行4）。
- 多候选并存 → top_level_code 保持 NULL（"存在其他合理解释"不强选）。
- 对外响应只暴露有码结论（response_shape：无码时 diagnosis=None，不给儿童猜测标签）；LearningEvent 保留 V2 完整三段判定（审计 + 未来 confirmed 聚合）。幂等重放同规则。
- confirmed 状态**保留值位不启用**：判定条件（跨资源跨session+反例排除）按评审 §6 属待校准 OPEN 项。
- `session_result.py` 诊断汇总兼容 top_level_code 与 V1 历史事件 code；`/v1/diagnosis` 独立端点经兼容层。
- 测试重写 +15（NULL 合法/兜底移除实证/观察驱动/兼容外形/hint 不变），后端 71 passed；API 冒烟实证：答错无观察 diagnosis=None、V2 空工作区→E05 候选成立。
- E01~E07 语义与 LE-* 分离不变；tag→观察匹配表为保守缺省，正式标签字典待内容/教学规则审定进 ADR（评审 §6）。

## Added（FE-1405 A5 纵向链端到端打通，2026-10-02）

> V2 契约从"可执行 Schema"推进到"真实链路端到端可跑"：第一条 implemented renderer（number-line）的 V2 题完成 下发→渲染→提交→判分→幂等 全链验证。

- `app/content/resource_seed_v2.py`：V2 纵向链资源独立文件（`ui_schema_version:"2.0"` 显式声明 + context_family canonical），首批 1 题（A5 数轴跳步，d3，before_after）。
- `seed_content.py`：按 `ui_schema_version` 分流构建 V1/V2 ui_schema；`_build_ui_schema_v2` 产出经 `validate_ui_schema_v2` 契约验证（CI 单测自证）。
- `learning.py`：查询期 V2 下发门控 `_v2_assignable()`——planned renderer 受控拒绝（不降级）；V2 提交判分提取 `answer.value`（V1 标量行为不变）。
- 前端：`taskUiSchemaNormalizer` 增加 V2→渲染视图转换（number-line/object-counter 映射到现有控件，携带 ui_revision/response_type/workspace_id 元数据）；新增 `v2AttemptAdapter`（按 MathResponse V2 信封构造提交报文，含 submission_id=uuid）；`http.ts submitAttempt` 接收可选 task 分流 V1/V2 payload。
- E2E 验证（真实 RDS + API）：V2 题入库契约 PASS → 下发 PASS → 错误提交判错(HINT) → 正确提交判对 → 重放幂等 PASS。
- 测试 +7（门控 4 例、seed 产物契约 2 例、answer 标量 1 例），后端 65 passed；tsc/check-v14 PASS。
- 存量 50 题 V1 行为零变化（门控只拦 V2-planned）。

## Added（FE-1404 TaskUISchema V2 + MathResponse V2 可执行契约，2026-10-02）

> 评审 V0.2 步骤 2 后半：契约从 V0.1 草案推进为可执行 Schema（冻结候选，待会签）。

- `packages/contracts/schemas/`：draft 2020-12 可执行 JSON Schema 两份（TaskUISchema V2 / MathResponse V2，全节点 `additionalProperties:false`——客户端自评字段机器级不可提交）。
- `packages/contracts/contracts/validate.py`：三层校验（schema→FE-1403 协议枚举→语义层：workspace_id 唯一/sequence 唯一/is_implemented 下发分层，planned 受控拒绝不降级）。
- `samples/`：五条纵向链全量合法样例（B5/A5/D5/E4/F6）+ 反例3组（renderer 别名/重复 workspace_id/客户端自评）+ `examples/` 带 interaction_events 全量 Attempt。
- 测试 +9（含 schema enum 与 renderer_protocol 代码枚举防漂移同步检查），后端 58 passed。
- `docs/frontend/29`：语义口径 + submission_id 幂等契约 + 待冻结清单 7 项（mode 字段级 Schema、submission_id 落库、TS 镜像、权威 OpenAPI 挂入=V1.4 基线立版动作）。
- pyproject dev 依赖 + jsonschema。
- 本期不动权威 OpenAPI（V1.3.1 冻结基线，ui_schema/response 为自由 object，V2 向后兼容不违反）。

## Added（FE-1403 Renderer Registry Contract 协议冻结，2026-10-02）

> 依据《V1.4 P0 Architecture Contract》P0-01 + 评审 V0.2 §3.1：冻结 23 个 Renderer 的 kebab-case 协议枚举与分流规则。

- `docs/frontend/28_RENDERER_REGISTRY_CONTRACT.md`：协议冻结文档——23 枚举（R-001~R-023，含来源/实现状态分层）、V1/V2 分流规则、V2 硬约束清单、unsupported 哨兵不入协议面、Registry 12 字段交付节奏。
- `app/content/renderer_protocol.py`：机器可读镜像 + `validate_renderer_id()`（UNKNOWN_RENDERER_ID 拒绝）+ `is_implemented()`（协议合法≠可下发，planned 受控拒绝）。
- 测试 +5（枚举冻结23/命名映射自检/非法拒绝/哨兵排除/implemented 分层），后端 49 passed。
- 前端 `rendererRegistry.ts` 补注释锚定协议事实源（行为零改动）。

## Added（V1.4 P0 Governance Closure：context_family 受控词表 + 50题回填，2026-10-01）

> 依据《V1.4 P0 Governance Closure》与《V1.3评审》§7：把 context_family 从自由文本升级为「受控词表 + 数据入口校验 + Engine 消费契约」。同时关闭 Gate 0 残留前置之一（L2→L3 生产可达性）。

- `docs/governance/CONTEXT_FAMILY_VOCABULARY.md`：受控词表唯一事实源（AC-01）——6 启用族（school_objects/comparison/before_after/lineup_position/shopping/time_schedule）+ 定义/正反例/分类优先级规则 + 扩展协议（§10）+ 50 题分类明细。
- `app/content/context_family.py`：Seed Validation（AC-02）——trim→canonical→lookup，非法值 `UNKNOWN_CONTEXT_FAMILY` 拒绝；`everyday_objects` 未批准前亦拒。
- `app/content/context_family_map.py`：50 题 stem→family 映射（AC-04）——PASS 44 / REVIEW 6（日常物品无 canonical 族，留 NULL 不硬猜）/ REJECT 0。
- `seed_content.py`：mastery_rule 从写死 None 改为按映射生成（入口强校验）；`turn_service` 写证据时从 `resource_version.mastery_rule.context_family` 读取并写入证据列（唯一来源冻结）。
- 存量回填执行：50 题 mastery_rule 已回写 + 31 条历史原子证据 context_family 已补齐（幂等脚本）。
- 硬性检查（§7）：迁移题覆盖 comparison×2 + before_after×2 → **L2→L3 transfer diversity（≥2族）生产可达路径打通**；lineup/shopping/sharing 启用但零覆盖如实记录（待内容补题）。
- Transfer Regression（AC-05）：同族×2→insufficient、异族×2→数值，引擎判定按 canonical 计数验证通过。
- Engine Decoupling（AC-06）：核验 mastery.py 无族名分支，仅 distinct 计数——已满足。
- DDL 不变（§9）：varchar(64) 保持、不加 CHECK；职责四分离。
- 测试：新增词表校验 3 用例（拒绝非法值/50题覆盖/迁移族数），后端 44 passed。

### 待裁决（REVIEW 6 题，需产品/内容确认）

- 是否按 §10 扩展协议正式新增 `everyday_objects` 族（气球/玩具车/水果/球/玻璃珠/杯子 6 题）；批准前其 context_family 保持 NULL，不参与 transfer 计数。

## Added（Session Result 契约写入权威 OpenAPI，2026-09-30）

> DRIFT-001 收口：权威 OpenAPI 此前缺少 Session Result endpoint，前端一直靠可配置 Path + Normalizer 过渡。

- 权威 `02_openapi_v1.3.1.yaml` 补 `GET /v1/learning/sessions/{session_id}/result` 及 `SessionResult` / `AbilityChange` / `LearningBehavior` / `NextRecommendation` / `DiagnosisSummaryItem` schema。
- 顺带补齐 `MasteryDecision.decision` 枚举：`collect_evidence` / `recovering`（后端已在用，此前 yaml 漏同步）。
- 前端 `config.ts` 默认 path 已与权威路由一致，注释更新；`SHA256SUMS` 同步重算。
- `CONTRACT_DRIFT_REGISTER` 将 DRIFT-001 标为 RESOLVED。

## Added（V1.3 Mastery Closure 后端收口，2026-09-30）

> DRIFT-002 完整闭环：运行实现此前只接「半条链」（证据落库但从不消化成能力等级、L1→L2 空壳秒升、L2+ 因缺 transfer 证据不可达）。分四个 PR 收口后 QA replay 全绿，正式激活 `mastery-v1.3.1`。

- **FE-1311（PR-A Atomic Evidence Truth，#15）**
  - B1：L1→L2 补真实 Gate（非空壳）——eligible standard/retention ≥5、resource_version ≥3、session ≥2、C≥0.80/I≥0.50/S≥0.50，外加非补偿门槛「≥4/5 任务 hint≤2」；不足返回 `collect_evidence`。
  - B2：`evidence_role` 落到 Task Assignment——`task_instance.strategy_policy` 写 `evidence_role`(standard/transfer/retention) + `task_purpose`；`turn_service` 按 role 决定 evidence_type，不再硬编码 `attempt_standard`。
  - B3：单 Task 单证据——首个可评分 Attempt 为唯一 Mastery 原子证据，后续 Retry 仅写 Attempt/Event，不覆盖能力测量。
- **FE-1312（PR-B Evidence Coverage Truth，#16）**
  - B4：四维指标改 Optional——coverage 不足返回 `None` 而非 `0.0`（区分「没测」vs「测了不会」）；`mastery_score` 任一维度缺失 = `None`，不重归一化、不把缺当 0。
  - B5：多样性约束严格执行——C/I 需 ≥3 resource + ≥2 session；S 需 ≥3 resource + ≥2 session；T 需 ≥2 rows + ≥2 context + ≥2 session。
- **FE-1313（PR-C Derived Evidence + L4，#17）**
  - B6：`stability_window`/`transfer_window` 派生证据落库，带 `source_evidence_ids` 可追溯 + `window_signature` sha1 幂等。
  - B7：L3→L4 完整 Gate——T≥0.80 + transfer 证据≥3 + context≥3 + 节点级 `level_schema.l4_gate`（禁用 if-else 硬编码）。
- **FE-1314（PR-D Mastery→Curriculum Closure，#18）**
  - B8：review 状态机——`decide_review` 纯函数；单次失败不降级、窗口内 ≥2 失败 review_required、≥3 全失败最多降 1 级；trend 综合语义(up/down_review/watch/stable)；Curriculum 按 evidence need 选 role（儿童端仅见 NEXT_TASK）。
- **FE-1315（激活，#19）**
  - `scripts/qa_replay_mastery.py` 回放后端指南 §14 全部 14 条必测用例，14/14 通过。
  - `RULE_VERSION` 由 `mastery-v1.3` 激活为 `mastery-v1.3.1`（models 默认值同步），消除 `turn_service` 硬编码 `rule_version`。
  - 历史数据按 v1.3.1 重算回灌。

相关文档新增：`docs/backend/01_V13_MASTERY_CLOSURE_IMPLEMENTATION.md`、`docs/frontend/23_MASTERY_CLOSURE_FRONTEND_CONTRACT.md`、`docs/frontend/24_MASTERY_FRONTEND_BACKEND_INTEGRATION.md`。

## Changed（V1.3 Mastery Closure 前端对齐，2026-09-30）

- FE-1310：能力趋势统一转换为儿童可理解文案（有进步 / 很稳定 / 继续积累 / 正在巩固），不暴露 review/downgrade 内部术语。
- FE-1310：结果页从“只显示第一项 ability_change”改为完整渲染一次 Session 的全部能力变化。
- FE-1310：Session Result Normalizer 兼容 `old_level/new_level` 与 MasteryDecision `decision` 迁移字段。
- QA-1311：V1.3 静态 QA 增加 Mastery UI 边界校验，防止儿童端重新引入复核术语或只渲染单能力。
- Mock：补充 up / stable / down_review 三种能力状态，用于结果页和成长地图回归。


## Fixed（Sprint 3 联调阶段修复，2026-09-28）

> 以下 6 处修复在`前后端真实联调`中暴露，均为「mock 模式测不出、接真后端才会踩到」的契约/bug。
> 事前已通过「前后端 API 对齐评审」+ 真实 RDS 端到端验证逐一确认。

### F1. 前端 next_action 空值兜底
- **文件**：`apps/child-web/src/features/learning/machine.ts`
- **根因**：后端 `record_attempt` 答错时返回 `next_action`，答对时返回 `null`；前端 `getNextActionCode` 无条件读 `result.next_action.type`，答对时崩 `Cannot read properties of null (reading 'type')`。
- **修复**：改为 `result.next_action?.type ?? "NEXT_TASK"`，加空值兜底。
- **影响**：修复答对即崩溃。

### F2. 前端提交防重入锁
- **文件**：`apps/child-web/src/features/learning/useLearningSession.ts`
- **根因**：快速连点「提交」/ 连按 Enter，导致同一 `(task_instance_id, attempt_no)` 提交两次，撞后端唯一约束 `attempt_task_instance_id_attempt_no_key` → 500。
- **修复**：新增 `submittingRef`（`useRef`），提交中禁止再次触发，`try/finally` 保证解锁。
- **影响**：修复重复提交导致的 500。

### F3. 前端 response 契约对齐（object 而非 string）
- **文件**：`apps/child-web/src/features/learning/useLearningSession.ts` + `apps/child-web/src/lib/api/contracts.ts` + `apps/child-web/src/lib/api/mock.ts`
- **根因**：OpenAPI 明确 `AttemptRequest.response` 是 `object`，但前端传的是字符串 `state.answer`，后端 `response.get("answer")` 会取不到答案，http 模式判分失效。
- **修复**：`response` 改为 `{ answer: state.answer }`；`contracts.ts` 类型收紧为 `Record<string, unknown>`；`mock.ts` 判分改为取 `.answer`。
- **影响**：修复 http 模式判分失效。

### F4. dev ui-kit 组件 prop 对齐
- **文件**：`apps/child-web/app/dev/ui-kit/page.tsx`
- **根因**：`AbilityGrowthCard` 在 V1.2 已把 prop 从 `level` 改为 `afterLevel`，但 ui-kit 仍用旧 `level`，导致 typecheck 报错。
- **修复**：`level={2}` → `afterLevel={2}`。
- **影响**：修复 typecheck 失败。

### F5. 首页「今日目标」措辞与能力排序
- **文件**：`apps/child-web/src/screens/MathHomeScreen.tsx` + `apps/learning-api/app/services/profile.py`
- **根因**：后端 `profile` 的 `developing` 按数据库无序返回，导致「今日目标」误推链末环能力（如「检查验算」）给零基础孩子；措辞「继续练习」对从未开始的孩子不准确。
- **修复**：后端 `developing` 按能力依赖链 `_CANONICAL_ORDER` 排序（读题理解→…→迁移变式）；前端 `level===0` 显示「开始练习」而非「继续练习」。
- **影响**：首页推荐能力更符合教学顺序，零基础措辞准确。

### F6. 后端提交幂等
- **文件**：`apps/learning-api/app/services/turn_service.py`
- **根因**：与 F2 同源，前端防重入是缓解，后端幂等才是根治。
- **修复**：`record_attempt` 提交前查已有 `(task_instance_id, attempt_no)`，存在则直接返回第一次结果（不重复写 attempt/event/evidence）。
- **影响**：即使前端漏防，同一 attempt 重复提交也返回 200 + 相同 attempt_id，不再 500。

## Added（V1.3 Math Interaction Foundation，待正式发版）

> 来自 `Math_Sprint3_Frontend_V1.3` 交付包的三方合并；开发期间不升版本号，仍保持 `1.2.0`。

- FE-1301 Task Renderer V1：学习页改由 `TaskRenderer` 统一渲染（number / manipulative / unsupported 三分支）
- FE-1302 隔离的 Workspace State：`math-workspace` 状态与学习状态机解耦（`WorkspaceProvider` + `workspaceReducer`）
- FE-1303 交互式 Object Counter（一一对应摆一摆）
- FE-1304 交互式 Bar Model（线段图）
- FE-1305 交互式 Number Line（数轴跳跃）
- API-1306 TaskUISchema V1：`contracts.ts` 引入判別联合 schema + `taskUiSchemaNormalizer` 兼容旧 schema
- API-1307 Structured Response：attempt 提交 `TaskResponse { answer, representation }`
- API-1308 Workspace-aware Hint：`HintResponse.ui_action` 驱动图示高亮/聚焦
- QA-1312 `/dev/v1.3-qa` 双皮肤（healing / math-lab）QA 页

## Changed（与 FE-1300 三方合并）

- `math-workspace` / `task-renderer` 全新目录，`manipulatives` 3 个交互组件
- `MathLearningScreen` 用 `TaskRenderer` 替代旧的 `MathQuestionCard + MathWorkspace`
- `machine.ts`：`answer: string` → `response: TaskResponse`，`SET_ANSWER` → `SET_RESPONSE`
- `config.ts`：`apiBaseUrl` 默认去掉 `/api` 后缀（对齐后端实际 `/v1/...` 前缀）

---

# [1.2.0] - 2026-09-28

**Release Name:** Learning Result Closure

## Added

### Session Result 正式前端契约
新增：
- `SessionResult`
- `LearningBehavior`
- `AbilityChange`
- `NextRecommendation`

文件：

```text
src/lib/api/contracts.ts
```

### Session Result API
新增：

```text
LearningApi.getSessionResult(sessionId)
```

实现：
- `HttpLearningApi`
- `MockLearningApi`

### Session Result Normalizer
新增：

```text
src/lib/api/sessionResultNormalizer.ts
```

用途：
- 将当前后端结果Payload统一转为前端Canonical Contract
- 隔离后端Schema演进
- 等权威OpenAPI补齐SessionResult后再收紧别名兼容

### 结果页正式后端驱动
`MathResultScreen` 不再把 `sessionStore` 作为主要数据源。

结果页现在由：

```text
Session Result API
├── learning_behaviors
├── ability_changes
├── duration_ms
├── task_count
├── attempt_count
├── hint_usage
└── next_recommendation
```

直接驱动。

### 结果页状态
新增：
- loading
- success
- fallback
- error
- retry

### 版本管理
新增：
- `VERSION`
- `releases/1.2.0.json`
- `docs/10_RELEASE_NOTES_V1.2.md`
- `docs/11_SESSION_RESULT_INTEGRATION.md`
- `docs/12_VERSION_MANAGEMENT.md`
- `docs/13_MIGRATION_V1.1_TO_V1.2.md`
- `docs/14_KNOWN_ISSUES_V1.2.md`
- `docs/15_RELEASE_CHECKLIST.md`

## Changed

### sessionStore职责调整
V1.1：

```text
sessionStore → Result Page主要数据源
```

V1.2：

```text
Session Result API → Result Page主要数据源
sessionStore → 仅异常兜底 / 临时缓存
```

### LearningBehaviorChecklist
由后端：

```text
learning_behaviors
```

直接驱动，不再由前端根据 attempt/hint 数量推断教育行为。

### NextTaskCard
由后端：

```text
next_recommendation
```

驱动标题与描述。

### AbilityGrowthCard
优先使用：

```text
ability_changes
```

可展示：
- before_level
- after_level
- trend
- evidence_delta

### SessionStats
正式使用 Session Result：
- duration
- task_count
- attempt_count
- hint_usage

## Compatibility

- 无破坏性页面路由变化
- 现有 Session / Task / Attempt / Hint API 不变
- Mock 模式保持完整可跑
- 结果页正式数据源发生变化

## Known Constraint

当前本地冻结的 `02_openapi_v1.3.yaml` 尚未包含新 Session Result 路径，因此 V1.2 使用：

```env
NEXT_PUBLIC_SESSION_RESULT_PATH_TEMPLATE
```

作为接口路径适配层。

正式后端 OpenAPI 更新后，应以权威路径替换环境变量并收紧 Normalizer。

---

# [1.1.0] - 2026-09-28

## Added

### 项目接手文档
新增：

```text
docs/06_FRONTEND_MODULE_MAP.md
```

内容包括：
- 前端8大模块
- 各页面功能清单
- 当前能力
- 状态
- API依赖
- 功能边界
- 已完成/待完成

### 后续开发路线图
新增：

```text
docs/07_NEXT_DEVELOPMENT_ROADMAP.md
```

明确：
- P0 / P1 / P2
- Math Manipulative Engine
- Task Renderer
- Session Result API
- Ability Detail
- Evidence
- Learning Plan
- Skin Resolver
- Parent Dashboard
- Skin Engine
- Voice/TTS

### 接手指南
新增：

```text
docs/08_HANDOVER_GUIDE.md
```

用于新开发人员快速上手。

### Changelog
新增根目录：

```text
CHANGELOG.md
```

后续所有版本必须更新本文件。

## Changed

- README 增加“项目当前完成度 / 下一步开发 / 版本记录”入口
- package version 从 `1.0.0` 升为 `1.1.0`
- handoff metadata 增加版本和变更记录要求

## Code Changes

本版本主要为文档治理与工程交接增强。

核心业务代码、Learning Engine API、状态机逻辑未改变。

---

# [1.0.0] - 2026-09-28

## Added

### 可运行 Next.js 工程
新增：
- App Router
- TypeScript
- npm scripts
- Mock / HTTP 双模式

### 页面
新增：
- `/child/math`
- `/child/math/session/[sessionId]`
- `/child/math/result/[sessionId]`
- `/child/math/growth`
- `/dev/ui-kit`

### 18个核心组件
完成：
- 4个基础UI组件
- 3个首页组件
- 5个学习组件
- 5个结果组件
- 1个成长组件

### 系统内置皮肤
完成：
- healing
- math-lab
- 默认 math-lab

### Learning Flow
完成：
- Create Session
- Next Task
- Submit Attempt
- Diagnosis
- Hint
- Retry
- Next Task
- Complete

### Learning Engine API
完成：
- Profile
- Abilities
- Session
- Task
- Attempt
- Hint

### Mock Engine
新增完整本地Mock闭环。

### Session Runtime
新增前端 Session Snapshot，用于正式 Session Result API 尚未接入时支撑结果页。

## Known Limitations

- 无正式 Session Result API
- MathWorkspace 仅为视觉/基础操作区
- 无完整 Manipulative Engine
- 无家长端
- 无 Learning Plan 页面
- 无 Skin Engine
- 无 Voice/TTS

---

# 历史前置资产

在 Sprint 3 前端之前，存在：

```text
Math_Child_UI_BuiltIn_Skins_V1.0
```

该包属于：

> 视觉规范 + Built-in Skin Runtime 骨架

Sprint 3 Frontend V1.0 在此基础上补齐了：
- 组件实现
- 页面组装
- 学习状态机
- API接线
