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
