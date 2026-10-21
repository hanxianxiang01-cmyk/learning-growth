# FE-1467｜Q05 / Q03 工作清单重建（以当前 Published RVID 为口径）

日期：2026-10-21　｜　前置：Q07 CLOSED（限定范围，PR#123 后）

## 一、为什么重建

终审 §五：

> 下一批应使用当前 Published RVID 重新整理 Q05和Q03工作清单。**211／212是此前基线中的待办数量，不应未经复扫就继续作为当前精确数量；历史报告保持不变，新基线另行归档。**

因此本轮不沿用任何历史数字，全部从当前库存重算。

## 二、口径

| 项 | 取值 |
|---|---|
| 对象口径 | `resource_version.review_status = 'published'` → **225 条** |
| 判定来源 | `scripts/iqc/scan.py --audit-only published`（复用既有规则，**未新造规则**） |
| 规则版本 | `2.2/iqc/1` |
| 库存快照 | `79f90852d2800b8e…`（全 304 条，其中 published 225 / superseded 51 / qa_retired 27 / qa_staged 1） |
| 只读 | 全程 SELECT，0 写入 |

> **两个口径不得混用**：published 是治理口径（可下发），all_versions 是审计追溯口径。本文所有"当前数量"均指 published。

## 三、重建中发现并修复一个口径缺陷

**这是本轮最重要的发现，必须先讲。**

首次重建跑出 `published=225` 但 findings 覆盖 **239 个 RVID**、共 467 条，且 `Q03-UNVERIFIED = 225` 恰好等于 published 总数——数字看起来都"正常"，只有把分子分母对账才会发现矛盾。

根因在 `scripts/iqc/scan.py`：

1. Q01 版本链校验需要 mapping 两端版本，于是把 `version_migration_map.csv` 端点的历史版本（当前全为 superseded，共 14 条）**补载进 `items` 字典**；
2. 随后的「逐题规则」循环遍历的是**整个 `items`**；
3. 于是 published 口径的 Q03/Q05/Q06 findings 混进了 14 条非 published 版本。

修复：在 mapping 扩展**之前**冻结逐题规则作用域 `target_ids`，逐题循环只走该快照；coverage 的 `audited_published` 同按冻结集合计算，并新增 `audited_scope` / `mapping_side_loaded` 两个显式字段。

修复后：

| 指标 | 修复前 | 修复后 |
|---|---|---|
| audited_published | 225 | **225** |
| audited_scope | （无此字段） | **225** |
| mapping_side_loaded | （无此字段） | **14** |
| findings_total | 467 | **440** |
| distinct RVID | 239 | **225** |
| Q03-UNVERIFIED | 225 | **212** |
| 恒等式 | 不成立 | **212 + 13 = 225 = published** ✓ |

**回归保护**：新增 `scripts/iqc/test_scan_scope.py`（S1a–S3，含变异对照），已挂进 `pr_gate.py` 第 5 项，PR-IQC-GATE 硬阻断。`audit-only all` 口径不受影响（304 条、`mapping_side_loaded=0`），说明修复精确作用于 published 口径。

> 历史基线 `findings_fe1460_225.jsonl` 同样带此缺陷（239 个 RVID / 470 条，`audited_published` 却写 225）。按 §五"历史报告保持不变"，该文件**未改动**，差异在第四节显式说明。

## 四、与历史 225 基线的差异（已逐项归因）

| 项 | 旧 | 新 |
|---|---|---|
| distinct RVID | 239 | 225 |
| 交集 / 仅旧 / 仅新 | — | 188 / **51** / **37** |
| Q05-HOMOGENEOUS | 224 | **209** |
| Q03-UNVERIFIED | 225 | **212** |
| Q03-OK | 14 | 13 |
| Q06-STEM-LEAK | 7 | 6 |

差异**完全可由 Q07 治理事实解释**，经 DB 核对：

- **仅旧 51 条**：全部为当前 `review_status='superseded'`，即被替代的旧版本，本就该退出 published 口径；
- **仅新 37 条**：全部为当前 `review_status='published'`，即 Q07 的 37 项资源替代版本，本轮首次进入口径。

