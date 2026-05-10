"""
Тест SC001 — новый пользователь.

## Трассируемость
Feature: F001 — Регистрация пользователя.
Scenario: SC001 — новый пользователь.
Business rule: BR001 (упомянут в SC002).

## BDD
Given: В БД нет пользователя с tg_id=123.
When:  POST /api/v1/users {tg_id:123, username:'alice'}.
Then:  201, body.telegram_id=123, body.created=true.
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_sc001_creates_user_returns_created_true(client, api_prefix, sample_user_payload):
    """SC001 — пустая БД, новый POST → 201 + created=true."""
    # When
    response = await client.post(f"{api_prefix}/users", json=sample_user_payload)
    # Then
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["telegram_id"] == 123
    assert body["username"] == "alice"
    assert body["created"] is True


@pytest.mark.asyncio
async def test_sc001_username_at_prefix_is_stripped(client, api_prefix):
    """BR002 — '@' в username не сохраняется."""
    response = await client.post(
        f"{api_prefix}/users", json={"tg_id": 999, "username": "@bob"}
    )
    assert response.status_code == 201
    assert response.json()["username"] == "bob"
