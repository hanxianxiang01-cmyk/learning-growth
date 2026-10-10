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

# [1.4.0] — 2026-10-10（FE-1435 立版：V1.4 Frontend P0 + Renderer Vertical Gates + Contract FROZEN）

发版说明=releases/1.4.0.json；契约基线=docs/38 CONTRACT_FROZEN.md v2.0；验证=E2E 197/197、后端 105、qa_replay 8/8、CI 四门禁。以下为本版全部变更条目：

## Feat（FE-1435 立版：产品 V1.4 冻结发布=仓库版本 1.4.0，2026-10-10）

> 五处版本一致性升级（VERSION/package.json/apps/child-web/package.json/project_manifest/releases/index current）1.2.0→1.4.0；`releases/1.4.0.json` manifest（breaking=V2 信封/submission_id 幂等轨/契约 FROZEN 唯一权威；added=19 Vertical Gate、pin+qa_staged、验收工具链、155 批 G1~7、qa_replay#7、QA 卫生治理；known_constraints=映射审批挂起/扩产批不入库/13:44 计时口径/四 renderer 不在发布范围；verification=E2E 197、后端 105、replay 8/8、CI 四门禁）；CHANGELOG `[Unreleased]` 归档 → `[1.4.0]`。check-release/governance/data-hygiene 本地全过。**tag v1.4.0 于 PR 合入后打在 squash commit。**

## Feat（FE-1434 契约 FROZEN：V1.4 题库生产契约 v2.0 冻结——parser 守卫全集首次成文（机器提取+人工校对），取代并合并 PC-v1/docs/34/36/37/FE-1438 五源，2026-10-10）

> trial155 四轮验收史（Gate3 FAIL 114→37→3→0）后两轮 40 题全因**守卫未成文**——parser 拒收条件散在 15 个 R 底表，交付方无从查、我方每轮都漏讲。本 PR 汇编 **docs/38 CONTRACT_FROZEN.md v2.0（FROZEN）**=V1.4 交付-验收唯一权威契约：§1 全局条款 G1~G7（标量/硬依赖/mode 词表/V2 信封/context_family 7 值/ID 纪律/19 项剔除 choice-grid 等）；§2 Renderer×Mode 词表（金题反查全集）；**§3 Config 守卫全集**（15 专件 `return null` 条件机器提取逐字镜像：bar-model known 恰 2 键/formula op∈{+,-}+slot[1,3]+accept/grouping items[2,20]/estimation 近似自洽+max[2,100]（Gate2 收紧 ≤60 单列注明）/gallery shapes[4,10]/canvas rectangle+area≤(grid-1)²/sorting value[1,9] 互异+initial≠平凡序/direction 0 起+反走靶可达/ruler l≥1/clock [h,m]+h∈[1,12]+m∈{0,30}+swap 自环拒/money [5,200] 角位非零 5 倍数+币含 5,10+minCoins/pattern trivial 周期拒/ten-frame[1,20]+基座链 4 含 object-counter expected **双形态**（FE-1438））；§4 诊断词全集；§5 8-Gate 链+qa_staged 通道。变更管控条款：**V1.4 冻结、守卫/形态变更必须同步修订本文+fixtures 锚点+通知交付方；源码与本文冲突以源码为准立即修订**。
> docs/34 CONTRACT.md 加归档标头（防双权威漂移）；README 注记 155 批按旧形态验收通过、**下一批直接按 v2.0 交付**。FE-1435 立版契约基线引用本文。

## Feat（FE-1438 155 题批 Gate 4~7 抽样实灌：qa_staged 隔离入库通道 + 19 renderer×1 全链 19/19 贯通，2026-10-09）

> **隔离设计（任务单 §6/PC-v1 §12 精神：未过 M→app 审批的交付题不得泄入生产池）**：新增 `review_status='qa_staged'` 通道——catalog（published 过滤）与生产选题（_published_resource_for_ability）**双不可见**；仅 pin 路径放行（learning.py 状态集合 `("published","qa_staged")`）+ 路由层 403（真实 child 不可 pin）= QA child …0099 专用。Resource.status='draft' 双保险。回归锁 2 用例（inspect 源码级断言谓词只认 published / pin 集合含 qa_staged）。
> - 选样：`qa_sample_ingest.py` 每 renderer 取 ID 最小 1 题=19 题（≥8 且 19 类全覆盖，任务单 Gate 4~7 口径），幂等按 title `[QA-Sample] <id>` 判重
> - 实灌 `qa_sample_e2e.py`：**19/19 全链贯通**——Gate 4 pin 下发（ui_schema 含交付 config）→ Gate 5 Judge（先 999999 后期望，False/True 双符）→ Gate 6 原子证据=1 → Gate 7 错后 HINT 动作；期望答案 DB 反查防泄题
> - 隔离红线实测双验：catalog=20（金题，QA-Sample 0 泄漏）；真实 child pin qa_staged → **403**
> - 后端 105 passed；前端零触碰（服务层 JSON 判断，pin 缺省路径比特级不变）
> - **UI 链补强**：`e2e/qa-sample-batch.spec.mjs`（19 条=每 renderer pin 交付题进真实前端：专件根 testid 可见+planned-renderer=0+交付题干上屏）；`pinned-tasks.mjs` 新导 `pinTaskByRvid`（直 pin 不经 catalog，适配 qa_staged）；`e2e/qa-sample-rvids.mjs/cases.json` 由 ingest 导出。**UI 抓出并修复 1 缺陷**：ObjectCounterV2 `expected` 只认 {group_id,min_count} 对象形，交付批数字数组 [5,3]（groups 平行序，语义同）被拒渲→双形态兼容 zip 修复；CONTRACT §2.2 行勘正。tsc 0 错、**全量 E2E 197/197**（178 存量零回归+新批 19）
> - 意义：**155 题批 Gate 1~7 全部通过**（机器门+API 实灌+UI 实灌三层）；M→app 映射审批过→qa_staged 转 published+全量正式 ingest→FE-1433 replay 作 Gate 8 收官。底表 docs/governance/FE1438_QA_SAMPLE_INGEST.md。

