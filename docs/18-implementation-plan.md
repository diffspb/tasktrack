# 18. План реализации MVP

8 этапов от пустого репозитория до готового к исследовательскому запуску продукта. Каждый этап — законченный, демонстрируемый и покрытый тестами.

Архитектура — `docs/17-architecture.md`. Полный план с кодовыми примерами — в plan-файле Claude.

---

## Ограничения

- **Миграции:** `metadata.create_all` в lifespan до Этапа 8, затем переключение на Alembic
- **Тесты:** пишутся вместе с кодом, `make test` обязателен перед каждым коммитом
- **DB:** разработчик запускает postgres вручную (`make db-start`), параметры в `backend/.env.dev.example`
- **Коммиты:** один на этап + тег `impl-phase-N`

---

## Этап 0. Фундамент

**Цель:** `make dev` → сервер на :8000, `GET /health` → 200, `make test` → зелёный, `make reset` → чистая БД.

**Что создаётся:**
- `backend/` scaffold: `app/main.py`, `core/config.py`, `core/db.py`, `core/auth.py`, `core/auth_stub.py`, `models/base.py`, `api/v1/health.py`
- `scripts/reset_db.py` — drop_all + create_all + пустой seed
- `tests/conftest.py` — testcontainers postgres + AsyncClient + deps override
- `backend/.env.dev.example` — DATABASE_URL + команда запуска DB (`docker run ...`)
- `backend/Makefile` — `db-start`, `db-stop`, `reset`, `dev`, `test`, `install`
- `backend/pyproject.toml` — все зависимости

**Тесты:** `test_health.py` — GET /health → 200

---

## Этап 1. Пользователи и проекты

**Цель:** Создать проект, посмотреть список, добавить участника через API.

**Что создаётся:**
- Модели: `User`, `Project`, `ProjectMember`
- Сервис: `project_service` (create, list, update, archive, members)
- API: POST/GET/PATCH `/api/v1/projects`, POST/DELETE `/members`
- Seed: 3 пользователя (admin/manager/dev1) + демо-проект

**Тесты:** create, list (только доступные), add member, archive

---

## Этап 2. Воркфлоу и резолюции

**Цель:** Настроить воркфлоу проекта (статусы, переходы), управлять резолюциями.

**Что создаётся:**
- Модели: `Workflow`, `Status`, `Transition`, `Resolution`
- Сервис: `workflow_service` (CRUD, validate_transition, migrate_status)
- API: CRUD для воркфлоу/статусов/переходов/резолюций + `POST .../migrate`
- Seed: воркфлоу «Базовый» (To Do → In Progress → Review → Done) + 4 резолюции

**Тесты:** create, validate_transition (допустимый/недопустимый), delete status с активными → 409 → migrate → 200

---

## Этап 3. Задачи и назначения

**Цель:** Сценарий S1 работает через API — создать задачу → назначить → воркфлоу → закрыть.

**Что создаётся:**
- Модели: `Task`, `Assignment`, `TaskLink`
- Сервис: `task_service` (create, assign, transition_status с SELECT FOR UPDATE, _recalculate_global_status)
- API: CRUD задач, POST/PATCH assignments/status, GET /users/me/tasks
- Seed: 8 задач в разных состояниях + 1 мульти-исполнительская

**Тесты:** create→open, assign→in_progress, полный воркфлоу→closed, RESOLUTION_REQUIRED, VERSION_CONFLICT, soft delete→404

---

## Этап 4. Frontend scaffold + Projects UI

**Цель:** В браузере виден список проектов, можно создать новый. Работает без Keycloak (AUTH_STUB).

**Что создаётся:**
- `frontend/` scaffold: Vite + React 19 + TS + Tailwind v4 + shadcn/ui
- `AuthProvider` с stub-режимом
- axios client с auth interceptor
- TanStack Query setup
- `make gen-types` из FastAPI /openapi.json
- `features/projects/`: ProjectList, ProjectForm, api.ts

**Тесты:** Vitest — рендер списка проектов

---

## Этап 5. Tasks UI + Kanban (S1 complete) ★

**Цель:** S1 полностью в браузере — создать задачу, назначить, Kanban, закрыть с резолюцией.

**Что создаётся:**
- `features/tasks/`: TaskBoard (Kanban по personal_status), TaskDetail, TaskForm, api.ts
- Инвалидация TanStack Query при смене global_status

**Тесты:** задача в правильной колонке, инвалидация кэша

**Чекпоинт:** демонстрация S1 команде → тег `s1-complete`

---

## Этап 6. Decision Process backend (S2/S3 ядро)

**Цель:** Мульти-исполнительские задачи работают через API.

**Что создаётся:**
- Модели: `Solution`, `DecisionCriteria`, `TaskDecision`
- Сервис: `decision_service` (submit с SELECT FOR UPDATE, withdraw, make_decision, request_revision)
- API: solutions CRUD + submit/withdraw/request-revision, decisions, PUT decision-criteria, POST close

**Тесты:** happy path S2, revision cycle S3, **concurrent submit** (asyncio.gather), SOLUTION_IN_REVISION, consultant → 403

---

## Этап 7. Decision Process UI (S2/S3 complete) ★

**Цель:** S2 и S3 полностью в браузере.

**Что создаётся:**
- `features/decision-process/`: SolutionEditor, SolutionList, DecisionPanel, DecisionBadge

**Чекпоинт:** демонстрация ключевой фичи → тег `s23-complete`

---

## Этап 8. Доводка

**Цель:** Готово к исследовательскому запуску в локальном dev-режиме.

**Что делается:**
1. Notifications + badge (счётчик непрочитанных в шапке, события Decision Process)
2. Dashboard «Мои задачи» с фильтрами по роли/статусу/проекту
3. FTS-поиск через PostgreSQL tsvector (russian)
4. Унифицированный error-handling на фронте (toast по error code) + skeleton states
5. Закрытие непокрытых тестов из `tech-debt.md`
6. UX-долг #1: отображение названия проекта в шапке/сайдбаре

**Тесты:** notifications, dashboard фильтры, FTS-поиск.

### Отложено на post-MVP

**Alembic** — на исследовательский запуск остаёмся на `metadata.create_all` + `scripts/reset_db.py`. Переключение мешает быстрому циклу «поправил модель → пересоздал базу с сидом», который удобен для локального изучения. Подключим перед пилотом, когда схема стабилизируется и потеря данных между миграциями станет проблемой.

**Keycloak** — `AUTH_STUB=true` + dev-переключатель «View as» полностью покрывают локальную работу одного-двух человек. JWT-flow и реальный OIDC подключаем перед командным пилотом. PyJWKClient в `core/auth.py` уже есть, чтобы можно было довести быстро.

---

## Сводная таблица

| Этап | Тег | Что демонстрируется |
|------|-----|---------------------|
| 0 | `impl-phase-0` | `/health` + тесты зелёные |
| 1 | `impl-phase-1` | Проекты через API |
| 2 | `impl-phase-2` | Воркфлоу через API |
| 3 | `impl-phase-3` | S1 через API |
| 4 | `impl-phase-4` | Проекты в браузере |
| 5 | `s1-complete` | **S1 в браузере** |
| 6 | `impl-phase-6` | DP через API |
| 7 | `s23-complete` | **S2/S3 в браузере** |
| 8 | `mvp-research-launch` | Готово к локальному исследовательскому запуску |
