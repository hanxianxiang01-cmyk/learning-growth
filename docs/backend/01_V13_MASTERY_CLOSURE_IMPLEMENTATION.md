# V1.3 Mastery Decision Loop 后端闭环实施指导

## 1. 目的

本文件用于把 `learning-core-v1.3.1` 已冻结的 Mastery 设计真正落到运行代码，并关闭当前实现漂移。

目标链路：

```text
ResourceVersion
→ TaskInstance
→ Attempt × N
→ 1条有效 Atomic Mastery Evidence / Task
→ C / I / Stability / Transfer
→ MasteryDecision
→ AbilityState
→ FitBand / Curriculum
→ 下一题（standard / transfer / retention / review）
```

## 2. 当前权威基线

以以下内容为准：

1. `baselines/learning-core-v1.3.1/01_schema_postgresql_v1.3.1.sql`
2. `baselines/learning-core-v1.3.1/02_openapi_v1.3.1.yaml`
3. `app/core/education_rules.py`
4. `apps/learning-api/app/services/mastery.py`
5. `apps/learning-api/app/services/turn_service.py`
6. `apps/learning-api/app/services/fitband.py`
7. `apps/learning-api/app/services/curriculum.py`

当前已发现 DRIFT-002：冻结规则已定义四维窗口与升级 Gate，但运行实现未完整接线。

## 3. 当前代码偏差

| 编号 | 当前实现 | 问题 |
|---|---|---|
| B1 | `_decide(level=1)` 无条件返回 L2 | L1→L2 是空壳 |
| B2 | `record_attempt` 固定写 `attempt_standard` | 永远没有 `attempt_transfer` |
| B3 | 每次 Attempt 都写一条 MasteryEvidence | 同一 Task 重试会重复污染窗口 |
| B4 | transfer 证据不足返回 `0.0` | 无证据与真实失败混为一谈 |
| B5 | `mastery_db` 未加载 resource/session 多样性 | 冻结的窗口覆盖条件未执行 |
| B6 | Stability/Transfer 在内存计算，未写派生 evidence | 与冻结 DDL 注释不一致 |
| B7 | L3→L4 只检查 T≥0.80 | 未检查3条迁移/3 context/node gate |
| B8 | `fitband.next_task_recommendation(need_review=True)` 未接 Curriculum | review 分支是死路 |

## 4. V1.3 收口边界

### 必须完成

- 修复 L1→L2 Gate；
- 接通 standard / transfer / retention evidence role；
- 一个 `task_instance` 最多保留一条有效 Mastery 原子证据；
- 缺证据使用 `NULL/insufficient` 语义；
- 执行 C/I/S/T 的窗口数量与多样性约束；
- 生成 stability_window / transfer_window 派生证据；
- L2→L3、L3→L4 可真实到达；
- review_required 能驱动 Curriculum 选 review/retention 任务；
- 规则回放覆盖 L0→L4、review、recovery/downgrade。

### 不在 V1.3 扩张

- 不引入 BKT/IRT/复杂遗忘模型；
- 不重调 0.35/0.25/0.20/0.20；
- 不为未来49节点写硬编码 if/else；
- 不要求儿童端理解 Mastery reason code；
- 不做复杂 transfer distance 算法。

## 5. Evidence Role：不新增 DDL 的最小方案

V1.3 优先复用 `resource_version.mastery_rule jsonb` 与已有 `transfer_distance` 字段。

建议 `mastery_rule`：

```json
{
  "evidence_role": "standard",
  "context_family": "school_objects",
  "representation_family": "bar_model"
}
```

`evidence_role` 允许：

```text
standard
transfer
retention
explanation
```

映射：

| evidence_role | mastery_evidence.evidence_type |
|---|---|
| standard | attempt_standard |
| transfer | attempt_transfer |
| retention | retention_check |
| explanation | explanation |

未配置时默认 `standard`，保证已有资源兼容。

注意：`app_transfer` 是一个能力节点；`transfer` 是每个 ability 自己的证据维度，二者禁止等同。

## 6. Task Outcome：一个 Task 只贡献一条有效原子证据

Raw Attempt 全部保留，用于诊断/行为分析。

Mastery 侧规则：

```text
同一 task_instance
→ 可以有多个 Attempt
→ 任何时刻最多1条 valid=true 的原子 MasteryEvidence
```

建议实现：

1. 每次新 Attempt 后读取该 task 全部 Attempt；
2. 计算当前 Task Outcome：
   - correctness：当前最终结果；
   - max_hint_level：该 task 迄今最大提示级；
   - independence：按冻结映射；
3. 将该 task 旧原子 evidence 标 `valid=false`；
4. 写一条新的有效 evidence，指向最新 Attempt；
5. 再触发 `persist_mastery_state()`。

这样“错→Hint→再错→最终对”只形成1条最终有效证据，而不是3条。

## 7. Evidence Coverage 与 NULL 语义

### Correctness / Independence

最近8条有效可评分原子证据，并要求：

```text
>=3 distinct resource_version_id
>=2 distinct learning_session
```

不满足覆盖条件：该维度用于升级时视为 `insufficient`，不得假装已充分测量。

### Stability

最近5条 `attempt_standard/retention_check`，要求：

```text
>=3 resource_version
>=2 session
```

每条：

```text
source_quality = correctness × independence
```

满足覆盖后：

```text
stability = mean(source_quality)
```

并写 `stability_window`，保存 `source_evidence_ids` + `rule_version`。

### Transfer

最近最多4条 `attempt_transfer`，至少2条，并要求：

