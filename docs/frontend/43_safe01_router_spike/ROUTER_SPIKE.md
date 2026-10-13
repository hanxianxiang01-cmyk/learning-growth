# 单 Renderer 双实现路由｜独立技术 SPIKE

**状态：机制纯函数验证通过；React/Next真实运行未执行，尚未满足E1合入门。**

## 1. 方案

`TaskRenderer` 在V2 `number-input`分支接入 `TaskRendererImplementationBoundary`；
旧组件 `NumberInputV2` **原封不动保留**，新增 `NumberInputKernelPilot` 作为真正不同的交互视图，但共享旧组件的配置解析、答案序列化与 `NUMBER_INPUT_CHANGED` 事件格式。

- 19个V1.4发布 Renderer ID 保持不变，没有创造新 `renderer_id`；
- 目前**仅 `number-input` 有真实第二实现**。Clock/竖式/其他17个仍只有旧实现，不能认为迁移完成；
- 默认 `NEXT_PUBLIC_MIK_RENDERER_FLAGS=`，全部 `legacy`；可在独立QA环境设置 `NEXT_PUBLIC_MIK_RENDERER_FLAGS=number-input=kernel`；
- Renderer实现选择储存在浏览器 `localStorage`，仅 task_instance_id/renderer_id/ui_revision/实现版本/时间，无答案、儿童profile或作答；
- 同TaskInstance跨React重挂载、刷新后复用锁定记录。**当前应用刷新不保证恢复同一个TaskInstance或工作区状态，这是上层恢复链路的缺口**；
- 锁定的 kernel 版本若被移除，不静默换成legacy，而显示明确的恢复阻断；任务内 rendererId/UI revision 变化同样阻断；
- 对新TaskInstance，发现 kernel 未实现会拒绝启用该版本并选择legacy；对已有任务，不允许中途自动切换。

## 2. 切换与回滚规则

| 事件 | 预期 |
|---|---|
| 未设置 flag，新任务 | legacy |
| 已有kernel pilot且flag开启，新任务 | kernel，记录锁 |
| 同一任务期间关闭flag | 仍使用已锁定的kernel |
| 新任务开始，flag关闭 | legacy |
| 同任务原kernel部署不再提供 | BLOCKED，不能偷偷转legacy |
| 存储记录损坏、Task身份/Revision不匹配 | BLOCKED，不信任旧记录 |
| 浏览器存储不可用 | 只允许legacy，**跨刷新版本持久锁定不保证** |

建议E1完成时增加：任务完成后的显式锁清理、刷新/断网状态恢复、同任务跨标签页竞态测试，以及业务端可观察的路由版本诊断（开发工具记录，不进入儿童题卡）。

## 3. 验证结果

- 原始TS编译执行的19条策略用例：**19/19 PASS**；覆盖默认值、启用、持久锁、旗标反转、缺实现阻断、异常存储、新任务重选、任务内身份变化、长时任务、无答案落盘。
- 策略模块独立 `tsc --strict --noEmit`：PASS。
- TS/TSX转译语法检查：5/5 PASS；不等于完整Next类型检查。
- `number-input` KernelPilot的接口与响应结构参考旧组件，不另行计算数学正确性。
- React/Next真实页面路由、焦点/可及性、任务刷新恢复、Clock和竖式的实际二路由、三端/双皮肤：**NOT_RUN**。

## 4. 需要在E1前补齐

- 将选择路由从单个试点推广为显式注册的每Renderer适配器实现映射，**仅在第二实现真正存在时才放行**。
- 实测新旧两种R04输入产生相同合法响应结构与Evidence字段；新UI事件只能来自真实孩子操作，不伪造操作来源。
- 确认浏览器重启与任务恢复的权威路径：当前localStorage只锁版本、并不保存作答。
- 处理正在执行的老任务、失败/超时重试与发布回滚；禁止任务中静默重换组件。
- V6完整工程基线（FE-1445或等价）Typecheck/Build、HTTP/Judge/Evidence/DB、Legacy回归都通过后，才能作为公共Kernel合入基线。

## 5. 代码位置

- `apps/child-web/src/features/math-interaction/implementationPolicy.ts`
- `apps/child-web/src/features/math-interaction/TaskRendererImplementationBoundary.tsx`
- `apps/child-web/src/features/math-interaction/NumberInputKernelPilot.tsx`
- `apps/child-web/src/features/task-renderer/TaskRenderer.tsx`（R04双实现路由）
- `apps/child-web/.env.example`（flag说明）

**SPIKE的目的：技术风险实证，不代表19 Renderer可通过一个布尔配置直接替换成新内核。**
