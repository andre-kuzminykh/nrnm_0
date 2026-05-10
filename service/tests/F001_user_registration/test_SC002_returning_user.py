"""
Тест SC002 — повторная регистрация.

## Трассируемость
Feature: F001.
Scenario: SC002.
Business rule: BR001 (идемпотентность upsert).

## BDD
Given: Пользователь tg_id=123 уже существует.
When:  POST /api/v1/users с тем же tg_id.
Then:  200, created=false, в БД одна запись.
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_sc002_second_post_returns_created_false(
    client, api_prefix, sample_user_payload
):
    # Given
    first = await client.post(f"{api_prefix}/users", json=sample_user_payload)
    assert first.status_code == 201

    # When
    second = await client.post(f"{api_prefix}/users", json=sample_user_payload)

    # Then
    assert second.status_code == 200
    body = second.json()
    assert body["created"] is False
    assert body["telegram_id"] == 123
