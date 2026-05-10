"""
UsersAPI — HTTP-клиент к бэкенду пользователей.

## Трассируемость
Feature: F001.
Scenarios: SC001, SC002, SC003.
"""
from __future__ import annotations

from typing import Optional

import httpx

from bot.core.config import config


class UsersAPI:
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout_s: Optional[float] = None,
    ) -> None:
        self._base_url = (base_url or config.backend_url).rstrip("/")
        self._timeout = timeout_s or config.request_timeout_s

    async def register(self, tg_id: int, username: Optional[str]) -> dict:
        """Идемпотентная регистрация. Возвращает dict с ключом 'created'."""
        async with httpx.AsyncClient(
            base_url=self._base_url, timeout=self._timeout
        ) as client:
            response = await client.post(
                "/api/v1/users", json={"tg_id": tg_id, "username": username}
            )
            response.raise_for_status()
            return response.json()
