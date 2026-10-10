# V1.4 Renderer Config 契约对照表（trial155 实灌审计产出，2026-10-08）

> 📦 **已归档（FE-1434，2026-10-10）**：本对照表为 trial155 时代审计产出，其 §2/§7 守卫条款已逐字并入并**由 `docs/frontend/38_contract_frozen/CONTRACT_FROZEN.md` v2.0 取代**（V1.4 唯一权威契约）。本文件保留作 trial155 四轮验收史溯源（b114→g37→h3→i0），**新的交付/验收以 FROZEN v2.0 为准**。

**用途**：交付方《V1.4 P0 试灌题包 155 题》的 config/answer 形状与我方 19 个已闭
Vertical Gate 的**实战契约**（`resource_seed_v2.py` 金题 + `*V2.ts` parser 守卫）逐渲染器对照。
**扩产 3,108 前必须按本表对齐**——题包自身的 TaskUISchema JSON Schema 校验通过≠能进我方链，
错位大头不在字段名（可机器转换），在**答案语义轴与评估器口径**（不可转换，只能重导）。

## 0. 审计方法（可复现）

```bash
# ① 原始包 config 直接过我方 15 专件 parser：
cd apps/child-web && NODE_OPTIONS="" node --experimental-strip-types --no-warnings \
  scripts/audit-155-config.mjs <trial155.json>
#   → 专件覆盖 122 题：PASS 8 / FAIL 114（93%）；基座链 41 题（宽松 asNumber 读取，不硬拒）
# ② 临时垫片转换后再审（convert_trial155.py）：
cd apps/learning-api && python3 scripts/convert_trial155.py <in.json> /tmp/conv.json
#   → 可转换 92 / 语义缺口拒转 22（sorting 8+formula 6+gallery 8）；转换后再审 PASS 51 / FAIL 41
```

**结论**：字段名错位约占 1/3（垫片可救）；答案轴错位约占 2/3（**必须交付方重导**）。

## 1. 全局差异（先读这三条）

| # | 我方契约 | 题包现状 | 影响 |
|---|---|---|---|
| G1 | `content.answer` = **标量**（int/str），`_judge` float 相等或字符串相等判分 | `answer={type,value}` 对象 | 判分链直接失效；垫片可提取 value，但**按契约应直接给标量** |
| G2 | seed 硬依赖：`hint_ladder`（4 级）、`goal`、`evidence_targets`、`error_models[].pattern↔前端 structure.error 词表逐字一致` | 无 hint_ladder/goal；diagnosis 为自由文本 tag（20 种）与我方 error 词表**零重合** | 诊断链接不通——前端 serialize 吐 `direction_reversed`，题包标 `direction_or_position_error`，观察匹配永不命中 |
| G3 | mode 词表=我方各 Gate 定稿值（如 route_navigation / time_setting / shape_drawing） | 自造 mode（shortest_path / set_time / compose…） | seed 校验可过（mode 不强校验），但组件按我方 mode 语义渲染，题包 mode 只是标签 |

## 2. 逐渲染器对照（19 全量）

> 「我方金样例」= resource_seed_v2 实际入库 config；「parser 守卫」= 前端拒收条件（违反=必然 FAIL）。

### 2.1 专件 Gate（15 个，有独立 parser，硬拒）

