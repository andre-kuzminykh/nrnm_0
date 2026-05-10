"""
Создание Bot и Dispatcher.

## Трассируемость
Project: Neuronium Companion Bot.

Если BOT_TOKEN не задан — Bot не создаётся (для CI/тестов). Запуск бота
требует валидного токена.
"""
from __future__ import annotations

from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.core.config import config


def build_bot() -> Optional[Bot]:
    if not config.bot_token:
        return None
    return Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def build_dispatcher() -> Dispatcher:
    return Dispatcher(storage=MemoryStorage())
