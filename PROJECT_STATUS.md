# Project Status

> 这是项目当前状态的**唯一人工可读仪表盘**。  
> 任何工作开始/完成/阻塞时都应更新对应条目。

状态：

```text
⚪ TODO
🔵 IN PROGRESS
🟡 REVIEW
🟢 DONE
🔴 BLOCKED
```

## Stable Baseline

| Item | Version / State |
|---|---|
| Child Web | `1.2.0` |
| Frontend release | Learning Result Closure |
| Built-in skins | `healing`, `math-lab` |
| Default child skin | `math-lab` |
| Learning result source | Session Result API |
| Frozen learning-core baseline | `v1.3.1` |
| Mastery rule version (active) | `mastery-v1.3.1` |
| Governance | `1.0.0` |

## Current Completed Capabilities

| Area | Capability | Status |
|---|---|---|
| Child UI | Home / Learning / Result / Growth | 🟢 DONE |
| UI | 18 core components | 🟢 DONE |
| Skin | 2 built-in skins | 🟢 DONE |
| Learning | Session / Task / Attempt / Hint | 🟢 DONE |
| Learning | Result API frontend closure | 🟢 DONE |
| Runtime | Mock / HTTP adapters | 🟢 DONE |
| Governance | Git-ready repository structure | 🟢 DONE |
| Governance | PR / Issue / CI / Release templates | 🟢 DONE |
| Learning | Mastery L0→L4 全链路（evidence role / coverage / derived / review） | 🟢 DONE |
| Learning | 证据消化→能力升级闭环（persist AbilityState） | 🟢 DONE |

## Current Partial / Gaps

| Local ID | Area | Work | Status | Owner | PR |
|---|---|---|---|---|---|
| DRIFT-001 | Contract | Session Result API尚未写入冻结OpenAPI | 🟢 DONE | Backend/Contract | #21 |
| DRIFT-002 | Mastery | 运行实现 vs 冻结 v1.3.1 契约漂移（B1~B8） | 🟢 DONE | Backend | #15~#19 |
| FE-1311 | Mastery | Atomic Evidence Truth（L1→L2 Gate + evidence_role + 单Task单证据） | 🟢 DONE | Backend | #15 |
| FE-1312 | Mastery | Evidence Coverage（Optional 维度 + 多样性约束） | 🟢 DONE | Backend | #16 |
| FE-1313 | Mastery | Derived Evidence + L4 Gate | 🟢 DONE | Backend | #17 |
| FE-1314 | Mastery | Review 状态机 + Curriculum 选 role | 🟢 DONE | Backend | #18 |
| FE-1315 | Mastery | QA replay 14/14 → 激活 mastery-v1.3.1 | 🟢 DONE | Backend | #19 |
| P0-GOV-CF | V1.4 Governance | context_family 受控词表 + Seed 校验 + 50题回填 + Transfer 回归 | 🟢 DONE（AC-01~07；待裁决6题REVIEW） | Backend/Content | — |
| FE-1403 | V1.4 Protocol | Renderer Registry Contract：23 枚举冻结 + 校验 + V1/V2 分流规则 | 🟢 协议冻结（Registry 12 字段随交付填充；V2 JSON Schema 待冻结） | Backend/Frontend | — |
| FE-1404 | V1.4 Protocol | TaskUISchema V2 + MathResponse V2 可执行 Schema + 五链样例 + 校验器 | 🟡 冻结候选（待会签；待办7项见 docs/frontend/29 §5） | Backend/Content/Frontend | — |
| FE-1405 | V1.4 Vertical | A5 纵向链端到端：V2 题下发→渲染→提交→判分→幂等（真实 E2E PASS） | 🟢 DONE（首批 1 题；submission_id 迁移为后续项） | Backend/Frontend | — |
| FE-1301 | Task Renderer | V1（number/manipulative/unsupported） | 🟢 DONE | Frontend | — |
| FE-1302 | Math Workspace | 隔离 Workspace State | 🟢 DONE | Frontend | — |
| FE-1303 | Manipulative | Object Counter interactive | 🟢 DONE | Frontend | — |
| FE-1304 | Manipulative | Bar Model interactive | 🟢 DONE | Frontend | — |
| FE-1305 | Manipulative | Number Line interactive | 🟢 DONE | Frontend | — |
| API-1306 | Contract | TaskUISchema V1 | 🟢 DONE | Frontend | — |
| API-1307 | Contract | Structured Response | 🟢 DONE | Frontend | — |
| API-1308 | Hint | Workspace-aware ui_action | 🟢 DONE | Frontend | — |
| QA-1312 | QA | /dev/v1.3-qa 双皮肤页 | 🟢 DONE | Frontend | — |
| FE-1310 | Mastery UI | 能力状态儿童文案、多能力结果页、Normalizer迁移兼容 | 🟢 DONE | Frontend | — |
| QA-1311 | QA | Mastery前端边界静态回归 | 🟢 DONE | Frontend | — |
| EVT-1208 | Events | Interaction Event schema | ⚪ TODO | — | — |

## V1.4 Frontend P0

| Item | Capability | Status | Validation |
|---|---|---|---|
| V14-01 | Renderer Registry + safe fallback | 🟢 DONE | static contract check |
| V14-02 | Workspace API + capability gate | 🟢 DONE | pure TypeScript check |
| V14-03 | TaskUISchema renderer/capability metadata | 🟢 DONE | pure TypeScript check |
| V14-04 | Structured Response interaction_events | 🟢 DONE | static contract check |
| V14-05 | AttemptResult / HintResponse normalizer | 🟢 DONE | pure TypeScript check |
| V14-06 | Dual-skin V1.4 QA route | 🟢 DONE | transpile/parse check |
| V14-07 | Full Next production build | 🟢 DONE | `next build` 通过（2026-09-30 本地补验，9 routes 含 /dev/v1.4-qa）|

## V1.3 Scope

功能已三方合入 `main`（来自 `Math_Sprint3_Frontend_V1.3` 交付包）；版本号仍保持 `1.2.0`，待里程碑验收后由 Release Owner 统一升 `1.3.0`。

外部待办（后端对齐）：

- 🟡 Backend Structured Response acceptance
- 🟡 Backend TaskUISchema V1 alignment
- 🟡 Backend Hint ui_action alignment
