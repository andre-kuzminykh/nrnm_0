"""
Дополнительный кейс SC003 — HTTPStatusError.

## Трассируемость
Feature: F001.
Scenario: SC003.
"""
from __future__ import annotations

import httpx
import pytest

from bot.handler.v1.user.start.F001.start_widget import handle_start
from bot.node.start.trigger.start_trigger import StartTrigger


@pytest.mark.asyncio
async def test_sc003_http_status_error_falls_back(
    mock_message, mock_state, code_with_api, spy_registry, mock_users_api
):
    request = httpx.Request("POST", "http://x")
    response = httpx.Response(500, request=request)
    mock_users_api.register.side_effect = httpx.HTTPStatusError(
        "server error", request=request, response=response
    )

    name = await handle_start(
        mock_message,
        mock_state,
        trigger=StartTrigger(),
        code=code_with_api,
        registry=spy_registry,
    )

    assert name == "service_unavailable"
