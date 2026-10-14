# V6 隔离组件与页面检查

这套检查加载仓库真实 React 组件、真实 state/parser/serializer、真实 HTTP 客户端和学习 hook；只替换 Next 导航、API fetch 与 SVG 资源加载。所有 fetch 失败关闭，不能发送到真实服务；只用专用 QA 身份。它不是 Next SSR/hydration、生产构建或真实数据库端到端验收。

## 正常复跑

在仓库根目录先执行 `npm ci`；另需 Python 3.11+ 与 Python Playwright（本次环境为 Python 3.13.5 / Playwright 1.57.0）。浏览器可使用 Playwright 安装的 Chromium，或通过 `V6_BROWSER_EXECUTABLE` 指定本机路径。

```sh
npm run child:v6:isolated:prepare
python tests/v6-isolated/test_renderers.py 0 10
python tests/v6-isolated/test_renderers.py 10 20
python tests/v6-isolated/test_pages.py
```

默认从已安装依赖读取锁定的 React 18 UMD；输出在 `.cache/v6-isolated/evidence/`，包含实际运行时版本、报文与截图。结果失败时 Python 进程返回非零退出码。

## 依赖受限诊断模式

`V6_TYPESCRIPT_PATH` 可指定外部检查编译器；`V6_VENDOR_BOOTSTRAP` 可指定显式提供真实 React/ReactDOM 的脚本，要求暴露 `window.__vendor.{r,e,j}`。测试报告永远记录实际 React 版本，不能把不同版本的运行结果当作锁定工具链验证。本次交付证据使用外部 TypeScript 5.8.3 / React 19.1.1，因此 Next 14 + React 18 的正式验证仍待执行。第三方运行时脚本没有打入源码包。

20 个示例来自原仓库金题，覆盖 19 个 Renderer；formula-board 包含数值与运算符两种示例。错误/正确预期由示例与测试脚本给定，不使用产品 judge() 作为正确性的唯一依据；检查的是提交与交互契约，不冒充真实后端判分。
