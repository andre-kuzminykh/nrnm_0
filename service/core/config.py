"""
Конфигурация бэкенд-сервиса.

## Трассируемость
Feature: F001 — Регистрация пользователя.
Все настройки берутся из env с разумными дефолтами для dev.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    db_url: str
    api_v1_prefix: str
    log_level: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            db_url=os.getenv(
                "DATABASE_URL",
                "sqlite+aiosqlite:///./neuronium_companion.db",
            ),
            api_v1_prefix=os.getenv("API_V1_PREFIX", "/api/v1"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


config = Config.from_env()
