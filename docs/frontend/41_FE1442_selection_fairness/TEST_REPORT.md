# FE-1442 测试报告（SEL 矩阵 + 回归）

## SEL 矩阵（真实 RDS，QA child …0099，18:1x）

**12/12 通过**（脚本 `scripts/qa_selection_fairness_e2e.py`，可复跑）：

| SEL | 结果 | 关键数据 |
|---|---|---|
| 01/02 公平覆盖 | ✅ | app_cond 18 session：唯一=9/9、**counts 全=2（max-min=0）** |
| 03 同 session 不重复 | ✅ | 3 连各异 |
| 04 带内耗尽不跨带 | ✅ | app_rd band8 第 9 次=`SESSION_POOL_EXHAUSTED`（**首跑 FAIL 抓出实现 bug：band_pool_all 误带 exclude——修复后过**） |
| 06/14 发布门禁 | ✅ | 全程 31 selected 无一非 published（qa_retired 25+候选 3108 零混入） |
| 07① 带内 100%+溯源 | ✅ | selection_policy=v1.4-fe1442 全落 strategy_policy |
| 07② 重复≠跨带 | ✅ | 带内 P2（RECENT_FALLBACK）不触发兜底 |
| 07③ BAND_FALLBACK | ✅ | app_transfer：band_fallback+TARGET_BAND_EMPTY+requested[1,2]/selected 3 记因 |
| 07④ Mastery 真难度 | ✅ | assigned_difficulty=真实资源难度（D2 请求兜底 D3=按 D3 入账） |
| 11 Pin 零触碰 | ✅ | pin task policy 无 selection 字段；qa_replay 8/8 |
| 12 历史口径 | ✅ | HISTORY_PARTIAL 快照入报告（app_rel 22605 条 V1 历史计入"下发覆盖"非"阅读"） |
| 13 小池不死循环 | ✅ | app_rd×10 次 uniq=3 轮转 |
| 15 回滚 | ✅ | 无 schema 依赖，revert PR 即还原 |
| 08/09/10 | NOT RUN | 裁决裁剪在案（无调度契约/无服务端幂等字段/单真实 child 无并发；**不宣称跨设备并发安全**） |

## 生产账号实证（真实 child …0001，只读 dry-run + 实练）

- dry-run 预测 10 次：9 T155+1 金题全 `UNSEEN_PRIORITY`
- 18:23 实练三连（真 task_instance）：`还剩几只鸟`（未见金题）、`[T155] P0-056`、`[T155] P0-076`——旧题常胜症状消失，判分 True×3

## 回归矩阵

- 后端：**111 passed**（+6：公平性纯函数 5 + 源码锁；SEL-04 bug 修复后复跑）
- Gate 8 qa_replay：**8/8**（SEL 写库后复跑）
- UI 全量 E2E：196/197 → r02-bar-model 定点重跑 **9/9**（全量轮那次=用户同库实练的 session 排除时序噪声，非回归）
