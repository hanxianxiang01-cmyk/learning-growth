# Learning Engine API Mapping

Base URL：

```text
NEXT_PUBLIC_LEARNING_API_BASE_URL=http://localhost:8000/api
```

## 已按冻结 OpenAPI 接线

### Profile
`GET /v1/children/{child_id}/profile`

用于：
- 首页儿童信息
- 今日能力提示

### Abilities
`GET /v1/children/{child_id}/abilities`

用于：
- 首页能力摘要
- 结果页刷新
- 成长地图

### Create Session
`POST /v1/learning/sessions`

请求：
```json
{
  "child_id": "uuid",
  "subject": "math",
  "requested_minutes": 15
}
```

### Next Task
`POST /v1/learning/tasks/next`

请求：
```json
{
  "child_id": "uuid",
  "session_id": "uuid",
  "subject": "math",
  "requested_minutes": 15
}
```

响应核心：
- task_instance_id
- ability_id
- difficulty
- ui_schema
- strategy_policy
- goal

### Submit Attempt
`POST /v1/learning/attempts`

请求：
- task_instance_id
- attempt_no
- response
- client_elapsed_ms
- used_hint_levels

响应：
- attempt_id
- correct
- diagnosis
- next_action

支持：
`RETRY | HINT | TEACH | COMPLETE | NEXT_TASK`

### Hint
`POST /v1/learning/hints`

请求：
- attempt_id
- requested_level 1–4

响应：
- policy_id
- hint_level
- action_type (`QUESTION | STRUCTURE_HINT | STEP_HINT | TEACH`)
- text（实际提示文本）
- answer_revealed（是否已经揭示答案）


---

## Session Result（V1.2新增）

前端接口：

```ts
getSessionResult(sessionId: string): Promise<SessionResult>
```

Canonical Result：

```text
duration_ms
task_count
attempt_count
hint_usage
learning_behaviors
ability_changes
next_recommendation
```

### 当前路径策略

本地冻结 `02_openapi_v1.3.yaml` 尚未找到新Result Endpoint，因此：

```env
NEXT_PUBLIC_SESSION_RESULT_PATH_TEMPLATE
```

作为前端适配点。

页面不直接拼URL。

### Source of Truth

V1.2开始：

```text
Session Result API
```

是结果页正式数据源。

`sessionStore` 只做异常fallback。
