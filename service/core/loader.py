"""
FastAPI-приложение и lifespan-инициализация.

## Трассируемость
Feature: F001.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from service.core.database import db_connect
from service.model.base_model import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with db_connect.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Neuronium Companion Backend", version="0.1.0", lifespan=lifespan)


def _wire() -> None:
    from service.api.v1.exception_handlers import register_exception_handlers
    from service.api.v1.include_router import include_routers

    register_exception_handlers(app)
    include_routers(app)


_wire()
