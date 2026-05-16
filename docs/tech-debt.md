# Технический долг (бэкенд)

Список отложенных бэкенд-задач, которые не блокируют текущий этап, но должны быть закрыты до выпуска MVP. Закрытые пункты — удалять, история есть в git.

> Для UX-долга фронтенда — см. [ux-debt.md](./ux-debt.md).
> Для решений по модели данных Этапа 2 — см. [ADR-006](./decisions/ADR-006-phase2-model-decisions.md).

---

---

## Отложено на post-MVP (после исследовательского запуска)

**APScheduler стартует без задач.**
`scheduler.start()` в lifespan — мёртвый код. Структуру не убираем; задачи (напоминания decision-maker'у через 3 дня в `awaiting_decision`) — после реализации полноценного Decision Process (зависит от восстановления Assignment+Solution).

---

## Отложено на post-MVP (после исследовательского запуска)

**Alembic.** На исследовательский запуск остаёмся на `metadata.create_all` + `scripts/reset_db.py`: цикл «поправил модель → пересоздал базу с сидом» удобнее, чем миграции, пока схема нестабильна и пользователь активно изучает реализацию локально. Переключаемся перед пилотом, когда потеря данных между миграциями станет реальной проблемой.

**Keycloak.** `AUTH_STUB=true` + dev-переключатель «View as» полностью покрывают локальную работу. `PyJWKClient` в `core/auth.py` уже подготовлен — нужно подключить `get_current_user` к JWT-валидации в `deps.py` и реальный OIDC-flow на фронте перед командным пилотом.

**Мульти-исполнители и Assignment.** MVP-упрощение (коммит `40caac4`): таблица `Assignment` удалена, задача имеет один `assignee_id`. Восстановить: таблицу `Assignment (task_id, user_id, role, current_status_id, workflow_id, resolution_id)`, поле `Task.global_status`, логику пересчёта `global_status` при изменении Assignment'ов. Это основная дифференцирующая фича продукта; откладывается до стабилизации базового флоу.

**Decision Process (Solution / TaskDecision).** Таблицы `Solution` и `TaskDecision` не реализованы. В MVP: суррогат через `Comment` с `labels=["solution"]` и `meta.solution_comment_id`. Восстановить: полноценные таблицы, API `submit_solution / make_decision / request_revision`, state machine `draft → submitted → accepted / revision_requested`. Зависит от восстановления Assignment.

**Transition: несколько ролей.** Сейчас `Transition.required_role` — одиночная строка (один required_role или NULL). Документация описывала `allowed_roles[]` (массив). Изменить на массив, когда понадобится разрешать переход нескольким разным ролям одновременно.

**`resolution_id` хранится в `Task.meta` как строка, не как FK.**
При переходе в финальный статус воркфлоу `resolution_id` сохраняется в `Task.meta["resolution_id"]` (строка UUID). Последствия: нет FK-ограничения (можно указать несуществующую резолюцию), нет индекса для фильтрации задач по резолюции, `TaskResponse` не возвращает `resolution_id` — фронтенд не может показать выбранную резолюцию на карточке задачи. Правильное решение: добавить `Task.resolution_id FK → resolutions.id` как отдельную колонку.

**`Comment.search_vector` не реализован.**
Поиск по тексту комментариев (`09-mvp.md`: 🟢) не работает — `Comment` не имеет поля `search_vector`, `search_service.py` ищет только по `Task.search_vector`. Добавить: поле `search_vector tsvector` в `Comment`, триггер обновления, `GIN`-индекс, расширить запрос в `search_service.py`.

**`_count_active_assignments()` — вводящее в заблуждение имя.**
Функция в `workflow_service.py` считает `Task.current_status_id`, а не Assignment-записи (которых нет). Переименовать в `_count_tasks_in_status()`.

**MCP-сервер: неполное покрытие операций.**
Текущий набор инструментов закрывает основной сценарий «AI-агент = исполнитель» (CRUD задач, комментарии, переходы, связи, поиск задач/пользователей, edit комментария — добавлено 2026-05-09). Не реализовано через MCP, хотя есть в REST:
- `delete_task` (soft-delete) — `DELETE /tasks/{id}`
- `delete_comment` — `DELETE /comments/{id}`
- Notifications: `list_notifications`, `mark_read`, `mark_all_read` — `/notifications/*`. Без них агент не видит новых упоминаний/назначений.
- Project events / activity log — `GET /projects/{id}/events`. Полезно для понимания контекста изменений.

Управление проектами, members, workflow CUD остаётся через UI/REST по дизайну — MCP-доступ не нужен.

---

## Баги и упущенные проверки

**Нет валидации соответствия workflow ↔ task_type при создании задачи.**
`task_service.py:27-32` разрешает любой workflow для любого task_type. Нет проверки, что выбранный workflow является `default_workflow` для данного task_type. Следствие: можно создать задачу с несовместимым workflow.

**Нет retry для `VERSION_CONFLICT` (HTTP 409).**
При конкурентном обновлении задачи клиент получает 409 и должен самостоятельно перечитать версию и повторить запрос. В сервисе нет retry/backoff-логики. При частых параллельных обновлениях UX деградирует без явного объяснения.

---

## Непокрытые тесты

Закрыты P0/P1 перед Этапом 4 (2026-04-29). Оставшиеся кейсы:

**Error cases:**

- `TASK_NOT_FOUND` при GET/PATCH/DELETE с несуществующим UUID задачи
- `NO_DEFAULT_WORKFLOW` при создании задачи в проекте без дефолтного воркфлоу
- `STATUS_WORKFLOW_MISMATCH` в `migrate_status` (target из другого воркфлоу)
- `TRANSITION_NOT_FOUND` при `DELETE /transitions/{id}` с несуществующим ID
- `STATUS_DEFAULT_MUST_BE_INITIAL` через `PATCH /statuses/{id}`

**Happy path:**

- `PATCH /workflows/{id}` — `update_workflow` happy path
- `update_status` happy path через `PATCH`