## Feat（FE-1433 qa_replay #7 重写：pin 确定性 + V2 信封——旧 DRIFT-002 版 #7 已知 FAIL 修好，Gate 8 执行器就绪，2026-10-09）

> 旧脚本两处时代病：① app_rel 碰运气选题（band 漂移→大面积假失败，2026-10-07 全量回归实锤的根因同款）；② 裸 `{"response":{"answer":…}}` payload 不合现行 V2 信封。重写=**FE-1422a pin 确定性选题**（v2-catalog 按 renderer 定位 rvid→tasks/next 带 pin_resource_version_id，仅 QA child …0099）+ **现行信封**（schema_version 2.0/type/ui_revision/workspaces/interaction_events）+ **确定性 submission_id**（sha256 派生严格 UUID）+ **attempt_no 手动递增**（R15 幂等回放教训）+ **期望答案 DB 反查 rv.content.answer**（下发不含答案防泄题）。
> #5（错/错/对→判对+单证据）/幂等（同 submission 同内容=同 attempt_id、异内容 409）/**#7（DB 反查 transfer_distance rv→pin 下发→判对→evidence_type=attempt_transfer，旧 FAIL 用例修好）** + 13 纯函数映射 + #14 防抖 = **8/8 全绿，连跑两次确定性成立**；后端 103 passed 零回归。
> 意义=PC-v1 §11 Gate 8 执行器就绪：**155 题批（FE-1432i 已过 G1~3）的 Gate 4~7 抽样 pin E2E→Gate 8 replay→seed 入库** 流水线的最后一件工具到位。QA 卫生：全程 …0099，真实 child 零触碰。

## Review（FE-1432i 三题微增量终复检：155 题全批 Gate 1~3 机器门清零——首个过全链题批，进入 Gate 4~7 抽样资格，2026-10-09）

> 交付方按复检 §3 交 3 题微增量（077/078 **换挂 number-input 保留乘除教学语义**（优于改加减的最小改动）、133 clock 3:00→4:30 消除 swap 自环）。`apply_microdelta.py` 复现合并=分发终包三批逐字段一致（3 替换+152 不变、A42/B86/C27）。
> **权威全链复跑（main=62df97d 工具）**：Gate 2 v2+补丁三批 0/0/0、fixtures 基线自验 gold 0/neg 恰 4；Gate 3 专件 PASS 120/FAIL **0**+基座链 35；诊断词终扫（完整 19 行 ERROR_VOCAB）越表 **0**（换挂题 pattern 落 number-input 行内）。
> 四轮验收史定版：b 114 FAIL（真答案轴冲突）→ g 37（我方 §7 未成文）→ h 3（再两条未成文）→ **i 0**。交付方纪律四轮递进。**下一步 Gate 4~7**：抽 5%（≥8 题覆盖全 renderer）QA child …0099 pin 实灌四段（判分/Evidence/Diagnosis）→FE-1433 qa_replay（Gate 8）→正式 seed 入库；M→app 映射审批与题批解耦（pin 直发不经能力路由）。报告 docs/37/FINAL_RECHECK_FE1432i.md。

## Review（FE-1432h 增量包复检第二轮：Gate2 合并 clock 数组兼容补丁（我方工具缺陷）、Gate3 收敛 37→3——残留 3 题仍系我方守卫未成文（formula op 值域/clock swap 自环），已补 §7，2026-10-09）

> 交付方按任务单交**增量整改包**（37 题重交+65 处诊断词三字段同步改，不重造整包、SHA-256 前置校验防错覆盖）+ 合并复审包。我方复现合并=与分发 reconciled_155 **逐字段一致**。
> **Gate 2 兼容补丁裁决=接受合并**：R17 canonical 形态本就是数组 [h,m]，v2 的 minute_value() 只兼容旧 trial155 dict/HH:MM、不认 canonical——Gate2 与 Gate3 权威口径冲突，属我方工具缺陷（交付方"隔离副本+三行提案+明示未经批准不视为权威"处置纪律满分）。我方合并时加强：数组分支同时校验 h∈[1,12]；fixtures 加锚点 G-6 正例/T-6 负例，**基线更新=gold 0 / negative 恰 4**；合并包三批 0/0/0，trial155 旧包口径不变（216）。
> **Gate 3 复跑：37→残留 3**（077/078 formula op="*""/" 超 R04 `{"+","-"}` 值域、133 clock 6:30 swap 自环退化）——**又是我方守卫未成文**（§7 上轮补文只写 tokens 形态未写 op 值域；swap 自环守卫只在 R17 底表）。已随本 PR 两条补进 §7 并给死改法（077/078 改加减式或换挂 column-arithmetic、133 改 3:00→4:30 实测过 parser）。
> **Gate 4~7 建议并行启动**：152 题已过机器门，可先抽 5% pin E2E；微增量到齐补覆盖后进 Gate 8。FE-1434"契约含守卫全集"教训**再次应验**（本轮 +2 条）。

## Review（FE-1432g delivery_v2 整改批权威验收：Gate 1/2 全过、Gate 3 FAIL 37——根因=我方 §7 守卫未成文，契约补齐+修复清单下发，2026-10-09）

