# Ревью проекта TaskTrack — май 2026

Дата: 2026-05-14  
Охват: документация, архитектура, качество кода (backend + frontend), полнота реализации.

---

## Итог одной строкой

Инфраструктура и базовый флоу задач реализованы качественно; главная дифференцирующая фича — Decision Process — не завершена ни на фронтенде, ни на бэкенде; документация описывает две реальности одновременно (MVP-суррогат и целевое состояние v2), что создаёт путаницу.

---

## 1. Соответствие документации исходным целям

### Что хорошо

- Исходные цели (мульти-исполнители + Decision Process) ясно зафиксированы в `docs/00-context.md` и `docs/glossary.md`.
- Архитектура описана детально (`docs/17-architecture.md`, ADR-каталог).
- MVP-сценарии (S1: создание/работа с задачами, Kanban) завершены и задокументированы.
- Известный долг собран в `tech-debt.md` и `ux-debt.md`.

### Проблемы

| Проблема | Файл | Оценка |
|---|---|---|
| `07-decision-process.md` описывает целевую механику (v2), не MVP-суррогат | `docs/07-decision-process.md` | Вводит в заблуждение |
| `12-data-model.md` не содержит `BoardColumn` / `BoardColumnStatus` (добавлены в Phase 9) | `docs/12-data-model.md` | Устаревший ERD |
| MCP-сервер не отражён в `15-api.md` | `docs/15-api.md` | Документ неполный |
| `tech-debt.md` не содержит чек-листа восстановления Assignment/Decision Process | `docs/tech-debt.md` | Долг задокументирован, путь к нему — нет |
| `Transition.required_role` в коде — одна строка, документ обсуждал массив | `docs/15-api.md` | Противоречие |
| Этап 8 (Alembic, Keycloak) помечен как 🔲, но нет целевой даты и критериев готовности | `docs/18-implementation-plan.md` | Размытый статус |

**Ключевой дефект:** документация одновременно описывает `[TARGET STATE]` и `[MVP-SIMPLIFIED]` без явных маркеров — читатель не понимает, что реализовано сейчас, а что запланировано. Рекомендуется добавить в разделы, описывающие мульти-исполнителей и Decision Process, явные маркеры состояния.

---

## 2. Архитектурное соответствие

Заявленная архитектура (`docs/17-architecture.md`): FastAPI + PostgreSQL + Keycloak + React 19 + Traefik + Docker Compose.

**Соответствует:**
- Стек совпадает полностью.
- Разделение на `api/v1/`, `services/`, `models/`, `schemas/`, `core/`, `mcp/` — чистое.
- Feature-first организация фронтенда (`features/tasks`, `features/projects`, etc.).

**Не соответствует:**
- `Assignment` как отдельная таблица (задокументирована в `12-data-model.md`) — заменена на `Task.assignee_id` в MVP, но документ не обновлён.
- `Solution` и `TaskDecision` как таблицы — не реализованы; суррогат через `Comment.labels` нигде в архитектурных документах не зафиксирован.
- `BoardColumn` / `BoardColumnStatus` — реализованы (Phase 9), в ERD отсутствуют.

---

## 3. Качество кода — Backend

**Общая оценка: 7.5/10**

### Сильные стороны

- Чёткое разделение слоёв: API → Services → Models. Зависимости текут в одном направлении.
- Полная Python typing во всех сервисах и роутерах.
- Pydantic v2 (`ConfigDict(from_attributes=True)`) используется корректно.
- Именование самодокументирующее (`_check_decision_task_unblocked`, `require_project_access`).
- Versioned optimistic locking (`Task.version`) с правильным HTTP 409 при конфликте.
- Soft delete через `deleted_at`.
- Тесты на PostgreSQL через `testcontainers`, savepoint-изоляция между тестами.

### Проблемы

**P1 — Decision Process не выражен в REST API явно**  
Блокировка финального статуса (`_check_decision_task_unblocked` в `task_service.py:311-325`) есть, но нет роутера `/api/v1/decisions`. Клиент работает с Decision Process через комментарии с меткой — это обходной путь, не контракт.

**P2 — Soft-delete комментариев не фильтруется при листинге**  
`comment_service.py:85-86` — `list_comments` не добавляет `.where(Comment.deleted_at.is_(None))`. Удалённые комментарии видны клиенту.

**P3 — Нет retry для `VERSION_CONFLICT`**  
При 409 клиент обязан сам перечитать версию и повторить запрос. В сервисе нет retry/backoff. При частых параллельных обновлениях UX деградирует.

**P4 — Нет валидации соответствия `workflow` ↔ `task_type`**  
`task_service.py:27-32` не проверяет, что выбранный workflow является `default_workflow` для данного `task_type`. Можно назначить несовместимый workflow.

**P5 — MCP tools не имеют полного паритета с REST API**  
`/app/mcp/tools/tasks.py` поддерживает базовые операции, но gantt, board_columns, notifications через MCP недоступны. Агенты получают неполную картину проекта.

### Покрытие тестами

Тесты большие и реалистичные (~72k строк в 6 основных файлах). Пробелы:
- Нет тестов для логики блокировки Decision Process (`_check_decision_task_unblocked`).
- Нет тестов concurrent update scenarios (optimistic lock под нагрузкой).

---

## 4. Качество кода — Frontend

**Общая оценка: 7.2/10**

### Сильные стороны

- Feature-based архитектура (`/features/`) — правильное разделение.
- TanStack Query v5 используется по всем канонам: правильные `queryKey`, `enabled`, `staleTime`, оптимистичные обновления с rollback в `useTransitionStatus`.
- Real-time обновления через SSE (`useProjectEvents`) с инвалидацией кэша.
- Строгая типизация, практически нет `any`.
- Skeleton loaders везде, error toasts через `sonner`.

