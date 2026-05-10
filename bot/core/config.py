"""
Конфигурация бота. Берёт значения из env.

## Трассируемость
Project: Neuronium Companion Bot.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    bot_token: str
    backend_url: str
    request_timeout_s: float
    log_level: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            bot_token=os.getenv("BOT_TOKEN", ""),
            backend_url=os.getenv("BACKEND_URL", "http://localhost:8000"),
            request_timeout_s=float(os.getenv("REQUEST_TIMEOUT_S", "10")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


config = Config.from_env()