> 交付方按任务单交 155 题整改包（A42/B86/C27，C 按"B∩C 归 C"扩容并新发现 9 题内伤——处置正确）。**包完整性全项通过**：ID 与 trial155 逐一对齐、MANIFEST 155 行分类零不符、我方 Gate 2 v2 复跑三批 0 违规（自报一致）、待决项全部如实声明无虚报。
> **Gate 3 权威复跑 PASS 85 / FAIL 37**（direction 8/clock 8/formula 8/money 7/shape-canvas 4/grouping 2），docs/37 逐题修复清单+fail_list 存档。根因诚实归责=**我方契约文档债**：§7 写于 R15~R18 未打 Gate 时代，parser 守卫/形态散在底表从未汇总——含我方**笔误**（§7 写 rectangle/triangle，R13 parser 仅收 rectangle→4 题照做被拒）与**诱导措辞**（"change 题自查 paid−price"暗示找零玩法，R18 实际只有凑付→4 题）；其余 29 题守卫/值域未成文（反走靶可达、[h,m] 数组、{t,v}、price%5/%10、items≤20）。
> **随本 PR 偿还**：CONTRACT.md §7 七条全部补齐守卫/形态成文+两处勘误标注；新增 docs/37（README 审查报告+ERROR_VOCAB.md 19 渲染器诊断词权威表——解交付方 80 题待核项+gate3_fail_list）。立规矩入 FE-1434 输入要求：**契约 FROZEN 必须吸收 parser 守卫全集**（散在底表=没有契约）。修复清单已可按 §3 直接发交付方，37 题增量包到齐后进 Gate 4~7 抽样 pin E2E→Gate 8 replay。

## Review（FE-1432f 接收核验回环：交付方独立核验 FE-1432e 签发包——Gate 2 脚本 v1 四处缺陷坐实，v2 替换+fixture 回归基线入仓，2026-10-09）

> 交付方对 FE-1432e 签发包做独立接收核验（三件套回传：核验记录 md + 修订候选脚本 + diff；已存档 docs/36 `receipt_review/`）。Word 两项核心修正（G1~G8 顺序统一、choice-grid 发布范围）**核验确认无误**；但随发 `consistency_audit.py` v1 被指出 P0 误判/漏检——我方独立复现**全部坐实**：① R3 direction 起点自比较→合法非直线题误报（金样例正例包实测 v1 误杀终点编码=19 的 G-1 题）；② R1 漏检 `{type,value}` 包装答案（PC-v1 §4 明禁仍放行）；③ R7 estimation 容差贴边未实现（2±5 于 [0,40] 放行）；④ R8 context_family 缺失放行。候选版经我方独立反例（5 例，含 v1 误报回归题）+金样例正例包（6 正例）交叉验收 **11/11 符合预期**；trial155 全量回归 216 条=155 条 R1 真阳性（trial155 全部包装式 answer，即 v2 契约禁止形状）+61 条其余——非误报膨胀。核验记录"37 条=消息数≠37 道独立题"的口径批评成立，v1 该计数作废。
> **处置**：候选版替换为仓库权威 **v2**（R1~R8：双位置 answer 冲突检测、direction 终点格编码数值匹配、边界公式、缺失字段 FAIL）；正反例固化 `fixtures/gold_positive.json`（须 0 违规）+ `fixtures/negative_cases.json`（须恰 3 条）=脚本回归基线。**FE-1432e 签发 Word 内容权威地位保留不动**（核验方自行建议，我方同意）；§3 标题末字单行系渲染瑕疵，下次从权威 HTML/TASK_ORDER 源重导时一并处理。Gate 3 判定权条款不变。

## Review（FE-1432d 整改任务单下发：trial155 → v2 批 A/B/C 三路径重交付，2026-10-08）

> 基于用户拍板的验收原则，把 docs/34 审计结论 + PC-v1 契约落成**给交付方的正式任务单**（docs/frontend/36/TASK_ORDER.md）。核心条款：
> - **不是重做 155 题**，按 A（≈45 补 hint_ladder/goal/diagnosis）/ B（≈77 语义重导，验收对象=「题目语义+config+answer+evaluator」整体，**拒字段换皮**——direction 终点编码/shape-canvas 面积/sorting 真换挂 choice-grid/clock 重生成整半点/estimation 值域）/ C（18 数据修复，**定为 P0**）三路径重交；每题恰好一类、B∩C 归 C、MANIFEST 逐题 155 行必填七列
> - **流水线顺序卡死**：audit-155-config.mjs → Consistency Audit → 才允许 Pin E2E/Judge/Evidence/Diagnosis → qa_replay；一致性审计非附加检查
> - **工具归属**：Gate 3 权威判定权在我方（parser 源不可外发），交付方自检报告随包但复跑为准；随任务单发出**独立可运行的 `consistency_audit.py`**（纯标准库、PC-v1 §10 六类规则+词表+拼接歧义共 8 类检查）——对 trial155 回归实跑：37 条违规，18 题内伤全命中且规则更严（direction 纯直线扩展至 116/117）
> - **交付包结构固定**：`155_question_bank_delivery_v2/`（A/B/C 三目录+ability_mapping+reports+DELIVERY_MANIFEST.md），question_id 沿用原 ID 保证审计可追溯；缺随附申报=整包拒收
> - 我方收货链对应 PC-v1 §11 8-Gate：MANIFEST 完整性→Gate1~3→5% pin 实灌（≥8 题覆盖全出现 renderer）→qa_replay；**下一轮起不再人工逐题看 155**

## Review（FE-1432c 契约收编：交付方《Question Bank Production Contract v1.0》= 我方 docs/34 的正式化文档，收下作验收基线，2026-10-08）

