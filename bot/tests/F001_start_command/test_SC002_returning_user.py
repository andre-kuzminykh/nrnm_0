"""
Тест SC002 — вернувшийся пользователь видит welcome_back.

## Трассируемость
Feature: F001.
Scenario: SC002.

## BDD
Given: Бэкенд возвращает created=false.
When:  Виджет обрабатывает /start.
Then:  Вызван welcome_back_answer.run.
"""
from __future__ import annotations

import pytest

from bot.handler.v1.user.start.F001.start_widget import handle_start
from bot.node.start.trigger.start_trigger import StartTrigger


@pytest.mark.asyncio
async def test_sc002_returning_user_sees_welcome_back(
    mock_message, mock_state, code_with_api, spy_registry, mock_users_api
):
    mock_users_api.register.return_value = {"created": False, "telegram_id": 123}

    name = await handle_start(
        mock_message,
        mock_state,
        trigger=StartTrigger(),
        code=code_with_api,
        registry=spy_registry,
    )

    assert name == "welcome_back"
    spy_registry["welcome_back"].run.assert_awaited_once()
    spy_registry["welcome_new"].run.assert_not_awaited()
