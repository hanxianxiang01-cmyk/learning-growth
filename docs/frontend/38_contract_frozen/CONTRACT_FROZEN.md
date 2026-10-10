# V1.4 题库生产契约 FROZEN v2.0（FE-1434）

- **状态**：🧊 FROZEN（2026-10-10）。本文件 = V1.4 题库交付-验收的**唯一权威契约**，取代并合并：PC-v1（docs/35，交付方原契约）、docs/34 CONTRACT.md（我方对照审计表，含 §7 四轮守卫补文）、docs/36 TASK_ORDER.md 验收条款、docs/37 ERROR_VOCAB.md、docs/governance/FE1438_QA_SAMPLE_INGEST.md 隔离通道。
- **冻结含义**：下列条款（尤其 §3 守卫全集）为 parser 源码的逐字镜像；parser 源码与本文**冲突时以源码为准并立即修订本文**（先修契约再扩产）。
- **变更管控（四轮教训定版）**：V1.4 期间冻结。任何 renderer 的 parser 守卫/值域/形态变更 → 必须同步修订本文对应行 + fixtures 金样例正/反例锚点 + 通知交付方；**散在底表/源码=没有契约**（trial155 四轮验收史：114→37→3→0 的 37/3 两轮全因本条款缺失）。
- 提取方法（可复现）：`*V2.ts` parse*Config 全部 `return null` 守卫机器提取 + `GOLD_RESOURCES_V2` 金样例反查 + ObjectCounterV2 组件级双形态（FE-1438）。

## 1. 全局条款（每题必守）

| # | 条款 |
|---|---|
| G1 | `answer` = **非空标量**（int 或 str），禁止 `{type,value}` 包装；`_judge` float 相等或字符串相等判分；空串/包装=拒 |
| G2 | 硬依赖字段：`hint_ladder`（4 级，首级不泄答案）、`goal`、`evidence_targets`、`error_models[].pattern` **逐字取自 §4 诊断词表对应 renderer 行**（自造词=Gate 6 永不命中） |
| G3 | `mode` 取 §2 词表值（组件按我方 mode 语义渲染；自造 mode 只是标签、误导审计） |
| G4 | `ui_schema` 顶层=TaskUISchema V2：`schema_version:"2.0"` + `prompt.text` + `workspaces[0]`（workspace_id:"main"/renderer/mode/config/initial_state/capabilities/constraints）+ `response_contract`；提交信封=`{schema_version,type,ui_revision,answer,workspaces[{workspace_id,data}],interaction_events}` |
| G5 | `context_family` ∈ 受控词表 7 值：`school_objects / comparison / before_after / lineup_position / shopping / sharing / time_schedule`（必填，缺失=Gate 2 FAIL） |
| G6 | `question_id` 全局唯一且交付批内保留原 ID；换 ID=新题全流程重审 |
| G7 | `renderer_id` 归一 kebab-case ∈ §2 的 19 项；**choice-grid / data-table / pictograph / timeline 不在 V1.4 发布范围**（组件保留运行，无验收 parser，出现=整包拒收） |

## 2. Renderer × Mode 词表（19 项，= V2_RELEASE ∩ 金题实证）

bar-model `part_whole` ｜ number-line `jump_sequence` ｜ object-counter `count_compose` ｜ number-input `numeric_answer` ｜ column-arithmetic `addition`（减法=`subtraction`）｜ place-value `place_value_build` ｜ ten-frame `quantity_structure` ｜ formula-board `unknown_number` / `unknown_operator` ｜ array-board `array_structure` ｜ grouping-board `equal_groups` ｜ estimation-canvas `estimation_range` ｜ shape-gallery `shape_classification` ｜ shape-canvas `shape_drawing` ｜ sorting-board `ordering` ｜ direction-grid `route_navigation` ｜ ruler `measurement` ｜ clock `time_setting` ｜ money-board `payment` ｜ pattern-board `pattern_extension`

## 3. Config 守卫全集（parser 源码逐字镜像；违反=Gate 3 硬拒）

### 3.1 专件 15（独立 parser，硬拒）

**bar-model**：mode 必填；`answer_bar ∈ {a,b,c}`；`known` 对象恰含 2 个键（第 3 个=答案位，已知数不得包含 answer_bar）且值=int ∈[1,∞)；part_whole 解出值 ≥1。

**place-value**：`target` int ∈[10,999]；`pool` 长度=target 位数、每位 ∈[0,9]、`sorted(pool)==sorted(target 各位数字)`（多重集相等，数字不得多给/少给）。

