"""
Глобальные фикстуры для бэкенд-тестов.

## Трассируемость
Project: Neuronium Companion Backend.

Здесь:
- Подкладываем sys.path так, чтобы `service.*` импортировался из репозитория.
- Поднимаем in-memory SQLite + клиент httpx через ASGITransport.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Использовать in-memory SQLite до того, как core.config прочитает env.
os.environ.setdefault(
    "DATABASE_URL", "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"
)

from service.core.database import db_connect  # noqa: E402
from service.core.loader import app  # noqa: E402
from service.model.base_model import Base  # noqa: E402


@pytest_asyncio.fixture
async def async_session():
    """Свежая БД на каждый тест."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", echo=False, future=True
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sm() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def client(async_session):
    """HTTP-клиент к ASGI-приложению с подменённой сессией БД."""

    async def _override():
        yield async_session

    app.dependency_overrides[db_connect.get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def api_prefix() -> str:
    from service.core.config import config

    return config.api_v1_prefix
