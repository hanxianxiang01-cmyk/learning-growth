# GitHub Setup

> 本文件是仓库配置的**总览**。分支保护的**逐步点击操作**见专门的
> [`GITHUB_BRANCH_PROTECTION_CHECKLIST.md`](./GITHUB_BRANCH_PROTECTION_CHECKLIST.md)。

仓库创建后建议：

## main branch protection

开启：
- Require a pull request before merging
- Require status checks
- Require branches to be up to date
- Block force pushes
- Block deletion

建议至少要求（**status check 名 = CI job 名，逐字一致**）：

```text
governance
child-typecheck
child-build
```

> 详细步骤、三个易踩的坑、配置后自测方法，见 `GITHUB_BRANCH_PROTECTION_CHECKLIST.md`。

## Merge
推荐：
- Squash merge enabled
- Delete head branches after merge

## Milestones
每个 MINOR 版本建立一个 Milestone：

```text
V1.3
V1.4
```

## Labels
建议：

```text
area:frontend
area:api
area:contract
area:math-ui
area:skin
area:docs
type:feature
type:bug
type:chore
status:blocked
breaking-change
```
