# Worker Handoff Protocol

当一个Worker把任务交给另一个Worker：

## 必须提供

```text
Issue / Local ID
Branch
Last commit
Current status
Completed
Remaining
Known risks
Contract changes
Files changed
Tests run
```

## 未完成任务

状态必须改为：

```text
🔴 BLOCKED
或
🔵 IN PROGRESS
```

不能写成 DONE。

## 聊天记录

聊天可以作为补充说明，但不能作为唯一交接载体。
所有关键结论必须进入：
- Issue/PR
- ADR
- Contract Drift
- Project Status
- Changelog
中的至少一个。
