# V1.4 `error_models[].pattern` 权威词表（交付方 80 题诊断词逐字对照底稿）

- 来源＝仓库 20 道 V2 金题 `resource_seed_v2.py` 实际 seed + 各渲染器 parser/evaluator 源码交叉验证（main=4ded4f4 后）
- 用途＝任务单 §2 判定手段、PC-v1 §9 词表纪律：交付方 v2 批 `error_models[].pattern` **必须逐字取自本表对应渲染器行**，自造词 = Gate 6 Diagnosis 永不命中
- 语义两类：**FAIL 错因**（判错题的观察标签）与 **PASS 留痕**（判对题的过程观察，如 detour/uses_extra/changed_once/misaligned）——留痕词只能出现在对应 PASS 留痕字段语境
- ⚠️ 部分词（modeling/calc/strategy/operator/relation/group_count/unequal_share/transpose/count/place_value_confusion 等）为金题 seed 既有**能力/动作标签**，非纯错因；交付方引用时保持原样即可，勿自行替换

| renderer | 允许 pattern 全集 |
|---|---|
| bar-model | modeling, relation, calc |
| number-line | strategy, calc |
| object-counter | modeling, calc |
| number-input | strategy, calc |
| column-arithmetic | calc, strategy |
| place-value | place_value_confusion, calc |
| ten-frame | modeling, calc |
| formula-board | operator, relation |
| array-board | transpose, count |
| grouping-board | group_count, unequal_share, calc |
| estimation-canvas | no_reference_use, too_high, too_low |
| shape-gallery | attribute_confusion, missed |
| shape-canvas | vertex_count, not_right_angle, wrong_size |
| sorting-board | dimension_confusion, reversed, disordered |
| direction-grid | direction_reversed, wrong_position, detour（留痕） |
| ruler | from_zero_reading, wrong_span, misaligned（留痕） |
| clock | hand_swap, wrong_time |
| money-board | denomination_confusion, underpaid, overpaid, uses_extra（留痕） |
| pattern-board | phase_shift, rule_ignored, wrong_sequence, changed_once（留痕） |
