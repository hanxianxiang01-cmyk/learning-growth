# MIK-A5｜基于 FE-1445 V6 (504a93d) 的 16 Renderer 统一 React 接线 — Review Only

**状态：SOURCE INTEGRATED · ISOLATED TESTS PASS · LIVE/BUILD NOT VERIFIED · MAIN NOT MODIFIED**

> 本交付可进入候选分支代码复核，**不得用作 MIK 生产合入通过证明**。FE-1445 PR #87 仍保持独立 Draft；这里所有测试均发生在本地 ZIP 重建的独立工作树，不是 GitHub PR #87 上的 CI 结果。

## 1. 基线、来源及纠偏

- **唯一合并基线**：用户提供 `FE1445_V6_Full_Source_504a93d.zip`，标识 commit `504a93d66f24d7b784e5eeed8e5763e69bf14e1d`（ZIP 不含 Git 历史；此 commit 标识取自用户提供的分支信息，不是由 ZIP 自行认证）。
- **第二来源**：`MIK_SAFE01_Spike_Candidate_Source_2026-10-13.zip`，为 SAFE-01 净化和单 Renderer Router 的 Spike 候选，**不是含完整 MIK A0–A4 内核的包**。
- **A5 来源**：此前生成的 A5-16 自然意图/React 控件候选，已经对 V6 原领域模型作逐项签名核验与必要修正。
- **docs/43**：两份用户 ZIP 中相应 11 件文档校验完全一致，未用历史旧文档覆盖仓库最新纠偏及 `SAFE01_FINAL_VERDICT.md`。`VERDICT §3` 仍明确跨版本真实 QA 尚未完成；不得宣称 PASS。
- **清理范围**：构建包不携带 `.env.local`、`node_modules/`、`.next/`、测试数据库或生产密钥。

## 2. SAFE-01 与 V6 无损并账

1. 采纳 Spike 的 `v2AttemptAdapter.ts` 净化版：前端继续产生 Evidence，但不注入 `evaluation`，Judge 与判分仍由真实服务端负责。
2. 同步修复 `apps/child-web/scripts/check-v14-contracts.mjs` 对 `getRendererEvaluator` 的过期硬断言。原脚本已验证 PASS。
3. 只移植 Router Pilot 所需的 TaskRenderer 接线，保留 V6 已完成的 `uiVersion` 双入口、`ChildSkinProvider`、`RendererFrame`、现有皮肤 CSS、`taskResponse.ts` 等主线逻辑。不复制回退旧版 `TaskRenderer.tsx`。
4. 保留任务绑定的 `legacy|kernel` 决策（`localStorage` 锁定），默认 `legacy`。仅在明确设置 `NEXT_PUBLIC_MIK_RENDERER_FLAGS` 时才启用候选交互，非法旗标及版本身份不匹配均 fail closed。

## 3. 16 项一次性 React 接线清单

| Renderer ID | 原 V6 域动作（前端必须复用） | 挂载形式 | 注意事项 |
|---|---|---|---|
| number-input | 原组件文本/事件契约 | 独立 `NumberInputKernelPilot` Router | 输入须保留不完整/错误答案到后端的路径 |
| formula-board | 激活槽、数字键、运算符键 | V6 原组件 + A5LivePanel | 必须显式选择槽，禁止合成前置事件 |
| ten-frame | `applyCell` | 同上 | 连续填格是既有领域规则，不能按自由格占用解释 |
| grouping-board | `applyAddItem/RemoveItem` | 同上 | 单件操作、数量守恒 |
| money-board | `applyAddCoin/RemoveCoin` | 同上 | 金额维度为角，不与元混淆 |
| bar-model | `applyBarDelta` | 同上 | 仅被配置允许的条块 |
| array-board | `applyRowDelta/ColDelta` | 同上 | 行列上限由原规则决定 |
| place-value | `applyPick/Slot` | 同上 | 选择卡片是一次真实操作，不伪装为拖拽内隐选择 |
| sorting-board | `applySelectCard/Swap` | 同上 | 同上，交换要保持原事件历史 |
| number-line | `applyJump` | 同上 | 跳格必须落在 `tickStep` 对应合法刻度 |
| ruler | `applyPlaceMark` | 同上 | 第一枚、第二枚顺序真实依赖原状态；不假设零起点为实测值 |
| direction-grid | `applyMoveTo` | 同上 | 仅正交相邻格，不准斜跳 |
| shape-canvas | `applyAddPoint` | 同上 | 点合法性由原 Domain 裁决，无隐式画线 |
| pattern-board | `applyReplaceAt` | 同上 | 新增任意空槽定点放置 `dropToken`；只发一条原有 PATTERN 事件 |
| shape-gallery | `applySelect/PlaceHome/ReturnHome` | 同上 | 归类可错答；已入盒退回不要求虚构选中 |
| estimation-canvas | `applyEstimate` | 同上 | PointerUp 后才提交；不在连续预览时写历史 |

