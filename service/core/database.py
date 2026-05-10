"""
Подключение к БД (async SQLAlchemy).

## Трассируемость
Feature: F001.
Используется всеми репозиториями через зависимость `db_connect.get_session`.
"""
from __future__ import annotations

from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from service.core.config import config


class DBConnect:
    def __init__(self, url: str) -> None:
        self._engine = create_async_engine(url, echo=False, future=True)
        self._sessionmaker = async_sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )

    @property
    def engine(self):
        return self._engine

    async def get_session(self) -> AsyncIterator[AsyncSession]:
        async with self._sessionmaker() as session:
            yield session


db_connect = DBConnect(config.db_url)
