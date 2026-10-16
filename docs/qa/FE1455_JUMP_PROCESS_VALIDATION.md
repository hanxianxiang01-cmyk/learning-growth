# FE-1455 NumberLine 跳步过程校验（任务单）

**状态：批准立项（产品方 Q4 Rev.A 整改裁决 §二.3），本文档为范围冻结，实施前不再讨论方向。**
**动机：`8eb5de92`（从20出发，每次向右跳5，跳3次=35）——题面规定过程，系统只检查终点。
浏览器实证（2026-10-16，修复前取证 §A2）：孩子一步直跳 20→35（跳距15）提交 correct=true。
终点正确不能证明完成了"3 次 ×5 右跳"的过程 → 该题不得以终点判分冒充过程验证。**

**当前缓解**：`8eb5de92-d04b-…5fcd` 已转 `qa_staged`（生产池/目录/自动推荐不可见；
QA pin 通道保留取证；历史 1647 个 task 引用与 evidence 对应关系不受状态迁移影响）。
**在 FE-1455 实现并回归前，该资源版本不得转回 published。**

## 实施范围（五层，逐层验收）

| 层 | 要求 | 落点 |
|---|---|---|
| ① 题目配置 | `workspace.config` 增 `jump_constraint = {jump_size, direction, expected_jumps}`（V2 契约扩展，可选字段） | content seed / validate_ui_schema_v2 契约包 |
| ② Renderer | 记录**每一步**移动（现有 `jumps[]` 已含 from/to/jump_id——确认无损序列化即可） | `numberLineV2.ts` / `NumberLineV2.tsx`（已基本具备，补测试） |
| ③ Response | `serializeNumberLineV2` 完整轨迹进 `v2_workspaces[].data`（现状已含 jumps 明细——核对 Evidence targets） | `v2AttemptAdapter` |
| ④ 后端验证 | 提交判分：终点值一致 **且**（若配置声明 jump_constraint）逐跳核对步长/方向/次数；不符 → correct=false + 诊断观察 `rule_ignored`/`direction_reversed` 类分诊码 | `turn_service`/`_judge` 扩展或 V2 结构判分器 |
| ⑤ Mastery | 过程要求未满足 → 该 attempt 不生成对应过程能力的有效掌握证据（correct=false 已被证据链排除；确认 transfer/retention 语义不旁路） | `mastery._scorable` 回归测 |

## 兼容性红线（裁决明示）

- **旧题不强制**：未声明 `jump_constraint` 的数轴题（现有 8 道 jump_sequence + 其它）
  行为逐比特不变——终点判分即合格。校验只作用于**显式声明约束**的资源版本。
- 前端对无约束 config 不报错、有约束 config 才启用逐跳校验。
- V1 legacy 数轴（50 题中的 11 道）不在本项范围。

## 验收标准

1. `e2e/q4-reva-contract.spec.mjs` 哨兵断言翻转：`Q4_MODE=after` 下非法跳步（1 步 15）
   → correct=false；合法跳步（+5×3）→ correct=true。
2. 后端单测：约束声明/缺省两态、方向反/步长错/次数少 三类非法轨迹各锁一条。
3. 回归：现有数轴 E2E（r03 系）+ 全量后端测试 + 12 周成长状态机不受扰动。
4. 8eb5de92 修复合入后：新版本转 published 走 Q4 六列完整教学契约 PASS 通道。

## 建议拆排

- FE-1455a（可先行）：后端判分器扩展 + 单测（契约字段定义=本任务单①）。
- FE-1455b：Renderer/E2E 哨兵翻转 + 题内容补 `jump_constraint`（依赖 1455a）。
