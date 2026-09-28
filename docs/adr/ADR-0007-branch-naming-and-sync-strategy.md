# ADR-0007｜Branch Naming & Sync Strategy

**Status:** Accepted

## Context

V1.3 开发涉及多个并行功能，同时存在 Bug 修复与线上紧急修复需求。需要一套清晰、可强制、不产生误合并的分支战略。

## Decision

分支命名（强制，由 CI `branch:check` 校验）：

```text
fix/BUG-xxxx-*          Bug 修复
hotfix/BUG-xxxx-*       紧急生产修复
feat/FE-13xx-*          V1.3 功能
docs/*                  文档/治理
chore/*                 工程配置
```

分支模型：

- 唯一长期分支：`main`。
- **不维护长期「大开发分支」**（无 `develop`、无 `release/V1.3` 长跑分支）。
- **一个 Issue = 一个 feature branch**，短生命周期，合入即删。

同步规则：

- Bug 修复（`fix/*` 或 `hotfix/*`）合入 `main` 后，**所有活跃 V1.3 分支**（`feat/FE-13xx-*`）必须 merge 最新 `main`（或 rebase）并重新通过 CI。

## Consequence

- 分支名不合规的分支无法通过 governance check 合入 main。
- 修复不会在并行功能分支上遗漏、漂移。
- `hotfix/*` 修复合入 main 后由同步规则自动扩散到所有活跃功能分支，避免线上修复与开发线分叉。