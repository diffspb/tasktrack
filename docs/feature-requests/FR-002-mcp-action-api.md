# FR-002: Action-oriented MCP API

**Статус:** На рассмотрении  
**Приоритет:** Post-MVP  
**Связано с:** `backend/app/mcp/`

---

## Проблема

Текущий MCP-сервер — тонкая обёртка над REST API: `transition_task_status`, `update_task`, `create_task_link`. Агент вынужден знать внутренние детали (UUID статусов, UUID типов связей, порядок вызовов), чтобы выполнить одно логическое действие.

Примеры неудобства:
- «Взять задачу в работу» = 2 вызова: `update_task(assignee_id=me)` + `transition_task_status(status_id=???)` — нужно сначала найти правильный статус в воркфлоу
- «Заблокировать задачу» = `transition_task_status` + `create_task_link` + `add_comment` — три разных инструмента, нет единой точки входа
- Создание связи требует `link_type_id` (UUID) — агент должен знать его заранее или делать дополнительный запрос

---

## Предложение

Переработать набор инструментов в **action-oriented стиль**: каждый инструмент отражает намерение, а не операцию над БД. Один инструмент может объединять несколько шагов.

---

## Группы инструментов

### Ориентация (что вообще происходит)

| Инструмент | Что делает | Заменяет |
|---|---|---|
| `my_work()` | Мои задачи: статус, дедлайны, блокеры | `list_my_tasks` |
| `project_board(project_key)` | Сводка колонок Kanban с числами задач | `list_tasks` (partial) |
| `blocked_tasks(project_key?)` | Всё заблокированное + причины | `list_tasks` (filtered) |
| `overdue_tasks(project_key?)` | Просроченные задачи | `list_tasks` (filtered) |
| `find_tasks(query, project?, status?, assignee?)` | Поиск по тексту и фильтрам | `search_tasks` (расширить) |
| `get_task(id_or_key)` | Полный контекст: описание, статус, assignees, связи, последние комменты | `get_task` / `get_task_by_key` |

### Работа с задачей (исполнитель)

| Инструмент | Что делает | Заменяет |
|---|---|---|
| `take_task(task_id)` | Назначить на себя + перевести в «в работе» | `update_task` + `transition_task_status` |
| `start_work(task_id)` | Перевести в рабочий статус (если уже назначен) | `transition_task_status` |
| `update_progress(task_id, note)` | Добавить комментарий с прогрессом, опционально сменить статус | `add_comment` + `transition_task_status` |
| `report_blocker(task_id, description, blocked_by_task?)` | Перевести в «заблокировано» + комментарий + опционально создать связь | `transition_task_status` + `add_comment` + `create_task_link` |
| `put_on_hold(task_id, reason)` | Пауза + причина | `transition_task_status` + `add_comment` |
| `submit_completion(task_id, summary?)` | Перевести в «сделано» / «на проверке» + итоговый комментарий | `transition_task_status` + `add_comment` |

### Decision Process

| Инструмент | Что делает | Заменяет |
|---|---|---|
| `submit_solution(task_id, summary)` | Подать Solution — переводит Assignment в финальный статус | `transition_task_status` (assignment) |
| `record_decision(task_id, outcome, rationale)` | Decision-maker фиксирует Decision | `transition_task_status` + `add_comment` |
| `request_revision(task_id, assignee_email, comment)` | Вернуть задачу исполнителю на доработку | `transition_task_status` + `add_comment` |

### Управление задачами (PM / lead)

| Инструмент | Что делает | Заменяет |
|---|---|---|
| `create_task(title, project, description?, parent?, assignees?)` | Создать задачу, назначить сразу | `create_task` (расширить) |
| `assign_task(task_id, user_email)` | Добавить исполнителя | `update_task(assignee_id=...)` |
| `set_deadline(task_id, date)` | Установить дедлайн | `update_task(due_date=...)` |
| `link_tasks(task_a_key, relation, task_b_key)` | `"A blocks B"`, `"A depends on B"` — в человеческом синтаксисе | `create_task_link` |
| `unlink_tasks(task_a_key, relation, task_b_key)` | Снять связь | `delete_task_link` |
| `close_task(task_id, reason?)` | Закрыть / отменить задачу | `transition_task_status` |

### Коммуникация

| Инструмент | Что делает | Заменяет |
|---|---|---|
| `comment(task_id, message)` | Добавить комментарий | `add_comment` |
| `reply(comment_id, message)` | Ответить на комментарий | `add_comment(parent_id=...)` |

---

## Что убрать / схлопнуть

- `transition_task_status` — покрывается `start_work`, `put_on_hold`, `submit_completion`, `close_task`
- `create_task_link` / `delete_task_link` — заменяются `link_tasks` / `unlink_tasks` с текстовым синтаксисом (`"blocks"`, `"depends on"`)
- `list_tasks` — слишком сырой, заменяется `project_board` + `find_tasks` + `my_work`
- `get_workflow`, `list_workflows` — внутренние детали, агенту не нужны напрямую

---

## Решение

### Подход

Новые инструменты реализуются как **сервисный слой поверх существующих сервисов** — без дублирования бизнес-логики. Каждый action-инструмент вызывает те же сервисные функции, что и REST API.

Структура: новый модуль `backend/app/mcp/actions/` (рядом с `tools/`), каждая группа — отдельный файл. Старые `tools/` оставить временно для обратной совместимости, постепенно deprecate.

### Ключевые решения

**Разрешение статусов по смыслу, не по UUID.**  
`take_task` ищет статус с `initial=False, is_default=True` или с именем из предзаданного списка (`["in progress", "в работе", "doing"]`). Если воркфлоу нестандартный и статус не найден — возвращает ошибку с перечнем доступных статусов, чтобы агент мог уточнить.

**Разрешение типов связей по строке.**  
`link_tasks("PROJ-1", "blocks", "PROJ-2")` ищет `LinkType` по `outward_name` или `inward_name` (case-insensitive). Список доступных отношений возвращается в ошибке если не найдено.

**Разрешение пользователей по email.**  
`assign_task(task_id, "user@example.com")` вызывает `search_users` внутри и падает с внятной ошибкой если пользователь не найден.

**Составные действия — транзакционно.**  
`report_blocker` меняет статус + создаёт связь + добавляет комментарий в одной транзакции. При частичном сбое откатывается всё.

### Файлы

| Файл | Содержимое |
|---|---|
| `backend/app/mcp/actions/work.py` | `take_task`, `start_work`, `update_progress`, `report_blocker`, `put_on_hold`, `submit_completion` |
| `backend/app/mcp/actions/manage.py` | `create_task`, `assign_task`, `set_deadline`, `link_tasks`, `unlink_tasks`, `close_task` |
| `backend/app/mcp/actions/decision.py` | `submit_solution`, `record_decision`, `request_revision` |
| `backend/app/mcp/actions/query.py` | `my_work`, `project_board`, `blocked_tasks`, `overdue_tasks`, `find_tasks`, `get_task` |
| `backend/app/mcp/actions/communication.py` | `comment`, `reply` |
| `backend/app/mcp/server.py` | Регистрация новых инструментов, deprecation старых |

---

## Открытые вопросы

- Нужна ли обратная совместимость со старыми инструментами или можно заменить полностью?
- Как обрабатывать воркфлоу без стандартных статусов (полностью кастомные)? Fallback с перечнем или ошибка?
- Стоит ли `my_work` делать умным (приоритизировать по дедлайну / блокерам) или просто плоский список?