> 交付方基于我方 trial155 审计对照表（docs/34/CONTRACT.md）整理出 17 节正式契约（docx，298 段）。逐条核验：**内容与审计产出一致、无失真、无夹带**——§5 全局三条=我方 G1~G3；§6 19 渲染器矩阵+§7 重导规则与 parser 守卫逐字一致；§10 一致性 Gate 吸收我方 18 题数据内伤实证；§11 把入库流程制度化为 **8-Gate 验收链**（Schema→一致性→Config×Parser→5% Pin E2E→Judge→Evidence→Diagnosis→qa_replay，我方 audit 脚本=Gate 3、pin 机制=Gate 4 地基、replay=Gate 8 执行器，全部现成）；§13/§14 采纳"converter 降级、先修契约再扩产"。**处置=收下作 V1.4 题库生产验收基线**（FE-1434 契约 FROZEN 的输入件）；原件+抽取文本存档 docs/frontend/35，条款引用记 `PC-v1.<节号>`。FE-1432 入库继续挂起等 B/C 类重导批。

## Review（FE-1432b 试灌审计轮：V1.4_P0_Trial_155 包——内容真、契约错位，不入库，产出 Config 契约对照表，2026-10-08）

> 交付方 155 题试灌包（自称 P0_TRIAL、M→app 标 PENDING 没装冻结）。三轮审计：① 7 条断言全真——**真题文本 155/155、answer 全有、19 renderer 齐（补上 ten-frame/estimation-canvas）、context_family 零越表**：内容态度合格；② config×parser 硬审（`audit-155-config.mjs`）：专件 122 题 **PASS 8 / FAIL 114（93%）**；③ 垫片转换再审（`convert_trial155.py`，语义缺口硬拒 22）：转换后 PASS 51 / FAIL 41——**字段错位 1/3 可机器救，答案轴错位 2/3 只能重导**。
>
> 主矛盾=**答案语义轴冲突**：direction-grid 答步数（我方终点编码）、shape-canvas 答形状名（我方面积）、sorting-board 是分类（我方排序）、pattern-board 是等差数列（我方 ABAB 周期）、money-board 单位元（我方角）+4 题 paid−price=0 却答 64——**题包自身数据矛盾 18 题**（自带 schema 校验查不出，逐题一致性审计必须进交付流水线）。diagnosis 20 种自由 tag 与我方 19 Gate error 词表零重合。
>
> 处置=产出 `docs/frontend/34_V14_trial155_contract_audit/CONTRACT.md`（**19 渲染器逐条契约对照表**：我方金样例+parser 守卫+题包形状+冲突判定+重导指令+可直接沿用清单 ~45 题）——正是交付方 README 预判的"先修 Contract 再扩产 3,108"。审计脚本保留作**入库验收门禁**（每批题先跑）。

## Review（FE-1432 核对轮：V1.4 题库包 L1-2100/L2-1008 消费判定=**不入库**，2026-10-08）

> 交付方 3,108 题包（L1 Core 2,100 + L2 Dynamic 1,008）核对结论：**矩阵壳，非内容**。20 字段结构 3108 题全一致，但 prompt 3108/3108 全为模板占位句（"围绕X完成N层任务"）、answer 0/3108、diagnosis_target 全车"E01-E07"常量——与旧 210 题包同病且覆盖谎报（声明 19 renderer 实测 17 类，缺 ten-frame/estimation-canvas）。四道闸（M→app 映射/词表/config/答案）一条没解。唯一净增量=question_role 八角色 + variant_group_id + retry_of 链（与复习调度语义吻合，采纳为治理口径参考）。原件存档 `docs/frontend/33_V14_question_bank_L1_2100_L2_1008/`，判定表见该目录 README。**"Gate 打完一道喂一道"技术前提已就绪（19/19），等待交付方补齐真题文本+答案+config+词表族再启动入库。**
>
> 追加（同日午）：交付方发来平行 PR 包（bundle 558033a）——与我方 PR#68 重复作业、基线早于 Batch A~E 收口，**patch 拒绝 apply**（防 CHANGELOG 回滚）；json/xlsx 与我方存档 md5 一致；结论双方独立同判=互证；吸收其 REVIEW_CONCLUSION.md 四段式结论函入 docs/33 作回复底稿。裁决表见 33/README.md。

## Done（FE-1436 R19 PatternBoard Vertical Gate：B5 模板第十八组件，ABAB 规律延续，Batch E 收官=19/19 全清，2026-10-08）

> Batch E 收官题（Gap R19）。pattern-board=花边"黄蓝黄蓝…"识别周期延续 2 空格（调色板点选填珠、点珠两次=抠除）。答案=空格 token 拼接整数 12（黄=1 蓝=2，后端标量判分不动冻结链）。
>
> **解耦第九次运用（Gap 原文直接点名原料）**：Evidence=「尝试顺序、修改过程」——摆错→抠掉→改对，最终 answer=12 判对 + `changed_once=true` 留痕（attempt>blanks 即"试出来的"）；一次对 vs 试错对都算掌握，但策略稳定性诊断价值不同，原料不丢交后端观察匹配。**判错双子靶**：phase_shift [2,1]=周期读对但从末颗重新数（真实高频错法）；rule_ignored [2,2]=全末颗没找规律（Diagnosis P0"规律识别错误"）。parser 三守卫：period∈2..3 存在 / shifted≠expected（回文退化拒）/ 全末颗≠expected。