**formula-board**：`tokens` 非空数组，元素形态 **`{t,v}`**（t∈num|op|eq|slot）；num.v=int；**op.v ∈ `{"+","-"}`（乘除拒——operator 分诊基于加减翻转语义；乘除题换挂 column-arithmetic/number-input）**；eq 恰 1 个；slot.id 必填全题唯一、`accept ∈ {number,operator}`、slot 数 ∈[1,3]；`answer_slot` 必须是已存在的 slot.id。

**array-board**：`target_rows`/`target_cols` int ∈[1,9]；`max_rows/max_cols` 可选（≥target 且 ≤12，缺省=9）。

**grouping-board**：`items` int ∈[2,20]；`target_groups` int ∈[2,items]；`max_groups` 可选（∈[target_groups,items]，缺省=items）。答案语义=**等分**（每份数），包含分口径=语义错位拒收（Gate 6 层）。

**estimation-canvas**：`reference` int ≥1；`max` int ∈[2,100]（parser 值域；交付纪律 Gate 2 R7 收紧 ≤60 且不贴边，严于 parser）；`expected/actual` int 且全部落 [1,max]（reference/expected/actual 三者）；`expected ≥10` 且为 10 的倍数；`actual ≥11` 且**非** 10 的倍数；`round(actual/10)*10 == expected`（近似自洽）；`tolerance` 可选（≥1，缺省=max(1,round(max×0.1))）。

**shape-gallery**：`shapes` 4~10 张，每张 `{id,name,color,kind}` 全字符串必填、id 唯一；`target_kind` ∈ 组件 KIND_SET；目标类计数 ∈[1, shapes.length)（全都不在/全都在=无区分度拒）。

**shape-canvas**：`grid` int ∈[4,6]；`target_area` int ∈[2,20] 且 ≤(grid−1)²（点阵可达）；**`target_shape` 仅 `"rectangle"`**（triangle/复合形评估器不支持——§7 旧笔误已勘误）。

**sorting-board**：`direction` 仅 `"asc"`；`items` 3~6 张 `{id,value,visual_rank}`：id 唯一、value int ∈[1,9] 且**互异**、visual_rank 互异且恰覆盖 1..n；`initial_order`=id 全排列不重复；初始态≠目标值序（已排好拒）且≠visual_rank 序与逆序（平凡拒）。

**direction-grid**：`rows/cols` int ∈[3,6]；`start/target` 接受数组 `[r,c]` 或对象 `{r,c}`/`{row,col}` 双形态；坐标 int、**0 起**且 <rows/cols；start≠target；**dr≠0 且 dc≠0**（纯直线无转向教学点）；**反走靶可达**：(start.r−dr, start.c−dc) 落盘内（direction_reversed 分诊原料）。answer=终点格编码 `row×cols+col`。

**ruler**：`max` int ∈[10,30]；`object`=[l,r] 两元素、int、**l ≥1**（零起误读 from_zero_reading 分诊原料）、r>l、r≤max。

**clock**：`start/target` 必须**数组 `[h,m]`**（parser readTime 只认数组；{hour,minute} 对象=拒；旧 trial155 对象形仅历史审计兼容）；h int ∈[1,12]、**m ∈{0,30}**（整/半点两档 UI）；start≠target（题已做完拒）；**swap 靶自环退化**：swapOf(target)（分针读数当时针）与 target 重合（6:30、12:00 类）拒——hand_swap 分诊不存在。answer=总分钟数（6:00→360）。

**money-board**：单位=角；`price` int ∈[5,200]、**price%5==0 且 price%10!=0**（角位非零 5 倍数——保 under/overpaid 混淆靶与 PASS 互斥）；`denominations` ≥2 枚、int>0 互异、**必含 5 和 10**、币制建议 [1,5,10,50]；`minCoins(price,den)≠−1`（凑得出）。**无"付钱找零"交互**：R18=凑付玩法（拿币凑 price），change 场景题必须改造成凑付或换挂 number-input。

**pattern-board**：`visible` 3~6 项、int ∈[1,5]；`blanks` ∈[2,3]；`palette` 2~4 项、int ∈[1,5] 互异、visible⊆palette；存在最小周期且非 trivial（全同 lastVisible=无规律拒）；answer=空位 token 拼接个位数（多位整型=拼接歧义拒）。

**ten-frame**：`target_count`（或 `target`）int ∈[1,20]；`max_frames` ≥1（缺省 2）。

### 3.2 基座链 4（无独立 parser、宽松读取——不硬拒，但语义必须对）

