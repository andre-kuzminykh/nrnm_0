"""
ServiceUnavailableAnswer — экран при недоступном бэкенде.

## Трассируемость
Feature: F001.
Scenario: SC003.
"""
from __future__ import annotations

from typing import Any

from bot.core.vocab import t


class ServiceUnavailableAnswer:
    name = "service_unavailable"

    async def run(self, *, event: Any, user_lang: str, data: dict) -> None:
        await event.answer(t(user_lang, "service_unavailable"))
