# 消费索引：V1.4 Question Bank Production Contract v1.0（2026-10-08）

**判定：收下，作为 V1.4 题库生产的正式验收基线（FROZEN candidate）。**
交付方基于我方 `docs/frontend/34/CONTRACT.md`（trial155 审计产出）整理的正式契约文档。
逐条核验：内容与审计产出**一致、无失真、无夹带**；§10/§11/§13/§14 把我们建议的
"一致性审计/验收门禁/转换器降级/先修契约再扩产"全部制度化，姿态端正。

## 核验表（Contract v1.0 条款 vs 仓库事实）

| Contract 章节 | 内容 | 对照 | 判定 |
|---|---|---|---|
| §5 Global G1~G3 | 标量 answer / hint_ladder+goal+evidence+error 词表 / mode 词表 | = docs/34 §1 | ✅ |
| §6 19 Renderer 矩阵 | 逐渲染器 可转/重导/换挂/直接对齐 判定 | 19 行齐全（15 专件+4 基座链），与我方逐项一致 | ✅ |
| §7 重导规则 | direction 终点编码 0-based+dr/dc非零、shape-canvas 限 rect/tri、money 角+[1,5,10,50]+paid−price=answer、pattern ABAB、clock 整/半点+总分钟 等 | 全部与我方 parser 守卫逐字一致 | ✅ |
| §8/§9 | hint 4 级不泄答案；context_family 只准受控 7 词、禁混题型轴 | 与我方 seed 口径+trial155 亮点确认 | ✅ |
| §10 一致性 Gate | 6 类逐题机器校验 | 吸收我方 18 题内伤实证（P0-141 等） | ✅ |
| §11 8-Gate 验收链 | Schema→一致性→Config×Parser→5% Pin E2E→Judge→Evidence→Diagnosis→qa_replay | 我方 audit-155-config.mjs=Gate 3 工具；Gate 4 复用 pin 机制（FE-1422a 地基现成） | ✅ 采纳为**每批题入库流程** |
| §12 A/B/C 分级 | 直接沿用/重导/数据矛盾先修 | 与我方"~45 题可沿用/62 题重导/18 题内伤"对应 | ✅ |
| §13 Converter 政策 | convert_trial155.py 仅审计、禁作入库通道 | 与我方处置一致 | ✅ |
| §14/§15/§16 | trial155=验证样本非题库；生产禁止项 9 条；DoD 11 项 | 无冲突 | ✅ |
| §17 溯源 | 基准=我方 docs/34 对照表 | 如实标注 | ✅ |

## 落地责任（我方侧）

1. **Gate 3 工具已就位**：`apps/child-web/scripts/audit-155-config.mjs`（每批题入库前跑）；
2. **Gate 4 复用 pin 链**：抽样 5% 经 `v2-catalog + pin_resource_version_id` 实灌（QA child …0099），四连判分——FE-1422a 地基直接可用，无需新开发；
3. **Gate 8 = qa_replay**：与 FE-1433（replay#7 重写）同轨——replay 框架即本契约的验收执行器；
4. 契约引用口径：外部文档条款引用记 **`PC-v1.<节号>`**（对齐既有 `SEM-<n>` 纪律）。

## 与 V1.4 收官链关系

- FE-1432 题库入库继续**挂起**：等待按本契约重导的题批（B 类重导 + C 类修数后再审）；
- FE-1433 qa_replay#7 / FE-1434 契约 FROZEN / FE-1435 立版**不依赖**题批，照常推进；
- FE-1434 冻结清单中把本 Contract v1.0 列**附录资产**（8-Gate 验收链成为正式验收协议）。

## 文件

- `V1.4_Question_Bank_Production_Contract_v1.0.docx`：交付方原件（298 段无损）
- `extracted_text.md`：全文抽取（检索/引用底稿）
