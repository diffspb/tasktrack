# 17. Архитектура реализации

Документ для команды разработки. Описывает конкретную структуру проекта, ключевые решения и первые шаги.

Стек зафиксирован в [ADR-002](./decisions/ADR-002-tech-stack.md). Инфраструктура готова: Traefik v3 + Keycloak 24 + Netdata + Dozzle на `busypage.ru`. Паттерн новых приложений описан в `infra/simple/scripts/new-app.sh`.

---

## 1. Структура репозитория

Монорепо. Backend и frontend в одном репозитории — разработчик открывает один проект, shared-типы генерируются автоматически из OpenAPI-схемы, одна CI-пайплайн.

```
tasktrack/                        ← корень репозитория (уже существует)
├── CLAUDE.md
├── Makefile                      ← делегирует в backend/ и frontend/
├── docs/                         ← вся документация
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py           ← shared dependencies (get_current_user, get_db, pagination)
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py     ← include_router для всех доменов
│   │   │       ├── projects.py
│   │   │       ├── tasks.py
│   │   │       ├── assignments.py
│   │   │       ├── solutions.py
│   │   │       ├── decisions.py
│   │   │       ├── workflows.py
│   │   │       ├── users.py
│   │   │       └── auth.py
│   │   ├── core/
│   │   │   ├── auth.py           ← JWT-валидация из инфры (new-app.sh паттерн)
│   │   │   ├── auth_stub.py      ← AUTH_STUB=true заглушка для локальной разработки
│   │   │   ├── config.py         ← pydantic-settings
│   │   │   ├── db.py             ← async engine, get_session dependency
│   │   │   └── scheduler.py      ← APScheduler lifespan-интеграция
│   │   ├── models/               ← SQLAlchemy ORM модели
│   │   │   ├── base.py           ← Base, UUIDMixin, TimestampMixin
│   │   │   ├── user.py
│   │   │   ├── project.py
│   │   │   ├── task.py           ← Task, Assignment, TaskLink
│   │   │   ├── workflow.py       ← Workflow, Status, Transition
│   │   │   ├── decision.py       ← Solution, DecisionCriteria, TaskDecision
│   │   │   └── notification.py
│   │   ├── schemas/              ← Pydantic v2 схемы (request/response)
│   │   │   ├── project.py
│   │   │   ├── task.py
│   │   │   ├── decision.py
│   │   │   └── ...
│   │   ├── services/             ← бизнес-логика, всё нетривиальное — здесь
│   │   │   ├── task_service.py   ← CRUD + global_status transitions
│   │   │   ├── workflow_service.py
│   │   │   ├── decision_service.py  ← Decision Process state machine
│   │   │   └── notification_service.py
│   │   └── main.py
│   ├── alembic/
│   │   ├── env.py                ← async-совместимый
│   │   ├── script.py.mako
│   │   └── versions/
│   ├── tests/
│   │   ├── conftest.py           ← testcontainers PostgreSQL, AsyncClient
│   │   ├── test_projects.py
│   │   ├── test_tasks.py
│   │   └── test_decision_process.py
│   ├── Dockerfile
│   ├── docker-compose.yml        ← base (сети, volumes)
│   ├── docker-compose.dev.yml    ← dev Traefik labels, --reload, .env.dev
│   ├── docker-compose.prod.yml   ← prod Traefik labels, .env.prod
│   ├── Makefile
│   └── pyproject.toml
└── frontend/
    ├── src/
    │   ├── features/             ← feature-based структура
    │   │   ├── projects/
    │   │   │   ├── api.ts        ← TanStack Query hooks для проектов
    │   │   │   ├── ProjectList.tsx
    │   │   │   ├── ProjectForm.tsx
    │   │   │   └── index.ts
    │   │   ├── tasks/
    │   │   │   ├── api.ts
    │   │   │   ├── TaskBoard.tsx  ← Kanban
    │   │   │   ├── TaskDetail.tsx
    │   │   │   └── index.ts
    │   │   ├── decision-process/
    │   │   │   ├── api.ts
    │   │   │   ├── SolutionForm.tsx
    │   │   │   ├── DecisionPanel.tsx
    │   │   │   └── index.ts
    │   │   └── auth/
    │   │       ├── auth-client.ts  ← oidc-client-ts обёртка
    │   │       └── AuthProvider.tsx
    │   ├── shared/
    │   │   ├── api/
    │   │   │   ├── client.ts     ← axios/fetch с JWT инъекцией
    │   │   │   └── types.ts      ← сгенерированные из OpenAPI (openapi-typescript)
    │   │   ├── ui/               ← переиспользуемые компоненты поверх shadcn/ui
    │   │   └── hooks/
    │   ├── app/
    │   │   ├── router.tsx        ← React Router v7 маршруты
    │   │   └── App.tsx
    │   └── main.tsx
    ├── public/
    ├── package.json
    ├── vite.config.ts
    └── tsconfig.json
```

