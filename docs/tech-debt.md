# Технический долг (бэкенд)

Список отложенных бэкенд-задач, которые не блокируют текущий этап, но должны быть закрыты до выпуска MVP. Закрытые пункты — удалять, история есть в git.

> Для UX-долга фронтенда — см. [ux-debt.md](./ux-debt.md).
> Для решений по модели данных Этапа 2 — см. [ADR-006](./decisions/ADR-006-phase2-model-decisions.md).

---

## Отложено на post-MVP (после исследовательского запуска)

**APScheduler стартует без задач.**
`scheduler.start()` в lifespan — мёртвый код. Структуру не убираем; задачи (напоминания decision-maker'у через 3 дня в `awaiting_decision`) — после реализации полноценного Decision Process (зависит от восстановления Assignment+Solution).

**Мульти-исполнители и Assignment.** MVP-упрощение (коммит `40caac4`): таблица `Assignment` удалена, задача имеет один `assignee_id`. Восстановить: таблицу `Assignment (task_id, user_id, role, current_status_id, workflow_id, resolution_id)`, поле `Task.global_status`, логику пересчёта `global_status` при изменении Assignment'ов. Это основная дифференцирующая фича продукта; откладывается до стабилизации базового флоу. **Под вопросом:** [ADR-016](./decisions/ADR-016-responsible-review-model.md) (на рассмотрении) предлагает не восстанавливать `Assignment` — при его принятии пункт снимается.

**Decision Process (Solution / TaskDecision).** Таблицы `Solution` и `TaskDecision` не реализованы. В MVP: суррогат через `Comment` с `labels=["solution"]` и `meta.solution_comment_id`. Восстановить: полноценные таблицы, API `submit_solution / make_decision / request_revision`, state machine `draft → submitted → accepted / revision_requested`. Зависит от восстановления Assignment. **Под вопросом:** по [ADR-016](./decisions/ADR-016-responsible-review-model.md) заменяется предложениями результата и отдельной проверкой (FR-003, TT-14/15).

**Transition: несколько ролей.** Сейчас `Transition.required_role` — одиночная строка (один required_role или NULL). Документация описывала `allowed_roles[]` (массив). Изменить на массив, когда понадобится разрешать переход нескольким разным ролям одновременно.

**`Comment.search_vector` не реализован.**
Поиск по тексту комментариев (`09-mvp.md`: 🟢) не работает — `Comment` не имеет поля `search_vector`, `search_service.py` ищет только по `Task.search_vector`. Добавить: поле `search_vector tsvector` в `Comment`, триггер обновления, `GIN`-индекс, расширить запрос в `search_service.py`.

**MCP-сервер: неполное покрытие операций.**
Текущий набор инструментов закрывает основной сценарий «AI-агент = исполнитель» (CRUD задач, комментарии, переходы, связи, поиск задач/пользователей, edit комментария — добавлено 2026-05-09). Не реализовано через MCP, хотя есть в REST:
- `delete_task` (soft-delete) — `DELETE /tasks/{id}`
- `delete_comment` — `DELETE /comments/{id}`
- Notifications: `list_notifications`, `mark_read`, `mark_all_read` — `/notifications/*`. Без них агент не видит новых упоминаний/назначений.
- Project events / activity log — `GET /projects/{id}/events`. Полезно для понимания контекста изменений.

Управление проектами, members, workflow CUD остаётся через UI/REST по дизайну — MCP-доступ не нужен.

---

## Баги и упущенные проверки

**MCP-инструменты не поддерживают повтор по ключу (ADR-019).**
`Idempotency-Key` работает только в REST. Агент, повторяющий `create_task` / `add_comment` через MCP после обрыва, создаст дубль. Добавить необязательный параметр `idempotency_key` в изменяющие инструменты поверх `idempotency_service` — вместе с FR-002 / TT-18. Фоновой очистки `idempotency_keys` старше 24 ч нет.

**Создать проект может любой вошедший пользователь.**
`POST /projects` не проверяет роль, по матрице `13-permissions.md` — только Admin. Решить, кто создаёт проекты (суперпользователь? отдельное право?), и закрыть проверкой.

**Журнал событий (ADR-018) покрывает не все изменения.**
Размечены задачи, комментарии, связи, проект, участники, служебные учётные записи и ключи. Не пишут события: CUD воркфлоу/статусов/переходов, представления и колонки борды, конфигурация типов задач, Гант, импорт проекта (`project_export_service.import_project` создаёт задачи без событий). MCP-инструменты не принимают причину изменения (`X-Change-Reason` есть только в REST). Добавлять по мере того, как эти изменения понадобятся потребителям журнала.

**`deploy/install.sh` устарел.**
Рабочая установка разворачивается PaaS-деплоером (`docs/configuration.md`, «Развёртывание через PaaS-деплоер»), который сам передаёт окружение. `install.sh` тянет образ из ghcr, который никто не публикует, а `docker-compose.prod.yml` не передаёт `.env.prod` в контейнер — этот путь нерабочий. Удалить вместе с `.env.prod.example`, когда будет подтверждено, что им никто не пользуется.

**Матрица прав (`13-permissions.md`) реализована частично.**
С FR-003/TT-01 запись требует роли `member`+ (viewer и не участник публичного проекта только читают), переход — исполнитель или `manager`/`admin` с учётом `Transition.required_role`, Гант меняет только владелец. Не реализованы более тонкие правила матрицы: `member` редактирует и удаляет **любую** задачу проекта (по матрице — только свою; удаление — только в начальном статусе), назначает других исполнителей (по матрице — только себя), удаляет чужие связи.

**Нет валидации соответствия workflow ↔ task_type при создании задачи.**
`task_service.py:27-32` разрешает любой workflow для любого task_type. Нет проверки, что выбранный workflow является `default_workflow` для данного task_type. Следствие: можно создать задачу с несовместимым workflow.

**Нет retry для `VERSION_CONFLICT` (HTTP 409).**
При конкурентном обновлении задачи клиент получает 409 и должен самостоятельно перечитать версию и повторить запрос. В сервисе нет retry/backoff-логики. При частых параллельных обновлениях UX деградирует без явного объяснения.

---

## Непокрытые тесты

Список закрыт (сверено 2026-07-27): кейсы `TASK_NOT_FOUND`, `NO_DEFAULT_WORKFLOW`, `STATUS_WORKFLOW_MISMATCH`, `TRANSITION_NOT_FOUND`, `STATUS_DEFAULT_MUST_BE_INITIAL` и happy path `PATCH /workflows/{id}` / `PATCH /statuses/{id}` покрыты в `test_tasks.py`, `test_workflows.py`, `test_task_type_workflow.py`.

Что остаётся непокрытым:

- Блокировка перехода decision-задачи (`task_service._check_decision_task_unblocked`) — тестов нет.
- Фронтенд: тесты есть только у `TaskBoard` и `ProjectList`; `TaskView.tsx` (687 строк) без тестов — см. `ux-debt.md`.
