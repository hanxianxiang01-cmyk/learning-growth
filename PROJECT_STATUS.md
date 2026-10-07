# Project Status

> 这是项目当前状态的**唯一人工可读仪表盘**。  
> 任何工作开始/完成/阻塞时都应更新对应条目。

状态：

```text
⚪ TODO
🔵 IN PROGRESS
🟡 REVIEW
🟢 DONE
🔴 BLOCKED
```

## Stable Baseline

| Item | Version / State |
|---|---|
| Child Web | `1.2.0` |
| Frontend release | Learning Result Closure |
| Built-in skins | `healing`, `math-lab` |
| Default child skin | `math-lab` |
| Learning result source | Session Result API |
| Frozen learning-core baseline | `v1.3.1` |
| Mastery rule version (active) | `mastery-v1.3.1` |
| Governance | `1.0.0` |

## Current Completed Capabilities

| Area | Capability | Status |
|---|---|---|
| Child UI | Home / Learning / Result / Growth | 🟢 DONE |
| UI | 18 core components | 🟢 DONE |
| Skin | 2 built-in skins | 🟢 DONE |
| Learning | Session / Task / Attempt / Hint | 🟢 DONE |
| Learning | Result API frontend closure | 🟢 DONE |
| Runtime | Mock / HTTP adapters | 🟢 DONE |
| Governance | Git-ready repository structure | 🟢 DONE |
| Governance | PR / Issue / CI / Release templates | 🟢 DONE |
| Learning | Mastery L0→L4 全链路（evidence role / coverage / derived / review） | 🟢 DONE |
| Learning | 证据消化→能力升级闭环（persist AbilityState） | 🟢 DONE |

## Current Partial / Gaps