| renderer | 我方 config 金样例 | 题包 config | 答案轴冲突 | 判定 |
|---|---|---|---|---|
| **bar-model** | `{mode:"part_whole", known:{a:5,b:3}, answer_bar:"c", max_blocks:12}` ans=8 | `{relationship:"part-whole", bars:[{id,value}…], max_value}` ans=value | 轴同（求未知量）；字段名可转 | 🟡 垫片可救（9 题里 8 题转后过审） |
| **place-value** | `{target:352, pool:[2,5,3]}` ans=352（摆数） | `{number:47, target_place:"ones"}` ans=7（数位含义） | 🔴 **两种玩法**：我方=数位卡摆数（R06），题包=问某数位数字。题包语义更接近 number-input | 重导或换挂 renderer |
| **formula-board** | `tokens` 数组（slot/op/num/eq）+answer_slot，ans=数或符号 | `{expression:"7+□=12", slots, operators}` 字符串模板 | 轴同（求未知数），但"□=几"我方仅支持**单 slot+固定缺位**；construct 类（自组算式）我方评估器不判结构 | 🟡 已知数在右的式子可转（6/8 转后仍拒——表达式解析歧义） |
| **array-board** | `{target_rows:3, target_cols:4, max_rows:8, max_cols:8}` ans=12 | `{rows:3, columns:4, editable, show_multiplication}` ans=12 | 轴同 | ✅ 纯改名（8 题全过） |
| **grouping-board** | `{items:12, target_groups:3, max_groups:6}` ans=每组数 4（**等分**） | `{total:12, group_size:3}` ans=4（**包含分**：12里有几个3） | 🔴 数学上同为除法但**交互语义不同**：R09 孩子建组分糖、答案=每份数；题包答案=份数。转置后 6/8 过、2 题（21÷3=7、24÷6=4→groups 超 max_groups 或 items 非整除）被守卫拒 | 重导：改"把 total 平均分成 N 份"口径 |
| **estimation-canvas** | `{reference:10, max:60, expected:40, actual:38, tolerance:6}` ans=40（滑条估算+理由） | `{objects:{count}, estimate_targets:[10..100], tolerance:2}` ans=20（选最近档） | 🔴 交互不同：R11=连续滑条+tolerance 区间判；题包=离散档位选择。max>60/tolerance<6 还会撞守卫值域 | 重导或换挂 number-input |
| **shape-gallery** | `{target_kind:"square", shapes:[{id,name,kind,color}…6]}` ans=目标类计数 | `{shapes:["triangle"…字符串], target_shape:"三角形", ask:"corner_count"}` ans=3（属性问答） | 🔴 题包问"角数"是**属性读数**，R12 是**分类放家计数**。id/name/color 结构化对象也缺 | 重导 |
| **shape-canvas** | `{grid:5, target_area:6, target_shape:"rectangle"}` ans=面积 6（数值） | `{canvas_size:{w,h}, allowed_shapes, target:"square/house/two_triangles"}` ans=**形状名字符串** | 🔴 答案轴不同（数值 vs 文本）；house/large_square/rotated_rectangle 等复合拼形我方几何评估器（shoelace+点积）判不了 | 重导：给面积目标 |
| **sorting-board** | `{direction:"asc", items:[{id,value,visual_rank}], initial_order}` ans=数值拼接 1247 | `{items:["2,4,6","1,3,5"], categories:[A,B], rule:"奇偶"}` ans=规则字符串 | 🔴 **完全不同族**：R14=数值排序（order evaluator），题包=分类归组（categorize）。且 answer"奇数和偶数"文本无法标量判分 | 重导：分类题应换挂 shape-gallery 类交互 |
| **direction-grid** | `{rows:5, cols:5, start:{r,c}, target:{r,c}}` ans=**终点格编码** 19 | `{grid:{rows,cols}, start:{row,col}, target:{row,col}, allowed_directions}` ans=**最少步数** 2 | 🔴 答案轴不同（编码 vs 步数——步数多解、我方标量判分不认）；row∈1..4 撞 0 起值域（row=4 在 4×4 越界）；dr/dc 有零（纯直线）触守卫 | 重导：改终点格编码 |
| **ruler** | `{max:20, object:[3,8]}` ans=间隔 5 | `{scale:{min,max,step}, objects:[{id,start,end,unit}], unit:"cm"}` ans=5 | 轴同（间隔） | ✅ 垫片可救（7/8；1 题 left=0 触"零起靶退化"守卫——**该题本身设计错误**，正好证明守卫价值） |
| **clock** | `{start:[3,0], target:[6,0]}` ans=**总分钟 360** | `{start:{hour,minute}, target:{label:"3:30"}, minute_step:5}` ans=**"3:30" 文本** | 🔴 答案轴不同（标量分钟 vs HH:MM 文本——_judge float 失败退字符串比对，题包 value 是 str 勉强可判，但 R17 评估器按 (h,m) 组合判 hand_swap，minute_step=5 的任意分针位（如 :15）我方两档 UI 做不出 | 重导：整/半点 + 分钟数答案 |
| **money-board** | `{price:35, denominations:[1,5,10,50]}` ans=**角** 35 | `{denominations:[1,5,10,20,50,100], target:{total}|{price,paid}}` ans=元数 | 🔴 单位轴不同（角 vs 元——100 元档、20 元非我方币制）；**change 题答案与 config 自相矛盾**（paid=10,price=10,ans=64——交付方数据错误实锤） | 重导 + 交付方修数据 |
| **pattern-board** | `{visible:[1,2,1,2], blanks:2, palette:[1,2]}` ans=token 拼接 12 | `{visible:[2,4,6,null], hidden_index, rule_candidates:[" +1","+2"…]}` ans=下一数 8 | 🔴 R19=ABAB 颜色周期延续（token≤5）；题包=**等差数列+规则选择**（数字>5 破坏拼接无歧义守卫，rule_candidates 需选规则字符串）——是"数型规律"不是"Repeat 型规律" | 重导或换挂 number-input |
| **ten-frame** | `{target_count:13, max_frames:2}` ans=13 | `{frame_count, capacity, filled:6, target:10}` ans=4（补几个成十） | 🟡 make_ten 子玩法我方 parser 只认 quantity_structure；轴可映射（filled+answer=target）但缺独立 mode | 半可救 |

