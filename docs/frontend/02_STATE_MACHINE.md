# 学习交互状态机

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
 │                         ↓ requestHint
 │                       hint_loading
 │                         ↓
 │                       hint_active
 │                         ↓ retry
 │                       answering (attempt_no + 1)
 ├─ wrong + RETRY       → retry → answering
 └─ error               → error
```

## 关键规则

- 第一次错误不显示标准答案。
- Hint 1–4 由 Learning Engine 返回/控制。
- `E01~E07` 作为 2xx 教育诊断数据处理。
- HTTP/系统错误使用冻结码：
  - LE-4001
  - LE-4091
  - LE-4221
  - LE-4291
  - LE-5001
  - AG-5031
- 前端不计算 Mastery。
