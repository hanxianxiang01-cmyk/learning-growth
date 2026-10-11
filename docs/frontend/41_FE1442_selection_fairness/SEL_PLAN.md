# FE-1442 生产选题公平性测试（SEL 矩阵）

- [ ] SEL-01 9 题池跨 9 session 9/9 唯一（QA child app_cond 带内夹具）
- [ ] SEL-02 18 次每资源各 2
- [ ] SEL-03 同 session 3 次不重复
- [ ] SEL-04 单候选 session 第二题=SESSION_POOL_EXHAUSTED（不跨带）
- [ ] SEL-05 跨 session 小池允许重复+回退原因
- [ ] SEL-06 qa_retired/candidate 不混入
- [ ] SEL-07 四场景：带内 100%/带内 P2 不触发兜底/带空 BAND_FALLBACK 记因/真实难度计分
- [ ] SEL-08 SCHEDULED_REPEAT — NOT RUN（上游无指定原题调度契约，裁决在案）
- [ ] SEL-09 request_id 幂等 — NOT RUN（本轮裁剪：无服务端幂等字段，防重入锁仅单客户端验证，不宣称跨设备安全）
- [ ] SEL-10 并发串行化 — NOT RUN（裁决裁剪：单真实 child 无并发流量，保留扩展点）
- [ ] SEL-11 Pin/qa_replay 确定性回归
- [ ] SEL-12 历史回填口径（HISTORY_PARTIAL 申明）
- [ ] SEL-13 P2 RECENT_FALLBACK 不死循环
- [ ] SEL-14 取消发布排除（qa_retired 即活体样本）
- [ ] SEL-15 回滚演练（代码级还原说明）

## 工具
- `apps/learning-api/tests/test_selection_fairness.py`：_pick_fair 纯函数单测 + 源码锁（reason 枚举/版本/无 random）
- `apps/learning-api/scripts/qa_selection_fairness_e2e.py`：真实 RDS SEL-01~07/13/14（QA child 夹具历史清场后跑）
