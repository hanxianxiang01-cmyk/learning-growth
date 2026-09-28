# Branch & PR Policy

> 本文是分支命名的**唯一权威来源**。分支名由 CI 的 `branch:check` 强制校验（见 `scripts/check-branch-name.mjs`），不合规无法通过 governance check 合入 main。

## 命名规范（强制）

业务分支三条主线：

```text
fix/BUG-xxxx-*         Bug 修复（如 fix/BUG-1013-result-empty）
hotfix/BUG-xxxx-*      紧急生产修复（针对线上 release，修复后须同时回灌 main）
feat/FE-13xx-*         V1.3 功能（如 feat/FE-1301-task-renderer）
```

> 编号段 `xxxx` / `13xx` 对应 Issue 编号。分支尾缀用短横线小写描述，如 `-task-renderer`。

辅助分支（文档/工程，同样走 PR）：

```text
docs/*       文档与治理
chore/*      工程配置、脚本
```

## 分支模型核心原则

- **不设长期「大开发分支」**（无 `develop`、无 `release/V1.3` 长跑分支）。
- **一个 Issue = 一个 feature branch**，短生命周期，合入即删。
- 唯一长期稳定分支：`main`。

## Bug 合入后的同步（强制）

```text
1. fix/BUG-xxxx-* 开 PR 合入 main（走 CI，全绿后方可合）
2. main 一旦含该 Bug 的修复，所有活跃的 V1.3 分支（feat/FE-13xx-* 及其子孙）
   必须从最新 main 向后合并（merge main → 活跃分支）或 rebase，
   确保修复不遗漏、不漂移。
3. 同步时必须重新跑 CI，通过后再继续开发/合并该分支。
```

同步示例：

```text
git checkout feat/FE-1301-task-renderer
git fetch origin
git merge origin/main          # 或 git rebase origin/main
git push
# 等待 CI 全绿
```

## PR size

建议一个 PR：

- 一个主要目标
- 尽量 < 500 行有效业务改动
- 大型改造拆分为基础设施 PR + 功能 PR

## Shared files

高冲突文件：

- OpenAPI
- contracts
- state machine
- root CHANGELOG
- PROJECT_STATUS
- skin tokens

修改高冲突文件前，应先确认没有另一个进行中的 PR 修改同一区域。