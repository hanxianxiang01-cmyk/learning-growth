# V6 全量迁移 · 实际测试报告

执行日期：2026-10-11。报告只计入实际执行结果。源码交付与产品正式验收分开表述。

## 1. 执行环境

| 项目 | 原仓库锁定值 | 本轮实际情况 |
|---|---|---|
| Node | >=22 | 22.16.0 |
| Next | 14.2.35 | 未安装成功，未构建 |
| React / ReactDOM | 18.3.1 | 隔离检查使用19.1.1，明确不是锁定版本验收 |
| TypeScript | 5.9.3 | 外部检查编译器5.8.3 |
| JS Playwright Test | 1.49.1 | 未安装成功，真实Next测试未执行 |
| Python / Python Playwright | 不属于应用锁文件 | 3.13.5 / 1.57.0，仅用于隔离检查 |
| 浏览器 | 待部署环境确认 | Chromium144.0.7559.96 |

`npm ci`因DNS/EAI_AGAIN失败。本环境没有为获得“通过”而修改package-lock、升级/降级项目依赖。浏览器不允许本地URL导航，因此隔离检查在内存页面中挂载真实组件；没有修改浏览器管理策略。

## 2. 已执行并通过

| 检查层 | 结果 | 能说明什么 |
|---|---|---|
| 原M1/M2纯模块检查 | 38通过，0失败 | Clock几何/输入、原数学序列化、学习重试、幂等、缓存失败与限定范围纯TS语义检查 |
| 全量迁移检查 | 38通过，0失败 | 19分支清单、20原例、七能力展示、缺失/零证据/未知趋势、默认开关、启动参数及DEV门禁等 |
| 源代码转译 | 132个源模块，语法诊断0 | 语法可转译；不等同于完整应用类型正确 |
| Renderer隔离浏览器 | 20/20示例，通过；19种Renderer | 真实组件交互、提交内容、两种皮肤、视口变化、锁定与重置 |
| 页面/流程隔离浏览器 | 7/7组通过，另运行时错误检查通过 | 真实screen/hook/HTTP客户端在固定接口边界下的接线与恢复 |
| 原仓库脚本 | governance/release/V1.4/renderers/contracts/frontend-release全部通过 | 原有静态治理与契约检查没有被本轮破坏 |

### 每个Renderer的实测项

初始不完整答案禁止提交；合法错误答案允许提交；捕获的提交与组件真实response一致；切换healing保留完整response和事件；768/390/320宽度变化保留状态且页面不横向溢出；外部disabled锁定按钮/输入但不丢状态；原生重置（数字输入为清空）恢复初始未就绪；正确答案与独立示例预期一致并能提交。每个示例保存探索实验室1280与治愈390两张截图。

预期值来自原金题及独立的动作/预期脚本，测试没有调用产品judge()证明产品自身正确。测试验证提交报文，真正的服务端判分没有在本环境执行。撤销的纯运行时检查已执行；不能把“重置20/20”写成“19个renderer的所有撤销路径均已浏览器实测”。

### 页面/流程实测组

1. 真实首页组件：profile/abilities固定接口返回、5类挑战、双皮肤1280/390/320。
2. 七能力节点地图：选择保持、窄屏详情、零证据不显示已掌握。
3. 缺失能力数据：不编造等级、不锁关。
4. 延迟、接口失败与重新加载。
5. 首页创建会话 → Clock5:00合法错误提交 → 固定错误结果 → 服务端提示端点 → 保留原答案重试 → Clock6:00正确提交 → 固定完成结果 → 学习小结。验证单次提交锁、V2 envelope、attempt_no、稳定submission_id及提示使用attempt_id。
6. 提交返回503后，答案锁定；重试发送逐字段相同body与submission_id，不生成第二份答案。
7. 结果不可用时显示错误，重载恢复；不展示捏造的完成统计。

网页截图、完整工作区报文、API请求记录均使用**专用QA身份与固定fixture**。没有向真实儿童、真实会话或数据库发送测试流量。

## 3. 阻断 / 未执行

| 项目 | 实际结果 / 原因 |
|---|---|
| `npm ci` | EAI_AGAIN/DNS失败，锁定依赖不可用 |
| `npm run child:typecheck` | 已尝试，退出2：缺少Node/React/ReactDOM等类型定义；不是通过 |
| `npm run child:build` | 已尝试，退出127：next不存在 |
| `npm run child:v6:e2e` | 已尝试，退出1：环境只有另一Playwright命令，缺少锁定的@playwright/test；没有启动真实Next测试 |
| `npm run branch:check` | 已尝试，退出1：ZIP工作副本无Git分支；未创建/合并PR |
| SSR、hydration及生产路由404 | 代码与静态门禁已检查；生产Next行为未执行 |
| 本机有缓存时的fallback浏览器路径 | 展示分支已实现；本轮内存浏览器无法建立真实sessionStorage来源，未单独覆盖此路径 |
| 真实后端判分、DB落库、证据消化、Mastery | 未执行；固定响应链路不能代替这些验收 |
| 全模式/全边界、真实触屏/无障碍专项、L2教研与L3真实儿童测试 | 未完整执行，不能由20示例推断全通过 |

完整stdout/退出码保留在 `evidence/command-results.json` 及对应日志。旧M1/M2测试报告是历史数据，不计入本轮新覆盖。

## 4. 复验命令

依赖正常的机器上，从仓库根目录：

```sh
npm ci
npm run child:typecheck
npm run child:v6:check
npm run child:v6:lab -- --build
npm run child:v6:healing -- --build
```

真实Next组件回归（不会启动或写入后端）：

```sh
npm run child:v6:preview
# 另一个终端；首次需安装与锁定Playwright兼容的浏览器
npm --workspace @learning/child-web exec -- playwright install chromium
npm run child:v6:e2e
```

隔离检查完整复跑见 `tests/v6-isolated/README.md`。默认使用本机安装的锁定React18 UMD，报告记录实际版本；本次原始证据采用显式外部React19运行时。第三方运行时与字体文件均未打包。

进入Git协作时，在原始基线对应分支上应用补丁，执行原有PR/CI流程；本交付没有代替Release Owner修改版本或发布。