51 = 当前 superseded 总数，37 = Q07 替代资源数，两个方向都对齐。

> ⚠ **巧合警示**：Q03-UNVERIFIED 旧 225 / 新 212，与历史 211/212 数值接近，但**集合不同**（交集仅 175，旧集合含 50 条已 superseded 版本）。不可据此认为"缺口没变"。

## 五、当前基线与工作清单

**本次基线（published 225 条）：**

| 规则 | 数量 | 对应工作 |
|---|---|---|
| Q05-HOMOGENEOUS | **209** | 错误模型 `code == pattern` 同质占位，需逐题重写错误模型 |
| Q03-UNVERIFIED | **212** | 无独立推导模板，无法用独立实现核验答案 |
| Q03-OK | 13 | 已可独立核验且答案一致（PASS） |
| Q06-STEM-LEAK | 6 | 题面披露语境含答案，需教学复核 |
| Q03-ANSWER_MISMATCH | **0** | P0 阻断项为 0 |
| 合计 findings | 440 | — |

**能力分布：**

| 能力 | Q05 | Q03 |
|---|---|---|
| app_rel | 63 | 55 |
| app_cond | 45 | 47 |
| app_model | 32 | 36 |
| app_strat | 26 | 30 |
| app_rd | 21 | 23 |
| app_check | 15 | 13 |
| app_transfer | 7 | 8 |
| **合计** | **209** | **212** |

**211 / 212 的正式降级：**

| 旧数字 | 状态 | 原值 | 当前 | 说明 |
|---|---|---|---|---|
| Q05 待办 211 | `HISTORICAL_BASELINE_ONLY` | 211 | **209** | 旧基线基于 published=443 的另一集合，不可直接比较 |
| Q03 待办 212 | `HISTORICAL_BASELINE_ONLY` | 212 | **212** | 数值巧合但集合不同，见第四节警示 |

## 六、交付物

| 文件 | 内容 |
|---|---|
| `scripts/iqc/runs/FE1467_q05_q03_baseline.json` | 新基线全量：口径声明、缺陷修复记录、差异归因、两份工作清单（逐 RVID + 标题 + 能力 + renderer + 证据） |
| `scripts/iqc/rt1464/rebuild_q05_q03_baseline.py` | 重建脚本（复用 inventory + scan，只读） |
| `scripts/iqc/scan.py` | 口径缺陷修复（冻结逐题规则作用域） |
| `scripts/iqc/test_scan_scope.py` | 口径回归测试（S1a–S3 + 变异对照） |
| `scripts/iqc/pr_gate.py` | 门禁新增第 5 项 |

## 七、下一批工作建议

1. **Q03 优先**（212 条）：它决定"答案是否可信"，是可自动化程度最高的一条线；`Q03-ANSWER_MISMATCH=0` 说明当前无已知错答案，缺口是"无法独立验证"而非"验证失败"。
2. **Q05 次之**（209 条）：需教研介入重写错误模型，无法纯工程闭合。
3. 两清单**高度重叠**，建议按 RVID 合并成一张表，一题同时修两件事，避免两轮重复返工。

**两清单的集合关系（已核对）：**

| 项 | 数量 | 说明 |
|---|---|---|
| Q05 清单 | 209 | — |
| Q03 清单 | 212 | — |
| **交集** | **197** | 既有同质错误模型、又无独立核验——优先处理 |
| 仅 Q05 | 12 | 只需重写错误模型 |
| 仅 Q03 | 15 | 只需补独立核验模板 |
| **并集** | **224** | 合并去重后的总工作量 |
| 不在任一清单 | 1 | `5d41bfd4…`，仅命中 Q03-OK（已可独立核验且答案一致）——无待办 |

> 恒等式核对：`Q03-UNVERIFIED(212) + Q03-OK(13) = 225 = published`，每条 published 恰有一条 Q03 结论；未进入 Q05/Q03 待办清单的只有那 1 条 Q03-OK。
>
> 合并成一张表后，实际待办是 **224 条**，不是 209 + 212 = 421 条。这一点直接影响排期，务必按并集规划。