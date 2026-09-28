"""通用 repository 辅助：get/create/list。"""
from __future__ import annotations

import uuid
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


async def get_or_none(db: AsyncSession, model: type, pk: Any) -> Any | None:
    """按主键取单条，无则 None。兼容 uuid / str 主键。"""
    return await db.get(model, pk)


async def create_instance(db: AsyncSession, model: type, **values: Any) -> Any:
    obj = model(**values)
    db.add(obj)
    await db.flush()
    return obj


async def list_all(db: AsyncSession, model: type, limit: int = 100) -> list[Any]:
    result = await db.execute(select(model).limit(limit))
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, model: type, id_field: str, value: Any) -> Any | None:
    result = await db.execute(select(model).where(getattr(model, id_field) == value))
    return result.scalar_one_or_none()


def as_uuid(v: Any) -> uuid.UUID:
    return v if isinstance(v, uuid.UUID) else uuid.UUID(str(v))