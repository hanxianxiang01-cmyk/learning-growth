# FE-1403 Renderer Registry Contract（协议冻结 · V1.0）

> 状态：**协议冻结候选（P0-01 落地）**。23 个 renderer 的 kebab-case 协议枚举 + 注册表字段契约 + V1/V2 分流规则。
> 依据：《V1.4 P0 Architecture Contract》P0-01、《V1.4评审 V0.2》§3.1、42 能力矩阵 Sheet 02（Renderer 目录）。
> 机器可读镜像：`apps/learning-api/app/content/renderer_protocol.py`（本文件与其一一对应，改动必须同步）。

---

## 1. 命名契约（§3.1 冻结）

- 显示名 = PascalCase（矩阵口径），协议 ID = kebab-case；映射由注册表生成，**禁止**在资源里混用别名。
- 校验：`validate_renderer_id()` → 非枚举值 `ValueError: UNKNOWN_RENDERER_ID`（对齐 UNKNOWN_CONTEXT_FAMILY 模式）。

## 2. 冻结枚举（23 项，R-001~R-023）

| 协议 ID | 显示名 | R-ID | 来源 | 实现状态 |
|---|---|---|---|---|
| `object-counter` | ObjectCounter | R-001 | v1.3_reuse | implemented |
| `bar-model` | BarModel | R-002 | v1.3_reuse | implemented |
| `number-line` | NumberLine | R-003 | v1.3_reuse | implemented |
| `number-input` | NumberInput | R-004 | base_ui | implemented |
| `choice-grid` | ChoiceGrid | R-005 | base_ui | planned |
| `place-value` | PlaceValue | R-006 | v1.4_new | planned |
| `ten-frame` | TenFrame | R-007 | v1.4_new | planned |
| `column-arithmetic` | ColumnArithmetic | R-008 | v1.4_new | implemented（FE-1403；Gate B5 待E2E） |
| `array-board` | ArrayBoard | R-009 | v1.4_new | planned |
| `grouping-board` | GroupingBoard | R-010 | v1.4_new | planned |
| `formula-board` | FormulaBoard | R-011 | v1.4_new | planned |
| `estimation-canvas` | EstimationCanvas | R-012 | v1.4_new | planned |
| `shape-gallery` | ShapeGallery | R-013 | v1.4_new | planned |
| `shape-canvas` | ShapeCanvas | R-014 | v1.4_new | planned |
| `sorting-board` | SortingBoard | R-015 | v1.4_new | planned |
| `direction-grid` | DirectionGrid | R-016 | v1.4_new | planned |
| `ruler` | Ruler | R-017 | v1.4_new | planned |
| `clock` | Clock | R-018 | v1.4_new | planned |
| `timeline` | Timeline | R-019 | v1.4_new | planned |
| `money-board` | MoneyBoard | R-020 | v1.4_new | planned |
| `data-table` | DataTable | R-021 | v1.4_new | planned |
| `pictograph` | Pictograph | R-022 | v1.4_new | planned |
| `pattern-board` | PatternBoard | R-023 | v1.4_new | planned |

**关键语义：协议合法 ≠ 可下发。** planned 的 renderer 允许出现在词表/文档/内容规划里，但**不得**被任何 published 资源引用；下发前 `is_implemented` 校验，未实现即受控拒绝（不错误降级为数字题——评审 §3.1 明令）。

## 3. V1 / V2 分流规则（接线规则，评审 §3.1）

```
ui_schema.schema_version
├─ "1.0"（含缺失，V1.3 存量 50 题）
│   renderer_id 可不声明 → 由 kind/visual.type 推导（现行 resolveRendererId 行为）
│   若声明，必须 ∈ 23 枚举（非法 = UNKNOWN_RENDERER_ID）
│   C 域资源继续走 V1 适配，不通过 normalizer 静默转 V2
└─ "2.0"（五域新资源，待 TaskUISchema V2 正式冻结）
    renderer_id 必填、必须 ∈ 枚举、且必须 implemented
    mode / renderer_version / config 由 Renderer 注册表校验
    未知版本或模式 → 受控拒绝，下发前即筛除（评审红线）
```

**V2 硬约束清单**（来自 P0 Architecture Contract + 评审 §3.1，V2 Schema 正式冻结时写入判别联合）：
- `workspace_id` 任务内唯一；一 Task 可含多 Workspace/多 Renderer Instance（INV-02/03）；
- 公共层：`schema_version / ui_revision / prompt / workspaces / response_contract`；
- 工作区层：`workspace_id / renderer / renderer_version / mode / config / initial_state / capabilities / constraints`；
- `capabilities` 必须 ⊆ 该 renderer 注册表声明的 interaction_capabilities（前端 can() 门控的协议依据）；
- 跨 Renderer 数据只走 Workspace bindings，禁止 renderer 间直接 API。

## 4. 前端镜像对齐（本 PR 附带的唯一代码改动）

`rendererRegistry.ts` 现含 23 个协议 ID，其中 5 个真实 Renderer 已实现（object-counter/bar-model/number-line/number-input/column-arithmetic）+ 1 个内部兜底哨兵 `unsupported`。**`unsupported` 不在 23 协议枚举内**——它是前端运行时的安全降级状态（"当前无可渲染 renderer"），不是协议身份。

冻结口径：
- `RendererId = 23 协议 ID + "unsupported"（前端专用哨兵，标注注释，永不进入资源/后端/数据）`；
- `resolveRendererId` 行为不变：协议外 declared → unsupported（已符合）。

## 5. Registry 完整字段（P0-01 要求，随各 Renderer 交付逐项填充）

每个注册表条目的完整契约字段：`renderer_id / renderer_name / renderer_version / source / status / input_contract / state_contract / interaction_contract / response_contract / evidence_capability / diagnosis_capability / serialize_contract / theme_contract`。

- 本 PR 冻结前 5 项（身份字段）+ interaction 能力；
- 其余 7 项随 mode 专属 Schema（评审 §3.2 "模式才允许发布资源"）在各 Renderer 实现 PR 中交付；
- 首批纵向链（Phase 1 前）：B5 column-arithmetic、A5 number-line(扩展 mode)、D5 shape-canvas、E4 ruler、F6 data-table。

## 6. 不变量（继承 P0 Architecture Contract，前后端共同遵守）

- INV-01 Renderer 不算 Mastery/Diagnosis/Curriculum（check-v14 已扫禁止关键词）；
- INV-04 Response 不直接改 Mastery，必经 Evidence→Learning Engine；
- 前端不提交能力等级/正确率/证据角色；客户端不得伪造 schema_version/renderer 声明（后端从 TaskInstance 核对资源版本与 UI revision）。

## 7. 验收对照

| 项 | 状态 |
|---|---|
| 23 协议 ID kebab-case 枚举（代码+文档） | ✅ 本 PR |
| 非法 ID 拒绝（UNKNOWN_RENDERER_ID） | ✅ +单测 |
| implemented/planned 分层 + 下发受控 | ✅ is_implemented() |
| V1/V2 分流规则成文 | ✅ §3 |
| unsupported 哨兵不入协议面 | ✅ §4 |
| Registry 全 12 字段 | ⏳ 随各 Renderer 交付（§5） |
| V2 可执行 JSON Schema + OpenAPI | ⏳ TaskUISchema V2 正式冻结（下一步） |
