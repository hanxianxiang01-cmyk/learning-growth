# 学习状态与数学工作区状态

## 1. Learning Flow State

```text
idle
 ↓
loading_task
 ↓
answering
 ↓ submit
submitting
 ├─ correct + NEXT_TASK → correct → loading_task
 ├─ correct + COMPLETE  → completed → result
 ├─ wrong + HINT/TEACH  → hint_available
 │                         ↓
 │                       hint_loading
 │                         ↓
 │                       hint_active
 │                         ↓ retry
 │                       answering
 ├─ wrong + RETRY       → retry → answering
 └─ error               → error
```

Learning State只负责：
- Task
- Structured Response
- attemptNo
- Hint
- Learning status

## 2. Workspace State（V1.3）

独立存在：

```text
initial
present representation
history
highlightedTargets
focusedTarget
lastHintAction
```

Action：

```text
COMMIT
UNDO
RESET
APPLY_HINT
REINITIALIZE
```

## 3. 为什么分离

禁止把：

```text
dragging
object position
bar value
number-line jump
selection
```

塞入 Learning State。

后续新增 Sorting / Matching / Geometry 时，只扩 Workspace，不重构 Learning Flow。

## 4. 教育规则

- 第一次错误不揭答案；
- Hint 1–4由 Learning Engine 控制；
- E01~E07 是教育诊断业务载荷；
- 前端不计算 Mastery；
- Workspace representation 是过程证据，不是前端教育结论。