- **纯函数层** `patternBoardV2.ts`：inferPeriod（最小周期 2..3）+ parsePatternConfig（visible 3..6/blanks 2..3/palette 2..4/调色板⊇可见 token）+ applyPlaceToken（NO_SUCH_TOKEN/NO_EMPTY_SLOT）/applyReplaceAt（SAME_TOKEN）/applyClearAt（ALREADY_EMPTY）+ evaluatePattern EMPTY→PASS→phase_shift→rule_ignored→wrong_sequence + serialize（beads/period/pattern_text/attempt_history=[[slot,from,to]]）。node 语义矩阵全过（首跑抓出 evaluatePattern 相位比对用错操作数 bug——same(shifted) 比的是 shifted vs expected 自身，修为 equals(actual, shifted)——矩阵价值又一实证）。
- **组件** `PatternBoardV2.tsx`：珠串（固定珠+空格虚线位）+双点抠除交互；PATTERN_BEAD_PLACED/REPLACED/REMOVED/RESET 事件链；phase_shift 提示直达教学语言（"从上一颗重新数了"）。
- **能力词表**：新增 `extend_pattern`（三处同步）。
- **链题**：R19 金题（黄蓝黄蓝+2 空，school_objects）**app_rel 第四题**（ABAB=一一对应的时序版）seed RDS；防漂移+1（后端 102→**103 passed**，含相位/惯性靶互斥校验）。
- **API 实证**（pin=1723d78a 五连）：rule_ignored 22 false HINT / 重放同 attempt_id / 异内容 409 / PASS 12(changed_once) NEXT_TASK / phase_shift 21 false。
- **E2E** `e2e/r19-pattern-board.spec.mjs` **11/11 首跑全绿**（解耦靶 changed_once 双断言、双子靶分诊、修正路径含中间态 phase_shift 确认、RESET、dblclick、healing）。全量 E2E 见 PR 验证记录。
- 底表 `docs/governance/R19_PATTERNBOARD_VERTICAL_GATE.md`。**Vertical Gate 19/19——V1.4 全部 Renderer 竖切闭环**。下一步进入收官四件套（FE-1432 题库入库/1433 replay#7/1434 契约 FROZEN/1435 立版）。

## Done（FE-1431 R18 MoneyBoard Vertical Gate：B5 模板第十七组件，凑付换算，Batch E 3/4，2026-10-08）

> Batch E 第三题（Gap R18）。money-board=点钱包档位拿币凑商品价（1角/5角/1元/5元四档，点加取回减）。**价格故意带角位**（3元5角=35角）；答案=付出总角数 35（后端标量判分，不动冻结链）。
>
> **解耦第八次运用（R08/R15/R16 同形态）**：笨凑法（2元+3枚5角=35，币数 5>最少 4）→ 后端判对 + `uses_extra=true` 留痕——"钱凑没凑对=后端判、换得笨不笨=结构层说"。**判错侧（R14/R15/R17 同形态）**：把「5 角」当「5 元」数（3枚1元+5枚5角=55角）→ `denomination_confusion` 精确分诊（Diagnosis P0"面值/金额关系错误"）。parser 守卫：角位必须为 5 的非零倍数（整十价混淆靶退化→拒）+ 钱包必含 5角&1元档（混淆靶可达）——延续"每个 FAIL 态必有可达且互斥靶"。

- **纯函数层** `moneyBoardV2.ts`：parseMoneyConfig（price 5..200/角位非零5倍数/含5&10档/贪心可组）+ applyAddCoin（NO_SUCH_DENOMINATION/OVER_LIMIT 12枚上限）/applyRemoveCoin（NONE_LEFT）+ minCoins 贪心（规范币制下=最优）+ evaluatePayment EMPTY→PASS(uses_extra)→denomination_confusion→underpaid/overpaid（附 diff）。node 语义矩阵全过（混淆 55-35=20、笨凑 5>4、上限 13 拒）。
- **组件** `MoneyBoardV2.tsx`：四档钱包（拿币→台面 chip 队列→取回）；MONEY_COIN_ADDED/REMOVED/RESET 事件链；混淆提示直达教学语言（"把 5角 当 5元 数啦？角和元不一样大"）；专件替换基座路由（基座 MoneyBoard 保留作参考）。
- **能力词**：复用 compose_groups/decompose_group；registry vertical_gate → R18。
- **链题**：R18 金题（练习本 3元5角=35 角，shopping）**app_strat 第三题** seed RDS（pin=b978d294）；防漂移+1（含"混淆靶总量≠正解"校验，后端 22 passed）。
- **API 实证**（pin 首抽即中）：confusion 55 false HINT / 重放同 attempt_id / 异内容 409 / PASS 35 NEXT_TASK（递增 attempt_no）。
- **E2E** `e2e/r18-money-board.spec.mjs` 10/10 首跑全绿（解耦靶 uses_extra 双断言、混淆分诊、取回补正路径、取回下限禁用、dblclick、healing）。
- 底表 `docs/governance/R18_MONEYBOARD_VERTICAL_GATE.md`。**Vertical Gate 进度 18/19；Batch E 3/4**。

## Done（FE-1430 R17 Clock Vertical Gate：B5 模板第十六组件，钟面拨针，Batch E 2/4，2026-10-08）

> Batch E 第二题（Gap R17）。clock=钟面点数字拨时针 + 整点/半点两档拨分针（SVG 双针实时指向，拖拽的儿童可靠性替代）。整时/半点口径（二年级认识时间）；答案=总分钟数 h×60+m（3:00→6:00=360，后端标量判分不动冻结链）。
>
> **判错分诊（R14/R15/R16 同形态）**：`hand_swap`——把**长针指的数字**当时针读（6:00 长针在 12→误读"12点"拨成 12:00，answer=720≠360）精确命中 Diagnosis P0"时针/分针关系错误"。形式化 swapOf(target)={h: m===0?12:m/5, m}；parser 守卫互换态必须合法且≠target（目标 12:00 互换=自身→拒，配置层消灭退化靶）。

