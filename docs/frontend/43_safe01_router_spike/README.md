# SAFE-01 & Renderer Implementation Router 技术验证交接

## 总状态

- `SAFE01_AUDIT.md`：**原始 Spike 快照**。发现条件性出站 `expected_answer`；候选出站净化验证通过；生产前仍需处理跨部署幂等、已发布资源和真实DB。其 BLOCKED 定级已被终查更新，**最终裁决以 `SAFE01_FINAL_VERDICT.md` 为准**。
- `SAFE01_FINAL_VERDICT.md`：**审计收官（2026-10-13 批复）**——真实库终查（175 题双键零命中/1879 条历史全量 NOT_EVALUATED，Evidence 共 7 份）、定级 P2、409 兼容面澄清、Router 设计前置通过/运行验收待完成、执行顺序四步定版。
- `ROUTER_SPIKE.md`：R04单Renderer双实现路由，19项纯函数策略测试通过；默认旧版，真机/Next构建/后端全链路未执行。
- 原始用户ZIP只有443个文件，与V6 529文件的仓库分支不同：**禁止把这两个包不经对照直接合并**。

## 本地执行

```sh
node tests/spikes/safe01-envelope-audit.cjs
node tests/spikes/implementation-policy.test.cjs
python tests/spikes/safe01-backend-judge.py
# 跨版本包体兼容测试，需要指向未修改的原始ZIP解压树
BASELINE_REPO=/path/to/original/learning-growth-main node tests/spikes/safe01-cross-version-idempotency.cjs
```

前端依赖安装成功后，在隔离QA环境启用：

```sh
NEXT_PUBLIC_MIK_RENDERER_FLAGS=number-input=kernel npm run child:dev
```

此配置为构建/运行环境变量，只有R04 pilot可用。UI版本仍为用户上传的最新仓库版本，**不包含此前V6全量视觉资产**。

## 合入前门禁

1. SAFE01跨部署幂等、生产配置真实核查与DB回归；
2. React18/Next14锁定依赖 `npm ci` + 全量Typecheck/Build；
3. QA真实TaskInstance恢复验证和双版本路由端到端；
4. 真实Judge/Evidence闭环、无事件词表漂移、Legacy回退。

**结论：可用于技术复审和继续研发，当前不是生产可发布版本。**
