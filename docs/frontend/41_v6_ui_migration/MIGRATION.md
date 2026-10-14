> **历史 M1/M2 记录。当前全量范围与测试状态见 `../42_v6_full_migration/`。此处旧默认开关、覆盖范围与待办不代表当前交付状态。**

# FE-1443 · V6 原型到真实前端：M1 / M2 迁移交接

日期：2026-10-11。状态：**M1 仓库对照完成；M2 代码候选已写入，运行环境验证阻断；不得标记 DONE / 已通过生产联调。**

这次交付是 Next.js / React 源代码，不是独立 HTML，不是已经合并的 PR。以用户上传源码为唯一实施基础；V6 HTML 仅作为批准的视觉／交互参考。

## 1. 输入、分支与不变项

| 项目 | 证据 |
|---|---|
| 用户源码 | `learning-growth-main (1).zip` |
| 输入 ZIP SHA-256 | `b2a925b76358fdda4164da663599ffeeb4ddb44e3225b90b19fe5b7d12c7f401` |
| 原型参考 | `V14_Full_Illustrated_UI_v6.html` |
| 参考 HTML SHA-256 | `a346be99ffb364932bb71b94fee60395c734c529ccd5d8100d3a6ee3e8c6df66` |
| 冻结版本 | 仓库 `VERSION=1.4.0`，合同 `docs/frontend/38_contract_frozen/CONTRACT_FROZEN.md` v2.0；不升版本 |
| 本地工作分支 | `feat/FE-1443-v6-clock-migration`，branch:check 通过 |
| Git 边界 | ZIP 不含上游历史；本地初始化快照仅用于生成／验证补丁，不是用户 main；无远程 push、无 PR、无合并 |

未修改：后端代码、DB schema、OpenAPI、TaskUISchema、AttemptResult/HintResponse/AbilityState/SessionResult、内容包、Renderer 注册表、clock 原 parser/state/serializer、Evidence/Evaluator/Diagnosis 适配链、主版本和锁文件。

`evidence/frozen-files-check.json` 对13个关键文件作输入快照逐字节校验。静态契约脚本通过不代表 UI/E2E 已通过。

## 2. 三个必须尊重的源码事实

### 2.1 两套皮肤与开关

运行时真实 skin ID 为 `exploration-lab` / `healing`，见 `src/theme/skins.ts`。部分治理文档把默认皮肤称为 `math-lab`，配置文件对非 `healing` 值回退至 `exploration-lab`。本次不重命名。

ADR-0004 / AI_CONTRIBUTING 禁止儿童自行换肤。因此正式儿童端没有皮肤切换器。两皮肤通过部署配置选择，DEV 检查区可以切换。不把 HTML 外层评审控制器搬到儿童端。

新增 `NEXT_PUBLIC_CHILD_UI_VERSION=legacy|v6` 为**构建期、默认关闭**的展示开关。不是在线动态开关，不是按儿童的后台灰度服务，修改后须重新构建或重启开发服务。

### 2.2 提示接口不支持原型中的“首次作答前随时提示”

真实 `POST /v1/learning/hints` 需要服务端 `attempt_id`。本轮保持：确认错误结果且 `next_action` 为 HINT/TEACH 后，才出现可调用的提示入口。提示正文来自接口，不能自造 `attempt_id` 或从原型本地 hint_ladder 补齐。

Clock 原内容金样例第4级提示含目标结果；本轮不改内容、不承诺“全部提示均不泄答案”。该内容审核属于 L2，不能靠 UI 隐藏改写解题合同。

### 2.3 上传包未包含 FE-1442 生产公平选题改造

`apps/learning-api/app/services/learning.py::_published_resource_for_ability` 仍按 `difficulty.asc(), created_at.asc()` 选首题。目录 catalog 的金题优先排序不是生产选题公平性机制。聊天中的 FE-1442 完成情况不可替代当前源码。

本轮不改选题服务。Clock 真实测试仅使用仓库已有 QA pin 通路；不能以 pin 命中证明生产选题公平性。接上游 PR 前需确认 FE-1442 是否位于其他分支，避免覆盖后续合入。

## 3. M1 页面文件级对照

| 原型页面 | 真实源文件／通路 | 本轮处置 |
|---|---|---|
| P01 今日学习 | `src/screens/MathHomeScreen.tsx`，Profile/Abilities/CreateSession API | 不全量迁移。避免把示例3/5进度当真实任务计划 |
| P02 成长地图 | `src/screens/MathGrowthScreen.tsx` / `AbilityMap` / Abilities API | 保留现行实现，M3迁移节点布局与接口；不灌原型43/3/4条数据 |
| P03 答题 | `src/screens/MathLearningScreen.tsx` / TaskRenderer | V6开关分支：单题卡＋大操作区＋按需反馈，不显示内部能力评审说明 |
| P04 提示 | `useLearningSession` / `requestHint` | 按真实attempt依赖接入共享反馈区；不是独立业务路由 |
| P05 正确 | 服务端AttemptResult → machine → Feedback | 只展示服务端结果；不带入原型 localFeedback |
| P06 错误与重试 | 同上 | INCORRECT警示/继续修改后RETRY；保持真实作答状态与尝试序号 |
| P07 小结 | `src/screens/MathResultScreen.tsx` / SessionResult API | 沿用。现有临时缓存回退及行为汇总仍需后续和ADR对照 |

