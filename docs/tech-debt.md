# Технический долг (бэкенд)

Список отложенных бэкенд-задач, которые не блокируют текущий этап, но должны быть закрыты до выпуска MVP. Закрытые пункты — удалять, история есть в git.

> Для UX-долга фронтенда — см. [ux-debt.md](./ux-debt.md).
> Для решений по модели данных Этапа 2 — см. [ADR-006](./decisions/ADR-006-phase2-model-decisions.md).

---

## Отложено на post-MVP (после исследовательского запуска)

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

- Фронтенд: у большинства экранов нет тестов (есть у `TaskBoard`, `ProjectList`, `TaskView`, компонентов результата и проверки, `ControlPage`). Нет e2e-проверки полного цикла в браузере.

## Фронтенд: качество кода

**`eslint` находит 21 ошибку в старом коде.** `set-state-in-effect` (`GeneralSettingsPage`, `CreateTaskModal`, `use-mobile`), чтение ref во время рендера (`TaskSearchPopover`, `GanttChart`), `only-export-components` в `components/ui/*` и `AuthProvider`, неиспользуемые параметры. Новый код их не добавляет (проверено на изменённых файлах); починить отдельным проходом, затем включить `eslint` в CI/`make`.