---

## 2. Архитектура бэкенда

### ORM: SQLAlchemy 2.0 async ORM

Не SQLModel (слишком ограниченный для сложных запросов), не чистый Core (слишком многословный для CRUD). SQLAlchemy 2.0 ORM в async-режиме даёт полный контроль над запросами и нормальную типизацию.

```python
# models/base.py
import uuid
from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

### Alembic: async env.py

```python
# alembic/env.py — ключевой фрагмент
from sqlalchemy.ext.asyncio import async_engine_from_config

def run_migrations_online():
    connectable = async_engine_from_config(config.get_section(config.config_ini_section))
    
    async def run():
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    
    asyncio.run(run())
```

### Auth: паттерн из инфры

Файл `app/core/auth.py` берётся напрямую из `new-app.sh` — там уже готова JWKS-валидация с кешированием на 1 час и `require_role()`. Только добавляем синхронизацию с нашей моделью User:

```python
# app/api/deps.py
async def get_current_user(
    session: AsyncSession = Depends(get_session),
    token_payload: dict = Depends(get_token_payload),  # из core/auth.py
) -> User:
    """Sync Keycloak user with local DB on first login."""
    sub = token_payload["sub"]
    user = await session.scalar(select(User).where(User.keycloak_id == sub))
    if not user:
        user = User(keycloak_id=sub, email=token_payload.get("email"), ...)
        session.add(user)
        await session.commit()
    return user
```

### AUTH_STUB для локальной разработки

```python
# app/core/auth_stub.py
from app.models.user import User

STUB_USER = User(
    id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
    email="dev@localhost",
    display_name="Dev User",
    is_active=True,
)

# app/api/deps.py
async def get_current_user(...) -> User:
    if settings.auth_stub:
        return STUB_USER
    # ... обычная логика
```

Включается через `AUTH_STUB=true` в `.env.dev`. В Dockerfile/prod — переменная не передаётся.

### APScheduler в lifespan

```python
# app/core/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(check_overdue_decisions, "interval", hours=1)
    scheduler.start()
    yield
    scheduler.shutdown()
```

### Логирование под Dozzle

Dozzle читает stdout/stderr контейнеров. Достаточно стандартного logging с JSON-форматом:

```python
# app/core/config.py
import logging, json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({"level": record.levelname, "msg": record.getMessage(), "logger": record.name})

logging.getLogger().addHandler(logging.StreamHandler())  # → stdout → Dozzle
```

---

## 3. Архитектура фронтенда

### Роутинг: React Router v7

TanStack Router лучше типизирован, но React Router v7 имеет data loaders, Actions, и достаточно TypeScript-дружелюбен. Для MVP выбираем стабильность.

```tsx
// app/router.tsx
import { createBrowserRouter } from "react-router-dom";