| Local ID | Area | Work | Status | Owner | PR |
|---|---|---|---|---|---|
| DRIFT-001 | Contract | Session Result API尚未写入冻结OpenAPI | 🟢 DONE | Backend/Contract | #21 |
| DRIFT-002 | Mastery | 运行实现 vs 冻结 v1.3.1 契约漂移（B1~B8） | 🟢 DONE | Backend | #15~#19 |
| FE-1311 | Mastery | Atomic Evidence Truth（L1→L2 Gate + evidence_role + 单Task单证据） | 🟢 DONE | Backend | #15 |
| FE-1312 | Mastery | Evidence Coverage（Optional 维度 + 多样性约束） | 🟢 DONE | Backend | #16 |
| FE-1313 | Mastery | Derived Evidence + L4 Gate | 🟢 DONE | Backend | #17 |
| FE-1314 | Mastery | Review 状态机 + Curriculum 选 role | 🟢 DONE | Backend | #18 |
| FE-1315 | Mastery | QA replay 14/14 → 激活 mastery-v1.3.1 | 🟢 DONE | Backend | #19 |
| P0-GOV-CF | V1.4 Governance | context_family 受控词表 + Seed 校验 + 50题回填 + Transfer 回归 | 🟢 DONE（AC-01~07；待裁决6题REVIEW） | Backend/Content | — |
| FE-1403 | V1.4 Protocol | Renderer Registry Contract：23 枚举冻结 + 校验 + V1/V2 分流规则 | 🟢 协议冻结（Registry 12 字段随交付填充；V2 JSON Schema 待冻结） | Backend/Frontend | — |
| FE-1403-B5 | V1.4 Renderer | B5 column-arithmetic 切片：State/Reducer/Serializer/Evaluator+组件+双皮肤；后端 implemented 翻转 | ✅ **Vertical Gate CLOSED**（Playwright 浏览器 E2E 10/10 PASS，G1~G9 全实证；见 B5_E2E_VERTICAL_GATE.md） | Frontend/Backend | #36~本轮 |
| FE-1404 | V1.4 Protocol | TaskUISchema V2 + MathResponse V2 可执行 Schema + 五链样例 + 校验器 | 🟡 冻结候选（待会签；待办7项见 docs/frontend/29 §5） | Backend/Content/Frontend | — |
| FE-1405 | V1.4 Vertical | A5 纵向链端到端：V2 题下发→渲染→提交→判分→幂等（真实 E2E PASS） | 🟢 DONE（首批 1 题；submission_id 迁移为后续项） | Backend/Frontend | — |
| FE-1406 | V1.4 Diagnosis | 诊断 V2：三段判定、无证据不猜、NULL 合法、confirmed 待校准（评审步骤3） | 🟢 DONE（匹配表保守缺省，正式标签字典待 ADR） | Backend/教学规则 | — |
| FE-1407 | V1.4 Mock | mock 同步 V2：B5 竖式演示题入 taskBank（与后端链题同源，复用既有 V2 链路） | 🟢 DONE（A5 number-line 待 V2Renderer 就绪后同步） | Frontend | #33 |
| FE-1408 | V1.4 Renderer | V2Renderer 接 number-line（纯函数层+组件+分流）+ mock A5 题同步——A5 链浏览器可玩 | 🟢 DONE（Gate A5 前端链路闭合） | Frontend | — |
| FE-1409 | V1.4 Renderer | V1.4 Frontend Development Package：18 个 V2 组件交付（V2RendererLibrary 基座）+ 后端 23/23 implemented 同步 | 🟡 组件交付（渲染就绪；各组件 Vertical Gate 待逐个补：mode Schema/链题/Evaluator/E2E） | Frontend/Backend | — |
| FE-1410 | V1.4 Migration | submission_id 落库（attempt 列 + partial 唯一索引）+ 双轨幂等（权威轨重放/409，V1 旧轨不变）+ 409 路径 | 🟢 DONE（真实 RDS 迁移已执行；五轨实证；防漂移单测 +3；docs/29 §5-2 关闭） | Backend | — |
| FE-1411 | V1.4 Hotfix | V1 操作题 WorkspaceProvider 无限渲染循环修复（schema 引用不稳定） | 🟢 DONE（探针复现 718→1；QA 待办：V1 manipulative 路径浏览器回归专项） | Frontend | — |
| FE-1412 | Governance | QA 数据卫生：测试流量分池（QA-Simulator child …0099）+ 存量污染清理（77 条标废+生产路径重算，app_rel conf 0→0.75）+ 凭据根治 + check-data-hygiene CI 门禁 | 🟢 DONE（E2E 分池实证：真实 child 新增 0；待办：用户轮换 RDS 密码；qa_replay #7 转 FAIL 属诚实暴露，待真实链题后重写） | Backend/QA | — |
| FE-1413 | Governance | 消费 V1.4 Renderer Semantic Completion Pack（4 份：Matrix/Gap/Breakdown/任务表）：存档 docs/frontend/31 + 基线判定 + SEM-<n> 编号映射裁决 + 114 Checkpoints/Batch A~E/禁止条款采纳 | 🟢 DONE（只登记不开发；其 Batch A 起手工待与交付方协商——B5=其 SEM-1414 已 CLOSED） | Governance/Frontend | #47 |
| FE-1414 | V1.4 Renderer | R01 ObjectCounter Vertical Gate（B5 模板第二实例）：objectCounterV2 纯函数+组件（add/remove/compose/decompose+过程留痕 Evidence）、V2 金题 seed RDS、门禁=P0-01 同口径、E2E 10 用例 | ✅ **Vertical Gate CLOSED（R01）**（全量 E2E 20/20、后端 81 passed、healing 双皮肤过；见 R01_OBJECTCOUNTER_VERTICAL_GATE.md） | Frontend/Backend/QA | — |
| FE-1415 | V1.4 Renderer | R04 NumberInput Vertical Gate（B5 模板第三实例；submission_id 幂等专项验证入口）：NumberInputV2（EMPTY 拦截/越界/整数守卫、input_history Evidence）、R04 金题 seed、E2E 7 用例 | ✅ **Vertical Gate CLOSED（R04）**（幂等四连 API 实证：重放同 attempt/异内容 409；全量 E2E 27/27、后端 82 passed；见 R04_NUMBERINPUT_VERTICAL_GATE.md；Gate 进度 3/19） | Frontend/Backend/QA | — |
| FE-1416 | V1.4 Renderer | R07 TenFrame Vertical Gate（B5 模板第四实例；20以内十与一结构+补十打包 MAKE_TEN_COMPLETED）：tenFrameV2 连续填充/打包/拆袋、R07 金题（sharing 族首题）seed、E2E 8 用例、fill/grouping 能力入名单 | ✅ **Vertical Gate CLOSED（R07）**（全量 E2E 35/35 零回归、后端 83 passed；**Batch A 4/4 全清、Gate 进度 5/19**；见 R07_TENFRAME_VERTICAL_GATE.md） | Frontend/Backend/QA | — |
| FE-1417 | Governance | 消费 V1.4 Renderer Completed Pack（整仓快照基线=83a0e94）：框架层收编（rendererContract/evaluatorRegistry/diagnosis+nextTask adapter、19 Release Scope 入码、QA 看板、contracts/release 脚本）+ 交付 3 缺陷修复（submission_id 冒号串→404 致命、evidence attempt_no 恒1、事件枚举混入状态名）；zip 含明文凭据不入仓 | 🟢 DONE（E2E 35/35 零回归；19/19=Contract 结构层口径，实际 Vertical Gate 仍 5/19） | Governance/Frontend | #53 |
| FE-1418 | V1.4 Renderer | R02 BarModel Vertical Gate（B5 模板第五实例；Batch B 先锋）：模型结构 evaluator 三分法（modeling/relation/calc 各 E2E 可达）、part_whole+comparison 纯函数层、R02 金题（**app_model 节点首题**）seed、E2E 10 用例 | ✅ **Vertical Gate CLOSED（R02）**（全量 E2E 45/45 零回归、后端 84 passed；**Gate 进度 6/19**；见 R02_BARMODEL_VERTICAL_GATE.md） | Frontend/Backend/QA | — |
| FE-1419 | V1.4 Renderer | R06 PlaceValue Vertical Gate（B5 模板第六实例）：数字卡放位值框（pick/place/swap/return），牌堆 multiset 守卫→错误只剩"位值混淆"维度（structure evaluator 产出 place_confusion 原料），R06 金题=**app_rd 节点首题**，E2E 9 用例含 SWAP 修正路径 | ✅ **Vertical Gate CLOSED（R06）**（全量 E2E 54/54 零回归、后端 85 passed；**Gate 进度 7/19**；见 R06_PLACEVALUE_VERTICAL_GATE.md） | Frontend/Backend/QA | — |
| FE-1420 | V1.4 Renderer | R10 FormulaBoard Vertical Gate（B5 模板第七实例；Batch B 收官）：算式 token 板，equation semantic evaluator 二分类（operator 翻符号可救/relation 救不回，各有金题靶）；**V2 首个非数字答案链**（answer="-"端到端）；双金题=**app_strat 节点首题**；E2E 9 用例 | ✅ **Vertical Gate CLOSED（R10）**（全量 E2E 63/63 零回归、后端 87 passed；**Gate 进度 8/19、Batch B 4/4 全清**；见 R10_FORMULABOARD_VERTICAL_GATE.md） | Frontend/Backend/QA | — |
| FE-1421 | V1.4 Renderer | R08 ArrayBoard Vertical Gate（B5 模板第八实例；Batch C 起手）：行列建阵列乘，**product/structure 解耦**——摆4×3积对后端判对+transpose原料留痕（首个"判对但带诊断原料"实例）；R08 金题=app_model 第二题+**lineup_position 词表族首题**；E2E 9 用例 | ✅ **Vertical Gate CLOSED（R08）**（全量 E2E 72/72 零回归、后端 88 passed；**Gate 进度 9/19**；见 R08_ARRAYBOARD_VERTICAL_GATE.md） | Frontend/Backend/QA | — |
| FE-1422a | QA/Backend | QA 确定性钉题（QA_PINNED_TASK_PROPOSAL 方案 A 落地）：GET /v1/content/v2-catalog + tasks/next pin_resource_version_id（路由层硬校验仅 QA child…0099，真实 child 403；缺省路径比特级不变）；e2e/pinned-tasks.mjs 共享模块，9 spec 旧碰运气抽题全替换；qa_child_setup --reset-bands；openapi+契约测试（后端 89→94） | ✅ DONE（全量 E2E 连续 2 次 83/83——band 漂移下仍绿，钉题确定性实锤） | Backend/QA | — |
| FE-1422 | V1.4 Renderer | R09 GroupingBoard Vertical Gate（B5 模板第九实例）：主动建组平均分物，structure evaluator 二分类 count/unequal 各有靶；防丢物约束（有糖组不可解散）；EMPTY=没发完不可提交；R09 金题=**sharing 族第二题**；E2E 11 用例（含收回补发修正路径） | ✅ **Vertical Gate CLOSED（R09）**（全量 E2E 83/83、后端 89 passed；**Gate 进度 10/19**；见 R09_GROUPINGBOARD_VERTICAL_GATE.md） | Frontend/Backend/QA | — |
| FE-1423 | V1.4 Renderer | R11 EstimationCanvas Vertical Gate（B5 模板第十实例；Batch C 收官）：滑条估算+理由 chip，五态评估器（EMPTY×2/PASS/too_high/too_low），**近似数判分口径**（38≈40 答案唯一不动冻结判分链；方向对 actual/close 对 expected 的 tolerance 原料走 Evidence=R08 解耦同款）；adjust_history 调整过程可回放；R11 金题=**shopping 族首题**+app_model 第三题；E2E 10 用例 | ✅ **Vertical Gate CLOSED（R11）**（全量 E2E 93/93 零回归、后端 95 passed；**Gate 进度 11/19、Batch C 3/3 全清**；见 R11_ESTIMATIONCANVAS_VERTICAL_GATE.md） | Frontend/Backend/QA | — |
| FE-1424 | V1.4 Renderer | R12 ShapeGallery Vertical Gate（B5 模板第十一实例；Batch D 起手）：图形墙两步点选分类，**解耦最锋利例**（混入长方形但数对→后端判对+attribute_confusion 原料留痕，R08/R11 后第三次跨域成立）；evaluator 属性错优先于漏放；SHAPE_* 五事件轨迹 Evidence；R12 金题=**app_cond 第二题**；E2E 12 用例 | ✅ **Vertical Gate CLOSED（R12）**（全量 E2E 105/105 零回归、后端 96 passed；**Gate 进度 12/19**；见 R12_SHAPEGALLERY_VERTICAL_GATE.md） | Frontend/Backend/QA | — |
| FE-1425 | V1.4 Renderer | R13 ShapeCanvas Vertical Gate（B5 模板第十二实例；Batch D 2/4）：点阵板点顶点画图，geometry evaluator（shoelace 整数面积+点积直角判定，形状错优先尺寸错）；**解耦第四次运用**（平行四边形面积 6→判对+not_right_angle 原料）；move/rotate 以点序重建替代（差异入底表）；R13 金题=app_model 第三题；E2E 11 用例 | ✅ **Vertical Gate CLOSED（R13）**（全量 E2E 116/116 零回归、后端 97 passed；**Gate 进度 13/19**；见 R13_SHAPECANVAS_VERTICAL_GATE.md） | Frontend/Backend/QA | — |
| FE-1301 | Task Renderer | V1（number/manipulative/unsupported） | 🟢 DONE | Frontend | — |
| FE-1302 | Math Workspace | 隔离 Workspace State | 🟢 DONE | Frontend | — |
| FE-1303 | Manipulative | Object Counter interactive | 🟢 DONE | Frontend | — |
| FE-1304 | Manipulative | Bar Model interactive | 🟢 DONE | Frontend | — |
| FE-1305 | Manipulative | Number Line interactive | 🟢 DONE | Frontend | — |
| API-1306 | Contract | TaskUISchema V1 | 🟢 DONE | Frontend | — |
| API-1307 | Contract | Structured Response | 🟢 DONE | Frontend | — |
| API-1308 | Hint | Workspace-aware ui_action | 🟢 DONE | Frontend | — |
| QA-1312 | QA | /dev/v1.3-qa 双皮肤页 | 🟢 DONE | Frontend | — |
| FE-1310 | Mastery UI | 能力状态儿童文案、多能力结果页、Normalizer迁移兼容 | 🟢 DONE | Frontend | — |
| QA-1311 | QA | Mastery前端边界静态回归 | 🟢 DONE | Frontend | — |
| EVT-1208 | Events | Interaction Event schema | ⚪ TODO | — | — |

## V1.4 Frontend P0

| Item | Capability | Status | Validation |
|---|---|---|---|
| V14-01 | Renderer Registry + safe fallback | 🟢 DONE | static contract check |
| V14-02 | Workspace API + capability gate | 🟢 DONE | pure TypeScript check |
| V14-03 | TaskUISchema renderer/capability metadata | 🟢 DONE | pure TypeScript check |
| V14-04 | Structured Response interaction_events | 🟢 DONE | static contract check |
| V14-05 | AttemptResult / HintResponse normalizer | 🟢 DONE | pure TypeScript check |
| V14-06 | Dual-skin V1.4 QA route | 🟢 DONE | transpile/parse check |
| V14-07 | Full Next production build | 🟢 DONE | `next build` 通过（2026-09-30 本地补验，9 routes 含 /dev/v1.4-qa）|

## V1.3 Scope

功能已三方合入 `main`（来自 `Math_Sprint3_Frontend_V1.3` 交付包）；版本号仍保持 `1.2.0`，待里程碑验收后由 Release Owner 统一升 `1.3.0`。

外部待办（后端对齐）：

- 🟡 Backend Structured Response acceptance
- 🟡 Backend TaskUISchema V1 alignment
- 🟡 Backend Hint ui_action alignment
