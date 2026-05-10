"""
Точка входа бэкенд-сервиса.

Запуск (dev):

    uvicorn service.main:app --reload --host 0.0.0.0 --port 8000

## Трассируемость
Project: Neuronium Companion Backend.
"""
from __future__ import annotations

from service.core.loader import app  # noqa: F401  (re-export для uvicorn)
