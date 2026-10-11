# V1.4 生产选题策略（FE-1442 实装口径）

版本：`v1.4-fe1442`（写入 `strategy_policy.selection_policy`，回滚=还原 `_published_resource_for_ability` 旧排序，无 schema 依赖）。

## 规则（裁决 A 定版）

1. **两层决策**：能力/难度带/角色由上游（fit_band+evidence_role）决定，公平采样只在同带同角色内动。
2. **P0 未见优先** → 该 child 该能力从未下发过的合法题；**P1 低曝光** → 已见非近期，`count` 少者→`last_assigned` 久者胜；**P2 RECENT_FALLBACK** → 全部近期，仍按低曝光久未发轮转（不死循环、不跨带）。
3. **同层决胜=有界哈希**：`sha256(child|rv|salt)`，无全表 random（池≤200 应用层排序，EXPLAIN 零风险）。
4. **题目重复 ≠ 带空**：带内有题但全被本 session 排除 → `SESSION_POOL_EXHAUSTED`（精确 reason 透出，SEL-04）；**仅带内无任何 published** 才走兜底。
5. **BAND_FALLBACK 显式化**：兜底沿用既有"该能力最低难度"顺序（不引入新调度器），但记 `band_fallback=true + fallback_reason=TARGET_BAND_EMPTY + requested_band + selected_difficulty`。
6. **Mastery 真实计分**：`assigned_difficulty` 恒=真实资源难度（现状代码即如此，SEL-07④ 锁定）；D4 请求兜底发 D3 → 证据按 D3 入账。
7. **Pin/qa_replay 零触碰**：pin 分支不进公平采样（SEL-11 实证 policy 无 selection_policy 字段）。
8. **近期窗口** `RECENT_WINDOW=20`（模块常量，非 SQL 写死；按真实数据可调）。

## 历史数据源（零迁移）

`task_instance` 聚合 `(child_id, ability_id)` → `{resource_version_id: (count, last_assigned_at)}`，索引走 `idx_task_child` 既有。V1 时代历史天然在表（QA child app_rel=22k 条），口径=HISTORY_PARTIAL（E2E 测试流量计入下发覆盖，非"实际阅读"——任务单 §4.1 口径遵守）。

## 裁剪记录（裁决在案）

- request_id 服务端幂等：不做（前端防重入锁+事务；**不宣称跨设备并发安全**）
- advisory lock：不做，`_pick_fair` 单函数保留扩展点
- SCHEDULED_REPEAT 上游调度契约：不存在，SEL-08 NOT RUN
