# QA 钉题非确定性——结构性隐患与修复方案（2026-10-07 发现）

## 现象

九套 Vertical Gate 的 E2E spec 全靠 `buildTaskPool` 循环抽题直到命中目标 renderer
（ability_id + 25×18 次尝试）。今天（R09 收口）全量回归大面积超时：
**app_cond 的 QA band 不再命中 V2 竖式（只回 V1:number）**，B5 spec 起不来。

## 根因

1. **fitband 是自适应的**：`_published_resource_for_ability` 先取 fit_band 内 created_at
   最旧的 assignable 资源。QA child 每轮 E2E 都会写 attempt → mastery 引擎推 level →
   band 漂移。**今天之前 band=1~1 恰好覆盖 V2 d1/d2 金题（运气）**。
2. **band 被 E2E 自污染**：app_rel evidence 274 条、app_cond level 漂移——E2E 跑
   几百次后 band 早已不可预测（今天曾一度漂到 (4,5) 让 V2 d4 落带、又漂走）。
3. 昨天 R09 专项 11/11 是**新 QA band 状态下侥幸命中**；全量重跑必炸。
4. 数据层无 V1 app_cond d4 题、V2 d1 题在 band 3~4 时又被 created 顺序压在 V1 后面——
   **抽题成功与否 = f(band 历史轨迹)，完全不可复现**。

## 修复方案（推荐 A）

**A. QA 确定性钉题（后端小改，向后兼容）**：
1. 新只读端点 `GET /v1/content/v2-catalog`：返回 published 且 `_v2_assignable` 通过的
   V2 资源（resource_version_id / ability_id / renderer / title），供 spec 开机查目录；
2. `tasks/next` 加可选 body 参数 `pin_resource_version_id`（**仅限 QA child …0099**，
   服务端硬校验 child_id 非 QA 则 403）：存在且 V2-assignable → 直接落 task_instance，
   绕过 band/排除；
3. 全部 Gate spec 的 buildTaskPool 改为：查目录 → 取对应 RV → 新 session + pin（每
   task_instance 仍需独立 session/pin 组合拿独立 tid，语义不变、确定性 100%）；
4. QA child ability_state **重置脚本**（scripts/qa_child_setup.py 扩展 `--reset-bands`）：
   钉题 spec 首跑前把 QA band 统一回 (1,1)——目录 pin 路径不再依赖 band，但
   mastery 引擎回归测试（qa_replay）仍需干净起点。

**B. 数据面缓解（不解决根因）**：给 QA child 手工把各能力 band 设成覆盖各 Gate 金题
难度——**会再次漂移，禁止作为正式方案**（今天已临时做过一次恢复 (1,1)，仅应急）。

## 验收标准（方案 A）

- 全量 E2E **连续 2 次全绿**（今天这种 band 漂移下仍绿）；
- 生产路径零影响：pin 参数缺省时行为与现状比特级一致；真实 child 调 pin → 403；
- catalog 端点纳入 openapi.yaml + 契约测试。

## 现状数据备忘（2026-10-07 15:40）

- V2 published 11 题：app_cond×1(d4 竖式)/app_rd×1(d2)/app_rel×6/app_model×2/app_strat×2；
- QA 池当前被我临时设为 app_cond level4/conf0.2、app_rel level2/conf0.5（band 4/2-3）
  ——**方案 A 落地后此配置作废**，恢复 qa_child_setup.py 默认；
- R09 代码侧全绿（专项 11/11、后端 89、tsc/checks 全过），仅收口被此坑挡住。

## 落地记录（FE-1422a，2026-10-07 16:35）

方案 A 已实施，验收标准逐条对照：

| 验收项 | 结果 |
|---|---|
| 全量 E2E 连续 2 次全绿 | ✅ 第一轮 83/83（3.1m）+ 第二轮（band 已重置回 (1,1) 的"漂移前科"态） |
| pin 缺省时行为比特级一致 | ✅ 路由 `pin=None` → 原路径不动；契约测试 test_no_pin_never_403 |
| 真实 child 调 pin → 403 | ✅ API 实测 + 契约测试（路由层短路，不触库） |
| catalog 纳入 openapi.yaml | ✅ /v1/content/v2-catalog + tasks/next pin 参数与 403 响应均已入 spec |
| catalog 契约测试 | ✅ tests/test_qa_pin.py（路由守卫/判定函数/端点注册 6 用例，后端 89→94 passed） |

实现口径：
- `app/core/qa.py`：QA_CHILD_ID + is_qa_child（str/UUID/脏值容忍）；
- `list_v2_catalog`：schema_version 过滤在应用层（ui_schema 是通用 JSON 列，
  避免 PG 方言表达式；与 _v2_assignable 同门控，保证"目录可查=pin 可落"）；
- pin 路径落题时 strategy_policy 带 `"pinned": true` 标记（证据可审计，回放时可识别测试钉题流量）；
- `scripts/qa_child_setup.py --reset-bands`：7 能力回 level0/conf0/band(1,1)。

E2E 侧：9 个 spec 的旧 buildTaskPool/fetchTasks 全部替换为共享模块
`e2e/pinned-tasks.mjs`（catalog 模块级缓存 + 每 task 独立 session+pin）；
R10 双金题按 `renderer#mode` 键定位（catalog 增加 mode 字段）。