**边界说明：** 其中 15 个采用 V6 `RendererFrame` 内置新增 A5 操作面板（可能与原操作区重复，需 L3 UX 确认）；Number Input 为独立 Router Pilot。**不是**已替换全部原题面为最终儿童自然操作，也不是无条件为所有在用题目启用该面板。所有新路径默认关闭。

## 4. 完成的静态 / 隔离回归

| 检查 | 结果 | 证据范围 |
|---|---|---|
| 严格独立 TS 编译（A5 域/Hook/面板及导入的 15 个 V6 域模块） | PASS | `tsc -p tsconfig.mik-a5-isolated.json`，使用测试期 React 声明代用品 |
| 自然意图、场景与模拟 React 事件 | 117/117 PASS | `tests/a5-16/`；不代表真实 React 或浏览器 |
| 真实 V6 域函数、安全预检、原组件 JSX 挂载 | 49/49 PASS | `tests/spikes/mik-a5-live/`；源码与领域测试，不访问 DB |
| Router/任务绑定专项 | 19 条 PASS | `tests/spikes/implementation-policy.test.cjs` |
| SAFE-01 envelope 审计脚本 | PASS | 无客户端 Judge；静态/独立抽查 |
| V1.4 前端／契约／Registry／Release 脚本 | 全 PASS | 仍非 CI 下一轮执行结果 |
| V6 migration/full 检查、治理、卫生与 release | 全 PASS | 原有静态门禁 |
| Git 补丁空白检查 | PASS | `git diff --check` |

CI `child-typecheck` 增加 MIK-A5 隔离编译及 166 个案例的执行步骤，但新增 CI 配置**尚未在 GitHub 运行**，不能将既有 `504a93d` 的绿色结果归于本补丁。

## 5. 当前阻塞与合入门

1. **依赖安装**：本地 `npm ci --offline` 缺 `undici-types@6.21.0` 缓存；在线安装遭 `EAI_AGAIN` DNS/联网限制。不能据此认定源码编译 PASS 或 FAIL。完整 React18／Next14 类型检查与双皮肤 Build **NOT RUN**。
2. **实际浏览器手势**：Chromium+平板+手机，至少两种内置皮肤，Pointer Capture、拖动中断、触屏滑动/取消、键盘替代、任务更新中途取消，**NOT RUN**。
3. **真实 QA 学习链路**：TaskInstance→API HTTP→DB 判分落库→Evidence→Mastery，包含错误答案可提交、跨版本重试、重放幂等性，**NOT RUN**。
4. **Legacy 197 E2E**：PR #87 原负责人正在推进，本包未冒充该门通过。
5. **A4 三个高风险 Renderer**：`column-arithmetic/object-counter/clock` 的正式 A4 自然操作代码未包含于这次的两份输入 ZIP，因此这轮**不把 19/19 自然交互标为完成**。三项保留 V6 原实现；需要最新 A4 全源码单独按版本差异合入后再验收。
6. **UX/L2/L3**：16 个候选操作面板暂与 V6 原按钮并存，需要确认儿童理解与二套皮肤适配，冻结语义契约，不得用模拟 DOM 测试替代 L3。
7. **PR 与 main**：本地候选未推远端，不更改 GitHub PR #87 的 Draft 或 main；发布前须建立独立分支、独立 CI 与人工复核。

## 6. 重放 / 统一测试

将本包放在与基线 ZIP 对应的干净工作目录，复核源文件后执行：

```bash
# 默认 legacy；不要预先启用全部内核
npm ci
npm run child:typecheck
npm run child:build
npm run child:v6:check
node scripts/check-mik-a5-review.mjs
```

在隔离 QA 分支及真实浏览器中只对 16 项设置明确 `kernel` opt-in，不允许直接更改 production 环境。逐项验证答案不正确但结构完整时仍能按原题 Response 契约提交；第三方 Judge 不能由页面脚本替代。

**建议裁决：`MIK-A5 16项源码接线候选 READY FOR REVIEW`，`MIK-A5 生产/跨版本一体化验收 NOT APPROVED`。**
