"""
Тест SC004 — GET по telegram_id.

## Трассируемость
Feature: F001.
Scenario: SC004.

## BDD
Given: Пользователь tg_id=123 в БД.
When:  GET /api/v1/users/123.
Then:  200, body.telegram_id=123.
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_sc004_get_existing_user(client, api_prefix, sample_user_payload):
    await client.post(f"{api_prefix}/users", json=sample_user_payload)
    response = await client.get(f"{api_prefix}/users/123")
    assert response.status_code == 200
    assert response.json()["telegram_id"] == 123


@pytest.mark.asyncio
async def test_sc004_get_missing_user_404(client, api_prefix):
    response = await client.get(f"{api_prefix}/users/777")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"
