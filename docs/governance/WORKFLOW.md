# Git Workflow

## Truth Hierarchy

从高到低：

```text
1. main branch code
2. frozen baseline in baselines/
3. accepted ADR
4. current OpenAPI / schema contract
5. project docs
6. chat / handoff notes
7. historical ZIP
```

如果发生冲突，必须登记，不允许静默选择。

## Branch Model

只保留一个长期稳定分支：

```text
main
```

业务分支（命名由 CI 强制校验，详见 `BRANCH_AND_PR_POLICY.md`）：

```text
fix/BUG-xxxx-*         Bug 修复
hotfix/BUG-xxxx-*      紧急生产修复
feat/FE-13xx-*         V1.3 功能
```

辅助分支：

```text
docs/*
chore/*
```

核心原则：

- **不引入长期「大开发分支」**（无 `develop`、无 `release/V1.3` 长跑分支）。
- **一个 Issue = 一个 feature branch**，短生命周期，合入即删。
- Bug 合入 main 后，所有活跃 V1.3 分支必须 merge 最新 main（或 rebase）并重新过 CI，防止修复漂移。

## Pull Request

任何对 main 的代码修改必须经过 PR。

最小 PR：
- 一个主要Issue
- 明确Acceptance Criteria
- 测试结果
- 文档影响
- Contract影响
- Breaking Change判断

## Merge Strategy

建议：
- 小功能：Squash Merge
- 需要保留多Commit历史的架构改造：Merge Commit

禁止：
- 直接push main
- 两个独立ZIP人工合并
- 未登记Contract Drift直接联调
