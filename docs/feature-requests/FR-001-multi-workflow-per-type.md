# FR-001: Многоуровневые воркфлоу по типу задачи

**Статус:** На рассмотрении  
**Приоритет:** Post-MVP  
**Связано с:** ADR-006, `docs/12-data-model.md`

---

## Проблема

Сейчас у проекта один воркфлоу (дефолтный), который используют все типы задач.
Реально у Бага, Эпика, Decision-задачи жизненный цикл разный — общий воркфлоу не отражает это.

---

## Предложение

### Уровень 1 — системные дефолты по типу задачи

Каждый `TaskType` (task / bug / story / epic / decision) получает свой дефолтный воркфлоу.
Системные воркфлоу хранятся с `project_id = NULL` (как системные `TaskType`).

| Тип | Пример воркфлоу |
|-----|-----------------|
| task / story | To Do → In Progress → Review → Done |
| bug | Open → In Progress → Review → Verified → Closed |
| epic | Planning → Active → Done |
| decision | Open → Collecting → Awaiting Decision → Decided |

### Уровень 2 — переопределение на уровне проекта

Проект может выбрать для каждого типа задачи другой воркфлоу
(свой или системный). Таблица `project_task_type_config (project_id, task_type_id, workflow_id)`.

### Логика выбора воркфлоу при создании задачи

```
task_type → ProjectTaskTypeConfig (project) → TaskType.default_workflow_id → error
```

### Board columns — универсальные колонки

Board отображает 5 фиксированных колонок (настраиваются в settings проекта).
В настройках борды каждой колонке сопоставляются статусы из всех воркфлоу,
используемых в проекте.

Новые таблицы:
- `board_column (id, project_id, name, position)`
- `board_column_status (board_column_id, status_id)`

Board рендерится по `board_column`, не по `workflow.statuses`.

---

## Изменения данных

| Что | Где |
|-----|-----|
| `Workflow.project_id` допускает NULL | системные воркфлоу |
| `TaskType.default_workflow_id FK → Workflow` | дефолт по типу |
| Новая таблица `project_task_type_config` | проектный override |
| Новые таблицы `board_column`, `board_column_status` | универсальные колонки |
| Логика `task_service.create_task` | выбор воркфлоу по типу |
| Board компонент | рендер по board_column |

---

## Допущения текущего редактора (до реализации FR-001)

- Редактируется только дефолтный воркфлоу проекта
- Все типы задач используют один воркфлоу
- Board показывает колонки из `workflow.statuses` напрямую
