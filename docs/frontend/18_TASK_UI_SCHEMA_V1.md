# 18｜TaskUISchema V1

## Principle

Task schema告诉前端：
- 怎么显示
- 允许怎么操作
- 怎么提交

不包含：
- 正确答案
- Mastery规则
- Diagnosis规则

## Supported in V1.3

```text
kind=number
kind=manipulative + visual.type=objects
kind=manipulative + visual.type=bar-model
kind=manipulative + visual.type=number-line
```

未知类型：

```text
kind=unsupported
```

前端安全降级，不白屏。

## Structured Response

```json
{
  "schema_version": "1.0",
  "answer": "3",
  "representation": {
    "type": "object-counter"
  }
}
```

representation仅记录数学表征，不由前端转换成Mastery。
