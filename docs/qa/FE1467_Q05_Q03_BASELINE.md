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

差异**完全可由 Q07 治理事实解释**，经 DB 逐 RVID 核对（状态由 DB 实查，不做概括）：

| 集合 | 数量 | 实际状态分布（DB 实查） |
|---|---|---|
| 仅旧 | 51 | `superseded: 51` |
| 仅新 | 37 | `published: 37` |

51 = 当前 superseded 总数，37 = Q07 替代资源数，两个方向都对齐。

> ⚠ **不要把这个 51 与 Q03 那个 50 混为一谈**——它们来自不同比较对象，见第八节。

## 四之二、Q03 的两种集合比较（必须分开说）

复审 §二.3 指出：上一版一边说「旧集合 212」，一边说「旧集合含 50 条已退出版本」——这两件事不能同时成立，因为它们属于**不同的比较对象**。

现由脚本分别输出（`q03_set_comparisons`）：

| 比较 | 旧集合 | 新集合 | 交集 | 仅旧 | 仅新 |
|---|---:|---:|---:|---:|---:|
| **A** 旧工件全部 Q03（含 superseded 污染） | 225 | 212 | 175 | **50** | 37 |
| **B** 旧工件 Q03 剔除非 published | 175 | 212 | 175 | **0** | 37 |
| **C** FE1464 报告 `status.UNVERIFIED` | 212（**只有计数，无 RVID 集合**） | — | 无法比较 | — | — |

三条结论：

1. **A 的 225** 是「旧工件里 Q03 的全部 distinct RVID」，其中 50 条现在已 superseded——**这不是正式历史基线口径**，是受 `scan.py` 口径缺陷污染的集合。
2. **B 的 175** 才是「旧工件中当前仍为 published 的部分」，它与当前集合**完全包含关系**（仅旧=0）。也就是说：旧集合的已发布部分**没有被丢弃任何一条**，差异全部来自 **only_new=37**（Q07 替代资源首次进入口径）。
3. **C 的 212** 只有计数、没有 RVID 集合，**不能**与 A/B 的交集、only 数字并列引用。上一版的错误就是把 C 的计数当成 A 的集合来讲。

旧工件 Q03 的状态实测分布：`published: 175` / `superseded: 50`（合计 225）。

> 脚本输出 `q03_set_comparisons` 段，A/B/C 三组数字均由 `rebuild_q05_q03_baseline.py` 现场计算并落盘，可复算。

> ⚠ **三种不同的计数，不可混说**（2026-10-21 复审 §二.3 补正）：
>
> | 数字 | 是什么 | 不是什么 |
> |---|---|---|
> | 225 | 当前 published **题目（RVID）**数 | — |
> | 212 | 当前 Q03-UNVERIFIED 的**题目**数 | 不是"已确认错误"，是"尚未独立核验" |
> | 212 | 历史 `status.UNVERIFIED` 的 **Findings 条数** | **不是题目数** |
> | 440 | 本轮 **Findings 条数** | **不是题目数** |
>
> 后两个 212 数值相同纯属巧合，单位与集合都不同，详见第八节。

## 五、当前基线与工作清单

**本次基线（published 225 条）：**

| 规则 | 数量 | 对应工作 |
|---|---|---|
| Q05-HOMOGENEOUS | **209** | 错误模型 `code == pattern` 同质占位，需逐题重写错误模型 |
| Q03-UNVERIFIED | **212** | 无独立推导模板，无法用独立实现核验答案 |
| Q03-OK | 13 | 已可独立核验且答案一致（PASS） |
| Q06-STEM-LEAK | 6 | 题面披露语境含答案，需教学复核 |
| Q03-ANSWER_MISMATCH | **0** | P0 阻断项为 0 |
| 合计 findings | 440 | **Findings 条数，不是 440 道题** |

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
| Q05 待办 211 | `HISTORICAL_BASELINE_ONLY` | 211 | **209** | 旧值是 443 条 **findings** 上的状态分桶计数；当前值是 225 条 **published 题目**上的命中数。单位与集合都不同，不可直接比较 |
| Q03 待办 212 | `HISTORICAL_BASELINE_ONLY` | 212 | **212** | 数值巧合；旧值无 RVID 集合可查，见第八节 |

**211 / 212 的出处（可复算，非人工记忆）：**

两个数字并非独立计数器，而是同一份历史工件里 `status` 枚举的两个桶：

| 项 | 出处 |
|---|---|
| 工件 | `scripts/iqc/runs/FE1464_first_full_report.json` |
| 路径 | `fe1464_first_full_baseline.current_published_findings` |
| 计数对象 | **443 条 Findings**（字段名即 `current_published_findings`） |
| 211 | `status.REVISION_REQUIRED`（即 Q05 待办） |
| 212 | `status.UNVERIFIED`（即 Q03 待办） |

**恒等式：** `UNVERIFIED(212) + REVISION_REQUIRED(211) + PASS_RULES(13) + REVIEW_REQUIRED(7) = 443 = historical_published_findings(443)`。

