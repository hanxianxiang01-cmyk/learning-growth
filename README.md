# Learning Growth System

儿童学习成长系统 Git-ready 协作仓库。

## 当前稳定应用版本

```text
Child Web: 1.2.0
Release: Learning Result Closure
```

## 当前仓库治理版本

```text
VCS Governance: 1.0.0
```

> Git 仓库是唯一代码真相源。ZIP 只作为正式 Release Artifact，不再作为日常开发交换介质。

---

## Repository Structure

```text
apps/
├── child-web/          当前儿童数学前端
├── parent-web/         未来家长端占位
└── learning-api/       Learning Engine代码接入位

packages/
├── contracts/          未来共享API/Schema包
├── math-ui/            未来数学交互组件包
└── skin-runtime/       未来皮肤运行时包

baselines/
└── learning-core-v1.3.1/   冻结研发基线，不可原地改

docs/
├── frontend/           当前前端设计/模块/状态文档
├── governance/         Git/版本/协作治理
├── adr/                架构决策记录
└── releases/           发布说明

releases/               机器可读版本历史
.github/                PR / Issue / CI模板
```

---

## 开始工作前

任何人或 AI 工作者先读：

```text
1. PROJECT_STATUS.md
2. ROADMAP.md
3. CHANGELOG.md
4. AI_CONTRIBUTING.md
5. docs/governance/WORKFLOW.md
6. docs/adr/
7. 与任务相关的Spec
```

> 前端开发者另有专项交接：见 **`ONBOARDING_FRONTEND.md`**（15 分钟跑起来 + 避坑清单）。

---

## Working Model

```text
Issue
 ↓
Branch
 ↓
Commit
 ↓
Pull Request
 ↓
CI
 ↓
Review
 ↓
Merge to main
 ↓
Milestone complete
 ↓
Release Tag
 ↓
ZIP / Release Artifact
```

禁止直接把“某个Worker手里的ZIP”当成新基线。

---

## Branch Naming

```text
feat/FE-1301-task-renderer
fix/FE-1210-result-empty-state
api/API-1305-task-ui-schema
docs/DOC-003-architecture
chore/OPS-002-ci
```

---

## Checks

```bash
npm install
npm run governance:check
npm run release:check
npm run child:typecheck
npm run child:build
```

---

## Current Priority

当前 V1.2 已完成正式 Session Result 结果闭环。

V1.3 范围**尚未冻结**，候选方向见：

```text
ROADMAP.md
PROJECT_STATUS.md
```

下一步由 Milestone / Issues 冻结，不由任一工作者单方面定义。
