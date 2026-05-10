"""
WelcomeNewAnswer — экран для новых пользователей.

## Трассируемость
Feature: F001.
Scenario: SC001.
"""
from __future__ import annotations

from typing import Any

from bot.core.vocab import t


class WelcomeNewAnswer:
    name = "welcome_new"

    async def run(self, *, event: Any, user_lang: str, data: dict) -> None:
        await event.answer(t(user_lang, "welcome_new"))
