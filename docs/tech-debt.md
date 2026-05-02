# Технический долг (бэкенд)

Список отложенных бэкенд-задач, которые не блокируют текущий этап, но должны быть закрыты до выпуска MVP. Закрытые пункты — удалять, история есть в git.

> Для UX-долга фронтенда — см. [ux-debt.md](./ux-debt.md).
> Для решений по модели данных Этапа 2 — см. [ADR-006](./decisions/ADR-006-phase2-model-decisions.md).

---

## Отложено на Этап 8 (доводка)

**APScheduler стартует без задач.**
`scheduler.start()` в lifespan — мёртвый код. Структуру не убираем; задачи (напоминания decision-maker'у через 3 дня в `awaiting_decision`) — после реализации `Notification` в Этапе 8.

---

## Отложено на post-MVP (после исследовательского запуска)

**Alembic.** На исследовательский запуск остаёмся на `metadata.create_all` + `scripts/reset_db.py`: цикл «поправил модель → пересоздал базу с сидом» удобнее, чем миграции, пока схема нестабильна и пользователь активно изучает реализацию локально. Переключаемся перед пилотом, когда потеря данных между миграциями станет реальной проблемой.

**Keycloak.** `AUTH_STUB=true` + dev-переключатель «View as» полностью покрывают локальную работу. `PyJWKClient` в `core/auth.py` уже подготовлен — нужно подключить `get_current_user` к JWT-валидации в `deps.py` и реальный OIDC-flow на фронте перед командным пилотом.

**Мульти-исполнители и Assignment.** MVP-упрощение (коммит `40caac4`): таблица `Assignment` удалена, задача имеет один `assignee_id`. Восстановить: таблицу `Assignment (task_id, user_id, role, current_status_id, workflow_id, resolution_id)`, поле `Task.global_status`, логику пересчёта `global_status` при изменении Assignment'ов. Это основная дифференцирующая фича продукта; откладывается до стабилизации базового флоу.

**Decision Process (Solution / TaskDecision).** Таблицы `Solution` и `TaskDecision` не реализованы. В MVP: суррогат через `Comment` с `labels=["solution"]` и `meta.solution_comment_id`. Восстановить: полноценные таблицы, API `submit_solution / make_decision / request_revision`, state machine `draft → submitted → accepted / revision_requested`. Зависит от восстановления Assignment.

**Transition: несколько ролей.** Сейчас `Transition.required_role` — одиночная строка (один required_role или NULL). Документация описывала `allowed_roles[]` (массив). Изменить на массив, когда понадобится разрешать переход нескольким разным ролям одновременно.

---

## Непокрытые тесты

Закрыты P0/P1 перед Этапом 4 (2026-04-29). Оставшиеся кейсы не блокируют фронтенд-разработку, дописать в Этапе 8.

**Error cases:**

- `TASK_NOT_FOUND` при GET/PATCH/DELETE с несуществующим UUID задачи
- `ASSIGNMENT_NOT_FOUND` при переходе статуса по несуществующему `assignment_id`
- `WORKFLOW_NO_DEFAULT_STATUS` в `assign_user` (воркфлоу без дефолтного статуса)
- `STATUS_WORKFLOW_MISMATCH` в `migrate_status` (target из другого воркфлоу)
- `TRANSITION_NOT_FOUND` при `DELETE /transitions/{id}` с несуществующим ID
- `STATUS_DEFAULT_MUST_BE_INITIAL` через `PATCH /statuses/{id}`

**Happy path:**

- `PATCH /workflows/{id}` — `update_workflow` happy path
- `update_status` happy path через `PATCH`
