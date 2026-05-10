"""
WelcomeBackAnswer — экран для вернувшегося пользователя.

## Трассируемость
Feature: F001.
Scenario: SC002.
"""
from __future__ import annotations

from typing import Any

from bot.core.vocab import t


class WelcomeBackAnswer:
    name = "welcome_back"

    async def run(self, *, event: Any, user_lang: str, data: dict) -> None:
        await event.answer(t(user_lang, "welcome_back"))
