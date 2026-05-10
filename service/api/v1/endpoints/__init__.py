"""
Экспорты роутеров endpoint-групп.

## Трассируемость
Feature: F001.
"""
from service.api.v1.endpoints.users import router as users_router

__all__ = ["users_router"]
