# Learning API（Learning Engine）

儿童学习成长系统的后端服务——教育决策中心。职责边界（见 `docs/adr/`）：

> **前端不计算 Mastery、不实现 Diagnosis、不绕过 Learning Engine 调 LLM。**
> 本服务是教育规则的唯一持有者。

## 技术栈

- Python 3.12 + FastAPI + Pydantic 2 + SQLAlchemy 2（async）+ Alembic
- PostgreSQL（`pgcrypto` 已用，`pgvector` 可选待 RAG 阶段）
- DeepTutor 通过**外部 entry-points 插件**接入（`Core Patch = 0`，见 ADR-0001）

## 目录结构

```
app/
├── api/          HTTP 路由（/v1/learning/*、/v1/children/*、/v1/reports/*）
├── core/         config / database(async) / education_rules(冻结常量)
├── models/       18 张表 ORM（对齐 baselines/learning-core-v1.3.1）
├── schemas/      Pydantic DTO
├── services/     诊断 / Mastery / FitBand / Curriculum / Hint / Profile / Growth / SessionResult
└── content/      能力节点 + 黄金资源包 seed 数据
scripts/          建库校验 / seed / 验收脚本
tests/            pytest 单测
migrations/       Alembic 迁移
```

## 本地启动

```bash
# 1. 建 Python 3.12 虚拟环境并装依赖
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 2. 配置数据库（复制 .env.example → .env，填真实连接串）
cp .env.example .env

# 3. 启动服务
uvicorn app.main:app --reload
```

数据库连接串格式：`postgresql+psycopg://<user>:<password>@<host>:<port>/<db>`

## 初始化数据

```bash
# 内容 seed（能力节点 + 资源包，幂等）
DATABASE_URL=... python scripts/seed_content.py

# 演示孩子 seed（固定 child_id，幂等）
DATABASE_URL=... python scripts/seed_demo.py
```

## 测试

```bash
pytest -q
```

## 接口约定

- 教育诊断码 `E01~E07` 是**业务载荷**（HTTP 200），绝不当系统错误码返回。
- 系统错误码：`LE-4001 / LE-4091 / LE-4221 / LE-4291 / LE-5001 / AG-5031`。
- 接口签名以 `baselines/learning-core-v1.3.1/02_openapi_v1.3.1.yaml` 为 SSOT。
- Session Result 接口见 ADR-0005 与本目录 `app/services/session_result.py`。