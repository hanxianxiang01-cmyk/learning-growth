# Runtime Local Storage Boundary

`sessionStore.ts` 在 V1.2 的职责：

```text
temporary cache
navigation recovery
Session Result API failure fallback
```

它不再是：

```text
official learning result source
```

正式结果以：

```text
LearningApi.getSessionResult(sessionId)
```

为准。