- **number-line**：`scale:{min,max,tick_step}` + `start_marker:{marker_id,value}`；answer=落点值。
- **object-counter**：`groups:[{group_id,label,symbol,count,locked}]`；**`expected` 双形态合法（FE-1438 组件修复）**：金题=`{group_id,min_count}` 对象数组 / 交付批=与 groups 顺序平行的数字数组 `[5,3]`（组件按序 zip）；answer=总数。分组原料不得缺（objects 单组简化形= R01 语义降级，Gate 6 抓）。
- **number-input**：`{min,max,integer_only}`（+可选 placeholder）；answer=标量。
- **column-arithmetic**：`{operands:[a,b], places, operand_layout:"fixed"}`，mode ∈ `addition/subtraction`；answer=结果值。

## 4. 诊断词权威表（`error_models[].pattern` 逐字；FAIL 错因 vs PASS 留痕见注）

| renderer | pattern 全集 |
|---|---|
| bar-model | modeling, relation, calc |
| number-line / number-input / column-arithmetic / object-counter / ten-frame / grouping-board（共用） | strategy, calc, modeling（按行取：line/input/column=strategy+calc；counter/ten-frame=modeling+calc；grouping=group_count, unequal_share, calc） |
| place-value | place_value_confusion, calc |
| formula-board | operator, relation |
| array-board | transpose, count |
| estimation-canvas | no_reference_use, too_high, too_low |
| shape-gallery | attribute_confusion, missed |
| shape-canvas | vertex_count, not_right_angle, wrong_size |
| sorting-board | dimension_confusion, reversed, disordered |
| direction-grid | direction_reversed, wrong_position, detour（留痕） |
| ruler | from_zero_reading, wrong_span, misaligned（留痕） |
| clock | hand_swap, wrong_time |
| money-board | denomination_confusion, underpaid, overpaid, uses_extra（留痕） |
| pattern-board | phase_shift, rule_ignored, wrong_sequence, changed_once（留痕） |

> 权威源=`resource_seed_v2.py` 金题实际 seed + parser evaluate 返回枚举交叉（docs/37/ERROR_VOCAB.md）。留痕词（detour/uses_extra/changed_once/misaligned）出现在**判对**过程观察，语义勿混。

## 5. 验收链（8-Gate，口径 docs/36 §3 唯一权威）

Gate 1 JSON Schema → Gate 2 `consistency_audit.py`（**v2 canonical**：R1~R8 六类语义一致性+词表；回归基线 fixtures gold 0/neg 恰 4）→ Gate 3 `audit-155-config.mjs`（config×真实 parser，判定权=我方复跑）→ Gate 4 pin 下发 → Gate 5 Judge → Gate 6 Evidence → Gate 7 Diagnosis（4~7 抽样 ≥5%、≥8 题、覆盖全出现 renderer，QA child …0099）→ Gate 8 `qa_replay_mastery.py` #7（确定性回放）。

- 交付包结构固定：`155_question_bank_delivery_v2/`（A/B/C 三 questions.json+各报告+ability_mapping+reports+DELIVERY_MANIFEST.md 逐题七列）；缺随附申报=整包拒收。
- 机器门顺序卡死：G1/G2 任一未过→G3 不跑；G3 未过→G4~7 不跑。下一轮起不再人工逐题审。
- **qa_staged 隔离通道（FE-1438）**：未过 M→app 映射审批的题以 `review_status='qa_staged'` 入库——catalog/生产池不可见、仅 pin 路径+QA child 放行；审批过→转 published=正式入库。
- 能力映射：M01–M42→app_* 提案随包（TRIAL_MAPPING_PENDING_APPROVAL），正式入库前过映射审批。

## 6. 修订记录

| 版本 | 日期 | 变更 |
|---|---|---|
| **v2.0 FROZEN** | 2026-10-10 | FE-1434 汇编冻结：合并 PC-v1+docs/34/36/37+FE-1438；**§3=parser 守卫全集首次成文**（机器提取+人工校对，含四轮补文：反走靶可达/clock 数组+[h∈1,12]/formula {t,v}+op∈{+,-}/money %5%10+无找零/shape-canvas rectangle only/grouping [2,20]/estimation 近似自洽/object-counter expected 双形态）；§4 诊断词全集；§5 验收链含 qa_staged；变更管控条款（教训定版） |

> 上游史料（非权威，仅供溯源）：PC-v1 原件 docs/35；docs/34 CONTRACT.md（对照审计史）；docs/36（任务单签发史）；docs/37（四轮验收史 b114→g37→h3→i0）。
