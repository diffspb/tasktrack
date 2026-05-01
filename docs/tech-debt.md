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