### 2.2 基座链（4 个，无独立 parser、asNumber 宽松——不硬拒但语义要对）

| renderer | 我方金样例 | 题包 | 判定 |
|---|---|---|---|
| number-line | `{scale:{min,max,tick_step}, start_marker:{marker_id,value}}` ans=落点值 | 同形 +jump_size/count/direction | ✅ 形状基本兼容 |
| object-counter | `{groups:[{group_id,label,symbol,count,locked}], expected:[…]}` ans=总数 | `{objects:{symbol,count}, target, countable}` | 🟡 单组简化形，基座能吃但 R01 的分组 expected 原料缺失。**【FE-1438 勘正】实灌批用 groups 形+`expected:[5,3]` 数字数组（与 groups 顺序平行）——组件原只认 {group_id,min_count} 对象形已修双形态兼容；今后 expected 两种形态均合法** |
| number-input | `{min,max,integer_only}` | `{input_type,min,max,placeholder}` | ✅ |
| column-arithmetic | `{operands:[47,28], places, operand_layout:"fixed"}` ans=结果 | 同形 +operator:"addition/subtraction" | ✅（mode 由我方 addition/subtraction 区分，题包已对齐） |

## 3. 给交付方的重导指令（按渲染器归组）

**必改（答案轴/交互语义错位，共 7 类 ~62 题）**：
1. direction-grid：answer 改**终点格编码**（0 起，行主序），grid 坐标 0 起且 dr、dc 均非零；**【R15 守卫补文】反走靶必须可达**——(2·sr−tr, 2·sc−tc) 须落在盘内（方向反转分诊靶的可达性守卫，违反=parser 拒）；建议 5×5 盘（金样例 start(2,2)→target(3,4)，反走靶 (1,0)，answer=19）
2. shape-canvas：answer 改**面积数值**，target 限定 rectangle（house 等复合形删）【勘误：原写 rectangle/triangle 系笔误——R13 parser 仅接受 `target_shape:"rectangle"`，三角形评估不在本 Gate 范围】
3. sorting-board：改**数值升序排列**玩法（answer=数字拼接），分类归组题移到别的渲染器
4. pattern-board：改**ABAB 颜色周期**（token 1..5，answer=空格拼接数）；等差数列题改挂 number-input
5. clock：目标限**整时/半点**，answer=总分钟数（6:00→360）；**【R17 形态补文】config.start/target 必须为数组 [h,m]**（parser readTime 拒 {hour,minute} 对象形态）；**【R17 守卫补文·FE-1432h】swap 靶自环退化守卫**——target 的分针读数换算成时针位 `swapOf(target)` 若与 target 自身重合（6:30、12:00 类）parser 拒（hand_swap 分诊不存在）；合规例：3:00→4:30（swap=(6,30)≠target ✓）
6. money-board：单位统一**角**，币制 [1,5,10,50]；**【R18 守卫补文】price∈[5,200] 且 price%5==0 且 price%10!=0**（角位非零 5 倍数，保混淆靶互斥；整十/非 5 倍数 parser 拒）；change 题自查 paid−price=answer（现有 3 题自相矛盾）；**【边界声明】R18 实现为凑付玩法（拿币凑 price），无"付钱找零"交互——找零场景题必须改造成凑付题或换挂 number-input**
7. shape-gallery / estimation-canvas / place-value / grouping-board：按 §2 各行的"重导"栏口径；**【R09 值域补文】grouping items∈[2,20]**；**【R04 形态补文】formula-board tokens 用 `{t,v}` 形态（t∈num|op|eq|slot），slot 需 `accept:"number"|"operator"` 且 id 全题唯一；op 值域**仅 `+`/`-`**（R10 evaluator operator 分诊基于加减翻转语义，`*` `/` parser 拒——乘除式换挂 column-arithmetic 或 number-input）**

