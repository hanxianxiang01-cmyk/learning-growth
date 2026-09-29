# 20｜V1.3 后端 Contract 依赖

本地 V1.3 前端已实现新 Contract，但真实 HTTP 联调需要后端满足以下条件。

## API-1306 TaskUISchema V1

推荐后端逐步输出 Canonical V1：

```text
schema_version=1.0
kind
prompt
visual
tools
response_schema
```

前端目前保留 legacy normalizer 作为迁移层。

## API-1307 Structured Response

后端 Attempt Endpoint 需要接受：

```json
{
  "response": {
    "schema_version": "1.0",
    "answer": "8",
    "representation": {
      "type": "bar-model"
    }
  }
}
```

如果后端仍只接受 primitive string/number，则 HTTP 模式会产生 Contract 不兼容。

## API-1308 Workspace-aware Hint

Hint可选返回：

```json
{
  "ui_action": {
    "type": "highlight",
    "targets": ["a", "b"]
  }
}
```

支持动作：
- highlight
- align_groups
- focus
- show_bar_relation
- show_number_line_start

没有 `ui_action` 时前端仍正常显示文字 Hint。

## 安全边界

后端不能通过 ui_action：
- 执行任意JS
- 改页面路由
- 改Mastery
- 跳过Attempt
- 直接提交答案

它只能影响受控 Workspace 呈现。
