"""
Фикстуры F001.

## Трассируемость
Feature: F001.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from bot.node.start.answer.service_unavailable_answer import (
    ServiceUnavailableAnswer,
)
from bot.node.start.answer.welcome_back_answer import WelcomeBackAnswer
from bot.node.start.answer.welcome_new_answer import WelcomeNewAnswer
from bot.node.start.code.start_code import StartCode


@pytest.fixture
def code_with_api(mock_users_api):
    return StartCode(api=mock_users_api)


@pytest.fixture
def spy_registry():
    """Реестр с отслеживаемыми run-методами."""
    new = WelcomeNewAnswer()
    back = WelcomeBackAnswer()
    unav = ServiceUnavailableAnswer()
    new.run = AsyncMock(side_effect=new.run)
    back.run = AsyncMock(side_effect=back.run)
    unav.run = AsyncMock(side_effect=unav.run)
    return {
        "welcome_new": new,
        "welcome_back": back,
        "service_unavailable": unav,
    }
