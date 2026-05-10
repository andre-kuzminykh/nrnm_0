"""
UserModel — учётка Telegram-пользователя в системе.

## Трассируемость
Feature: F001 — Регистрация пользователя по Telegram ID.
Scenarios: SC001, SC002, SC003, SC004.
Business rules: BR001 (уникальность tg_id), BR002 (username без '@').
"""
from __future__ import annotations

from sqlalchemy import BigInteger, Column, String

from service.model.base_model import Base, BaseModel


class UserModel(Base, BaseModel):
    __tablename__ = "users"

    telegram_id = Column(BigInteger, nullable=False, unique=True, index=True)
    username = Column(String(64), nullable=True)
