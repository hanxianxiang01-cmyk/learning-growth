# Branch & PR Policy

## Branch names

```text
feat/FE-1301-task-renderer
fix/FE-1210-result-empty
api/API-1305-task-schema
docs/DOC-003-adr
chore/OPS-002-ci
```

## PR size

建议一个 PR：
- 一个主要目标
- 尽量 < 500 行有效业务改动
- 大型改造拆分为基础设施PR + 功能PR

## Shared files

高冲突文件：
- OpenAPI
- contracts
- state machine
- root CHANGELOG
- PROJECT_STATUS
- skin tokens

修改高冲突文件前，应先确认没有另一个进行中的PR修改同一区域。
