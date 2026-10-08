# V1.4 Question Bank Production Contract v1.0（抽取文本）

V1.4 Question Bank Production Contract
v1.0
题库生产、交付、入库与验收契约
项目
内容
版本
v1.0
适用版本
V1.4
适用对象
题库生产方 / 内容交付方 / 前端 Renderer / Learning API / QA / 数据入库
状态
Production Contract
基准来源
《V1.4 Renderer Config 契约对照表（trial155 实灌审计产出，2026-10-08）》
核心原则：TaskUISchema JSON Schema 校验通过，不等于题目能够进入 V1.4 生产链。题目必须同时满足 Renderer Config、Answer Semantics、Evaluator、Evidence、Diagnosis 与数据一致性契约。
1. 契约目的
本契约用于将题库生产从“结构可解析”提升为“可实际进入 V1.4 前端 Renderer + Learning API 判分链”。契约以 19 个已闭 Vertical Gate 的实际 config 金样例与 parser 守卫为基准，约束题干、答案、Renderer、交互语义、评估器、诊断和数据一致性。
正式扩产前，必须先完成契约对齐；不得以 trial155 的字段转换结果直接扩产至 3,108。
字段名错位可以通过机器转换处理；答案语义轴、交互玩法和评估器口径不一致时，必须重新生成题目。
任何题目若 config 与 answer 自身矛盾，即使 JSON Schema 通过，也不得入库。
2. 适用范围与生产边界
范围
契约要求
题目内容
必须是真实可判分题目，不得使用模板占位句。
答案
必须提供可由前端/后端实际判分的标量 answer。
Renderer
必须挂接到 V1.4 已闭 Gate 的实际 Renderer 语义，不得仅凭名称相似挂接。
Config
必须满足对应 Renderer 的真实 config 结构、mode、值域及 parser 守卫。
Evaluator
answer 语义必须与实际 evaluator 一致；不能依赖临时转换器改变数学/交互含义。
Diagnosis
error_models.pattern 必须使用前端实际 structure.error 词表中的值。
Evidence
必须提供 evidence_targets，使交互证据能够进入行为/诊断链。
一致性
题干、config、answer、hint、goal、evidence、error model 之间必须自洽。
3. 生产题目的最小契约
每一道生产题必须至少形成以下闭环：
Question Content：真实题干及必要的结构化内容。
Renderer Config：与目标 Renderer 的 Gate-final config 对齐。
Answer：直接给出 content.answer 标量，不使用 {type,value} 包装。
Evaluator：answer 的语义与实际 evaluator 完全一致。
Hint Ladder：4 级提示，最后一级不得直接泄露答案。
Goal：明确本题希望孩子完成的目标。
Evidence Targets：定义需要采集的交互证据。
Error Models：pattern 必须逐字使用前端 structure.error 词表。
Consistency：config 与 answer 必须可由机器验证，不能出现答案与题面/参数矛盾。
4. Answer Contract
规则
生产要求
禁止
数据类型
content.answer 为 int 或 str 等契约允许的标量
answer={type,value} 对象
语义
answer 表示对应 Renderer/evaluator 真正判分的目标量
为了适配题库原始设计而改变答案含义
唯一性
在实际 evaluator 下必须形成确定判分结果
多解却用单一标量强行判分
单位
与 Renderer Gate-final 单位一致
money-board 元/角混用
坐标
按 Renderer 约定的坐标体系编码
direction-grid 1-based 坐标
5. Global Contract
ID
契约
生产要求
G1
content.answer 标量
直接输出 int/str 标量；不得依赖 adapter 从对象中提取 value。
G2
Seed 硬依赖
必须提供 hint_ladder（4级）、goal、evidence_targets；error_models[].pattern 必须与前端 structure.error 逐字匹配。
G3
Mode 词表
mode 必须采用各 Gate 定稿值，不得自造 shortest_path、set_time、compose 等标签。
6. 19 Renderer Contract Matrix
Renderer
Gate-final 核心语义
处理
关键约束
bar-model
part_whole；known + answer_bar；未知量
可转
字段重命名后再过 parser
place-value
target + pool；答案=摆出的完整数
重导/换挂
不得将“某数位数字”挂为 place-value
formula-board
tokens + answer_slot；固定缺位结构
有限可转
construct 类结构不得依赖当前 evaluator
array-board
target_rows/target_cols；答案=总数
直接对齐
字段改名即可
grouping-board
等分建组；答案=每组数量
重导
不得使用“包含分/有几组”答案轴
estimation-canvas
连续滑条 + tolerance；答案=估算值
重导/换挂
不得用离散选项替代
shape-gallery
分类放置/计数目标类型
重导
不得改成角数等属性问答
shape-canvas
目标面积；答案=面积数值
重导
target 限 rectangle/triangle；删除复合 house
sorting-board
数值升序；答案=数字拼接
重导
分类归组题移出该 Renderer
direction-grid
终点格编码；0-based、行主序
重导
不得用最少步数作为答案
ruler
区间长度/间隔；答案=数值
基本可转
避免 left=0 触发退化守卫
clock
整点/半点；答案=总分钟
重导
不得使用任意 :15 等分钟位或 HH:MM 文本答案
money-board
单位=角；denominations=[1,5,10,50]
重导
change 必须满足 paid-price=answer
pattern-board
ABAB 颜色周期；token 1..5；答案=blank token 拼接
重导/换挂
等差数列移至 number-input
ten-frame
target_count/max_frames；答案=总数量
有限映射
make-ten 需明确独立 mode/契约
number-line
落点值；scale + start_marker
直接对齐
保持实际 config 语义
object-counter
groups + expected 结构；答案=总数
补结构
单组简化题可吃但缺 R01 分组证据
number-input
范围/整数约束；标量答案
直接对齐
保持 evaluator 可直接判分
column-arithmetic
operands + places + layout；答案=计算结果
直接对齐
addition/subtraction 按实际 mode
7. 重点 Renderer 重导规则
Renderer
重导要求
direction-grid
grid 坐标从 0 开始；answer 为终点格的 0-based 行主序编码；dr、dc 均不得为 0。
shape-canvas
answer 为目标面积数值；target 仅允许 rectangle/triangle；删除 house 等当前几何评估器无法判定的复合形。
sorting-board
改为数值升序排序，answer 为数字拼接；分类题不得继续挂 sorting-board。
pattern-board
使用 ABAB 颜色周期，token 1..5，answer 为缺失 token 拼接；等差数列转 number-input。
clock
仅使用整时/半点；answer 为总分钟数，例如 6:00→360。
money-board
统一以角为单位；denominations 固定为 [1,5,10,50]；找零题必须机器校验 paid-price=answer。
shape-gallery
采用分类/放置并计数目标类型的语义；不得将角数属性问答伪装成 gallery。
estimation-canvas
采用连续滑条估算+tolerance 语义；离散档位选择应换挂 number-input。
place-value
采用 target + pool 摆数语义；数位数字问答应换挂 number-input。
grouping-board
采用平均分/等分建组语义；答案为每组数量。
8. Hint / Goal / Evidence / Diagnosis Contract
每题必须同时具备以下四类生产元数据：
字段
契约
hint_ladder
4级提示；从轻到重；第4级不得直接泄露最终答案。
goal
描述本题学习/交互目标，不替代题干。
evidence_targets
明确需要从交互过程中采集的证据目标，用于后续 Behavior Evidence / Diagnosis。
error_models[].pattern
只能使用前端 structure.error 的实际词表，逐字匹配；不得使用自造 diagnosis tag。
9. context_family Contract
本次 trial155 审计中，context_family 已在受控词表范围内，因此正式生产应保持该受控口径。不得把题型、Renderer、错误类型等其他维度混入 context_family。
10. Data Consistency Gate
Schema 校验不能发现“答案与 config 自相矛盾”。因此生产流水线必须增加逐题一致性审计。至少覆盖：
数值关系：例如 money-board 的 paid - price = answer。
坐标值域：例如 direction-grid 的 row/col 必须符合 0-based grid 范围。
Renderer 值域：例如 clock minute 必须符合实际 UI/parser 的整点/半点约束。
答案轴：answer 的类型、单位、编码方式必须与 Renderer evaluator 一致。
交互路径：题目要求的玩法必须能由对应 Renderer 实际完成。
题目结构：config、answer、goal、hint、evidence、error model 不能互相冲突。
11. Mandatory Acceptance Pipeline
Gate
检查项
通过标准
Gate 1
JSON Schema
基础结构合法
Gate 2
Question Consistency Audit
题干/config/answer 内部一致
Gate 3
Config × Parser Audit
目标 Renderer 的真实 parser 守卫通过
Gate 4
5% Pin E2E
抽样题真实灌入前端/后端链路
Gate 5
Judge
实际 evaluator 可判分
Gate 6
Evidence
交互证据可采集
Gate 7
Diagnosis
error model 与实际 evidence/structure.error 可命中
Gate 8
qa_replay
回放与验收结果一致
12. Delivery Classification
类别
定义
处理
A — Direct Reuse
number-line、column-arithmetic、number-input、bar-model（字段重命名）等语义一致题目
允许在完成格式统一及全量门禁后进入后续交付
B — Contract Regeneration
答案轴、交互语义、Renderer 或 evaluator 不一致的题目
必须重新生成；不得依赖 converter 改变语义
C — Data Contradiction
题目自身 config/answer/坐标/值域矛盾
必须先修复数据，再进入 Renderer 审计
13. Converter Policy
apps/learning-api/scripts/convert_trial155.py 仅保留为审计分析工具，不得作为正式入库通道。原因是字段转换能够解决部分命名差异，但不能可靠解决答案语义轴、交互语义及 evaluator 不一致。
不得通过 converter 将“错误语义”伪装成“契约兼容”。
converter 的 semantic-gap reject 必须被视为需要重导的生产信号。
14. Trial155 与 3,108 扩产的关系
trial155 的定位是生产契约验证样本，而不是最终题库。当前审计结果显示：原始 122 个专件覆盖题中仅 8 个直接通过；临时转换后仍存在 41 个 FAIL。因此不得将 trial155 或其转换结果直接作为生产 seed。
在契约完全对齐前，不应继续以“扩大数量”为主要工作目标。正确顺序是：
冻结并执行本 Production Contract。
按 Renderer 语义重导不兼容题目。
完成逐题一致性审计。
重新执行 Config × Parser Audit。
通过 5% Pin E2E、Judge、Evidence、Diagnosis、qa_replay。
完成上述闭环后，再进入更大规模题库生产。
15. 生产禁止项
禁止使用模板占位 prompt 作为生产题干。
禁止没有 answer 的题目进入 seed。
禁止使用 {type,value} 作为正式 content.answer 结构。
禁止使用自造 mode 替代 Gate-final mode。
禁止使用自由文本 diagnosis tag 替代 structure.error 词表。
禁止以字段转换掩盖答案语义轴不一致。
禁止将分类、属性问答、等差数列等玩法挂到语义不匹配的 Renderer。
禁止跳过逐题一致性审计，仅凭 JSON Schema 判定可入库。
禁止把 convert_trial155.py 作为正式 ingestion path。
16. Release Definition of Done
项目
DoD
Content
每题均为真实题干，answer 完整，可判分
Renderer
目标 Renderer 与 Gate-final config 语义一致
Config
config 通过对应 parser 守卫
Answer
scalar + 正确单位/编码/答案轴
Metadata
hint_ladder 4级、goal、evidence_targets 完整
Diagnosis
error_models.pattern 与实际 structure.error 词表逐字一致
Consistency
题目自身数据关系全部通过
E2E
5% pin sample 完成真实灌入与判分链验证
QA
Judge / Evidence / Diagnosis / qa_replay 全部通过
Ingestion
仅允许正式生产链进入 DB，不允许 trial converter 作为入口
17. Audit Baseline / Source
本契约直接基于用户提供的《V1.4 Renderer Config 契约对照表（trial155 实灌审计产出，2026-10-08）》整理。该审计明确指出：TaskUISchema JSON Schema 通过不等于兼容；主要问题集中在答案语义轴、交互语义与 evaluator 口径；并给出了 19 个 Renderer 的逐项对照、重导规则、数据一致性问题及验收顺序。
