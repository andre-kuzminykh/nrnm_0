"""
Users — endpoint-группа.

## Трассируемость
Feature: F001.
Scenarios: SC001, SC002, SC003, SC004.
"""
from fastapi import APIRouter

router = APIRouter()

# Зарегистрировать обработчики (импорт ради side-эффекта декораторов).
from service.api.v1.endpoints.users import post as _post  # noqa: F401,E402
from service.api.v1.endpoints.users import get as _get  # noqa: F401,E402
