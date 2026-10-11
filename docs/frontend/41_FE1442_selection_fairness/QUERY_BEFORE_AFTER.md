# FE-1442 Before/After 查询与 Trace

## Before（头名常胜，L152 旧代码在 git 历史 d0c172c）

```sql
-- _published_resource_for_ability：带内
SELECT resource_version.* FROM resource_version JOIN resource ...
WHERE ability_id=:a AND review_status='published' AND difficulty BETWEEN :bmin AND :bmax
  AND resource_version_id NOT IN (:session_excluded)
ORDER BY difficulty ASC, created_at ASC LIMIT 50   -- 应用层取第一条可下发
```
同难度带内 `created_at ASC` → 最早 seed 的 V1 金题永远第一 → 新入库 155 题（created_at=2026-10-10）永不出头。
真实 trace：child …0001 最近 10 次全部命中 V1 金题（`原来有多少`/`哪两个条件要用`…），app_cond diff1 带内 T155=8 金题=1 却零命中。

## After（v1.4-fe1442）

候选查询只拉带内全量（≤200 行，limit 防大池），**分层与决胜全在应用层**（`_pick_fair` 纯函数）：

```
history = task_instance 聚合(child×ability×rvid) → {count, last_at}
recent_ids = last_at 降序前 20
P0 unseen → P1 not_recent → P2 all（RECENT_FALLBACK）
层内 key = (count asc, last_at asc, sha256(child|rvid|salt))
```

## SEL 矩阵真实 RDS Trace（2026-10-10 18:1x，QA child …0099）

| SEL | 场景 | Trace 摘要 | 结果 |
|---|---|---|---|
| 01/02 | app_cond 18 session | 唯一=9/9，counts 全=2（max-min=0） | ✅ 旧头名消失 |
| 03 | 单 session 3 连 app_rel | 3 题各异 | ✅ |
| 04 | app_rd band(1,1) 带内 8 题第 9 次 | `reason=SESSION_POOL_EXHAUSTED`（不跨带） | ✅ |
| 06/14 | 全程 31 次 selected | published 违例=0（qa_retired 25/candidate 3108 不混入） | ✅ |
| 07①② | app_cond 18 次 policy | selection_policy=v1.4-fe1442、reason∈{UNSEEN_PRIORITY,LOW_EXPOSURE,RECENT_FALLBACK}、band_fallback 无 | ✅ |
| 07③ | app_transfer band(1,2) 池最低=3 | `band_fallback=true, fallback_reason=TARGET_BAND_EMPTY, requested_band=[1,2], selected_difficulty=3` | ✅ 显式 |
| 07④ | 同上真实难度 | assigned_difficulty=3=资源难度（非请求带） | ✅ Mastery 真计分 |
| 11 | pin 金题 | policy={pinned:true}、无 selection 字段 | ✅ 确定性零触碰 |
| 12 | 起始快照 | app_rel 22605…HISTORY_PARTIAL 申明 | ✅ 口径入册 |
| 13 | app_rd 小池 10 次 | 10 全出、uniq=3（池即 3）轮转不死循环 | ✅ |
| 15 | 回滚 | 无 schema 依赖：git revert 本 PR 即还原旧排序 | ✅ 代码级 |
| 08 | SCHEDULED_REPEAT | **NOT RUN**（上游无指定原题调度契约，裁决裁剪） | — |
| 09 | request_id 幂等 | **NOT RUN**（本轮无服务端幂等字段；前端防重入锁=单客户端验证，不宣称跨设备） | — |
| 10 | 并发串行化 | **NOT RUN**（单真实 child，保留 _pick_fair 扩展点） | — |

回归配套：后端 111 passed（+5 公平性单测含源码锁：无 random()/created_at 头名/order_by 残留断言）；Gate 8 8/8；UI E2E 见 TEST_REPORT。