export const router = createBrowserRouter([
  { path: "/", element: <ProjectList /> },
  { path: "/projects/:projectId", element: <ProjectDetail /> },
  { path: "/projects/:projectId/tasks/:taskId", element: <TaskDetail /> },
]);
```

### Keycloak: oidc-client-ts

Не `keycloak-js` — он тянет legacy adapter, весит больше и хуже совместим с React 19. `oidc-client-ts` — чистый OIDC/OAuth2 клиент, фреймворк-независимый.

```typescript
// features/auth/auth-client.ts
import { UserManager } from "oidc-client-ts";

export const userManager = new UserManager({
  authority: import.meta.env.VITE_KEYCLOAK_URL + "/realms/home",
  client_id: "tasktrack",
  redirect_uri: window.location.origin + "/auth/callback",
  scope: "openid email profile",
});
```

### Типизация API: openapi-typescript

FastAPI автоматически генерирует `/openapi.json`. Команда `make gen-types` скачивает его и генерирует TypeScript-типы:

```bash
# Makefile (корневой)
gen-types:
    cd frontend && npx openapi-typescript http://localhost:8000/openapi.json -o src/shared/api/types.ts
```

После этого все схемы запросов/ответов типизированы без ручного написания.

### TanStack Query: инвалидация кэша

При переходах `global_status` задачи нужно инвалидировать несколько кэшей одновременно:

```typescript
// features/tasks/api.ts
export function useUpdateAssignmentStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (args) => api.patch(`/assignments/${args.id}/status`, args),
    onSuccess: (_, { taskId, projectId }) => {
      // Инвалидируем все представления, где задача может отображаться
      queryClient.invalidateQueries({ queryKey: ["task", taskId] });
      queryClient.invalidateQueries({ queryKey: ["tasks", projectId] });
      queryClient.invalidateQueries({ queryKey: ["my-tasks"] });
    },
  });
}
```

---

## 4. Интеграция с инфраструктурой

### Traefik: два роутера на один домен

Приложение будет доступно на `tasktrack.busypage.ru`. API-запросы (`/api/*`) идут в FastAPI, всё остальное — в nginx с Vite-билдом.

```yaml
# backend/docker-compose.prod.yml
services:
  api:
    image: tasktrack-api
    env_file: .env.prod
    networks:
      - traefik-public
    labels:
      - "traefik.enable=true"
      # API роутер (выше приоритет)
      - "traefik.http.routers.tasktrack-api.rule=Host(`tasktrack.busypage.ru`) && PathPrefix(`/api`)"
      - "traefik.http.routers.tasktrack-api.entrypoints=websecure"
      - "traefik.http.routers.tasktrack-api.tls.certresolver=letsencrypt"
      - "traefik.http.routers.tasktrack-api.middlewares=secure-headers@file"
      - "traefik.http.routers.tasktrack-api.service=tasktrack-api"
      - "traefik.http.routers.tasktrack-api.priority=20"
      - "traefik.http.services.tasktrack-api.loadbalancer.server.port=8000"

  frontend:
    image: tasktrack-frontend   # nginx + Vite build
    networks:
      - traefik-public
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.tasktrack-fe.rule=Host(`tasktrack.busypage.ru`)"
      - "traefik.http.routers.tasktrack-fe.entrypoints=websecure"
      - "traefik.http.routers.tasktrack-fe.tls.certresolver=letsencrypt"
      - "traefik.http.routers.tasktrack-fe.middlewares=secure-headers@file"
      - "traefik.http.routers.tasktrack-fe.service=tasktrack-fe"
      - "traefik.http.routers.tasktrack-fe.priority=10"
      - "traefik.http.services.tasktrack-fe.loadbalancer.server.port=80"

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: tasktrack
      POSTGRES_USER: tasktrack
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - tasktrack-db:/var/lib/postgresql/data
    networks:
      - traefik-public    # или internal-сеть — на усмотрение
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U tasktrack"]
      interval: 10s
      timeout: 5s
      retries: 5

networks:
  traefik-public:
    external: true

volumes:
  tasktrack-db:
```

Фронтенд-контейнер (`nginx`) отдаёт статику и проксирует `/api` → FastAPI не нужно, Traefik сам маршрутизирует.

### Keycloak: что создать

В realm `home` создать одного клиента `tasktrack`:
- **Client authentication**: OFF (публичный клиент, PKCE)
- **Valid redirect URIs**: `https://tasktrack.busypage.ru/*`, `http://localhost:5173/*`
- **Web origins**: `https://tasktrack.busypage.ru`, `http://localhost:5173`
- **Scope**: `openid email profile`

Добавить в `infra/simple/keycloak/realms/home-realm.json` конфиг клиента.  
В oauth2-proxy → Valid redirect URIs добавить: `https://tasktrack.busypage.ru/oauth2/callback` (если будет SSO-слой, но см. ниже — он не нужен).

**SSO middleware не нужен** для этого приложения: SPA сам получает токен от Keycloak через OIDC PKCE flow и передаёт Bearer. FastAPI валидирует JWT напрямую через JWKS. oauth2-proxy здесь лишний.

### Переменные окружения бэкенда

```bash
# backend/.env.prod
DATABASE_URL=postgresql+asyncpg://tasktrack:PASSWORD@db:5432/tasktrack
KEYCLOAK_URL=https://auth.busypage.ru
KEYCLOAK_REALM=home
KEYCLOAK_CLIENT_ID=tasktrack
CORS_ORIGINS=["https://tasktrack.busypage.ru"]
AUTH_STUB=false

# backend/.env.dev
DATABASE_URL=postgresql+asyncpg://tasktrack:tasktrack@localhost:5432/tasktrack
KEYCLOAK_URL=https://auth.busypage.ru
KEYCLOAK_REALM=home
KEYCLOAK_CLIENT_ID=tasktrack-dev
CORS_ORIGINS=["http://localhost:5173"]
AUTH_STUB=true
```

### RAM-бюджет

Инфра занимает ~485MB из 1GB. На приложение остаётся ~500MB:
- FastAPI (uvicorn): ~80MB
- PostgreSQL (tasktrack): ~50MB
- nginx (frontend): ~10MB
- Итого добавляем: ~140MB → **625MB всего**, комфортно.

---

## 5. Локальная разработка

### Что запускать в Docker, что нативно

```
Docker (один раз):
  └── PostgreSQL (tasktrack)  ← только БД

Нативно (каждая сессия):
  ├── backend: uvicorn --reload   (AUTH_STUB=true)
  └── frontend: vite dev          (проксирует /api → localhost:8000)
```

Keycloak в локалке не нужен — `AUTH_STUB=true` возвращает фиксированного пользователя.

```bash
# backend/Makefile
dev-db:
    docker compose -f docker-compose.dev.yml up db -d

dev:
    AUTH_STUB=true uvicorn app.main:app --reload --port 8000

migrate:
    alembic upgrade head

# frontend/Makefile (или package.json scripts)
dev:
    vite --port 5173
```

```typescript
// frontend/vite.config.ts — проксируем API на бэк
export default defineConfig({
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
```

### Корневой Makefile

```makefile
# Makefile (корень репозитория)
setup:
    cd backend && pip install -e ".[dev]"
    cd frontend && npm install

dev-db:
    cd backend && make dev-db

backend:
    cd backend && make dev

frontend:
    cd frontend && npm run dev

gen-types:
    cd frontend && npx openapi-typescript http://localhost:8000/openapi.json \
        -o src/shared/api/types.ts

migrate:
    cd backend && alembic upgrade head

test:
    cd backend && pytest
```

---

## 6. Критические технические решения

### global_status: сервисный слой + SELECT FOR UPDATE

Логика пересчёта `global_status` живёт только в `services/task_service.py`. ORM-хуки (`@event.listens_for`) не использовать — сложно тестировать и неочевидно трасировать.

```python
# services/decision_service.py
async def submit_solution(session: AsyncSession, solution_id: uuid.UUID) -> Solution:
    # SELECT FOR UPDATE на задаче — блокируем конкурентные переходы
    task = await session.scalar(
        select(Task)
        .where(Task.id == solution.assignment.task_id)
        .with_for_update()
    )
    
    solution.status = SolutionStatus.submitted
    session.add(solution)
    
    # Пересчитываем global_status
    all_lead_solutions = await _get_lead_solutions(session, task.id)
    if all(s.status == SolutionStatus.submitted for s in all_lead_solutions):
        task.global_status = TaskGlobalStatus.awaiting_decision
    
    await session.commit()
    return solution
```

### Миграции Alembic: первая

```bash
cd backend
alembic init alembic          # создаёт alembic/env.py
alembic revision --autogenerate -m "initial: users, projects, workflows, tasks"
alembic upgrade head
```

`autogenerate` работает только если все модели импортированы в `env.py` (добавить `from app.models import *`).

### Типизация: openapi-typescript workflow

```bash
# 1. Запустить бэкенд
make backend

# 2. Сгенерировать типы (в другом терминале)
make gen-types

# 3. Использовать в коде
import type { components } from "@/shared/api/types";
type Task = components["schemas"]["TaskResponse"];
```

Запускать после каждого изменения API-схемы. Можно добавить в pre-commit hook.

### Тестирование: testcontainers

```python
# tests/conftest.py
import pytest_asyncio
from testcontainers.postgres import PostgresContainer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest_asyncio.fixture(scope="session")
async def db_engine():
    with PostgresContainer("postgres:16-alpine") as pg:
        engine = create_async_engine(pg.get_connection_url().replace("postgresql://", "postgresql+asyncpg://"))
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield engine

# Запуск
# pytest tests/ -x -v  (Docker должен быть доступен)
```

---

## 7. Первые шаги до рабочего сценария S1

S1: создать проект → создать задачу → назначить исполнителя → провести по воркфлоу → закрыть с резолюцией.

1. **Scaffold backend**: скопировать паттерн из `new-app.sh` в `backend/`, расширить `pyproject.toml` (добавить `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `apscheduler`).

2. **Alembic env.py** под async + первая миграция: таблицы `users`, `groups`, `group_members`, `projects`, `project_members`.

3. **AUTH_STUB middleware**: `get_current_user` dependency, переключаемая через `AUTH_STUB=true`. Фиктивный пользователь автоматически создаётся в БД при первом обращении.

4. **Воркфлоу и резолюции**: таблицы `workflows`, `statuses`, `transitions`, `resolutions`. Миграция + дефолтные данные (seed: воркфлоу «Базовый» с To Do → In Progress → Done).

5. **Задачи и назначения**: таблицы `tasks`, `assignments`, `task_links`. Поле `global_status` в `tasks`.

6. **API endpoints для S1**: `POST /api/v1/projects`, `GET /api/v1/projects`, `POST /api/v1/projects/{id}/tasks`, `GET /api/v1/tasks/{id}`, `POST /api/v1/tasks/{id}/assignments`, `PATCH /api/v1/assignments/{id}/status`. Проверить через `curl` или httpie.

7. **Scaffold frontend**: `npm create vite@latest frontend -- --template react-ts`, добавить shadcn/ui, настроить Tailwind v4, proxy в `vite.config.ts`.

8. **Auth на фронте**: `oidc-client-ts`, `AuthProvider`, перехватчик axios/fetch для подстановки Bearer-токена. В dev-режиме при `AUTH_STUB=true` — пропускать авторизацию, работать без Keycloak.

9. **UI: Projects** — список проектов, форма создания (React Hook Form + Zod, TanStack Query).

10. **UI: Tasks + Kanban** — список задач проекта, Kanban-доска по `personal_status`, форма создания задачи, смена статуса assignment через drag-and-drop или кнопки.

После шага 10 сценарий S1 проходит end-to-end. Decision Process (S2–S3) — следующая итерация.