题干的来源仍是服务端 `task.ui_schema.prompt`；MathQuestionCard 在 V6 下仅显示一次题干，不另抄目标和解释。保持现有 prompt 内容，不在UI擅自纠正或重写。

## 4. 19 Renderer 覆盖与本轮范围

本轮只实施一个真实垂直切片，不将原型19/19展示计为19/19代码迁移。共同主题／题卡作用于V6页面，其余18个组件仍使用原交互实现。

| Renderer | 当前组件 | 本轮状态 |
|---|---|---|
| object-counter | ObjectCounterV2 | M3待迁移 |
| bar-model | BarModelV2 | M3待迁移；比较/部分整体模式须按内容合同选择 |
| number-line | NumberLineV2 | M3待迁移 |
| number-input | NumberInputV2 | M3待迁移 |
| column-arithmetic | ColumnArithmetic | M3待迁移 |
| place-value | PlaceValueV2 | M3待迁移 |
| ten-frame | TenFrameV2 | M3待迁移 |
| array-board | ArrayBoardV2 | M3待迁移；不能把原型前端结构判定替代服务端评价 |
| grouping-board | GroupingBoardV2 | M3待迁移 |
| formula-board | FormulaBoardV2 | M3待迁移 |
| estimation-canvas | EstimationCanvasV2 | M3待迁移 |
| shape-gallery | ShapeGalleryV2 | M3待迁移 |
| shape-canvas | ShapeCanvasV2 | M3待迁移 |
| sorting-board | SortingBoardV2 | M3待迁移 |
| direction-grid | DirectionGridV2 | M3待迁移 |
| ruler | RulerV2 | M3待迁移 |
| clock | ClockV2 → ClockV6／Legacy | **M2代码候选；构建和真实UI/API测试待执行** |
| money-board | MoneyBoardV2 | M3待迁移 |
| pattern-board | PatternBoardV2 | M3待迁移 |

## 5. M2 已写入的源码

### 5.1 公共UI

- `src/theme/uiVersion.ts`、`v6Tokens.ts`：版本开关、两皮肤tokens；主CTA统一#0A6972，成功/错误/重试反馈职责分离。
- `ChildSkinProvider` 保留旧skin和legacy tokens；`app/ui-v6.css` 采用开关作用域，不覆盖旧样式文件。
- `LearningChrome` / `LearningScenery` / `LearningFeedback`：原生React组件；装饰SVG在public路径，无运行时AI生成、无第三方图表引擎。
- `TaskPresentationBoundary`：展示异常只给儿童可恢复文案，不显示栈或parser错误。
- `MathLearningScreen`：feature flag决定新旧呈现；没有复制完整HTML、没有内嵌原型iframe、没有模拟评分。
- `app/dev/v6-clock/page.tsx` 是开发模式专用入口；同一检查组件同时登记 `/dev/ui-kit`。仅开发区可切换皮肤／版本及捕获报文。

### 5.2 Clock

- **不修改** `features/task-renderer/clockV2.ts`、`rendererRuntime.ts`、V2 payload适配器。
- config仍为数组时刻，state仍是h/m/adjust_history，答案仍为总分钟；分钟严格0或30。
- 数字点按、针尖拖动、键盘箭头/Home/End都调用原 `applySetHour/applySetMinute`。
- Pointer Events使用SVG坐标变换；7px启动阈值是待儿童试测的UI参数，不宣称已经适龄验证。
- 拖动中只预览；抬起才提交一个原有SET事件，一次拖动仅一条撤销历史。取消／失焦不提交。
- 使用原 `CLOCK_HOUR_SET / CLOCK_MINUTE_SET / UNDO / RESET`；没有自创后端事件或Diagnosis code。
- 去掉UI的PASS/FAIL、距离正确答案分钟差、hand_swap预判提示；原serialize仍按合同生成structure供既有链路消费。
- 零调整不能提交；任一合法、已操作的错误时间也能提交。
- 原ClockV2Legacy保留回滚。旧测试断言旋转transform/本地判题文案，只在legacy配置下有意义；新UI用独立测试，不改旧断言刷通过。

### 5.3 真实请求与重试保护（影响两种UI，需回归）

- SET_RESPONSE/重试保持完整V2答案与workspace，不清空answer造成“钟面保留但父状态丢答”。
- submit/hint的同步ref防重入；未知网络结果保留原提交体，恢复时重发原attempt_no／submission_id，而不是拿新答案复用旧尝试。
- 只有服务端确认才递增本机统计和尝试次数；sessionStorage失败不把已确认成功变成提交失败。
- 使用服务端next_action限制提示；提交未确认时暂时禁止编辑，显示恢复入口。
- 浏览器缓存改为hydration之后读取；不在SSR和首次客户端渲染输出不同的本机进度。
- task response的两个纯函数从TSX提取至`taskResponse.ts`，原导出仍保留，内容不变。

