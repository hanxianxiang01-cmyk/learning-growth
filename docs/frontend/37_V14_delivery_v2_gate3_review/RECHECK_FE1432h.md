# FE-1432h：增量整改包复检（第二轮 Gate 1~3）

- 复检对象：`FE1432g_37Q_65Diagnosis_Delta`（37 题整改+65 处诊断词增量）+ `FE1432g_Reconciled155_ReviewOnly`（合并复审包）
- 复检时间：2026-10-09 20:19 起
- 结论：**Gate 1 全过 / Gate 2 全过（经我方裁决合并 clock 数组兼容补丁后三批 0 违规）/ Gate 3 PASS 152 专件+基座 / FAIL 残留 3 题**——其中 3 题全部含我方守卫未成文（op 值域、swap 自环），随本 PR 补进 CONTRACT §7；无退回项属交付方"看得见却不做"情形。

## 1. 增量合并复现（通过）

`tools/apply_incremental.py` 对上一版 155 包复跑：SHA-256 前置校验 + 37 替换 + 65 诊断（14 重合）→ 产物与分发 `reconciled_155` 三批 JSON **逐字段一致**。增量不增号、ID/A/B/C 归属保留——符合任务单纪律。

## 2. Gate 2 兼容补丁裁决：**接受合并**（我方工具缺陷，非迁就）

R17 parser `readTime` canonical 形态=数组 `[h,m]`（金样例即数组、§7 勘误已点名数组形态），但 Gate 2 v2 的 `minute_value()` 只兼容了旧 trial155 的 dict/HH:MM 形态、**唯独不认 canonical 数组**——Gate 2 与 Gate 3 权威口径冲突，属我方工具缺陷。交付方提案（三行、隔离副本、明示"未经批准不视为权威更新"）处置纪律满分。

我方合并时按自家口径加强：数组分支同时校验时数值域 `h∈[1,12]`（提案只取分针）。fixtures 加锚点：gold+G-6（数组正例 3:00→4:30）、negative+T-6（h=0 数组负例）→ 回归基线更新为 **gold 0 违规 / negative 恰 4 条**。trial155 旧包口径不变（216 条）。合并包三批复跑 **0/0/0**。

## 3. Gate 3 权威复跑：37 题修复收敛至残留 3 题

| 题 | 渲染器 | 拒收守卫 | 归责 |
|---|---|---|---|
| V14-P0-077 | formula-board | `op:"*"`——R10 parser op 值域 **仅 `{"+","-"}`**（operator 分诊基于加减翻转语义，乘除不支持） | 我方未成文（§7 补文只写了 tokens 形态，没写 op 值域） |
| V14-P0-078 | formula-board | 同上 `op:"/"` | 同上 |
| V14-P0-133 | clock | `6:00→6:30`——`swapOf(6,30)=(6,30)` **靶自环退化**，R17 parser 拒（互换靶与 target 自身重合则 hand_swap 分诊不存在） | 我方未成文（守卫在 R17 底表 §守卫，§7 没搬） |

修复建议（已实证过 parser）：
- 077/078：`6×4=□`、`24÷6=□` 改加减式（如 `6+4=□`、`24−6=□`），或换挂 number-input/column-arithmetic（乘除语义真实所在）
- 133：改 `3:00→4:30`（answer=270，swap=(6,30) 合法且≠target，我方实测过 parser）

## 4. 数字口径

- Gate 3：专件 PASS 119（A17+B78+C24）/ FAIL 3 / 基座链无 parser 33（其中 object-counter 出现在 B/C——基座链宽松 config，进 Gate 4~7 实灌验语义）
- 诊断词：65 处越表→复扫描 0（65 处改选有效）

## 5. 处置与下一步

1. 残留 3 题随下轮微增量重交（预计 10 分钟工作量，改法已给死）
2. **不阻塞 Gate 4~7 启动**：建议对已过 152 题抽 5%（≥8 题、覆盖全部出现 renderer 含 direction/clock/money/pattern/shape-canvas）先行 pin E2E——微增量到齐后补齐覆盖再进 Gate 8
3. 交付方"来源局限"申报（勘误 CONTRACT 未在压缩内、只有 README §3）属实——本 PR 后 CONTRACT.md §7 已含全部成文守卫，下轮以仓库版为准

## 6. 本轮正面记录

增量不重造整包、SHA 前置校验防错覆盖、兼容补丁"隔离副本+不宣称权威+请验收方裁决"三步走、来源局限如实申报——交付方工程纪律已连续两轮满分。**教训继续有效：FE-1434 契约 FROZEN 必须吸收 parser 守卫全集**（本轮又添两条：formula op 值域、clock swap 自环）。
