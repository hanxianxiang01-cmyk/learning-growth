# AI Contributor Protocol

适用于所有 AI 工作者 / Coding Agent。

## 1. 开始任务前

必须先读取：

```text
PROJECT_STATUS.md
ROADMAP.md
CHANGELOG.md
docs/governance/WORKFLOW.md
docs/governance/CONTRACT_DRIFT_REGISTER.md
相关 ADR
```

不要只依赖聊天上下文、记忆或旧ZIP。

## 2. 一个 Issue 一个主 Owner

禁止两个 Worker 同时以“主开发”身份修改同一 Issue。

如需共同开发：
- 一个 Owner
- 一个 Reviewer / Supporting Worker

## 3. 不直接修改 main

所有修改：

```text
Issue → branch → PR → checks → review → merge
```

## 4. 不擅自升级版本

开发过程中统一记录：

```text
CHANGELOG.md → [Unreleased]
```

只有 Release Owner 在里程碑完成后：
- 修改 VERSION
- package version
- release manifest
- tag

## 5. Contract 修改规则

修改以下任一内容：

```text
OpenAPI
TaskUISchema
SessionResult
AttemptResult
HintResponse
AbilityState
DB schema
```

必须同步：
- Contract Drift Register
- API/Schema文档
- Consumer影响说明
- 必要时 ADR

## 6. 教育逻辑边界

前端禁止：
- 计算 Mastery
- 重写 Diagnosis
- 根据本地交互自行决定能力等级
- 绕过 Learning Engine 直接调用 LLM
- 将 E01~E07 当 HTTP Error

## 7. UI规则

- 新组件必须进入 `/dev/ui-kit`
- healing / math-lab 都要验证
- 孩子端不暴露研发术语
- 孩子端不允许自行换肤

## 8. 完成定义

“写完代码”不等于完成。

Issue DONE 至少要求：

```text
Acceptance Criteria通过
Typecheck通过
Build通过
相关测试通过
文档更新
CHANGELOG [Unreleased]更新
PR合并
```

## 9. 交接

如果任务未完成，必须在 Issue / PR 中留下：

- 已完成
- 未完成
- 风险
- 下一步
- 修改文件
- 测试状态

不要把未完成上下文只留在聊天里。
