"""
Тест SC003 — валидация tg_id.

## Трассируемость
Feature: F001.
Scenario: SC003.
Business rule: BR003 (tg_id > 0).

## BDD
Given: Запрос с tg_id=-1.
When:  POST /api/v1/users.
Then:  422 (validation error), запись не создаётся.
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_sc003_negative_tg_id_rejected(client, api_prefix):
    response = await client.post(
        f"{api_prefix}/users", json={"tg_id": -1, "username": "x"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_sc003_zero_tg_id_rejected(client, api_prefix):
    response = await client.post(
        f"{api_prefix}/users", json={"tg_id": 0}
    )
    assert response.status_code == 422
