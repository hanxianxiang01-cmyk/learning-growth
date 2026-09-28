# 11｜Session Result 前端接线

## Source of Truth

V1.2 开始：

```text
Session Result API
```

是结果页正式数据源。

`sessionStore.ts` 仅：
- 跳转过渡
- 网络错误临时兜底
- 本地恢复辅助

不能用于正式教育判断。

---

## Canonical Contract

```ts
SessionResult {
  session_id
  child_id?
  status?
  duration_ms
  task_count
  attempt_count
  hint_usage[]
  learning_behaviors[]
  ability_changes[]
  next_recommendation?
  completed_at?
}
```

---

## Result UI Mapping

### learning_behaviors

```text
LearningBehaviorChecklist
```

前端不得通过：
- attempt_count
- correct count
- hint count

自行推断“坚持、独立、检查”等教育行为。

---

### ability_changes

```text
AbilityGrowthCard
```

用于：
- before_level
- after_level
- trend
- evidence_delta

---

### next_recommendation

```text
NextTaskCard
```

用于：
- title
- description
- optional href

若没有 href：
默认返回儿童数学首页，由下一轮 Session 再交给 Learning Engine 选题。

---

## HTTP Path

当前本地冻结 `02_openapi_v1.3.yaml` 尚未包含新接口路径。

因此使用：

```env
NEXT_PUBLIC_SESSION_RESULT_PATH_TEMPLATE=/v1/learning/sessions/{session_id}/result
```

这个默认值是前端适配约定，不应被视为后端权威真相。

当后端 OpenAPI 更新后：

1. 修改环境变量为正式路径
2. 对照 Schema 收紧 `SessionResult`
3. 收紧 `sessionResultNormalizer.ts`
4. 更新 `CHANGELOG.md`
5. 更新本文件

---

## Fallback

如果 Result API 调用失败：

```text
API Failure
 ↓
sessionStore有快照？
 ├─ Yes → 显示“临时记录”并明确标识
 └─ No  → Error + Retry
```

禁止静默把本地推断当成正式结果。
