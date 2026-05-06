# Конфигурация сервиса TaskTrack

Все параметры задаются через переменные окружения. Бэкенд читает их через `pydantic-settings` из `.env.dev` (локально) или из окружения контейнера (прод).

---

## Подключение к базе данных

| Переменная | Обязательна | По умолчанию | Описание |
|---|---|---|---|
| `DATABASE_URL` | Да | `postgresql+asyncpg://tasktrack:tasktrack@localhost:5432/tasktrack` | Строка подключения к PostgreSQL (asyncpg-формат) |
| `POSTGRES_PASSWORD` | Да (prod) | — | Пароль PostgreSQL — используется только в `docker-compose.prod.yml` для подстановки в DATABASE_URL |

---

## Аутентификация пользователей

| Переменная | Обязательна | По умолчанию | Описание |
|---|---|---|---|
| `AUTH_STUB` | Нет | `false` | Если `true` — отключает проверку JWT. Все запросы принимаются как аутентифицированные (для локальной разработки). Запрещено в prod. |
| `KEYCLOAK_URL` | Нет* | `https://auth.busypage.ru` | URL Keycloak-сервера. *Обязательна при `AUTH_STUB=false`. |
| `KEYCLOAK_REALM` | Нет* | `home` | Realm в Keycloak. |
| `KEYCLOAK_CLIENT_ID` | Нет* | `tasktrack` | Client ID приложения в Keycloak. |

При `AUTH_STUB=false` бэкенд валидирует JWT через JWKS-эндпоинт Keycloak (`/realms/{realm}/protocol/openid-connect/certs`). Первый вход автоматически создаёт запись User по `sub`-клейму JWT.

---

## CORS

| Переменная | Обязательна | По умолчанию | Описание |
|---|---|---|---|
| `CORS_ORIGINS` | Нет | `["http://localhost:5173"]` | Разрешённые Origin для CORS. Принимает JSON-массив строк или строку, разделённую запятыми: `https://tasktrack.busypage.ru` или `["https://a.ru","https://b.ru"]`. |

---

## MCP-сервер для агентов

MCP-сервер встроен в основное приложение и доступен по `GET /mcp/sse`. Все параметры опциональны — при отсутствии конфигурации MCP-инструменты вернут ошибку при вызове.

| Переменная | Обязательна | По умолчанию | Описание |
|---|---|---|---|
| `MCP_AGENT_USER_ID` | Нет | — | UUID пользователя БД для dev-режима (один агент, без проверки ключа). Создаётся через `make mcp-bootstrap`. |
| `MCP_AGENTS` | Нет | `""` | Маппинг ключей → UUID пользователей для prod/multi-agent режима. Формат: `key1:uuid1,key2:uuid2`. Если задано — API-ключ в `Authorization: Bearer <key>` обязателен. |

**Приоритет:** если `MCP_AGENTS` задан и не пустой — используется он. Иначе — `MCP_AGENT_USER_ID`. Оба могут быть заданы одновременно (например, один агент без ключа для dev, несколько с ключами для prod — в разных env-файлах).

### Как создать агент-пользователей

```bash
cd backend

# Один агент (dev)
python scripts/bootstrap_agent_user.py
# → MCP_AGENT_USER_ID=<uuid>

# Именованные агенты (prod)
python scripts/bootstrap_agent_user.py --email pm-agent@tasktrack
# → Add to MCP_AGENTS: <your-key>:<uuid>

python scripts/bootstrap_agent_user.py --email exec-agent@tasktrack
# → Add to MCP_AGENTS: <your-key>:<uuid>
```

### Примеры конфигурации

**Dev (один агент, без ключа):**
```
MCP_AGENT_USER_ID=550e8400-e29b-41d4-a716-446655440000
```

**Prod (два агента с ключами):**
```
MCP_AGENTS=pm-secret-abc:550e8400-e29b-41d4-a716-446655440000,exec-secret-xyz:6ba7b810-9dad-11d1-80b4-00c04fd430c8
```

### Подключение агента (`.mcp.json`)

```json
{
  "mcpServers": {
    "tasktrack-pm": {
      "type": "sse",
      "url": "https://tasktrack.busypage.ru/mcp/sse",
      "headers": { "Authorization": "Bearer pm-secret-abc" }
    }
  }
}
```

Для dev (сервер на `localhost:8000`, `MCP_AGENT_USER_ID` задан, ключ не нужен):
```json
{
  "mcpServers": {
    "tasktrack-dev": {
      "type": "sse",
      "url": "http://localhost:8000/mcp/sse"
    }
  }
}
```

---

## Переменные Docker Compose

Используются только в `docker-compose.prod.yml` и `docker-compose.yml`, не читаются бэкендом напрямую.

| Переменная | Описание |
|---|---|
| `POSTGRES_PASSWORD` | Пароль PostgreSQL для инициализации контейнера `postgres:16-alpine` |

---

## Полные примеры env-файлов

### `.env.dev` (локальная разработка)

```bash
DATABASE_URL=postgresql+asyncpg://tasktrack:tasktrack@localhost:5432/tasktrack
AUTH_STUB=true
KEYCLOAK_URL=https://auth.busypage.ru
KEYCLOAK_REALM=home
KEYCLOAK_CLIENT_ID=tasktrack
CORS_ORIGINS=["http://localhost:5173"]

# MCP — опционально. После make mcp-bootstrap:
# MCP_AGENT_USER_ID=<uuid из вывода bootstrap>
```

### `.env.prod` (production)

```bash
# Auth
AUTH_STUB=false
KEYCLOAK_URL=https://auth.busypage.ru
KEYCLOAK_REALM=home
KEYCLOAK_CLIENT_ID=tasktrack

# Database
DATABASE_URL=postgresql+asyncpg://tasktrack:CHANGE_ME@postgres:5432/tasktrack
POSTGRES_PASSWORD=CHANGE_ME

# CORS
CORS_ORIGINS=https://tasktrack.busypage.ru

# MCP агенты (опционально — только если используются AI-агенты)
# MCP_AGENTS=pm-secret:uuid1,exec-secret:uuid2
```

---

## Фронтенд (Vite build-time переменные)

Фронтенд собирается на этапе `docker build` — переменные запекаются в JS-бандл через `--build-arg`. Менять после сборки нельзя.

| Переменная | По умолчанию в Dockerfile | Описание |
|---|---|---|
| `VITE_AUTH_STUB` | `false` | Если `"true"` — фронтенд показывает debug-панель переключения пользователей вместо OIDC-логина |
| `VITE_KEYCLOAK_URL` | `https://auth.busypage.ru` | URL Keycloak — должен совпадать с `KEYCLOAK_URL` бэкенда |
| `VITE_KEYCLOAK_REALM` | `home` | Realm — должен совпадать с `KEYCLOAK_REALM` |
| `VITE_KEYCLOAK_CLIENT_ID` | `tasktrack` | Client ID — должен совпадать с `KEYCLOAK_CLIENT_ID` |

Для локальной разработки без Docker: создать `frontend/.env.local`:
```bash
VITE_AUTH_STUB=true
VITE_KEYCLOAK_URL=https://auth.busypage.ru
VITE_KEYCLOAK_REALM=home
VITE_KEYCLOAK_CLIENT_ID=tasktrack
```
