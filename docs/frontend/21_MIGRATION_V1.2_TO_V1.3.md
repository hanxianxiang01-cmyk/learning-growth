# 21｜V1.2 → V1.3 Migration Guide

## 最大变化

V1.2：

```text
MathLearningScreen
→ MathQuestionCard
→ MathWorkspace
→ AnswerComposer
```

V1.3：

```text
MathLearningScreen
→ TaskRenderer
  → WorkspaceProvider
    → ObjectCounter / BarModel / NumberLine
```

## Attempt Contract变化

### V1.2

```json
{
  "response": "3"
}
```

### V1.3

```json
{
  "response": {
    "schema_version": "1.0",
    "answer": "3",
    "representation": {}
  }
}
```

这是本版最重要的 Contract 变化。

## 后端迁移

真实HTTP模式上线前必须确认 Attempt endpoint 接受 Structured Response。

如果后端尚未升级：
- 不应在正式环境启用V1.3 HTTP模式；
- 可以继续用Mock完成前端交互验收；
- 不建议把前端重新降级回 primitive answer。

## Task Schema

HTTP Adapter增加 `taskUiSchemaNormalizer.ts`，允许旧Schema过渡，但目标是后端输出Canonical TaskUISchema V1。

## Hint

`HintResponse` 新增可选：

```text
ui_action
```

没有该字段不影响文字Hint。

## Learning State

没有破坏原Learning Flow状态机。

新增独立Workspace State，禁止将drag/bar/jump状态合回Learning State。
