> **历史 M1/M2 记录。当前全量范围与测试状态见 `../42_v6_full_migration/`。此处旧默认开关、覆盖范围与待办不代表当前交付状态。**

# [Draft / 未创建远程PR] FE-1443：V6主题与Clock首条真实接口切片

建议分支：`feat/FE-1443-v6-clock-migration`。输入为用户提供的最新ZIP，接收方须先与远程当前main核对，不得覆盖main或回滚其他PR。

## 范围

- 默认关闭的V6主题/任务页/反馈；保留legacy展示。
- ClockV6原生React/SVG输入，沿用已冻结parser/state/serializer/event/adapter。
- 完整答案保留的重试与原请求重传保护，缓存失败不污染已确认结果。
- DEV双皮肤画廊；38项纯函数与纯TS检查；7个待运行组件用例、2个待运行真实HTTP用例。
- M1文件/接口对照，原型与仓库差异登记。

## 不在本PR

成长地图/首页/结果全量重设计；其余18Renderer的完整V6交互；FE-1442选题改造；预作答提示新API；DB/OpenAPI/schema/Mastery/Diagnosis/内容变更；版本升级。

## 硬前提

- [ ] npm ci成功；完整React/Next typecheck / build通过（当前环境阻断）。
- [ ] 两皮肤、三视口实际React浏览器测试。
- [ ] QA pin→真实Judge→Hint→Retry→SessionResult与持久化。
- [ ] 未确认请求原样重发只入账一次。
- [ ] legacy回滚及共享流程回归。
- [ ] L2签署；L3试用计划与结果。
- [ ] 源ZIP基线与当前上游无冲突；FE-1442分支状态核实。

## 合同变更

无DTO/DB/OpenAPI变更；原类型字段及serializer保持。客户端请求与恢复控制发生变更，属于consumer实现修复，需要E2E而非仅文档确认。

## 已执行证据

`TEST_REPORT.md`与`evidence/`。纯检查/静态门禁通过；不存在Typecheck/Build/E2E/PR已通过或合入的声称。

## 回滚

展示回滚：NEXT_PUBLIC_CHILD_UI_VERSION=legacy，重新构建／启动。
完整回滚：还原本PR，包括共享请求与重试修复。不得只删public SVG或CSS，留下引用错误。
