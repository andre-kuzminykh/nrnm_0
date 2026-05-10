"""
Виджет F001: команда /start.

## Трассируемость
Feature: F001 — Команда /start.
Scenarios:
  - SC001 — новый пользователь → answer: welcome_new.
  - SC002 — вернувшийся → answer: welcome_back.
  - SC003 — бэкенд недоступен → answer: service_unavailable.

Связывает Trigger → Code → Answer для команды /start.
"""
from __future__ import annotations

from typing import Any, Mapping

from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.handler.v1.user.router import start_router
from bot.node.start.answer.service_unavailable_answer import (
    ServiceUnavailableAnswer,
)
from bot.node.start.answer.welcome_back_answer import WelcomeBackAnswer
from bot.node.start.answer.welcome_new_answer import WelcomeNewAnswer
from bot.node.start.code.start_code import StartCode
from bot.node.start.trigger.start_trigger import StartTrigger

ANSWER_REGISTRY: Mapping[str, Any] = {
    "welcome_new": WelcomeNewAnswer(),
    "welcome_back": WelcomeBackAnswer(),
    "service_unavailable": ServiceUnavailableAnswer(),
}


async def handle_start(
    message: Message,
    state: FSMContext,
    *,
    trigger: StartTrigger | None = None,
    code: StartCode | None = None,
    registry: Mapping[str, Any] | None = None,
) -> str:
    """Trigger → Code → Answer.

    `trigger`/`code`/`registry` параметризованы ради тестов; в проде
    создаются по умолчанию.
    """
    trigger = trigger or StartTrigger()
    code = code or StartCode()
    registry = registry or ANSWER_REGISTRY

    trigger_data = await trigger.run(message, state)
    code_result = await code.run(trigger_data, state)
    answer_name = code_result["answer_name"]
    answer = registry[answer_name]

    lang = "ru"
    user = getattr(message, "from_user", None)
    if user is not None and getattr(user, "language_code", None) == "en":
        lang = "en"

    await answer.run(event=message, user_lang=lang, data=code_result.get("data", {}))
    return answer_name


@start_router.message(Command("start"))
async def _on_start(message: Message, state: FSMContext) -> None:
    await handle_start(message, state)
