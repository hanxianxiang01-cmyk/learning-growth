# ADR-0003｜Child UI Does Not Call LLM Directly

**Status:** Accepted

## Decision

```text
Child UI
→ Learning Engine
→ DeepTutor / LLM
```

禁止：

```text
Child UI → LLM
```

## Reason
教学策略、Hint等级、安全规则和审计能力必须由Learning Engine控制。
