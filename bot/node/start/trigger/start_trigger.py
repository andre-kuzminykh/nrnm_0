"""
StartTrigger — визуальные операции на входе /start.

## Трассируемость
Feature: F001 — Команда /start.
Scenarios: SC001, SC002, SC003.

Сейчас: сбрасывает FSM-состояние и извлекает идентификаторы пользователя
из сообщения. Удалять предыдущие экраны не требуется — /start всегда стартовый.
"""
from __future__ import annotations

from typing import Any


class StartTrigger:
    async def run(self, event: Any, state: Any) -> dict:
        if state is not None and hasattr(state, "clear"):
            await state.clear()
        user = getattr(event, "from_user", None)
        return {
            "tg_id": getattr(user, "id", None),
            "username": getattr(user, "username", None),
        }
