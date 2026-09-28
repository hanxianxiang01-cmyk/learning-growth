# Ownership

> GitHub账号尚未绑定，因此这里记录逻辑Owner。  
> `.github/CODEOWNERS.example` 在确定账号/团队后再启用。

| Area | Primary Owner Role | Review Required |
|---|---|---|
| `apps/child-web` | Frontend Worker | Frontend / Product |
| `apps/learning-api` | Learning Engine Worker | Backend / Architecture |
| `packages/contracts` | Contract Owner | Frontend + Backend |
| `packages/math-ui` | Frontend Math UI | Frontend |
| `packages/skin-runtime` | UI Platform | Frontend / Product |
| `baselines` | Architecture / Release Owner | 2-person review |
| `docs/adr` | Architecture | Cross-review |
| `CHANGELOG / VERSION / releases` | Release Owner | Release review |

原则：

> Contract 和 Frozen Baseline 不允许单人静默修改。
