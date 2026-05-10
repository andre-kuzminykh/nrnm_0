# Telegram Bot + Backend — архитектура

Этот документ — конкретизация спецификации виджетной архитектуры (Trigger →
Code → Answer) и слоистого FastAPI-бэкенда применительно к репозиторию.

## Layout

```
repo/
├── bot/                       # aiogram 3 — UI-слой
│   ├── app.py                 # точка входа
│   ├── prd.json               # требования (источник правды)
│   ├── core/                  # config, loader, vocab
│   ├── node/{tag}/            # Trigger / Code / Answer (LEGO-кирпичики)
│   ├── handler/v1/user/{tag}/{F###}/  # виджеты-оркестраторы
│   ├── service/api/           # HTTP-клиенты к backend
│   ├── callback/              # callback-data классы
│   ├── state/                 # FSM-состояния
│   └── tests/{F###}_{name}/   # моки aiogram + bot.service.api
│
├── service/                   # FastAPI — данные + логика
│   ├── main.py                # uvicorn entrypoint
│   ├── prd.json
│   ├── core/                  # config, database, loader, exceptions
│   ├── model/                 # SQLAlchemy ORM
│   ├── schema/                # Pydantic
│   ├── repository/            # CRUD
│   ├── service/               # бизнес-логика
│   ├── api/v1/endpoints/      # FastAPI routes
│   └── tests/{F###}_{name}/   # реальный SQLite + httpx ASGI
```

## Изоляция

- Бот **никогда** не импортирует `service.*` (бэкенд) и не лезет в БД.
- Бэкенд **никогда** не знает о Telegram, кроме того, что есть Telegram ID.
- Бот → Backend только через `bot/service/api/` (httpx).

## Текущие фичи

| ID | Название | Бэк | Бот |
|----|----------|-----|-----|
| F001 | Команда /start (регистрация) | `POST /api/v1/users`, `GET /api/v1/users/{tg_id}` | `bot.handler.v1.user.start.F001.start_widget` |

## Запуск

### Бэкенд (dev)

```bash
pip install -e ".[service]"
uvicorn service.main:app --reload --port 8000
# OpenAPI: http://localhost:8000/docs
```

### Бот

```bash
pip install -e ".[bot]"
BOT_TOKEN=<токен> BACKEND_URL=http://localhost:8000 python -m bot.app
```

### Тесты

```bash
pytest -q            # 168: neuronium 157 + backend 7 + bot 4
```

## Добавление новой фичи (короткий рецепт)

1. **PRD**: добавить feature в оба `prd.json` (бэк и/или бот) с
   `feature_id`, `acceptance_criteria`, `test_cases`.
2. **Бэкенд** (если нужны данные): `model/{group}/X_model.py` →
   `alembic revision --autogenerate` → `schema/` → `repository/` →
   `service/` → `api/v1/endpoints/{group}/...` → подключить роутер.
3. **Бот**: `bot/service/api/X_api.py` (HTTP-клиент) →
   `node/{tag}/{trigger,code,answer}/` → `handler/v1/user/{tag}/{F###}/X_widget.py`.
4. **Тесты**: `service/tests/F###_*/test_SC*_*.py` (httpx + SQLite),
   `bot/tests/F###_*/test_SC*_*.py` (моки).
5. Все модули содержат блок `## Трассируемость` со ссылкой на Feature и
   Scenarios.
