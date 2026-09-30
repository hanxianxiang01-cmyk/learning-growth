# 24｜V1.3 Mastery Closure 前后端对接说明

## 1. 总原则

Mastery 是 Learning Engine 的教育决策；Child Web 只提交行为并展示服务端状态。

```text
Child Web
  submit Attempt/Structured Response
        ↓
Learning Engine
  Diagnosis + Evidence + Mastery + Curriculum
        ↓
Child Web
  next_action / Task / SessionResult / AbilityState
```

前端禁止计算 C/I/S/T、MasteryScore、升级/降级和下一题类型。

## 2. Attempt 接口保持不变

`POST /v1/learning/attempts`

前端继续提交：

```json
{
  "task_instance_id": "uuid",
  "attempt_no": 1,
  "response": {
    "schema_version": "1.0",
    "answer": "7",
    "representation": {}
  },
  "client_elapsed_ms": 5000,
  "used_hint_levels": [1]
}
```

后端内部如何把任务识别为 standard/transfer/retention，不要求前端传入。

## 3. next_action 不扩成 Mastery 内部状态

儿童端现有枚举继续保留：

```text
RETRY
HINT
TEACH
COMPLETE
NEXT_TASK
```

以下内容属于后端调度原因，不新增为 Child UI State：

```text
collect_transfer
collect_retention
review_required
stability_missing
```

后端根据原因选好下一题后，前端仍收到 `NEXT_TASK`。

## 4. AbilityState Canonical Contract

```json
{
  "ability_id": "app_check",
  "name": "检查验算",
  "level": 2,
  "confidence": 0.58,
  "fit_band": {"min": 1, "max": 2},
  "evidence_count": 5,
  "trend": "down_review"
}
```

允许 trend：

```text
up
stable
watch
down_review
```

儿童端显示：

| Backend trend | Child UI |
|---|---|
| up | 有进步 |
| stable | 很稳定 |
| watch | 继续积累 |
| down_review | 正在巩固 |

前端不得显示“复核、降级、Mastery、Transfer不足”等内部术语。

## 5. SessionResult ability_changes

后端推荐 canonical：

```json
{
  "ability_changes": [
    {
      "ability_id": "app_rel",
      "name": "数量关系",
      "before_level": 1,
      "after_level": 2,
      "confidence": 0.79,
      "trend": "up",
      "evidence_delta": 3
    },
    {
      "ability_id": "app_check",
      "name": "检查验算",
      "before_level": 2,
      "after_level": 2,
      "confidence": 0.58,
      "trend": "down_review",
      "evidence_delta": 1
    }
  ]
}
```

最新前端已经遍历全部 `ability_changes`，不再只显示第一项。

迁移期 Normalizer 支持：

```text
old_level -> before_level
new_level -> after_level
```

如果临时拿到 MasteryDecision 风格数据且没有 `trend`：

```text
upgraded                         -> up
unchanged                        -> stable
candidate_upgrade/collect_evidence/recovering -> watch
review_required/downgraded_after_review       -> down_review
```

这只是前端过渡兼容，长期仍建议 SessionResult 输出 canonical trend。

## 6. 真正降级的展示

只有后端 `level` 实际下降时，Growth Map 才更新等级。

`trend=down_review` 但 `level` 不变时：

```text
L3 · 正在巩固
```

前端不得自行显示 L2，也不得自行推断降级。

如果后端确认 `L3→L2`，结果页显示当前 `L2`，不对儿童使用“降级”措辞。

## 7. MasteryDecision

`POST /v1/mastery/evaluate` 可继续存在，但 Child Web 不主动调用。

建议用于：

- Learning Engine内部；
- Admin/QA；
- 规则回放；
- 未来家长证据详情。

Child Web 的稳定依赖面应保持为：

```text
AbilityState
TaskInstance
AttemptResult
HintResponse
SessionResult
```

## 8. 错误码边界

教育诊断 E01~E07：HTTP 200业务载荷，不作为系统错误。

系统错误继续使用 LE-/AG- 命名空间。

Mastery reason code 也不是 HTTP error code，不直接展示给儿童。

## 9. 前端本次已改

- 新增 `src/lib/presentation/abilityStatus.ts`；
- `AbilityGrowthCard` 使用儿童文案；
- `AbilityMap` 将 `down_review` 显示为“正在巩固”；
- `MathResultScreen` 展示全部 ability_changes；
- `sessionResultNormalizer` 兼容 old/new level 和 decision fallback；
- Mock 增加 up/stable/down_review 三态；
- `check-v13.mjs` 增加 FE-1310 / QA-1311 静态边界检查。

## 10. 联调验收矩阵

| 场景 | Backend | Frontend预期 |
|---|---|---|
| L1→L2 | after_level=2, trend=up | 显示 L1→L2 + 有进步 |
| 保持 | level不变, stable | 显示当前L + 很稳定 |
| 缺Transfer | 后端调度transfer题 | 前端只 NEXT_TASK，不显示内部原因 |
| review | level不变, down_review | 显示当前L + 正在巩固 |
| confirmed downgrade | level真实下降 | Growth Map 更新新L；不显示“降级” |
| 多能力Session | ability_changes>1 | 全部渲染 |
| SessionResult失败 | API失败 | 本地snapshot仅兜底，不计算Mastery |

## 11. 联调时必须确认

1. SessionResult endpoint 的真实路径写入权威 OpenAPI；
2. `ability_changes.before_level` 的数据来源明确；
3. evidence_delta 按能力统计，不要把整个 Session 总 evidence_count 填给每个能力；
4. `down_review` 与真正 `level` 降级严格分离；
5. Curriculum 的 transfer/review/retention 调度对 Child Web 保持透明；
6. 后端完成 R-MASTERY-CLOSURE 后再关闭 DRIFT-002。
