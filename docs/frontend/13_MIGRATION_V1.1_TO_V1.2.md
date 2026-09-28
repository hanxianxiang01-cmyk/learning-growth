# 13｜V1.1 → V1.2 Migration Guide

## 核心变化

### V1.1

```text
COMPLETE
 ↓
sessionStorage Snapshot
 ↓
MathResultScreen
```

### V1.2

```text
COMPLETE
 ↓
Session Result API
 ↓
MathResultScreen
```

`sessionStorage` 降级为fallback。

---

# 代码迁移

## 1. LearningApi

新增：

```ts
getSessionResult(sessionId: string): Promise<SessionResult>
```

所有 `LearningApi` 实现必须补齐。

---

## 2. Result Screen

删除作为主流程的数据：
- `getAbilities()`拼结果
- `snapshot`推断behavior
- `snapshot`决定next recommendation

改用：

```text
result.learning_behaviors
result.ability_changes
result.next_recommendation
```

---

## 3. 环境变量

新增：

```env
NEXT_PUBLIC_SESSION_RESULT_PATH_TEMPLATE
```

---

## 4. sessionStore

不要删除。

继续用于：
- fallback
- navigation recovery

但禁止新代码把它当正式学习结果来源。

---

# 兼容性

本次没有：
- 路由Breaking Change
- Session流程Breaking Change
- Task/Attempt/Hint Contract Breaking Change

主要变化是：

> Result Page 的 Source of Truth 从 Client Snapshot 切换到 Server Result。
