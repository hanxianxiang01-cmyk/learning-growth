# 《V1.4 Renderer Completed Pack》消费索引（32 号交付）

交付物：`learning-growth-V1.4-renderer-completed.zip`（315 文件全仓快照，原件保留在 `~/Downloads/学习/儿童学习成长系统/`，**不入仓**——见下）+ `V1.4_RENDERER_DEVELOPMENT_COMPLETED.md`（已存档本目录）

> **zip 不入仓的原因（重要）**：该快照内 `scripts/qa_replay_mastery.py` 携带 RDS 明文密码（FE-1412 已根治的回退版本）。存仓=把凭据重新写入 git 历史，与「密码暂不轮换」决定（前提是新增内容干净）直接冲突，也会被 `check-data-hygiene` 的 R2 规则拦截。原件以 Downloads 本地为准。
交付主张：按 docs/frontend/31 的 Step 1–10 **实际改代码**（非方案）——Runtime/State/Event/Evidence Contract、Evaluator Registry、Response/Diagnosis 边界、submission_id 幂等、19 Renderer 纳入验收、VG-01~05 框架、QA 页升级、Contract/Release QA 脚本。自称 Contract QA 全绿 19/19，但**未跑 next build 与 Playwright E2E**（环境无 node_modules，如实声明）。

## 1. 基线判定（关键）

对每个重叠文件做三方 diff（我们 base 候选 × 交付 × 当前 main），锁定**交付工作基线 = main@83a0e94（FE-1411 热修）**，即 FE-1412/1413/1414/1415/1416 全部不在其视野内。因此：

| 交付快照内容 | 与当前 main 关系 | 处置 |
|---|---|---|
| qa_replay_mastery.py | **回退**：硬编码 RDS 密码 + 真实 child …0001 | ❌ 拒绝（保留我们 FE-1412 的 env 注入 + QA child 版） |
| integration-smoke.mts / b5 e2e spec | **回退**：真实 child …0001 | ❌ 拒绝（保留 …0099 分池版） |
| CHANGELOG/PROJECT_STATUS/治理文档 | 缺 FE-1412~1416 六条 Done | ❌ 拒绝（保留我们的） |
| ObjectCounter/NumberInput/TenFrame 专件与 spec | 缺失（其基线没有 R01/R04/R07） | ❌ 拒绝覆盖（保留我们的专件） |
| docs/frontend/31、hygiene 脚本、审计 CSV | 缺失 | ❌ 拒绝（保留我们的） |
| rendererContract/evaluatorRegistry/diagnosisAdapter/nextTaskAdapter | **纯新增**，我们无对应实现 | ✅ 采纳（框架层核心增量） |
| V2_RELEASE_RENDERER_IDS（19 口径） | 纯新增 | ✅ 采纳（此前只在 README 文档层，未入代码） |
| contracts.ts 事件枚举 | 新增 UPPER_SNAKE 一批 | ✅ 选择性采纳（**剔除其混入的 13 个状态名**——READY/INTERACTING 等属状态机枚举，不是事件） |
| InteractionEvent 元数据字段（session/attempt/sequence_no） | 纯新增 | ✅ 采纳 |
| stable submission_id 幂等 | **意图正确，实现有致命缺陷** | ✅ 采纳意图，⚠️ 重写实现 |
| QA 页 VG/Release 看板 | 纯新增展示层 | ✅ 采纳 |
| check-v14-contracts/release.mjs 脚本 | 纯新增 | ✅ 采纳（断言按实际采纳边界修正） |
| V2RendererLibrary 基座改写 | evidence 注入方式改变 | ❌ 拒绝（见 §2 缺陷） |

## 2. 交付方未自测出的两个真实缺陷（我们集成时修掉）