**格式统一（全 155 题）**：
- `content.answer` 直接给标量（去掉 `{type,value}` 包装）
- 补 `hint_ladder`（4 级，末级不泄答案）、`goal`、`evidence_targets`
- `error_models[].pattern` **逐字使用我方词表**（见各底表 §1 表，如 direction_reversed / hand_swap / denomination_confusion / from_zero_reading / phase_shift / rule_ignored…）
- context_family 保持现状（✅ 全部在受控词表内，唯二亮点之一）

**唯二可直接沿用**：number-line、column-arithmetic、number-input、bar-model（改名）——约 45 题（29%）。

## 3.5 交付方数据自身矛盾（18 题，与契约无关的内伤，必须修）

机器审计（一致性校验独立于我方 parser）实证：

| 渲染器 | 题 | 矛盾 |
|---|---|---|
| direction-grid | P0-113/114/115/118/119/120（6 题） | 坐标 **1 起**（row/col=4 在 4×4 盘越界）——我方 0 起值域；且这 6 条位移 dr 或 dc=0（纯直线，无转向教学点） |
| money-board | P0-141/142/143/144（4 题） | change 类 **paid−price=0 但 answer=3/7/64/11**——config.target 把 price 和 paid 填了同一个数，答案对不上自己题面 |
| pattern-board | P0-146/147/148/150/151/152/155（7 题） | 等差数列答案 11~40 **多位数**——若沿用"拼接"类标量口径破坏无歧义前提（本质是答案轴选择问题，见 §2） |
| clock | P0-132（1 题） | start=**2:15**——任意分针位，我方两档 UI（整点/半点）+ parser 守卫（m∈{0,30}）直接拒 |

> 这 17 题证明：**逐题机器一致性校验必须内置在交付流水线里**（题包自带 schema 校验查不出"答案与 config 矛盾"这类语义伤）。重导验收时我方将执行：JSON Schema（题包已有）→ 一致性审计（本表 §3.5 规则）→ config×parser 审计（audit-155-config.mjs）→ 抽样 pin 实灌四连。


## 4. 登记物清单

- `apps/child-web/scripts/audit-155-config.mjs`：config×parser 审计器（保留作交付验收门禁，每批题入库前先跑）
- `apps/learning-api/scripts/convert_trial155.py`：临时垫片转换器——**降级为审计分析工具**，不作入库通道（语义缺口硬拒 22 题就是证据）
- 原始包未存档（500KB 试灌性质；判定基线=本表+审计脚本可复现）——正式版入库时再存 docs
