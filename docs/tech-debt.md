# Технический долг (бэкенд)

Список отложенных бэкенд-задач, которые не блокируют текущий этап, но должны быть закрыты до выпуска MVP. Закрытые пункты — удалять, история есть в git.

> Для UX-долга фронтенда — см. [ux-debt.md](./ux-debt.md).
> Для решений по модели данных Этапа 2 — см. [ADR-006](./decisions/ADR-006-phase2-model-decisions.md).

---

## Отложено до Этапа 6 (Decision Process backend)

**APScheduler стартует без задач.**
`scheduler.start()` в lifespan — мёртвый код до Этапа 6. Структуру не убираем; задачи (напоминания decision-maker'у) добавляются в этом этапе.

**`get_current_user` / `core/auth.py` с JWT не подключены.**
`PyJWKClient` в `auth.py` не используется — `AUTH_STUB=true` покрывает все этапы до 6. При подключении Keycloak в Этапе 6 — реализовать полный flow в `deps.py`.

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
