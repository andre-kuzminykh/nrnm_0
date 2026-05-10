"""
Базовая ORM-модель: id, created_at, updated_at.

## Трассируемость
Project: Neuronium Companion Backend.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class BaseModel:
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def to_dict(self) -> dict:
        return {
            c.name: (v.isoformat() if isinstance((v := getattr(self, c.name)), datetime) else v)
            for c in self.__table__.columns
        }