> **这 443 是 Findings 条数，不是 443 道 published 题。** 旁证（同一工件）：`resources_discovered = 264`、`findings_total = 520`，而 `layering.review_status` 的 27 + 443 + 50 = 520 恰等于 `findings_total`——说明该三桶是按 review_status 把 **findings** 分桶，不是资源版本计数。
>
> **恒等式的效力边界**：它只证明 findings 状态分桶合计一致，**不证明**题目 RVID 去重覆盖正确，也**不证明**所有 `REVISION_REQUIRED` 都属于 Q05。排期清单必须由规则标识 + RVID 生成。

> 该恒等式现由 `rebuild_q05_q03_baseline.py` 的 `read_historical_provenance()` 在每次重建时读回工件并断言；同时对 `layering` 合计与 `findings_total` 的一致性做单位旁证。历史工件本身按 §五「历史报告保持不变」未改动，脚本只读不写。
>
> 同一函数由 `test_baseline_provenance.py`（P1–P9 + P7b 边界 + H 哈希冻结）在 CI 侧复验，已挂进 `pr_gate.py` 第 6 项。

## 六、交付物

| 文件 | 内容 |
|---|---|
| `scripts/iqc/runs/FE1467_q05_q03_baseline.json` | 新基线全量：口径声明、缺陷修复记录、211/212 出处与单位口径、`q03_set_comparisons` 三组比较、逐状态归因、两份工作清单（逐 RVID + 标题 + 能力 + renderer + 证据） |
| `scripts/iqc/rt1464/rebuild_q05_q03_baseline.py` | 重建脚本（复用 inventory + scan，只读） |
| `scripts/iqc/scan.py` | 口径缺陷修复（冻结逐题规则作用域） |
| `scripts/iqc/test_scan_scope.py` | 口径回归测试（S1a–S3 + 变异对照） |
| `scripts/iqc/rt1464/test_baseline_provenance.py` | 出处回归（P1–P9 + P7b 能力边界实测 + H 哈希冻结） |
| `scripts/iqc/test_static_callables.py` | 静态可调用性（C1–C4，含"未定义函数被调用"检出） |
| `scripts/iqc/pr_gate.py` | 门禁新增第 5、6、7 项（现共七项） |

## 七、下一批工作建议

1. **Q03 优先**（212 条，去重后与 Q05 合并为 224）：它决定"答案是否可信"，可自动化程度最高。
2. **Q05 同批处理**（209 条）：`code == pattern` 只是**候选信号**，真正要核验的是错误模型是否具有可解释、可观察、可区分的依据；不是"必须逐题重写 209 套文案"。
3. 两清单高度重叠，**按 RVID 合并成一张表**，一次取数、两个检查域分别出结论。

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

## 八、Q03-ANSWER_MISMATCH=0 的正确表述

这个 0 容易被读成"题库没有错答案"，**不成立**。可支持的表述只有：

> 当前已完成独立核验的适用范围内，未检出答案失配；其余 212 题尚未获得独立答案结论。

分母只有 13 条（Q03-OK），不是 225。

## 九、本轮补正清单（2026-10-21 复审）

| 项 | 问题性质 | 处置 |
|---|---|---|
| G7 `finally` 恢复错对象 | **真 bug**：`type(mut) is ExecMode`，`finally` 读到的是已被替换的属性，污染会扩散到后续用例 | 改为变异前保存 `original = ExecMode.allows_write` 再归还；新增 G7-S3/S3b 回归锁；变异验证确认检出 |
| G7 用"捕获异常"证明 | 证明力不足：异常也可能来自序列化/参数处理 | 改为注入 transport **计数**，三段式（只读=0 次 → 变异=1 次 → 恢复=0 次） |
| 只按 POST 控制 | **缺口**：`GET /sessions/{id}/result` 会执行结算 | 新增 `guarded_effect_get()` 受闸门约束；新增 G9/G10，并保留 G11 证明纯探测 GET 不误伤 |
| 两开关同时给 | 未定义行为 | `resolve_mode()` 显式拒绝，G8b 锁定 |
| 443 单位 | 把 Findings 数当题目数 | 字段改名 `historical_published_findings`，加单位旁证断言（`resources_discovered`/`findings_total`/`layering` 合计） |
| 两个 212 混讲 | 统计单位与集合矛盾 | `q03_set_comparisons` 分别输出 A/B/C 三组；A 明确标注"含污染，非正式口径" |
| 51 条归因 | 曾出现"全部 superseded（50+1 条 QA 状态）"的自相矛盾说法 | 改为 DB 实查逐状态分列：`superseded: 51` |
| "防历史工件被改" | 表述过强：结构校验查不出一增一减 | 收紧为"结构与计数一致性校验 + 本次运行不修改历史原件"；P7b **实测**该盲区；另加 H 哈希冻结兜底 |
| QA 台账 `valid=false` | 越权：把未来处置写成既定规则 | 改为"不删改；未来如需调整须单独评估并获授权"；原表述留档在 `superseded_statement` |
| `_post` 未定义 | **本项最严重**：定义在 #124 被删、调用点仍在，`except Exception` 吞掉 NameError，锁测"并发提交"分支可能从未真正发出请求 | 补回定义；新增 `test_static_callables.py`（C1 检出未定义调用）挂门禁第 7 项；变异验证确认能抓到该回归 |