### Проблемы

**P1 — КРИТИЧНО: Decision Process UI полностью отсутствует**  
`/frontend/src/features/decision-process/` — папка пуста (только `__tests__/`). Нет экранов для: просмотра критериев, подачи Solution, review решений, вынесения итогового Decision. Бэкенд имеет частичную поддержку, фронтенд — нулевую.

**P2 — `TaskView.tsx` — мегакомпонент**  
687 строк, 15+ состояний, вложенные `handleDrop`, `saveTitle`, `saveDesc` inline. Нет тестов. Трудно поддерживать и расширять. Нужна декомпозиция: `StatusTransition`, `EditTitle`, `DatesBlock`, `ChildTasks`, `LinksSection`.

**P3 — Drag-and-drop без keyboard accessibility**  
`TaskBoard.tsx:241-248` — только mouse events (`onDragStart`, `onDragOver`, `onDrop`). Нарушение WCAG 2.1 Level AA.

**P4 — Инвалидация кэша неполная при операциях с links**  
`useDeleteTaskLink` инвалидирует `['task-links', taskId]` и gantt, но не `['tasks', projectId]`. Доска может показывать устаревшие данные после удаления связи.

**P5 — Нет error boundaries на уровне layout**  
Если `AppSidebar`, `Breadcrumbs` или `SearchBar` падают, весь навигационный слой ломается без fallback UI.

### Покрытие тестами

Критически низкое: ~5-10% от кодовой базы. Протестированы только `TaskBoard` и `ProjectList`. `TaskView` (687 строк) — без тестов. `decision-process/__tests__/` — пусто.

---

## 5. Полнота реализации

| Компонент | Статус | Примечание |
|---|---|---|
| Auth (stub + Keycloak-ready) | ✅ Реализован | Keycloak интеграция — этап 8 |
| Projects CRUD | ✅ Реализован | Полный, включая члены/импорт |
| Tasks CRUD + Kanban | ✅ Реализован | S1 полностью завершён |
| Workflows + Transitions | ✅ Реализован | Board columns (FR-001) добавлены |
| Comments с labels | ✅ Реализован | Используется как суррогат Solution |
| Task Links (5 типов) | ✅ Реализован | Gantt-зависимости тоже |
| FTS поиск | ✅ Реализован | tsvector, глобальный |
| Notifications (in-app) | ✅ Реализован | SSE, базовые типы |
| MCP-сервер | ✅ Реализован | Multi-agent auth, 15+ tools |
| Admin: инициализация системы | ✅ Реализован | Кнопка в Global Settings |
| Decision Process — backend | ⚠️ Частично | Блокировка перехода есть, нет REST /decisions |
| Decision Process — frontend | ❌ Не реализован | Папка пуста |
| Мульти-исполнители (Assignment) | ❌ Не реализован | MVP: один assignee_id |
| Alembic миграции | ❌ Не реализован | create_all, этап 8 |
| Keycloak интеграция prod | ❌ Не реализован | Этап 8 |
| Retry для VERSION_CONFLICT | ❌ Отсутствует | — |

---

## 6. Приоритизированные рекомендации

### Критично (блокеры перед расширением команды)

1. **Реализовать Decision Process UI** (`/frontend/src/features/decision-process/`)  
   Минимум: экран просмотра decision-задачи с subtasks, кнопка Submit Solution на subtask, панель Decision-maker с выбором принятого Solution.

2. **Добавить `/api/v1/decisions` роутер** (backend)  
   Явные эндпоинты: `POST /tasks/{id}/submit-solution`, `GET /tasks/{id}/solutions`, `POST /tasks/{id}/make-decision`. Убрать зависимость от Comment-labels как механизма Decision Process.

3. **Исправить фильтрацию soft-deleted комментариев** (`comment_service.py:85-86`)  
   Одна строка: добавить `.where(Comment.deleted_at.is_(None))`.

### Важно (tech debt, UX)

4. **Обновить `12-data-model.md`** — добавить `BoardColumn`, `BoardColumnStatus` в ERD.

5. **Добавить маркеры `[MVP]` / `[TARGET v2]`** в `07-decision-process.md` и в user stories Decision Process.

6. **Декомпозировать `TaskView.tsx`** — разбить на 5-7 подкомпонентов, добавить тесты на ключевые сценарии.

7. **Починить инвалидацию кэша** в `useDeleteTaskLink` — добавить `['tasks', projectId]`.

### Желательно

8. **Keyboard accessibility для Kanban drag-drop** (WCAG 2.1).

9. **Error boundaries** на уровне Layout-компонента.

10. **Создать `docs/post-mvp-recovery-plan.md`** с пошаговым чек-листом восстановления Assignment → Solution → TaskDecision.

---

## Приложение: матрица оценок

| Область | Оценка | Комментарий |
|---|---|---|
| Документация: цели и контекст | 8/10 | Ясные, полные, но смешивают MVP и v2 |
| Документация: архитектура | 7/10 | ERD устарел (BoardColumn), MCP не отражён |
| Backend: архитектура кода | 8/10 | Чистые слои, хорошее разделение |
| Backend: типизация | 9/10 | Полная, Pydantic v2 |
| Backend: API полнота | 7/10 | Decision Process — суррогат, не контракт |
| Backend: тесты | 8/10 | Хорошее покрытие основного флоу |
| Frontend: структура | 8/10 | Feature-based, clean |
| Frontend: TypeScript | 9/10 | Строгая, минимум `any` |
| Frontend: State management | 9/10 | TanStack Query — образцово |
| Frontend: полнота реализации | 5/10 | Decision Process UI отсутствует |
| Frontend: тесты | 3/10 | Критически мало (&lt;10%) |
| **Итог** | **7.5/10** | Сильная основа, ключевая фича не завершена |
