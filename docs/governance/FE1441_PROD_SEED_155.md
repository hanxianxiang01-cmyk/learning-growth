# FE-1441：Trial-155 正式入库执行记录（FE-1439 ⑤ 收官）

- 执行：2026-10-10 14:55~15:15；放行条件=映射 APPROVED（#83）+ Gate 8 8/8（#83④）+ M30 内容阻断清零（#85）
- 用户确认："跑5"（14:53）——生产数据动作授权

## 执行明细

1. **入库器** `apps/learning-api/scripts/prod_seed_155.py`：题源=/tmp/final2_155（FE-1440a 终态）；title=`[T155] <question_id>` 幂等；ability_id **一律以 docs/39 final_app_id 覆盖（25 条改判生效）**；`is_transfer→transfer_distance=1`（喂 #7 证据链）；Resource+rv 双 published+published_at
2. **结果**：新增 155 / 0 跳过；qa_staged 25 条 → `qa_retired`（通道关闭：catalog/pin 双不可见；历史 task/evidence 保留=QA_DATA_HYGIENE 软删纪律）
3. **RDS 终态**：published 225（金题 20+T155 155+…）；catalog=**175**

## 入库当场抓出的真缺陷（已修，教训级）

**catalog 排序不稳定 → 金题组首位被交付题顶掉**。原 order_by(ability_id, difficulty) 无二级键：T155 题 ability 即金题同源节点（映射批准后同值）、difficulty 常更低——入库后**按 E2E 检索键实测金题组组内混排**，`fetchPinnedTasks` catalogIndex=0 命中交付题→pin 断言"renderer/mode 不符"→19 个 spec 面临全崩。
- 修①：order_by 加 created_at+rvid 终序（不足——同组键仍撞）
- 修②（定版）：**`title NOT LIKE '[T155]%' DESC` 金题优先首要键** + 终序；回归锁 `test_catalog_gold_first_ordering`（源码 inspect 级）
- E2E 口径复验：裸 renderer key + 金题 mode key **首位被顶=无 ✓**
- 教训入册：**生产内容扩容会改变既有工具的检索空间**——QA 工具依赖"第 0 个=我认识的题"的隐式约定，必须显式化为排序约束

## 回归矩阵（全绿）

| 层 | 结果 |
|---|---|
| Gate 8 qa_replay（transfer 反查同步加 published 过滤+created_at 确定序） | **8/8** |
| API 全量实灌（qa_sample_e2e 切生产端点，从 19 样本扩**全量 155**四段链） | **155/155** |
| 后端 | **106 passed**（+1 排序锁） |
| 真实 child …0001 抽验 | 选题正常（app_cond，生产池含 T155） |
| UI 全量 E2E | 本 PR 流水线跑（qa-sample-batch rvid 已重指 [T155] 生产资源） |

## 状态

**V1.4 题库线闭环**：交付→四轮整改→8-Gate→映射批复→M30 定向修复→正式 published。Trial-155 155 题对生产可见，真实孩子开始按 fit_band 正常下发。

后续（非 V1.4 范围）：3,108 扩产批按 CONTRACT FROZEN v2.0 重导（映射不自动继承，M42 逐题核 is_transfer）；qa_staged 通道保留为下批验收工具（qa_retired 25 条为历史痕迹）。
