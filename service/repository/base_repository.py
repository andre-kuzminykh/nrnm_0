"""
Generic CRUD-репозиторий.

## Трассируемость
Project: Neuronium Companion Backend.
Используется всеми наследниками — `get_by_id`, `get_all`, `create`, `delete`.
"""
from __future__ import annotations

from typing import Generic, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    def __init__(self, model: Type[ModelT]) -> None:
        self.model = model

    async def get_by_id(self, session: AsyncSession, entity_id: int) -> Optional[ModelT]:
        return await session.get(self.model, entity_id)

    async def get_all(self, session: AsyncSession) -> list[ModelT]:
        result = await session.execute(select(self.model))
        return list(result.scalars().all())

    async def create(self, session: AsyncSession, **fields) -> ModelT:
        obj = self.model(**fields)
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj

    async def delete(self, session: AsyncSession, obj: ModelT) -> None:
        await session.delete(obj)
        await session.commit()
