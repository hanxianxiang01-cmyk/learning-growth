# ADR-0005｜Session Result Server Source of Truth

**Status:** Accepted

## Decision
V1.2 起：

```text
Session Result API
```

是结果页正式学习结果来源。

`sessionStore` 仅用于：
- 临时缓存
- 导航恢复
- API失败fallback

## Consequence
前端不得根据本地统计自行推断 learning_behaviors。
