"""
UserService — регистрация/идентификация пользователя.

## Трассируемость
Feature: F001 — Регистрация пользователя.
Scenarios: SC001, SC002, SC004.
Business rules: BR001 (идемпотентность upsert по tg_id).

## Зависимости
- UserRepository.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from service.core.exceptions import NotFoundError
from service.model.users.user_model import UserModel
from service.repository.users.user_repository import UserRepository


@dataclass
class UserUpsertResult:
    user: UserModel
    created: bool


class UserService:
    def __init__(self, repo: Optional[UserRepository] = None) -> None:
        self._repo = repo or UserRepository()

    async def upsert(
        self,
        session: AsyncSession,
        *,
        tg_id: int,
        username: Optional[str],
    ) -> UserUpsertResult:
        """SC001/SC002 — идемпотентная регистрация по tg_id (BR001)."""
        existing = await self._repo.get_by_telegram_id(session, tg_id)
        if existing is not None:
            return UserUpsertResult(user=existing, created=False)
        user = await self._repo.create(session, telegram_id=tg_id, username=username)
        return UserUpsertResult(user=user, created=True)

    async def get_by_telegram_id(self, session: AsyncSession, tg_id: int) -> UserModel:
        """SC004 — получение пользователя; 404 если не найден."""
        user = await self._repo.get_by_telegram_id(session, tg_id)
        if user is None:
            raise NotFoundError(f"user with telegram_id={tg_id} not found")
        return user
