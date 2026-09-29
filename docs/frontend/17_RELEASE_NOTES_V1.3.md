# 17｜V1.3 Release Notes — Math Interaction Foundation

## Scope

本地完整实现以下冻结范围：

```text
FE-1301 Task Renderer V1
FE-1302 Workspace State
FE-1303 Object Counter
FE-1304 Bar Model
FE-1305 Number Line
API-1306 TaskUISchema V1
API-1307 Structured Response
API-1308 Workspace-aware Hint
QA-1312 Integration Acceptance
```

## Product Change

V1.2：

```text
题目 → 输入答案 → Attempt
```

V1.3：

```text
TaskUISchema
 ↓
TaskRenderer
 ↓
数学工作区（物件 / 线段图 / 数轴）
 ↓
孩子操作形成 representation
 ↓
TaskResponse { answer, representation }
 ↓
Attempt
```

## Architecture

Learning State 与 Workspace State 已分离。

Learning State继续负责：
- answering
- submitting
- hint
- retry
- correct
- complete

Workspace State负责：
- representation
- undo
- reset
- selection/highlight
- workspace hint action

## QA

开发验收入口：

```text
/dev/v1.3-qa
```

一次展示：
- Object Counter
- Bar Model
- Number Line

并分别在：
- healing
- math-lab

两套系统内置皮肤下验证。

右侧实时显示 Structured Response JSON。

## Local Build Basis

由于当前执行环境无法解析 github.com，本次下载包基于：
- 本会话最新 V1.2.0 本地项目包
- 用户提供的 `ONBOARDING_FRONTEND.md`

未推送远端 GitHub。
