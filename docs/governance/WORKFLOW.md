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

短分支：

```text
feat/*
fix/*
api/*
docs/*
chore/*
```

不引入长期 `develop`，除非团队规模显著扩大。

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
