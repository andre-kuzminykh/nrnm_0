"""
Точка входа бота.

Запуск:

    BOT_TOKEN=... BACKEND_URL=http://localhost:8000 python -m bot.app

## Трассируемость
Project: Neuronium Companion Bot.
"""
from __future__ import annotations

import asyncio
import logging
import sys

from bot.core.config import config
from bot.core.loader import build_bot, build_dispatcher
from bot.handler.include_router import include_routers


async def main() -> None:
    logging.basicConfig(level=config.log_level.upper(), stream=sys.stdout)

    bot = build_bot()
    if bot is None:
        raise RuntimeError(
            "BOT_TOKEN не задан. Поставьте env BOT_TOKEN перед запуском."
        )
    dp = build_dispatcher()
    include_routers(dp)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
