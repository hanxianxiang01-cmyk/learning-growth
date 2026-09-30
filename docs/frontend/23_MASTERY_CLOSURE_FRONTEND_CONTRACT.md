# 23｜V1.3 Mastery Closure 前端契约

## 边界

前端只负责：
- 提交 Attempt / Structured Response；
- 消费 `next_action`；
- 展示 `AbilityState` 与 `SessionResult`；
- 把后端趋势转换成儿童可理解文案。

前端禁止：
- 计算四维 Mastery；
- 判断升级/降级；
- 自己决定 transfer / retention / review 任务；
- 把 E01~E07 或 Mastery reason_code 直接展示给儿童。

## AbilityState UI

| trend | 儿童文案 |
|---|---|
| up | 有进步 |
| stable | 很稳定 |
| watch | 继续积累 |
| down_review | 正在巩固 |

`down_review` 只改变状态文案；后端 level 没变化时前端不得自行降低等级。

## Session Result

结果页必须遍历 `ability_changes[]`，一个 Session 涉及多能力时全部展示。

前端 normalizer 支持过渡别名：
- `old_level` -> `before_level`
- `new_level` -> `after_level`
- `decision=review_required/downgraded_after_review` -> `trend=down_review`
- `decision=collect_evidence/candidate_upgrade/recovering` -> `trend=watch`

## Curriculum

Mastery 缺证据、Retention、Transfer 与 Review 是 Curriculum Engine 的调度原因，不进入儿童前端状态机。

儿童端继续只接：
- RETRY
- HINT
- TEACH
- COMPLETE
- NEXT_TASK
