# ADR-006: Технический долг Этапа 2 — отложенные решения

**Статус:** Принято  
**Дата:** 2026-04-27

## Контекст

По результатам ревью Этапа 2 ряд замечаний отложен сознательно — либо требуют инфраструктуры следующих этапов, либо являются продуктовыми решениями, требующими ADR.

---

## Отложено до Этапа 3

**migrate_status не выполняет миграцию Assignments.**  
Функция удаляет статус, но не переносит `Assignment.current_status_id` на `target_status_id`. Заглушка с `# TODO(phase-3)` в `workflow_service.py`. Будет реализовано вместе с моделью `Assignment`.

**delete_workflow не проверяет наличие задач.**  
Удаление воркфлоу не проверяет, есть ли Task, ссылающийся на него. Добавить проверку при появлении модели `Task` в Этапе 3.

**_count_active_assignments возвращает 0 до появления Task/Assignment.**  
После появления модели `Assignment` в Этапе 3 — заменить заглушку реальным запросом.

**Транзакционная изоляция тестов (savepoint-паттерн).**  
Тесты используют общую SQLite in-memory БД в рамках сессии. Полная изоляция через savepoints требует PostgreSQL (SAVEPOINT не работает в SQLite с asyncpg). Реализовать при переходе на PG-тесты в Этапе 3.

---

## Отложено до Этапа 4

**APScheduler стартует без задач.**  
`scheduler.start()` в lifespan — мёртвый код до Этапа 6. Отключать не будем (структура уже создана), задачи добавятся в Этапе 6 (напоминания decision-maker'у).

---

## Отложено до Этапа 6 (Keycloak)

**`get_current_user` / `core/auth.py` с JWT не подключены.**  
`PyJWKClient` в `auth.py` не используется — `AUTH_STUB=true` покрывает все этапы до 6. При подключении Keycloak в Этапе 6 — реализовать полный flow в `deps.py`.

---

## Продуктовые решения (требуют уточнения)

**Transition.required_role: str | None вместо allowed_roles: list[str].**  
По `12-data-model.md` переход разрешён _списку_ ролей. Реализация хранит одну роль. Для MVP достаточно одной роли. При необходимости расширить — добавить JSON-поле `allowed_roles` и мигрировать.

**Resolution: is_default вместо is_active + position.**  
По `12-data-model.md` у Resolution должны быть `is_active` (архивирование без удаления) и `position`. Поле `position` добавлено. Поле `is_active` отложено: в MVP резолюции не архивируются, только удаляются. При необходимости — добавить `is_active: bool = True` и обновить API.

**Status.color не реализован.**  
По `12-data-model.md` у Status должно быть поле `color` для отображения столбцов Kanban. Сознательно опущено в MVP. Добавить в Этапе 5 (Kanban UI) или Этапе 8 (доводка).

**Status.is_default vs is_initial семантика.**  
Текущее решение: `is_default=True` означает "начальный статус для новых задач" и принудительно требует `category=initial`. В будущем можно упростить до `category` без `is_default`, если инвариант "ровно один initial-статус как default" станет жёстким.

---

## Что закрыто в рамках фикса ревью

- `permissions.py` — единая точка контроля доступа вместо импорта приватного `_get_member`
- `_get_member` → `get_member` (публичный) в `project_service`
- `create_transition` проверяет принадлежность обоих статусов к одному воркфлоу
- `is_default` уникальность: upsert для Status и Resolution
- `TimestampMixin` на Status и Transition
- `ondelete="CASCADE"` на FK в Status, Transition, Resolution, Workflow
- `delete_workflow` блокируется при `is_default=True`
- `create_project` возвращает 409 DUPLICATE_PROJECT_KEY при дубле
- Валидация формата `Project.key` (regex)
- Resolution вынесен в `resolution_service.py` и `schemas/resolution.py`
- Теги роутеров разделены: workflows / statuses / transitions / resolutions
- Уникальные ключи в тестах (uuid-based), enum вместо строк
