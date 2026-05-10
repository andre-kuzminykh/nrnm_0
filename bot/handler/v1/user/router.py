"""
Роутеры по тегам.

## Трассируемость
Project: Neuronium Companion Bot.
"""
from __future__ import annotations

from aiogram import Router

start_router = Router(name="user.start")

user_router = Router(name="user")
user_router.include_router(start_router)

# Импорт виджетов ради side-эффекта регистрации хендлеров.
from bot.handler.v1.user.start.F001 import start_widget  # noqa: F401,E402
