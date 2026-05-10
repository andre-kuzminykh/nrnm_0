"""
Тексты, команды, кнопки. Иерархия: vocab[<lang>][<key>].

## Трассируемость
Project: Neuronium Companion Bot.
Feature: F001 (welcome_new, welcome_back, service_unavailable).
"""
from __future__ import annotations

VOCAB: dict[str, dict[str, str]] = {
    "ru": {
        "welcome_new": (
            "👋 <b>Добро пожаловать в Neuronium Companion!</b>\n"
            "Я — твой ассистент. Готов помочь."
        ),
        "welcome_back": (
            "🙌 <b>С возвращением!</b>\n"
            "Рад снова тебя видеть."
        ),
        "service_unavailable": (
            "⚙️ Сервис временно недоступен. Попробуй ещё раз через минуту."
        ),
    },
    "en": {
        "welcome_new": (
            "👋 <b>Welcome to Neuronium Companion!</b>\nI'm here to help."
        ),
        "welcome_back": "🙌 <b>Welcome back!</b>",
        "service_unavailable": "⚙️ Service is temporarily unavailable. Try again later.",
    },
}


def t(lang: str, key: str) -> str:
    return VOCAB.get(lang, VOCAB["ru"]).get(key, key)
