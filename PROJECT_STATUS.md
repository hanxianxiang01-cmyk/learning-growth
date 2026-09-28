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

## Current Partial / Gaps

| Local ID | Area | Work | Status | Owner | PR |
|---|---|---|---|---|---|
| DRIFT-001 | Contract | Session Result API尚未写入冻结OpenAPI | 🔴 BLOCKED | Backend/Contract | — |
| FE-1201 | Math Workspace | Basic visual workspace only | 🟡 REVIEW | — | — |
| FE-1202 | Task Renderer | Schema/Renderer registry未实现 | ⚪ TODO | — | — |
| FE-1203 | Manipulative | Object Counter interactive | ⚪ TODO | — | — |
| FE-1204 | Manipulative | Bar Model interactive | ⚪ TODO | — | — |
| FE-1205 | Manipulative | Number Line interactive | ⚪ TODO | — | — |
| API-1206 | Contract | Structured Response contract | ⚪ TODO | — | — |
| API-1207 | Hint | Workspace-aware ui_action | ⚪ TODO | — | — |
| EVT-1208 | Events | Interaction Event schema | ⚪ TODO | — | — |

## V1.3 Scope

**尚未冻结。**

候选项在 `ROADMAP.md` 中。  
冻结 V1.3 时必须：

1. 建立 Milestone。
2. 为每个功能建立 Issue。
3. 指定单一 Owner。
4. 确认 API/Schema 依赖。
5. 更新此表状态。
6. 在 `CHANGELOG.md [Unreleased]` 写入范围。
