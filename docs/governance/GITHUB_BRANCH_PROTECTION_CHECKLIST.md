# GitHub 分支保护（Branch Protection）配置 Checklist

> 用途：把 `main` 分支配置成「必须 PR + 必须过 CI」的受保护分支，防止误推、漏检。
> 适用：`hanxianxiang01-cmyk/learning-growth`（公开仓库）。
> 前置：需要仓库 **Admin** 权限（仓库 Owner 天然具备）。

---

## 0. 三个关键坑（先读，别踩）

| # | 坑 | 说明 |
|---|---|---|
| 1 | **status check 名必须和 CI job 名逐字一致** | 本仓库 CI（`.github/workflows/ci.yml`）的 job 名是 `governance`、`child-typecheck`、`child-build`，核对时不能多空格、改大小写。 |
| 2 | **check 必须先在 main 上跑过一次** | 新拉的仓库，至少要有一个 PR 成功跑完 CI，`governance` 等名字才会出现在可选列表里。空仓库直接开，会出现「搜不到 check 名」的假象。 |
| 3 | **先配规则，再让协作者 clone** | 否则协作者可能已经直接 push 到 main，防护形同虚设。 |

---

## 1. 打开分支保护设置

```
GitHub 仓库页面 → Settings（齿轮图标）
  → 左侧 Code and automation 下的 Branches
  → 或：Rules → Rulesets（新界面）
```

> 老界面是「Branch protection rules」，新界面是「Rulesets」。两者等效，选你看得到的那个，本文按老界面路径写。

在 **Branch protection rules** 区域点 **Add branch protection rule**（或 Add classic branch protection rule）。

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
| └ Require approvals | ✅ 建议 `1` | 至少 1 人 approve（单人项目可先设为 0 再调） |
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