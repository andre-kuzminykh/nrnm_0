"""
Core layer — конфиг, БД, загрузчик приложения, исключения.

## Трассируемость
Project: Neuronium Companion Backend.
"""
from service.core.config import config
from service.core.database import db_connect
from service.core.exceptions import (
    AppException,
    NotFoundError,
    ValidationError,
)
from service.core.loader import app

__all__ = [
    "config",
    "db_connect",
    "app",
    "AppException",
    "NotFoundError",
    "ValidationError",
]
