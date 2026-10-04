# QA 数据卫生规则（QA_DATA_HYGIENE）

状态：ACTIVE ｜ 生效：2026-10-04 ｜ 背景 PR：FE-1412（本文件随附）

## 1. 动机

2026-10-04 实测发现：真实演示孩子（child `…0001` 小明）的 app_rel 已积累 108 条
mastery 证据，但其中大部分来自 QA 回放与 E2E harness 的模拟作答。Mastery 派生只看
最近窗口（CI_WINDOW=8、STABILITY_WINDOW=5），测试数据（含故意答错的题、同一
resource_version 一秒一题的批量重放）长期压住窗口顶部，真实学习水平永远测不上去。
同期还发现 `scripts/qa_replay_mastery.py` 把真实 RDS 密码硬编码进了 git（PR #19 引入）。

## 2. 规则（强制）

- **R1 真实 child 的学习数据只能由人产生。** 任何脚本 / E2E / 冒烟测试 / QA 回放
  向真实后端写入 attempt、evidence、event 时，一律使用 QA-Simulator child
  `00000000-0000-0000-0000-000000000099`，禁止 `…0001`。
  初始化：`DATABASE_URL=… python scripts/qa_child_setup.py`（幂等）。
- **R2 凭据只能来自环境变量。** 代码中禁止出现 RDS host（`pg.rds.aliyuncs.com`）、
  连接串密码、以及任何形式的 `postgresql://user:pass@host` 字面量。
  使用 `DATABASE_URL` 环境变量注入（见 `apps/learning-api/.env.example`）。
- **R3 新组件的 Vertical Gate E2E 继承本规则。** B5 五件套模板中 harness 的
  `CHILD` 取值必须是 `process.env.E2E_CHILD_ID ?? "…0099"`，不得复制旧常量。
- **R4 污染只标废不删除。** 已混入真实 child 的测试证据用 `valid=false` 作废
  （schema 原生语义），保留可追溯性；作废与重算走受控脚本，记录 PR。

## 3. 可执行边界

R1/R2 由 `scripts/check-data-hygiene.mjs` 在 CI 静态扫描（governance job）。
白名单：seed 脚本与前端 config/mock 中的 `…0001` 引用（那是产品演示身份，
不写真实库）；文档（*.md）不受扫描。

## 4. 隔离原理（为何零 DDL）

`ability_state` 主键 `(child_id, ability_id)`、`mastery_evidence` 按 child 过滤
派生——换 child_id 即全链路隔离，无需任何新表/新列。QA child 的掌握度数据
允许被测试任意折腾（它本来就是"无限升级"的模拟器）。