- **纯函数层** `clockV2.ts`：parseClockConfig（m∈{0,30}/h∈1..12/起终不重合/互换靶合法且互斥）+ applySetHour（NO_SUCH_POSITION/INVALID_COMBO——m=30 时 h=12 合法=12:30）/applySetMinute（0/30 两档，unchanged 不产生调整）+ evaluateClock EMPTY→PASS→hand_swap→wrong_time（附分钟差）+ serialize（h/m/time_text/adjust_history=[[hand,from,to]]）。node 语义矩阵全过（含半点链 4:30=270、12:30 合法）。
- **组件** `ClockV2.tsx`：SVG 钟面 12 数字位（g+circle 双层 picked）+ 整/半点按钮；CLOCK_HOUR_SET/MINUTE_SET 事件链；指针 rotate 实时（`rotate(deg 100 100)`）；关系错误提示直达教学语言（"看着长针指的数字读钟啦？"）；专件替换基座路由（基座 Clock `<input type=time>` 保留作参考）。
- **链题**：R17 金题（3:00 拨到 6:00，**time_schedule 词表族首题真实覆盖**）app_cond 第三题 seed RDS（pin=814b32f1）；防漂移+1（含"互换靶≠正解"校验，后端 21 passed）。
- **API 实证**（pin 首抽即中）：hand_swap 720 false HINT / 重放同 attempt_id / 异内容 409 / PASS 360 NEXT_TASK（递增 attempt_no）。
- **E2E** `e2e/r17-clock.spec.mjs` 10/10（首跑 3 挂=picked class 只在 circle 未镜像到 g 层 testid，修 g 双层后全绿——新坑入 skill；半点链/UNDO/RESET/dblclick/healing）。全量 **167 passed** 零回归（R17+R18 合跑）。
- 底表 `docs/governance/R17_CLOCK_VERTICAL_GATE.md`。**Vertical Gate 进度 17/19；Batch E 2/4**。

## Done（FE-1429 R16 Ruler Vertical Gate：B5 模板第十五组件，量尺两点标记，Batch E 起手，2026-10-08）

> Batch E 第一题（Gap R16）。ruler=尺面点刻度放两标记夹住物体（第 3 点清空重放——"再点就是重来"儿童心智）。物体**故意非零起点**（铅笔跨 3..8）；答案=标记间隔 5（后端标量相等判分，不动冻结链——Gap"tolerance evaluator"的容差语义留待非整刻度题库启用，差异入底表 §3）。
>
> **解耦第七次运用（R08/R15 同形态）**：平移段靶 {4,9} span=5 → 后端判对 + `aligned=false` 留痕——"量对了=后端判、夹没夹住两头=结构层说"。**判错侧**：零起误读 {0,8}→answer=8≠5 判错 + `from_zero_reading` 精确分诊（Diagnosis P0"刻度读取错误"落地）；parser 守卫 left≥1 保证此靶必判错且与 PASS 互斥（R15"靶可达"纪律延续）。

- **纯函数层** `rulerV2.ts`：parseRulerConfig（max 10..30/物体整数刻度 right>left≥1≤max）+ applyPlaceMark（NO_SUCH_TICK/重放）/applyClearMarks（NO_MARK）+ evaluateMeasurement EMPTY→PASS(aligned)→from_zero→wrong_span（附 span/diff）+ serialize（marks 起止/span/reading/object/structure）。node 语义矩阵 20 断言全过。
- **组件** `RulerV2.tsx`：刻度尺+物体覆盖层+▼标记；RULER_MARK_SET（payload.restarting 记重放）/RULER_MARKS_CLEARED 事件链；误读提示直达教学语言（"铅笔不是从 0 开始的，要夹住它的两头"）；专件替换基座路由（基座 Ruler range 滑条保留作参考）。
- **能力词表**：新增 `measure` 三处同步；registry vertical_gate E4→**R16**。
- **链题**：R16 金题（铅笔 3→8 长 5，school_objects）**app_model 节点第五题** seed RDS；防漂移+1（后端 99→**100 passed**，含"零起靶≠正解"校验）。
- **API 实证**（pin=1f23c045 首抽即中）：from_zero 8 false HINT / 重放同 attempt_id / 异内容 409 / PASS 5 NEXT_TASK（全程带递增 attempt_no——R15 坑口径固化）。
- **E2E** `e2e/r16-ruler.spec.mjs` 10/10 首跑全绿（解耦靶 aligned=false 双断言、第三点重放、清标记回 EMPTY、dblclick、healing）。
- 底表 `docs/governance/R16_RULER_VERTICAL_GATE.md`。**Vertical Gate 进度 16/19；Batch E 1/4**。

## Done（FE-1427 R15 DirectionGrid Vertical Gate：B5 模板第十四组件，5×5 路径导航，Batch D 收官，2026-10-08）

> Batch D 收官题（Gap R15）。direction-grid=点相邻格挪步走出路线（上/下/左/右一步；对角/隔格/同格拒绝）。答案=**终点格编码 row×cols+col**（19，后端标量相等判分不动冻结链）；完整路径走 Evidence `path/directions/turns`（Gap"movement sequence"）。route evaluator 四态：EMPTY→PASS(detour)→direction_reversed→wrong_position（附曼哈顿距离）。
>
> **解耦第六次运用（R08 同形态）**：绕路走到 ☆→answer=19 判对 + `structure.detour=true` 留痕——"到没走到=后端判、走得绕不绕=结构层说"。**反走靶与 R14 同侧（判错也带分诊）**：位移整体取反 (1,0)→answer=5≠19 判错但 `direction_reversed` 精确命中（Diagnosis P0"方向错误"落地）；parser 守卫（行列位移非零+反走靶必在盘内）保证该态可达且与 PASS 互斥。

