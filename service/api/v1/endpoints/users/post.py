"""
POST /api/v1/users — upsert пользователя по tg_id.

## Трассируемость
Feature: F001.
Scenarios: SC001 (создание), SC002 (повтор), SC003 (валидация).
"""
from __future__ import annotations

from fastapi import Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from service.api.v1.endpoints.users import router
from service.core.database import db_connect
from service.schema.users.user_schema import (
    UserCreateSchema,
    UserUpsertResponseSchema,
)
from service.service.users.user_service import UserService

_service = UserService()


@router.post(
    "",
    response_model=UserUpsertResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Upsert пользователя по Telegram ID",
)
async def upsert_user(
    payload: UserCreateSchema,
    response: Response,
    session: AsyncSession = Depends(db_connect.get_session),
) -> UserUpsertResponseSchema:
    result = await _service.upsert(
        session, tg_id=payload.tg_id, username=payload.username
    )
    # SC002: повторный запрос — 200 OK, created=false.
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return UserUpsertResponseSchema(
        id=result.user.id,
        telegram_id=result.user.telegram_id,
        username=result.user.username,
        created_at=result.user.created_at,
        updated_at=result.user.updated_at,
        created=result.created,
    )
