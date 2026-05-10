"""
StartCode — логика обработки /start.

## Трассируемость
Feature: F001.
Scenarios: SC001 (новый → welcome_new), SC002 (вернувшийся → welcome_back),
SC003 (бэкенд недоступен → service_unavailable).
Business rules: BR001, BR002.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from bot.service.api.users_api import UsersAPI

_log = logging.getLogger(__name__)


class StartCode:
    def __init__(self, api: Optional[UsersAPI] = None) -> None:
        self._api = api or UsersAPI()

    async def run(self, trigger_data: dict, state: Any) -> dict:
        tg_id = trigger_data.get("tg_id")
        username = trigger_data.get("username")
        if tg_id is None:
            # SC003 fallback: невозможно определить пользователя.
            return {"answer_name": "service_unavailable", "data": {}}
        try:
            api_result = await self._api.register(tg_id=tg_id, username=username)
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            _log.warning("backend unavailable on /start: %s", exc)
            return {"answer_name": "service_unavailable", "data": {}}
        answer_name = "welcome_new" if api_result.get("created") else "welcome_back"
        return {
            "answer_name": answer_name,
            "data": {"tg_id": tg_id, "username": username, "api": api_result},
        }
