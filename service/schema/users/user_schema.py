"""
Pydantic-схемы пользователя.

## Трассируемость
Feature: F001.
Scenarios: SC001, SC002, SC003.
Business rules: BR002 (username без '@'), BR003 (tg_id > 0).
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserCreateSchema(BaseModel):
    """Запрос на регистрацию/upsert пользователя."""

    tg_id: int = Field(..., gt=0, description="Telegram user id, > 0 (BR003).")
    username: Optional[str] = Field(default=None, max_length=64)

    @field_validator("username")
    @classmethod
    def _strip_at(cls, v: Optional[str]) -> Optional[str]:
        # BR002: username хранится без префикса '@'.
        if v is None:
            return v
        v = v.strip()
        if v.startswith("@"):
            v = v[1:]
        return v or None


class UserResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    username: Optional[str]
    created_at: datetime
    updated_at: datetime


class UserUpsertResponseSchema(UserResponseSchema):
    """Ответ POST /users: тот же User + флаг created."""

    created: bool
