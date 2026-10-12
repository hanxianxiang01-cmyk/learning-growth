# V1.4 · V6 全量视觉迁移源码交付

**本包是完整仓库，不是只有 Clock 的 M1/M2 补丁。应用版本保持 1.4.0。**

本轮覆盖：首页、七项能力节点成长地图、任务与反馈、学习小结，以及当前生产范围的 19 个 V2 Renderer；探索实验室 `exploration-lab`、轻量治愈 `healing` 两套皮肤共用数学状态。当前交付状态为“全量代码候选 + 已执行检查”，不是已合并/已正式上线。完整锁定工具链构建和真实数据库验收尚待执行。

## 1. 首次运行

使用 Node.js 22+，在解压后的 `learning-growth-main` 根目录运行：

```sh
npm ci
npm run child:v6:preview
```

访问 `http://127.0.0.1:3100/child/math` 预览首页；访问 `http://127.0.0.1:3100/dev/v6` 检查全部 19 个 Renderer。后者包含 20 个原仓库金题示例（算式板有两种模式），可以选择皮肤、锁定交互、观察真实组件生成的报文；不判分、不调用真实后端、不写入题库。

**preview 明确使用原仓库 mock 数据，不能据此确认真实学习结果。** 原 mock 题库并不覆盖所有生产 Renderer；完整视觉验收入口是 `/dev/v6`，不是不断点击 mock 首页猜测覆盖率。

直接预览治愈皮肤：

```sh
npm run child:v6:healing -- --api mock
```

## 2. 连接已有后端

后端沿用你的原仓库与现有部署，本轮没有执行数据库迁移或初始化。后端可访问后，再运行：

```sh
npm run child:v6:lab -- --api-base http://localhost:8000
# 或
npm run child:v6:healing -- --api-base http://localhost:8000
```

这两个命令默认 HTTP 模式，后端不可用会显示错误与重试，不会静默回退到假数据。已有的 `child_id` 参数和部署环境变量继续有效；QA 使用专门的测试身份，不要把自动化流量写入真实儿童账户。

配置样例见 `apps/child-web/.env.v6.example`。`NEXT_PUBLIC_*` 是构建期设置，修改后必须重启开发进程或重新构建。孩子端没有切换皮肤的按钮；只有开发画廊有切换器。本轮没有新增后台皮肤管理接口。

两套皮肤同时启动时使用不同端口：

```sh
npm run child:v6:lab -- --api mock --port 3100
npm run child:v6:healing -- --api mock --port 3101
```

启动脚本已为两套皮肤隔离 `.next` 目录，避免并行开发互相覆盖构建产物。旧项目命令 `npm run child:dev` 仍保留，但展示与 API 模式取决于环境变量；本轮验收优先使用上面明确的 V6 命令。

## 3. 构建、启动与回滚

```sh
npm run child:typecheck
npm run child:v6:check
npm run child:v6:lab -- --build
npm run child:v6:lab -- --start
```

治愈皮肤分别把 `child:v6:lab` 换成 `child:v6:healing`。构建和 start 必须采用相同 UI/皮肤及 API 设置。连接正式服务时先配置正确的公开 API 地址；`--start` 不会重写已经内联的构建配置。

回到旧界面：

```sh
npm run child:legacy -- --api mock
```

UI 回滚保留本轮共享的请求防重入、重试及缓存异常处理；完全回到原始源代码，应在 Git 分支上回滚整份补丁。不要只删新 CSS。生产环境 `/dev/v6`、`/dev/v6-clock` 与 `/dev/ui-kit` 返回 404。

## 4. 包内导航

| 路径 | 内容 |
|---|---|
| `apps/child-web/src/components/ui-v6/` | 场景、首页、地图、结果页、工作区外框、Clock、反馈 |
| `apps/child-web/src/components/renderers/` | 19 个 V2 Renderer 的真实 V6 展示分支；原 legacy 分支保留 |
| `apps/child-web/app/ui-v6.css` | 作用域化双皮肤与窄屏样式；不覆盖原 globals.css 文件 |
| `apps/child-web/public/child-ui-v6/` | 两套背景与角色 SVG，不含字体文件 |
| `apps/child-web/src/features/ui-v6/` | 能力展示映射、Clock 交互几何；不计算掌握度 |
| `apps/child-web/src/dev/v6/` | DEV 画廊与原金题示例 |
| `tests/v6-isolated/` | 本轮实际运行的隔离组件/页面测试，可移植复跑 |
| `apps/child-web/e2e-v6/` | 使用真实 Next dev 页面的 Playwright 回归代码，当前环境未能执行 |
| `docs/frontend/42_v6_full_migration/` | 全量覆盖、测试边界、证据与来源 |

`docs/frontend/41_v6_ui_migration/` 是之前 M1/M2 的历史记录，不能用于判断本次交付覆盖率。

## 5. 验证状态

已执行：38 项纯模块/限定范围 TS 语义检查、38 项全量迁移静态与展示/启动断言、132 个 TS/TSX/JSON 源模块的语法转译、20 组真实 Renderer 隔离浏览器检查（19 种）、7 组页面/流程检查与运行时错误检查，以及原仓库治理、版本、V1.4 契约相关脚本。

**没有通过的门不能算通过：** `npm ci` 在本环境发生 DNS/EAI_AGAIN，锁定依赖未安装；完整应用 typecheck、Next build、真实 Next 页面 Playwright 和 Git 分支检查均阻断。隔离浏览器采用 Chromium 144 / React 19.1.1 / TypeScript 5.8.3，不是锁定的 React 18.3.1 / Next 14.2.35 / TypeScript 5.9.3。没有进行生产后端判分、数据库落库、Mastery 更新或真实儿童学习验收。

详细实际结果与重跑命令见 `docs/frontend/42_v6_full_migration/TEST_REPORT.md`。
