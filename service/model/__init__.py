"""
Model-слой.

## Трассируемость
Project: Neuronium Companion Backend.
"""
from service.model.base_model import Base, BaseModel
from service.model.users.user_model import UserModel

__all__ = ["Base", "BaseModel", "UserModel"]
