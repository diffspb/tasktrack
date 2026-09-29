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

## Режим установки

| Переменная | Обязательна | По умолчанию | Описание |
|---|---|---|---|
| `APP_ENV` | Нет | `dev` | `production` задаётся в Docker-образе. При нём приложение **не стартует** с `AUTH_STUB=true` и с MCP без ключа (`MCP_AGENT_USER_ID` без `MCP_AGENTS`). Локально не задавать. |

---

## MCP-сервер для агентов

MCP-сервер встроен в основное приложение и доступен по `GET /mcp/sse`.

**Рекомендуемый способ — ключи служебных учётных записей** ([ADR-017](./decisions/ADR-017-service-accounts-api-keys.md)): переменные окружения не нужны, ключ работает и в MCP, и в REST, отзывается без перезапуска.

```bash
# на сервере, внутри контейнера приложения
python scripts/service_account.py create --email pm-agent@agents --name "PM agent"
python scripts/service_account.py issue  --email pm-agent@agents --key-name laptop --expires-days 90
# → token (shown once): tt_…
python scripts/service_account.py keys   --email pm-agent@agents
python scripts/service_account.py rotate --key-id <id>     # или revoke
```

Затем добавить учётную запись участником нужных проектов (роль `viewer` — только чтение) и указать токен в `.mcp.json` вместо `pm-secret-abc` в примере ниже.

Переменные ниже — **устаревший** способ (оставлен для существующих агентов):

| Переменная | Обязательна | По умолчанию | Описание |
|---|---|---|---|
| `MCP_AGENT_USER_ID` | Нет | — | UUID пользователя БД для dev-режима (один агент, без проверки ключа). Создаётся через `make mcp-bootstrap`. Запрещён при `APP_ENV=production`. |
| `MCP_AGENTS` | Нет | `""` | _Устарел._ Маппинг ключей → UUID пользователей для prod/multi-agent режима. Формат: `key1:uuid1,key2:uuid2`. Если задано — API-ключ в `Authorization: Bearer <key>` обязателен. |

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

## Развёртывание через PaaS-деплоер

Рабочая установка разворачивается деплоером из `/home/sanek/projects/codex/paas` (контракт — его `docs/platform-contract.md`, базовая инфраструктура VPS — `/home/sanek/projects/claudecode/simple`). Деплоер клонирует репозиторий, собирает образ из исходников и запускает `docker compose -p prod-tasktrack --env-file <project.env> -f docker-compose.yml -f docker-compose.prod.yml -f <override> up -d --build --force-recreate`. Traefik-метки генерирует он же — в compose-файлах репозитория их нет.

**Регистрация проекта** (один раз):

```bash
deployer projects add prod tasktrack --git-url git@github.com:diffspb/tasktrack.git --default-ref main \
    --compose-file docker-compose.yml --compose-file docker-compose.prod.yml
deployer components add prod tasktrack app --mode compose --compose-service app --port 8000
deployer endpoints add prod tasktrack web app --port 8000 --subdomain tasktrack \
    --auth none --middleware secure-headers@file --health-path /api/v1/health
deployer projects env-set prod tasktrack POSTGRES_PASSWORD=<пароль>
deployer projects env-set prod tasktrack CORS_ORIGINS=https://tasktrack.busypage.ru
deployer deploy prod tasktrack --ref main
```

`--auth none` обязателен: приложение само проверяет вход (Keycloak в браузере, ключи API у агентов); SSO-прокси перед ним сломал бы REST- и MCP-клиентов с `Authorization: Bearer`. `deployer.yml` в корне репозитория описывает то же самое в формате импорта деплоера.

**Переменные окружения** хранит деплоер (`deployer projects env-set prod tasktrack KEY=value`); они попадают и в подстановку `${…}` compose-файлов, и в окружение контейнера `app`. Файл `.env.prod` в этом способе не используется.

| Переменная | Обязательна | Значение для рабочей установки |
|---|---|---|
| `POSTGRES_PASSWORD` | Да | Пароль БД; без него compose не запустится |
| `CORS_ORIGINS` | Да | `https://tasktrack.busypage.ru` |
| `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID` | Нет | По умолчанию `https://auth.busypage.ru`, `home`, `tasktrack` |
| `APP_ENV` | — | Не задавать: `production` уже задан в образе |
| `AUTH_STUB`, `MCP_AGENT_USER_ID` | — | Не задавать: при `APP_ENV=production` приложение с ними не стартует |

Keycloak-настройки фронтенда (`VITE_KEYCLOAK_*`) вшиваются при сборке образа; значения по умолчанию в `Dockerfile` соответствуют рабочей установке.

**Эксплуатация на сервере** (имя compose-проекта `prod-tasktrack`, compose-файлы не нужны):

```bash
# резервная копия и восстановление (скрипты — в deploy/ исходников)
TASKTRACK_PROJECT=prod-tasktrack bash deploy/backup.sh /var/backups/tasktrack
TASKTRACK_PROJECT=prod-tasktrack bash deploy/restore.sh /var/backups/tasktrack/<файл>.dump

# служебные учётные записи и ключи агентов (ADR-017)
docker compose -p prod-tasktrack exec app python scripts/service_account.py --help

# первичное наполнение справочников (типы задач, типы связей) на пустой БД —
# или кнопкой инициализации в системных настройках под суперпользователем
docker compose -p prod-tasktrack exec app python -c \
    "import asyncio; from app.core.bootstrap import ensure_system_data; asyncio.run(ensure_system_data())"
```

Перед выкладкой новой версии образ можно проверить локально: `bash deploy/smoke-test.sh` (см. `10-nfr.md`).

Прежний способ установки `deploy/install.sh` (готовый образ из ghcr + `.env.prod`) удалён 2026-09-29: образ никто не публиковал, а `.env.prod` не доходил до контейнера.

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

### Рабочая установка

Файла окружения нет: переменные задаются в PaaS-деплоере (`deployer projects env-set prod tasktrack KEY=value`, см. «Развёртывание через PaaS-деплоер»). Минимальный набор:

```bash
POSTGRES_PASSWORD=<пароль>                      # DATABASE_URL собирается в docker-compose.prod.yml
CORS_ORIGINS=https://tasktrack.busypage.ru
# KEYCLOAK_URL / KEYCLOAK_REALM / KEYCLOAK_CLIENT_ID — только если отличаются от значений по умолчанию
# APP_ENV=production задан в образе; AUTH_STUB и MCP_AGENT_USER_ID не задавать
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
