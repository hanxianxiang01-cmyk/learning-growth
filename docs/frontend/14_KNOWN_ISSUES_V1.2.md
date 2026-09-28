# 14｜V1.2 Known Issues / Constraints

## 1. Session Result OpenAPI 路径待冻结

当前本地：

```text
儿童学习成长系统_V2.0_冻结基线_V1.3同步包/02_openapi_v1.3.yaml
```

尚未发现 Session Result Endpoint。

所以 V1.2 使用：

```env
NEXT_PUBLIC_SESSION_RESULT_PATH_TEMPLATE
```

作为适配。

状态：

```text
⚠️ Backend path awaiting authoritative OpenAPI baseline
```

---

## 2. Session Result Normalizer是过渡适配层

当前支持部分字段别名，目的是避免前端页面和后端字段变体直接耦合。

权威 OpenAPI 发布后必须：
- 收紧字段
- 删除无必要 alias
- 更新 Contract Tests

---

## 3. Math Manipulative Engine未实现

仍然是下一阶段重点。

状态：

```text
🟡 MathWorkspace基础展示
❌ Drag Blocks
❌ Number Line Interaction
❌ Bar Model Interaction
❌ Draw Canvas
```

---

## 4. Result Snapshot仍然存在

是有意保留，不是遗留忘删。

职责仅：

```text
API失败时临时兜底
```

UI会明确显示“临时记录”，不会冒充正式结果。