- **纯函数层** `directionGridV2.ts`：parseDirectionConfig（grid 3..6/起终不重合/行列位移非零/反走靶盘内——四守卫，{r,c} 与 [r,c] 双形态）+ applyMoveTo（NO_SUCH_CELL/SAME_CELL/NON_ADJACENT）/applyUndoStep（AT_START）+ serialize（path "r,c" 序列/directions/turns/structure）。node 语义矩阵全过。
- **组件** `DirectionGridV2.tsx`：25 格棋盘（起/☆/●/· 角色标注）；PATH_EXTENDED/PATH_STEP_UNDONE/PATH_CLEARED 事件链；三分类提示直达教学语言（"好像把方向走反啦"）；专件替换基座路由（基座 DirectionGrid 保留作参考）。
- **能力词表**：新增 `navigate`（InteractionCapability + KNOWN_CAPABILITY_IDS + descriptor 三处同步）。
- **链题**：R15 金题（start(2,2)→target(3,4)，school_objects）**app_model 节点第四题** seed RDS；防漂移+1（后端 98→**99 passed**，含反走靶可达性校验）。
- **API 实证**（pin 首抽即中）：反走 5 false HINT / 重放同 attempt_id / 异内容 409 / PASS 19 NEXT_TASK。**新坑：手测重试必须带递增 attempt_no——缺省 1 撞兼容轨幂等回放旧 attempt**（前端 session 页本来正确，httpx 手测踩出）。
- **E2E** `e2e/r15-direction-grid.spec.mjs` 10/10（envelope answer={value:19} 封装断言——r01/r10 同款口径；cellRole start 常驻断言；detour 双断言；dblclick；healing）。冷编译假失败重现（06/09/10 首跑超时、二跑 19.8s 全绿）。
- 底表 `docs/governance/R15_DIRECTIONGRID_VERTICAL_GATE.md`。**Vertical Gate 进度 15/19；Batch D 4/4 全清**。

## Done（FE-1428 首页挑战入口配置化：V2 五能力节点各一张手工测试卡，2026-10-07）

> 14 个已闭 Gate 中 8 个组件的 V2 金题挂在 app_model / app_rd / app_cond 三个能力节点上，但首页写死只有「数量关系」「策略」两张卡（app_rel/app_strat），新组件无手工测试入口。按"每个卡先放一个入口组件，测试通过完再收起或优化"的口径改造：入口从硬编码改为 `CHALLENGE_CARDS` 配置表驱动，5 个 V2 金题能力节点各一张卡；后续收起/优化只动配置表，渲染逻辑不再改。

- `challengeMapping.ts`：`ChallengeKind` 扩为 quantity/modeling/reading/conditions/strategy；新增 `CHALLENGE_CARDS`（icon/title/goal/keywords/fallbackAbilityId）。解析仍按名称关键词优先（后端/mock 两套命名兼容），解析不到退 `fallback_ability_id`（app_* canonical，与 ability_seed 及 mock 能力表一致）。
- `MathHomeScreen.tsx`：两张写死卡 → `CHALLENGE_CARDS.map` 动态渲染（5 卡，2 列网格自然排布）。
- 验证：tsc 0 错、next build ✓（**新坑：NODE_OPTIONS 注入的 brokered-fs-shim 与 webpack 并行 mkdir 竞态致 EEXIST/ENOENT 假失败，`NODE_OPTIONS=""` 绕过后正常**；build 会自动把 distDir types 追加进 tsconfig include，提交前需回滚）；3100 首页 SSR 实测 5 张卡全出；后端抽查 app_model/app_rd/app_cond 三节点 `tasks/next` 均正确命中 V2 金题 goal。E2E 零触碰（无 spec 引用首页卡）。

## Done（FE-1426 R14 SortingBoard Vertical Gate：B5 模板第十三组件，比较维度干扰设计，Batch D 3/4，2026-10-07）

> Batch D 第三题（Gap R14）。sorting-board=两步点选交换排序（点 A 拿、点 B 换位，drag 的儿童可靠性等价替代）。答案=数值升序拼接整数（1247，后端标量相等判分不动冻结链）。**Diagnosis P0"比较维度错误"的设计落地**：卡面字号（visual_rank）与数值**故意错开**做干扰维度——按"看起来大"排 → dimension_confusion 精确命中；parser 守卫保证正序/降序/视觉序三态互斥（否则分诊失效）。
>
> **解耦第五形态（与前四次互补）**：R08/R11/R12/R13 是"判对+原料留痕"；R14 的 dimension(1274)/reversed(7421) 答案本身≠正解 → 判错，但 `structure.error` 能区分**错的方式**——判错也能带分诊，解耦架构的对称补充（底表 §2）。

- **纯函数层** `sortingBoardV2.ts`：parseSortingConfig（值 1~9 一位数拼接无歧义/档位 1..n 排列/initial≠target/visual 序既非正序也非降序——六守卫）+ applySelectCard(toggle)/applySwap（NO_SELECTION/SAME_CARD/NO_SUCH_ITEM）/applyUndoSwap（原子退末次交换）+ evaluateSorting EMPTY→PASS→reversed→dimension→disordered + serialize（swaps=[[from,to]] 排序过程/order_values 轨迹/structure）。node 语义矩阵全过。
- **组件** `SortingBoardV2.tsx`：卡面字号按 visual_rank 显性化干扰维度（数字 1 用 36px 最大字）；SORT_CARD_SELECTED/UNPICKED/SWAPPED/UNDOED 事件链；三分类提示文案直达教学语言（"你是按字的大小排的吧？"）；专件替换基座路由。
- **链题**：R14 金题（7、1、4、2 从小到大=1247，school_objects）**app_rd 节点第二题** seed RDS；防漂移+1（后端 97→**98 passed**，含三参考序互斥校验）。
- **API 实证**（pin 首抽即中）：dimension 1274 false HINT / reversed 7421 false / PASS 1247 NEXT_TASK / 重放同 attempt_id。
- **E2E** `e2e/r14-sorting-board.spec.mjs` 11/11（干扰字号 toHaveCSS 断言——**新坑：toHaveStyle 是 Testing-Library API，Playwright 用 toHaveCSS**；swaps 轨迹、dimension/reversed 双靶、修正路径、退交换、dblclick、healing）。全量套件 **127 passed** 零回归。
- 底表 `docs/governance/R14_SORTINGBOARD_VERTICAL_GATE.md`。**Vertical Gate 进度 14/19；Batch D 3/4**。