这些是本轮必要的共享流程修复，不是只改CSS。新UI开关回滚不会撤销共享安全修复；完整回滚须还原本PR。

## 6. 明确未做／未验证

1. 未执行 npm 依赖安装成功、完整React/Next类型检查、Next构建、真实React浏览器测试或API/DB联调；详见TEST_REPORT。
2. 未迁移成长地图、首页、总结页的全部新视觉；未全面改造其余18个Renderer。开关开启后链接这些页仍进入现有页面。
3. 未修改成长等级、稳定状态、证据口径；没有新增单条证据读取接口。
4. 未实现刷新恢复未提交的当前题／未知网络提交。当前任务/待确认请求主要在内存中，刷新仍按现有接口取下一题。不能承诺刷新续作／跨设备恢复。
5. 未增加tasks/next服务端幂等键、并发锁或多设备调度，不将本机ref锁等同于服务端安全。
6. submit遇到任何异常先保持待确认状态；可重发相同请求。永久4xx的专门退出策略尚待后端错误合同确认，不静默丢弃原作答。
7. 钟面同向针尖热区、移动端实际48px触控、焦点可见性、减少动态效果和设备旋转须真机／浏览器验收，代码中的ARIA不等于已通过无障碍认证。
8. 没有改19 Renderer以外的协议枚举，没有将3,108候选题批量生产入库，没有远程操作用户数据库。
9. 没有签署L2/L3，没有提交/合并PR、升级VERSION或宣称发布。

## 7. 执行与开关

### 安装和静态检查（仓库根目录）

```sh
npm ci
npm run governance:check
npm run branch:check
npm run release:check
npm run child:typecheck
node apps/child-web/scripts/check-v6-migration.mjs
npm run child:v14:check
npm run child:build
```

仓库自带package-lock的根包版本标签仍是1.2.0，而package.json/发布版本为1.4.0；本轮未更新依赖或静默重写锁文件。恢复环境时如锁文件验证失败，单列依赖整理，不顺手升级React/Next。

### 打开真实接口模式（开发环境，不触达生产数据）

先按后端README配置Python3.12、数据库与已批准seed。启动HTTP学习API之后：

```sh
NEXT_PUBLIC_CHILD_UI_VERSION=v6 \
NEXT_PUBLIC_LEARNING_API_MODE=http \
NEXT_PUBLIC_LEARNING_API_BASE_URL=http://127.0.0.1:8000 \
npm --workspace @learning/child-web run dev -- --port 3100
```

皮肤分别用 `NEXT_PUBLIC_CHILD_MATH_SKIN=exploration-lab` 和 `healing` 启动验证。不要把mock模式画面当作真实接口测试。

开发组件入口：`/dev/v6-clock` 或 `/dev/ui-kit`；DEV控制区明确注明只捕获报文，不模拟判分、不写学习记录。

### 浏览器检查（另一个终端）

```sh
# 7个开发组件用例，不需要后端，不写学习数据
E2E_V6=1 E2E_WEB_BASE=http://127.0.0.1:3100 \
npm --workspace @learning/child-web exec -- playwright test --config=playwright.v6.config.mjs v6-clock-gallery

# 2个真实HTTP用例，只允许QA child …0099，会产生QA session/attempt/evidence
E2E_V6=1 E2E_V6_LIVE=1 E2E_WEB_BASE=http://127.0.0.1:3100 \
E2E_API_BASE=http://127.0.0.1:8000 \
npm --workspace @learning/child-web exec -- playwright test --config=playwright.v6.config.mjs v6-clock-live
```

浏览器默认系统Chrome；可用 `E2E_CHROMIUM_PATH=/absolute/path/to/chromium` 明确可执行文件。测试只给实际tasks/next添加既有QA pin字段，不伪造判分响应。包含6:30分钟错误与6:00正确链路，以及“服务端已保存但响应丢失→相同请求重发→仅1条记录”。QA测试数据应按既有数据卫生流程归档清理，不使用真实儿童ID。

### 回滚

将 `NEXT_PUBLIC_CHILD_UI_VERSION=legacy`，重启／重建应用；确认Clock和页面恢复原布局。共享请求防重入/重试修复仍然存在；若需完全恢复输入源码，应回滚本PR，而不是删除某一个CSS文件。

## 8. 首条真实链路的关闭标准

- 与V6对照的平板／手机／电脑、两皮肤截图和操作证据。
- 原Clock合同测试与新组件用例通过；不可只给外层SVG加tabindex刷可达检查。
- QA儿童真实tasks/next→attempt→错误→真实hint→retry保留→正确→SessionResult可查询。
- evidence事件／answer／workspace／submission_id正确，不重复入账。
- frontend typecheck/build成功；L2题面/初始状态/允许动作/答案轴/证据/反馈六项签署。
- 源码PR经review合入，才将M2转DONE；随后安排剩余18Renderer与三类旧页面迁移，L3逐步开展。
