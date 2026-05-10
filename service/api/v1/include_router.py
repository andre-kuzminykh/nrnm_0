"""
Подключение роутеров v1.

## Трассируемость
Feature: F001.
"""
from __future__ import annotations

from fastapi import FastAPI

from service.api.v1.endpoints import users_router
from service.core.config import config


def include_routers(app: FastAPI) -> None:
    app.include_router(users_router, prefix=f"{config.api_v1_prefix}/users", tags=["users"])
