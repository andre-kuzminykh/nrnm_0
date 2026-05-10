"""
Прикладные исключения. Транслируются в HTTP-ответы exception_handlers'ом.

## Трассируемость
Feature: F001 (NotFoundError, ValidationError используются service-слоем).
"""
from __future__ import annotations


class AppException(Exception):
    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class NotFoundError(AppException):
    status_code = 404
    code = "not_found"


class ValidationError(AppException):
    status_code = 400
    code = "validation_error"
