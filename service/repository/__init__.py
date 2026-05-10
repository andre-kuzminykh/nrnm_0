"""
Repository-слой: чистый CRUD над моделью.

## Трассируемость
Project: Neuronium Companion Backend.
"""
from service.repository.base_repository import BaseRepository
from service.repository.users.user_repository import UserRepository

__all__ = ["BaseRepository", "UserRepository"]