```text
>=2 context_family
>=2 session
```

不足：

```text
transfer = NULL
coverage.transfer = insufficient
```

不是 `0.0`。

满足后写 `transfer_window`。

## 8. L0-L4 Gate

### L0→L1

V1.3 继续遵守冻结基线：首次有效教学/诊断证据可进入 L1。

### L1→L2

冻结文本只定义“Hint≤2 支持下稳定完成”，运行代码必须补成可执行规则。

V1.3 默认建议：

```text
eligible standard/retention >= 5
resource_version >= 3
session >= 2
Correctness >= 0.80
Independence >= 0.50
Stability >= 0.50
Transfer 不要求
```

这些阈值是 V1.3 工程默认值，不是不可修改的科学常数；必须由新的 `rule_version` 固化，后续只能通过新版本校准。

### L2→L3

保留冻结 Gate：

```text
MasteryScore >= 0.80
C >= 0.80
I >= 0.75
S >= 0.75
T >= 0.60
```

任何 required dimension coverage 不足 → `collect_evidence`，不能重归一化。

### L3→L4

必须全部满足：

```text
T >= 0.80
transfer atomic evidence >= 3
context_family >= 3
node-specific validation gate = true
```

V1.3 应先为应用题7节点提供最小 node policy；未来能力树节点通过 `ability_node.level_schema` 配置，禁止写49套 if/else。

## 9. MasteryDecision 最小输出

建议内部 Decision：

```text
upgraded
unchanged
collect_evidence
review_required
recovering
downgraded_after_review
```

推荐结构：

```json
{
  "ability_id": "app_rel",
  "old_level": 2,
  "new_level": 2,
  "decision": "collect_evidence",
  "missing_evidence": ["transfer"],
  "reason_codes": ["transfer_coverage_insufficient"],
  "dimensions": {
    "correctness": 0.88,
    "independence": 0.81,
    "stability": 0.79,
    "transfer": null
  },
  "rule_version": "mastery-v1.3.x"
}
```

前端不需要完整消费这个对象；主要由 Curriculum/调试/审计使用。

## 10. Review / Downgrade 最小闭环

原则：单次失败不降级。

推荐最小流程：

```text
当前Level保持
→ trend=down_review
→ Curriculum安排validation/retention任务
→ 收集后续验证证据
→ 通过：trend恢复 stable/recovering，Level不变
→ 连续验证失败：最多下降1级
```

V1.3 默认 review trigger 可配置，建议保守：

- 至少2次跨 Session 的 retention/validation 失败；或
- 最近3条标准/保持证据质量明显低于当前等级底线。

具体阈值必须进入 rule config，不散落服务代码。

降级后至少收集新的 post-transition evidence 后才能再次升级，避免 L2↔L3 抖动。

## 11. Curriculum 接线

当前 `fitband.next_task_recommendation()` 已有 `need_review` 参数，但 `curriculum.py` 没使用。

V1.3 应加入 evidence need：

```text
review_required      -> retention/review role，优先难度带下沿
missing transfer     -> transfer role，仍在能力有效难度区间
missing stability    -> standard/retention，要求跨Session/资源多样性
normal practice      -> standard
```

儿童端仍只收到普通 `NEXT_TASK`，不暴露内部调度原因。

## 12. Session Result 对接要求

推荐 `ability_changes[]` 输出：

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

`trend` 继续使用：

```text
up
stable
watch
down_review
```

儿童端已实现安全文案映射，不需要新增 UI 枚举。

## 13. 代码改造建议

| 文件 | 改造 |
|---|---|
| `core/education_rules.py` | 增加 L1→L2 可执行 Gate、review policy、rule version |
| `services/mastery.py` | Optional dimension + coverage + 完整状态机 |
| `services/mastery_db.py` | join Task/Resource/Session；窗口多样性；派生 evidence 持久化 |
| `services/turn_service.py` | evidence_role；单Task单有效证据；不固定 attempt_standard |
| `services/curriculum.py` | 按 missing evidence/review 选 role |
| `services/fitband.py` | 保持难度带职责，不承担 Mastery 计算 |
| `services/session_result.py` | before/after level + trend + evidence delta，禁止重新算 Mastery |
| `tests/test_mastery.py` | 补 L1→L2、insufficient、transfer coverage、L3→L4 |
| `tests/*` | 补 Review→Curriculum E2E |

## 14. 必测用例

1. L0→L1 首个有效证据；
2. L1 证据不足不能升 L2；
3. L1 满足跨资源/跨Session Gate 升 L2；
4. Transfer 只有1条 → NULL/insufficient；
5. 同一 Task 三次 Attempt → 仅1条 valid atomic evidence；
6. L2 满足 C/I/S 但缺 T → collect_evidence；
7. Curriculum 下一题为 transfer role；
8. 满足 T 后 L2→L3；
9. L3 T>=.8 但 context<3 → 不升 L4；
10. L3 满足全部 gate → L4；
11. 单次失败 Level不降；
12. review_required 后通过 validation 保级；
13. review_required 后验证失败最多降1级；
14. 降级后无新证据不能立刻回升。

## 15. Release Gate

`R-MASTERY-CLOSURE` 必须阻断 V1.3 发布，直到：

- L1→L2 不再无条件；
- attempt_transfer 可真实产生；
- transfer 缺证据不是0；
- 单Task单有效证据；
- Stability/Transfer window 可追溯；
- L2→L3 / L3→L4 可达；
- Review 能驱动 Curriculum；
- 上述规则回放全部通过。
