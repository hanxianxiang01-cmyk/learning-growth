# Learning Engine API Mapping

## Base URL

```text
NEXT_PUBLIC_LEARNING_API_BASE_URL=http://localhost:8000
```

> 不带 `/api`；请求路径直接以 `/v1/...` 开头。

## Profile

`GET /v1/children/{child_id}/profile`

## Abilities

`GET /v1/children/{child_id}/abilities`

## Create Session

`POST /v1/learning/sessions`

## Next Task

`POST /v1/learning/tasks/next`

V1.3 起，HTTP Adapter 会通过：

```text
src/lib/api/taskUiSchemaNormalizer.ts
```

把后端 `ui_schema` 正规化成 `TaskUISchema V1`。

### Canonical TaskUISchema V1

支持：

```text
kind=number
kind=manipulative + objects
kind=manipulative + bar-model
kind=manipulative + number-line
```

未知类型 → `kind=unsupported`，前端安全降级。

## Submit Attempt

`POST /v1/learning/attempts`

V1.3 请求核心：

```json
{
  "task_instance_id": "uuid",
  "attempt_no": 1,
  "response": {
    "schema_version": "1.0",
    "answer": "3",
    "representation": {}
  },
  "client_elapsed_ms": 5000,
  "used_hint_levels": [1]
}
```

`representation` 可为：
- object-counter
- bar-model
- number-line

前端仅采集/提交，不自行转化成 Mastery。

## Hint

`POST /v1/learning/hints`

V1.3扩展：

```text
ui_action?:
- highlight
- align_groups
- focus
- show_bar_relation
- show_number_line_start
```

`ui_action` 是枚举化受控动作，不接受任意 UI command。

## Session Result

前端接口：

```ts
getSessionResult(sessionId: string): Promise<SessionResult>
```

Source of Truth 仍为服务端 Session Result。

路径通过：

```env
NEXT_PUBLIC_SESSION_RESULT_PATH_TEMPLATE
```

适配，页面不直接拼 URL。

## V1.3 Mastery Closure UI Contract

Mastery 计算与升级/复习判断仍完全由 Learning Engine 负责；儿童端不调用规则、不计算四维指标。

### AbilityState

儿童端继续消费：

```text
level: 0..4
confidence: 0..1
evidence_count
trend: up | stable | watch | down_review
```

儿童可见映射：

```text
up          -> 有进步
stable      -> 很稳定
watch       -> 继续积累
down_review -> 正在巩固
```

不得向儿童显示 `review_required / downgrade / transfer_missing / mastery_score` 等内部术语。

### Session Result ability_changes

推荐后端输出：

```json
{
  "ability_id": "app_rel",
  "name": "数量关系",
  "before_level": 1,
  "after_level": 2,
  "confidence": 0.79,
  "trend": "up",
  "evidence_delta": 3
}
```

迁移期 normalizer 同时兼容：

```text
old_level -> before_level
new_level -> after_level
MasteryDecision.decision -> trend fallback
```

结果页会渲染一次 Session 中的全部 `ability_changes`，不再只显示第一项。

### Curriculum transparency

`COLLECT_TRANSFER / COLLECT_RETENTION / REVIEW_REQUIRED` 属于后端教育决策，不应扩成儿童端学习状态。
后端完成调度后，儿童端仍通过现有 `NEXT_TASK` 加载下一题。
