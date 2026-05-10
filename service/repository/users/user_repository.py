"""
UserRepository — выборки и сохранение пользователей.

## Трассируемость
Feature: F001.
Scenarios: SC001, SC002, SC004.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from service.model.users.user_model import UserModel
from service.repository.base_repository import BaseRepository


class UserRepository(BaseRepository[UserModel]):
    def __init__(self) -> None:
        super().__init__(UserModel)

    async def get_by_telegram_id(
        self, session: AsyncSession, telegram_id: int
    ) -> Optional[UserModel]:
        result = await session.execute(
            select(UserModel).where(UserModel.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
