"""
Тест SC003 — недоступный бэкенд.

## Трассируемость
Feature: F001.
Scenario: SC003.
Business rule: BR002 (fallback при недоступном бэкенде).

## BDD
Given: UsersAPI.register бросает httpx.RequestError.
When:  Виджет обрабатывает /start.
Then:  Вызван service_unavailable_answer.run.
"""
from __future__ import annotations

import httpx
import pytest

from bot.handler.v1.user.start.F001.start_widget import handle_start
from bot.node.start.trigger.start_trigger import StartTrigger


@pytest.mark.asyncio
async def test_sc003_backend_down_falls_back(
    mock_message, mock_state, code_with_api, spy_registry, mock_users_api
):
    mock_users_api.register.side_effect = httpx.RequestError(
        "connection refused", request=httpx.Request("POST", "http://x")
    )

    name = await handle_start(
        mock_message,
        mock_state,
        trigger=StartTrigger(),
        code=code_with_api,
        registry=spy_registry,
    )

    assert name == "service_unavailable"
    spy_registry["service_unavailable"].run.assert_awaited_once()
    spy_registry["welcome_new"].run.assert_not_awaited()
    spy_registry["welcome_back"].run.assert_not_awaited()
