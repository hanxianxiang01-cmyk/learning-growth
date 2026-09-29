# 22｜V1.3 Known Issues / Constraints

## 1. Remote main未拉取

当前执行环境无法解析 `github.com`，因此本地V1.3基于会话最新V1.2.0包 + 用户提供的 `ONBOARDING_FRONTEND.md` 开发。

正式合入仓库前必须：

```text
fetch latest main
compare diff
rebase/cherry-pick as needed
CI
PR
```

## 2. Full Next Build未在当前环境执行

`npm install` 因外部网络超时未完成。

已通过：
- static V1.3 QA
- release check
- strict internal TypeScript validation（临时external shims）
- 53个TS/TSX语法转译
- runtime model QA

正式PR仍需执行仓库CI。

## 3. Structured Response需要后端兼容

V1.3 HTTP Attempt提交结构化对象。后端若仍只接受primitive answer会失败。

## 4. ui_action是可选扩展

后端没有 `ui_action` 时：
- 文本Hint正常；
- Workspace不会自动高亮/对齐。

## 5. 不在V1.3范围

- Interaction Events
- Choice Renderer
- Formula Renderer
- Free Draw
- Sorting / Matching
- Geometry
