# 前端开发者交接说明（Frontend Onboarding）

> 目标：前端开发者 clone 本仓库后，15 分钟内能跑起来并开始开发，不踩已知坑。

---

## 0. 一句话了解项目

儿童数学学习系统的**儿童端前端**（Next.js 14 + React 18 + TypeScript），对接 Learning Engine 后端（Python/FastAPI）。当前稳定版 `1.2.0`。

**核心铁律**（违反会被打回）：
- 前端**不计算 Mastery、不实现 Diagnosis 规则、不绕过 Learning Engine 调 LLM**；
- 教育诊断码 `E01~E07` 是业务载荷（HTTP 200），绝不当系统错误码；
- 孩子端**不暴露研发术语、不允许自行换肤**；
- 第一次答错**不直接揭答案**。

详细见 `docs/adr/` 与 `AI_CONTRIBUTING.md`。

---

## 1. 环境要求

| 项 | 版本 |
|---|---|
| Node.js | **>= 22** |
| npm | 随 Node 22 |

> `.nvmrc` 已锁定 Node 版本，用 `nvm` 的开发者 `nvm use` 即可。

---

## 2. 三步跑起来

```bash
# 1. 在仓库根目录装依赖（monorepo，只装一次）
npm install

# 2. 用 workspace 命令启动儿童端（默认 mock 模式，无需后端）
npm run child:dev
# 等价于：npm --workspace @learning/child-web run dev

# 3. 打开
# http://localhost:3000/child/math
```

常用校验命令（提交前务必跑）：

```bash
npm run child:typecheck   # 类型检查
npm run child:build       # 生产构建
npm run governance:check  # 治理文件完整性
npm run release:check     # 版本一致性
```

---

## 3. 必读文档（按顺序）

| 顺序 | 文件 | 内容 |
|---|---|---|
| 1 | `PROJECT_STATUS.md` | 当前完成度 / 待办（唯一人工可读仪表盘） |
| 2 | `ROADMAP.md` | V1.3 候选方向（未冻结） |
| 3 | `docs/frontend/06_FRONTEND_MODULE_MAP.md` | 8 大模块、组件、API 依赖、边界 |
| 4 | `docs/frontend/04_SPRINT3_ACCEPTANCE.md` | Sprint 3 验收标准 |
| 5 | `docs/frontend/03_API_MAPPING.md` | 已接的 Learning Engine API |
| 6 | `docs/adr/` | 架构决策（尤其 ADR-0002/0003/0004/0005） |

---

## 4. Mock vs HTTP 两种模式

前端默认 **mock 模式**（不依赖后端，能完整跑通学习闭环）。

要连真实后端时，复制 `.env.example` → `.env.local`，改：

```env
NEXT_PUBLIC_LEARNING_API_MODE=http
NEXT_PUBLIC_LEARNING_API_BASE_URL=http://localhost:8000
```

> ⚠️ `BASE_URL` **不要带 `/api` 前缀**。前端请求路径以 `/v1/...` 开头，后端路由也是 `/v1/...`。
>
> `server` 端后端启动见 `apps/learning-api/README.md`。

---

## 5. 目录结构（前端）

```
apps/child-web/
├── app/                # Next.js App Router 页面（/child/math、/dev/ui-kit …）
├── src/
│   ├── components/     # 18 个核心组件（ui/home/learning/result/growth）
│   ├── screens/        # 页面组装（MathHomeScreen 等）
│   ├── features/learning/  # 学习状态机 machine.ts + useLearningSession.ts
│   ├── lib/api/        # contracts.ts(契约) + http.ts + mock.ts + normalizer
│   ├── lib/runtime/    # sessionStore（仅异常兜底）
│   └── theme/          # 皮肤（healing / math-lab）
└── docs/               # 前端文档（01~16）
```

---

## 6. 开发规则（避坑清单）

1. **改组件** → 必须同步 `/dev/ui-kit`（18 组件 × 2 皮肤 = 36 样例），healing 和 math-lab 都要验证。
2. **改 API 契约**（`contracts.ts`）→ 同步 `docs/frontend/03_API_MAPPING.md`，并在 `docs/governance/CONTRACT_DRIFT_REGISTER.md` 登记。
3. **改状态机**（`machine.ts`）→ 同步 `docs/frontend/02_STATE_MACHINE.md`。
4. **不提交** `.env.local` / `node_modules` / `.next` / `*.tsbuildinfo`（`.gitignore` 已覆盖）。
5. **提交前** 跑 `npm run child:typecheck`，确保 0 错误。

---

## 7. 工作流（Git）

1. 只从最新 `main` 拉取，**不要从旧 ZIP 开发**；
2. 认领一个 Issue 后，开分支 `feat/FE-xxxx-描述` 或 `fix/FE-xxxx-描述`；
3. 提交 → 提 PR（必要时标注 Contract 影响）→ 走 CI → merge；
4. **不要直接 push main**（main 有分支保护）。

详见 `docs/governance/WORKFLOW.md`、`docs/governance/BRANCH_AND_PR_POLICY.md`。

---

## 8. 已知的下一步重点（V1.3 候选，未冻结）

按 `ROADMAP.md`，当前最优先是 **Task Renderer V1 + Math Manipulative Engine**（Object Counter / Bar Model / Number Line），而非继续堆页面。

**动手前先确认 V1.3 scope 已在 Milestone + Issue 冻结**——不要自选方向单方面开工。