"""
GET /api/v1/users/{tg_id} — получить пользователя по Telegram ID.

## Трассируемость
Feature: F001.
Scenarios: SC004.
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from service.api.v1.endpoints.users import router
from service.core.database import db_connect
from service.schema.users.user_schema import UserResponseSchema
from service.service.users.user_service import UserService

_service = UserService()


@router.get(
    "/{tg_id}",
    response_model=UserResponseSchema,
    summary="Получить пользователя по Telegram ID",
)
async def get_user(
    tg_id: int,
    session: AsyncSession = Depends(db_connect.get_session),
) -> UserResponseSchema:
    user = await _service.get_by_telegram_id(session, tg_id)
    return UserResponseSchema.model_validate(user)
