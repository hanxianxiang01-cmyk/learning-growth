# GitHub 分支保护（Branch Protection）配置 Checklist

> 用途：把 `main` 分支配置成「必须 PR + 必须过 CI」的受保护分支，防止误推、漏检。
> 适用：`hanxianxiang01-cmyk/learning-growth`（公开仓库）。
> 前置：需要仓库 **Admin** 权限（仓库 Owner 天然具备）。

> **状态（2026-09-28）**：本仓库的分支保护**已通过 API 配置完成**（ruleset `protect-main`，enforcement=active，含 require PR / **0 approval（单人阶段）** / 3 status checks / no-deletion / no-force-push）。
> **Approval 门槛说明**：单人维护阶段 `required_approving_review_count` 暂设为 **0**（GitHub 禁止作者自审自批，设 1 会导致合入死锁）。待前端开发者等协作者进场后，改回 **1** 即可恢复「必须 1 人 approve」的严格流程。
> 下方保留手动配置步骤，供团队将它迁移到 UI 或调整规则时参考。

---

## 0. 三个关键坑（先读，别踩）

| # | 坑 | 说明 |
|---|---|---|
| 1 | **status check 名必须和 CI job 名逐字一致** | 本仓库 CI（`.github/workflows/ci.yml`）的 job 名是 `governance`、`child-typecheck`、`child-build`，核对时不能多空格、改大小写。 |
| 2 | **check 必须先在 main 上跑过一次** | 新拉的仓库，至少要有一个 PR 成功跑完 CI，`governance` 等名字才会出现在可选列表里。空仓库直接开，会出现「搜不到 check 名」的假象。 |
| 3 | **先配规则，再让协作者 clone** | 否则协作者可能已经直接 push 到 main，防护形同虚设。 |
| 4 | **界面路径已迁到 Rulesets** | GitHub 已把旧的「Branch protection rules」入口折叠，主推 **Rulesets**。当前准确入口是仓库页顶部 **Settings 标签页 → 左侧 Rules → Rulesets**，或直接访问 `/settings/rules`。旧「Branches」菜单里的 classic 入口很多账号已不显示。 |

---

## 1. 打开分支保护设置

### 方法一：网页 UI（当前推荐）

```
仓库主页 → 顶部「Settings」标签页（不是侧边栏齿轮）
  → 左侧栏「Code and automation」分组下找「Rules」
    → Rulesets
  → 点「New ruleset」→ 选「New branch ruleset」
```

> 若左侧栏没有「Rules」分组，直接改 URL 访问：
>
> ```
> https://github.com/<owner>/<repo>/settings/rules
> ```

### 方法二：API（适合脚本化 / 一次性配置）

用具备 `Administration: Write` 权限的 token，通过 `POST /repos/{owner}/{repo}/rulesets` 创建。
参考 payload（正是本仓库当前生效的配置）：

```json
{
  "name": "protect-main",
  "enforcement": "active",
  "target": "branch",
  "conditions": { "ref_name": { "include": ["refs/heads/main"], "exclude": [] } },
  "rules": [
    { "type": "pull_request", "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": false,
        "required_review_thread_resolution": true } },
    { "type": "required_status_checks", "parameters": {
        "strict_required_status_checks_policy": true,
        "required_status_checks": [
          { "context": "governance" },
          { "context": "child-typecheck" },
          { "context": "child-build" }
        ] } },
    { "type": "deletion" },
    { "type": "non_fast_forward" }
  ]
}
```

---

## 2. 填写规则

### 2.1 Branch name pattern

```
main
```

（只保护 `main`，`feat/*` 等短分支不保护。）

### 2.2 逐项勾选（按下面的来）

| 配置项 | 勾选 | 说明 |
|---|---|---|
| **Require a pull request before merging** | ✅ | 强制走 PR |
| └ Require approvals | ✅ 当前 `0` | 单人阶段设 0（作者不能自审自批）；加协作者后改为 1 |
| └ Dismiss stale approvals when new commits are pushed | ✅ | 新提交后旧 approval 失效 |
| └ Require review from Code Owners | ⬜ 暂不勾 | 需要 CODEOWNERS 文件才有效（见 §5） |
| **Require status checks to pass before merging** | ✅ | 强制 CI 绿 |
| └ Require branches to be up to date before merging | ✅ | PR 合并前必须 rebase 到最新 main |
| └ 搜索并勾选 check 名 | ✅ 勾 3 个 | `governance`、`child-typecheck`、`child-build`（逐字） |
| **Require conversation resolution before merging** | ✅ 建议 | 所有 Comment 解决才能合 |
| **Do not allow bypassing the above settings** | ✅ 建议 | 管理员也不绕过 |
| **Restrict who can push to matching branches** | ✅ 建议 | 只允许你自己（Admin） |
| **Do not allow pushing to the branch / Force pushes** | ✅ 勾 Block | 禁止 force push |
| **Do not allow deletions** | ✅ 勾 Block | 禁止删 main |

> 说明：上面「搜索 check 名」那一步，若搜不到 `governance` 等名字，回到坑 #2 —— 先让 CI 在 main 上跑过一次。

### 2.3 保存

点页面底部 **Create**（旧界面）或 **Create rule**（新界面）。

---

## 3. 配置合并策略

仓库 Settings → **General**（或 Pull Requests）→ 找到 **Merge button**：

| 项 | 推荐 |
|---|---|
| Allow merge commits | ⬜ 关（保留特殊场景再手开） |
| Allow squash merging | ✅ 开（默认） |
| Allow rebase merging | ⬜ 关 |

> 上面是**推荐组合**：小功能一律 Squash，历史干净。大改造需保留多 commit 时再临时开 merge commit。

同页勾选 **Automatically delete head branches** ✅（feature 分支合并后自动删）。

---

## 4. 配好后的验证（30 秒自测）

1. 本地随便改个文件、开个 `feat/test-保护` 分支、直接 `git push origin main`（模拟直推）→ **应被拒绝**（remote rejected）。
2. 开一个 PR，看 CI 三个 check `governance` / `child-typecheck` / `child-build` 是否都跑、并通过。
3. 三个 check 通过前，Merge 按钮应显示灰色/不可点。

三条全符合 → 分支保护生效 ✅。

---

## 5. 可选增强（后续再做，非必须）

| 增强 | 说明 | 门槛 |
|---|---|---|
| **CODEOWNERS** | 指定 `docs/**`、`contracts` 等由谁 review | GitHub 免费 plan 对 public repo 可用，但需多人协作才有意义 |
| **Rulesets（新式规则）** | 比老式 branch protection 更细（可限定只允许某类提交、限制 push 者角色等） | 仓库 Settings → Rules → Rulesets |
| **Milestone + Labels** | 见 `docs/governance/GITHUB_SETUP.md` 的 Milestone/Labels 清单 | 纯网页操作 |
| **Require signed commits** | 要求 GPG/Sign 签名提交 | 团队统一配 GPG 后再开，否则新人会卡 |

---

## 6. 与治理文档的关系

- 规则口径以本文件为准；
- Labels / Milestones 建议见 `GITHUB_SETUP.md`；
- 日常分支命名/PR 大小见 `BRANCH_AND_PR_POLICY.md`；
- 发版流程见 `RELEASE_PROCESS.md`。