# README — 总览与架构评审 V1.3.1

## 当前进场判断
- 主线可以启动：E1/E2纯领域开发可并行。
- 唯一架构红灯：DeepTutor外部扩展SPI Spike（E0-01）。
- E3 Agent Integration：Spike未结论前禁止开工。
- 两项灰灯已关闭：learning_plan/FK、历史文档Superseded。
- 新增交付一致性硬Gate：`GATE-XLSX-CACHE`。它不阻塞业务研发，但阻塞任何更新后的Backlog XLSX提交/发布。

## 当前SSOT
1. DDL V1.3.1
2. OpenAPI V1.3.1
3. Freeze Baseline V1.3.1 + ADR-0001
4. Sprint Backlog V1.3.1
5. `06_validate_backlog_summary_cache.py` 作为Backlog缓存一致性预提交校验

## XLSX公式缓存规则
`05_Sprint_Backlog_v1.3.1.xlsx` 的 Summary A:F 为公式单元格，同时保存公式结果缓存 `<x:v>`。部分Python读取链路不会执行Excel公式，只会读取缓存值。

因此：
1. 任何Backlog明细变更后，必须使用具备公式计算能力的引擎重算工作簿（Excel、LibreOffice或artifact_tool等）；
2. 重算后必须刷新公式缓存再提交；
3. CI/Pre-commit必须运行：
   `python 06_validate_backlog_summary_cache.py 05_Sprint_Backlog_v1.3.1.xlsx`
4. 缓存缺失、缓存与明细独立复算结果不一致时，提交/发布失败；
5. 使用仅写入公式但不执行公式计算的Python库修改XLSX后，不得直接提交最终文件。

## 架构原则
Learning Engine拥有教育决策权；DeepTutor负责Agent运行与自然语言执行。
任何为了保留自定义Capability而修改DeepTutor Core的方案，必须先触发ADR，不得默认接受。
