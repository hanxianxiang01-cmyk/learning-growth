# Shared Contracts

前后端共享契约包（V1.4 起激活）。

当前内容：
- `schemas/task-ui-schema-v2.schema.json` — TaskUISchema V2（draft 2020-12，可执行）
- `schemas/math-response-v2.schema.json` — MathResponse/Attempt 外层 V2（可执行）
- `samples/` — 五条纵向链合法样例 + 非法反例（B5/A5/D5/E4/F6）
- `examples/` — 全量 Attempt 样例（含 interaction_events）
- `contracts/validate.py` — 三层校验入口（schema → 协议枚举 → 语义层/下发分层）

语义说明与待冻结清单：`docs/frontend/29_V2_CONTRACTS_EXECUTABLE_FREEZE.md`
协议枚举事实源：`docs/frontend/28_RENDERER_REGISTRY_CONTRACT.md` + `apps/learning-api/app/content/renderer_protocol.py`（CI 强制三处同步）。

> 历史备注：child-web 现阶段仍使用本地 `contracts.ts`；TS 类型镜像由本包导出属待办（见 29 号文档 §5-7）。
