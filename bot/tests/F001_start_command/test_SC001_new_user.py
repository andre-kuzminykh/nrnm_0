"""
Тест SC001 — новый пользователь видит welcome_new.

## Трассируемость
Feature: F001 — Команда /start.
Scenario: SC001 — новый пользователь.

## BDD
Given: Бэкенд возвращает created=true.
When:  Виджет обрабатывает /start.
Then:  Вызван welcome_new_answer.run; message.answer вызван.
"""
from __future__ import annotations

import pytest

from bot.handler.v1.user.start.F001.start_widget import handle_start
from bot.node.start.trigger.start_trigger import StartTrigger


@pytest.mark.asyncio
async def test_sc001_new_user_sees_welcome_new(
    mock_message, mock_state, code_with_api, spy_registry, mock_users_api
):
    # Given
    mock_users_api.register.return_value = {"created": True, "telegram_id": 123}

    # When
    name = await handle_start(
        mock_message,
        mock_state,
        trigger=StartTrigger(),
        code=code_with_api,
        registry=spy_registry,
    )

    # Then
    assert name == "welcome_new"
    spy_registry["welcome_new"].run.assert_awaited_once()
    spy_registry["welcome_back"].run.assert_not_awaited()
    spy_registry["service_unavailable"].run.assert_not_awaited()
    mock_message.answer.assert_awaited_once()
    mock_state.clear.assert_awaited_once()
