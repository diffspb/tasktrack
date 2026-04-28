# ADR-006: Технический долг Этапа 2 — отложенные решения

**Статус:** Принято  
**Дата:** 2026-04-27

## Контекст

По результатам ревью Этапа 2 ряд замечаний отложен сознательно — либо требуют инфраструктуры следующих этапов, либо являются продуктовыми решениями, требующими ADR.

---

## ~~Отложено до Этапа 3~~ — Закрыто

**✅ migrate_status** — реализует реальный UPDATE assignments, тест `test_migrate_status_reassigns_assignments`.

**✅ delete_workflow** — проверяет наличие задач, возвращает 409 WORKFLOW_HAS_TASKS, тест `test_delete_workflow_with_tasks_blocked`.

**✅ _count_active_assignments** — реальный SQL-запрос к таблице assignments.

**✅ Транзакционная изоляция тестов** — PostgreSQL + testcontainers + `join_transaction_mode="create_savepoint"`.

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

**✅ Status.color** — добавлен `String(7), nullable` в модель и схемы, возвращается в `StatusResponse`.

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