**缺陷 A（致命，会导致所有 V2 提交 404）**：
`v2AttemptAdapter` 的 stable submission_id 用 `` `${task}:${attempt}:${revision}` `` **冒号串**——而后端 `learning.py` 执行 `uuid.UUID(str(sub_raw))`，非 UUID 串抛 ValueError→404。交付环境无 node_modules、从未跑 E2E/真实后端，其 `check-v14-contracts.mjs` 只 grep 源码文本 `request.submission_id ??`，自然"通过"。
→ 修正：对派生材料做确定性哈希，输出严格 `8-4-4-4-12` hex 的 UUID 形状；同 (task,attempt,revision) 恒定（命中幂等权威轨），attempt_no 变化则 ID 变化（重试不误重放）。

**缺陷 B（Evidence.attempt_no 恒=1）**：
交付把 evidence/evaluation 注入放在 TaskRenderer 的 `handleResponseChange`（**交互更新时刻**），该处 `createRendererRuntimeState(..., 1)` attempt_no 写死 1，且每次 change 重建 runtime——attempt 序号与真实提交脱节。
→ 修正：注入点移到 **v2AttemptAdapter 提交时刻**，`attempt_no` 取 `request.attempt_no`（真实递增值），一次提交产出一份 evidence。rendererContract 模块本体原样采纳。

**缺陷 C（事件枚举污染）**：交付 `InteractionEventType` 混入 `READY/INTERACTING/VALIDATING/…` 等 **状态名**（那是 RENDERER_STATES，不是事件）。
→ 剔除，加注释划清边界。

## 3. "19/19" 与真实完成度的差距（诚实口径）

交付的 19/19 是 **Contract/静态脚本** 层面（结构齐备），不等于 **Vertical Gate** 层面。按 docs/frontend/31 的 114 Checkpoints 与我们的 E2E 实证标准：
- 真正打过浏览器 E2E Vertical Gate 的仍是 **5 个**：NumberLine(A5)/ColumnArithmetic(B5)/ObjectCounter(R01)/NumberInput(R04)/TenFrame(R07)；
- 其余 14 个（bar-model/place-value/array-board/…/pattern-board）交付补的是**框架契约**（有 state/event/evaluator 抽象），但**尚无链题、无组件语义 Evaluator、无 E2E**——属"契约就绪，语义待完成"，与 FE-1409 当初的诚实口径一致。

## 4. 有效增量（采纳后价值）

1. **框架底座补齐**：rendererContract（13 态状态机 + canTransition + 语义事件工厂 + evidence builder）/ evaluatorRegistry（23 evaluator 表，generic 弱判 NOT_EVALUATED 不猜）/ diagnosisAdapter + nextTaskAdapter（后端权威边界，前端只打包不判定）——这层是 114 Checkpoints 复用的地基，此前我们没有统一实现。
2. **stable submission_id**：把"重放保护"从依赖前端单次点击（crypto.randomUUID 每次不同，双击才靠 disabled 兜底）升级为**服务端幂等权威轨**（同 attempt 重试命中同 ID）——正确方向，缺陷 A 修掉后即可用。
3. **19 Release Scope 入代码**（V2_RELEASE_RENDERER_IDS）：把发布验收口径从文档固化到类型。
4. **QA 页 VG 看板**：/dev/v1.4-qa 可视化 Release Scope + 五条 VG 状态。

## 5. 消费动作与验证

- 采纳 = 4 新模块 + registry/QA-page/globals/package.json 增量 + contracts 事件枚举（清洗后）+ adapter stable submission_id（重写）+ 2 check 脚本（断言适配）；存档本 README + 完成度报告原件（zip 因含明文凭据不入仓）。
- **不采纳** = 全部测试脚本与治理文档的回退、基座库改写、其 CHANGELOG/PROJECT_STATUS。
- 验证：tsc 0 / check-v14{,-renderers,-contracts,-release} 全 PASS / 全量 Playwright E2E 35 例（B5+R01+R04+R07+healing 双皮肤）零回归——见提交记录。
- 下一步：14 个"契约就绪"组件按 B5 模板（renderer-vertical-gate skill）逐个补链题+语义 Evaluator+E2E 打 Vertical Gate。
