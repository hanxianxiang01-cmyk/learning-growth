# 10｜V1.2 Release Notes

## Version

```text
Math_Sprint3_Frontend_V1.2
package: 1.2.0
release: Learning Result Closure
```

## 本版本目标

V1.1 已经能够：

```text
Session → Task → Attempt → Hint/Retry → COMPLETE
```

但 Result Page 仍依赖浏览器 `sessionStorage` 快照。

V1.2 将结果页升级为：

```text
COMPLETE
 ↓
Session Result API
 ↓
SessionResult
 ↓
Learning Behaviors
Ability Changes
Session Stats
Next Recommendation
 ↓
Result Page
```

这意味着：

> 后端成为学习结果的正式 Source of Truth。

## 用户可见变化

结果页现在可以准确展示：
- 本次学习行为
- 完成任务数量
- 作答次数
- Hint使用
- 能力变化
- 下一步推荐

即使刷新结果页，也不应该依赖之前浏览器内存中的统计。

## 工程变化

新增：
- Result API Contract
- Result HTTP Adapter
- Result Mock Adapter
- Result Normalizer
- Result Loading/Error/Fallback状态

## 不在本版本

V1.2 不做：
- Task Renderer
- Drag & Drop
- Number Line Interaction
- Bar Model Interaction
- Draw Canvas
- Parent Dashboard
- Skin Engine

这些进入后续版本。