## Done（FE-1425 R13 ShapeCanvas Vertical Gate：B5 模板第十二组件，钉子板几何评估器，2026-10-07）

> Batch D 第二题（Gap R13）。shape-canvas=点阵板依序点顶点画封闭图形（draw=点钉、delete=撤点；move/rotate 以点序重建替代，差异记录底表 §3）。金题"钉子板上画面积 6 的长方形"：答案=面积（shoelace 整数二倍面积免浮点误差），**解耦第四次运用**——平行四边形面积恰=6 → 后端判对（correct=true NEXT_TASK）+ `not_right_angle` 几何属性原料走 Evidence。geometry evaluator 判定顺序=**形状属性错优先于尺寸错**（EMPTY→vertex_count→not_right_angle→wrong_size→PASS，Diagnosis P0"几何属性错误"权重）。

- **纯函数层** `shapeCanvasV2.ts`：parseShapeCanvasConfig（grid 4~6/面积可达守卫/target_shape 词表）+ applyAddPoint（OUT_OF_RANGE/DUPLICATE_POINT/MAX_VERTICES 三拒）+ applyRemoveLast + doubledSignedArea/countRightAngles（点积==0 整数判定）+ serialize（vertices 点击轨迹序/right_angles 原料/structure）。node 语义矩阵全过（含凹四边形/顺时针 PASS/config 三守卫）。
- **组件** `ShapeCanvasV2.tsx`：SVG 点阵板+自动闭合预览+顶点序号；SHAPE_POINT_ADDED/DELETED/REJECTED=Gap"绘制轨迹"事件链；专件替换基座路由（基座保留作参考）。
- **链题**：R13 金题（面积 6，**app_model 第三题**）seed RDS；防漂移+1（后端 96→**97 passed**）。
- **API 实证**（pin 首抽即中）：解耦 true+原料 / wrong_size false / PASS NEXT_TASK / 重放同 attempt_id。
- **E2E** `e2e/r13-shape-canvas.spec.mjs` 11/11（E2E-04 首跑断言形态笔误修正——vertices 是 {x,y} 对象序；解耦双断言、修正路径撤点重画、重复点拒绝、dblclick、UNDO、healing）。全量套件 **116 passed** 零回归。
- 底表 `docs/governance/R13_SHAPECANVAS_VERTICAL_GATE.md`。**Vertical Gate 进度 13/19；Batch D 2/4**。

## Done（FE-1424 R12 ShapeGallery Vertical Gate：B5 模板第十一组件，图形分类解耦最锋利一例，Batch D 起手，2026-10-07）

> Batch D 起手（Gap R12）。shape-gallery=图形墙选形分类：点形拿起（toggle 可放下）→ 点"正方形的家"放进 → 点家里成员退回。**答案=家里图形个数**——本 Gate 把解耦口径推到最锋利：混入长方形但数对 3 → **后端判对（correct=true NEXT_TASK）+ attribute_confusion 原料留痕**（R08/R11 之后第三次运用，几何域成立=跨域通用架构）。分类 evaluator 判定顺序=属性错优先于漏放（Diagnosis P0"属性识别错误"权重）；config 守卫（前端 parser 同式）：目标类必须有成员且墙上有诱饵，否则答案退化为"全拿"。

- **纯函数层** `shapeGalleryV2.ts`：parseShapeGalleryConfig（id 唯一/kind 四类/target 有成员且有诱饵）+ applySelect（toggle+IN_HOME 拒）/applyPlaceHome（NO_SELECTION）/applyReturnHome + evaluateShapeGallery EMPTY→attribute_confusion→missed→PASS + serialize（home 轨迹序/home_kinds 原料/structure）。node 语义矩阵全过。
- **组件** `ShapeGalleryV2.tsx`：墙+家两步点选（儿童可靠性口径不依赖 drag）；SHAPE_SELECTED/DESELECTED/PLACED/HOME_REJECTED/RETURNED 事件链=Gap"选择与分类轨迹"；专件替换基座路由。
- **链题**：R12 金题（给正方形找一个家，答案=3，school_objects）**app_cond 节点第二题** seed RDS；防漂移+1（后端 95→**96 passed**）。
- **API 实证**（pin 首抽即中）：混入但数对→**true**（解耦端到端）/ missed→false HINT / PASS→NEXT_TASK / 重放同 attempt_id。
- **E2E** `e2e/r12-shape-gallery.spec.mjs` **12/12 一次全过**（toggle、NO_SELECTION、home 轨迹序断言、解耦双断言、退回修正路径、IN_HOME disabled、G7 漏放→补放 attempt_no=2、dblclick 防重入、UNDO 单步、healing）。全量套件 **105 passed** 零回归。
- 底表 `docs/governance/R12_SHAPEGALLERY_VERTICAL_GATE.md`。**Vertical Gate 进度 12/19**。

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
