"""
Сборка всех роутеров бота.

## Трассируемость
Project: Neuronium Companion Bot.
"""
from __future__ import annotations

from aiogram import Dispatcher

from bot.handler.v1.user.router import user_router


def include_routers(dp: Dispatcher) -> None:
    dp.include_router(user_router)
