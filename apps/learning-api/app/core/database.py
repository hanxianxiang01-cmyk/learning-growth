"""SQLAlchemy 引擎与会话（同步 + 异步双通道）。

- 同步 engine：健康检查 / 反射 / Alembic。
- 异步 async_sessionmaker：FastAPI 业务服务。
URL 采用 "postgresql+psycopg://"，psycopg3 原生同时支持 sync/async。
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# 同步（health check / 反射用）
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# 异步（业务服务用）
async_engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类（表结构由 Alembic 迁移管理）。"""


async def get_db() -> AsyncSession:
    """FastAPI 依赖：返回异步会话。"""
    async with AsyncSessionLocal() as session:
        yield session