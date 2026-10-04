# V1.4 18 Renderers Document Pack —— 消费索引与落地裁决

> 交付来源：《V1.4_18_Renderers_Document_Pack.zip》（2026-10-04），1 份 Master + 18 份单 Renderer Spec。
> 原文抽取件在本目录（`.txt`，docx 逐段无损抽取）。本文件是消费结论，与原文冲突时以原文为准并登记差异。

## 1. 一致性核验（已完成）

```
Master §1 批次清单（18）== RENDERER_PROTOCOL_IDS(23) − IMPLEMENTED_RENDERER_IDS(5)
→ 程序交叉核对：全在枚举内 True、差集为空、数量吻合。与 FE-1403 冻结协议零漂移。
```

5 个已实现不在本批：number-input / object-counter / bar-model / number-line / column-arithmetic。

## 2. 交付性质判定

**契约骨架，非完整 Schema**。每份 Spec 给到：组件定位、Workspace/Response 合同（通用层）、建议事件模型、Evaluator/Diagnosis 边界、E2E 场景 E01~E09、最小 Fixture、DoD。
**未给**：mode 字段级 JSON Schema、workspace.data 具体结构、Evaluator 正反例——对应 `docs/frontend/29 §5-1`「随各 Renderer 交付」待冻结项，实现时由我方补出并过 `packages/contracts` 三层校验。

## 3. 批量合同要点（Master §2/§4，逐条与我方现状核对）

| 条款 | 我方现状 |
|---|---|
| V2 Schema、禁止静默降级 | ✅ TaskRenderer planned 阻断 + 后端 `_v2_assignable` |
| 共享 Runtime（workspace/history/events/undo/reset） | ✅ rendererRuntime.ts |
| **FAIL 必须可提交** | ✅ P0-01（#36）已修，条款即该教训的模板化 |
| Renderer 不管 mastery/Diagnosis 权威 | ✅ 架构不变量（additionalProperties:false 强制） |
| Response 统一走 v2AttemptAdapter | ✅ |
| 真实页面 E2E 不以纯函数替代 | ⚠️ 待浏览器 harness（B5_E2E_VERTICAL_GATE.md §4） |

## 4. 命名冲突登记（落地必须遵守）

Master §4 统一 Gate 编号 **E1~E9**（验证项编号）与 E 域组件 Gate（direction-grid 的 Vertical Gate 恰为 "E1"）**撞号**。本仓库文档口径：
- 验证项一律写 **E2E-Gate-1..9**（或直接引用 §4 表）；
- 组件 Vertical Gate 一律写 **A1/A2/E4/F6** 等域+编号全称。

## 5. 18 组件一览（核心交互 / 最小 Fixture）

| Protocol ID | Gate | 核心交互 | 最小 Fixture | 事件（建议） |
|---|---|---|---|---|
| choice-grid | 跨域通用 | 单选/多选确认 | 3 选项 1 正确 | OPTION_SELECTED/DESELECTED |
| place-value | A1 | 位值拆分 | 2305→2千3百0十5个 | DIGIT_MOVED/PLACE_ASSIGNED |
| ten-frame | A2 | 计数补十 | 7 补成 10 | —（见原文） |
| array-board | A3 | 行列阵列乘法 | 3×4 转乘法 | ROW/COLUMN_CHANGED |
| grouping-board | A4 | 等量分组 | 12 个每组 3 | ITEM_MOVED/GROUP_CREATED |
| formula-board | A6 | 算式构造 | 8+7=15 构造 15-7=8 | TOKEN_ADDED/MOVED |
| estimation-canvas | A7 | 估算合理性 | 198+203≈400 | REFERENCE/ESTIMATE_SET |
| shape-gallery | D1 | 图形属性识别 | 正方形/长方形/三角形 | —（见原文） |
| shape-canvas | D5 | 作图移动旋转组合 | 创建矩形并移动/旋转 | —（见原文） |
| sorting-board | F1 | 分类规则拖拽 | 8 对象按奇偶 | —（见原文） |
| direction-grid | E1 | 方向位置路径 | 5×5 从 A 到 B | CELL_SELECTED/PATH_EXTENDED |
| ruler | E4 | 测量刻度单位 | 测 6cm 线段 | —（见原文） |
| clock | E2 | 读时拨针 | 3:30→4:00 | HAND_MOVED/TIME_SET |
| timeline | E3 | 顺序时间间隔 | 4 事件排序 | —（见原文） |
| money-board | E5 | 金额组合找零 | 10/5/1 元付 18 | MONEY_ADDED/REMOVED |
| data-table | F6 | 数据录入读取 | 4 组读最大/最小 | CELL_EDITED/ROW_ADDED |
| pictograph | F5 | 图例数量读取 | 1 图标=2 读 4 类 | DATA_POINT_MOVED/SCALE_CHANGED |
| pattern-board | F4 | 规律补全 | 2,4,6,8,__,__ | BLANK_FILLED/VERIFY |

## 6. 落地裁决（本版块边界）

1. **本包只登记，不触发批量开发**——§13 同口径：先停止扩数量，B5/A5 的浏览器 E2E harness（P0-03/04/06）仍是 FE-1403 关闭与批量开工的前置。
2. 实施批次采纳 Master §3（A→F→D→E + choice-grid 穿插），但**每个组件的交付模板 = B5 已趟通的五件套**：纯函数层（含 mode 字段级 Schema + 正反例样例，进 `packages/contracts`）→ 组件（双皮肤）→ V2Renderer 分流 → seed/mock 链题 → check 脚本 + implemented 前后端同步翻转。
3. shape-canvas（D5）复杂度最高，允许最后交付、不阻塞其余（Gate 独立）。
4. **事件命名口径（已核实）**：本批 Spec 事件用 `UPPER_SNAKE`（DIGIT_MOVED / OPTION_SELECTED…），与我们 **MathResponse V2 Schema** 的 `event_type: ^[A-Z][A-Z0-9_]*$`（packages/contracts）一致——V2 链采用 Spec 建议事件名即可。注意与 **V1 前端 InteractionEventType 小写联合**（drag/align/…）是两条轨道：V2 renderer 事件走大写（Schema 强制），不要混入小写枚举。

## 7. 原文清单

`V1.4_18_Renderers_Master_Spec.txt` + 18 份 `V1.4_<id>_Renderer_Spec.txt`（本目录）。
