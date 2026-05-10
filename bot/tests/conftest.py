"""
Глобальные фикстуры для тестов бота.

## Трассируемость
Project: Neuronium Companion Bot.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def mock_message():
    msg = MagicMock()
    msg.from_user = MagicMock(id=123, username="alice", language_code="ru")
    msg.text = "/start"
    msg.answer = AsyncMock()
    return msg


@pytest.fixture
def mock_state():
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.set_data = AsyncMock()
    state.clear = AsyncMock()
    return state


@pytest.fixture
def mock_users_api():
    """Мок UsersAPI с настраиваемым register-результатом."""
    api = MagicMock()
    api.register = AsyncMock(return_value={"created": True, "telegram_id": 123})
    return api
