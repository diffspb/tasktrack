# Этап 9: FR-001 — Мульти-воркфлоу по типу задачи

**Статус:** В проработке  
**Приоритет:** Post-MVP (после `mvp-research-launch`)  
**Связано с:** `docs/feature-requests/FR-001-multi-workflow-per-type.md`, `docs/12-data-model.md`, `docs/15-api.md`

---

## Контекст

Сейчас у проекта один дефолтный воркфлоу, который используют все типы задач. Задача (`task`), баг (`bug`), эпик (`epic`) и решение (`decision`) имеют разные жизненные циклы — один воркфлоу это не отражает. FR-001 предлагает дать каждому типу задачи свой воркфлоу.

**Состояние кода на момент старта этапа:**
- `TaskType` — таблица, `project_id` nullable (системные типы: task, bug, story, epic, decision), поля: key, name, is_system, color, icon, meta_schema
- `Workflow.project_id` — NOT NULL (воркфлоу обязан принадлежать проекту)
- `Task.workflow_id` — NOT NULL FK → workflow (присваивается при создании напрямую)
- Канбан-борд рендерится по `workflow.statuses` проекта (дефолтный воркфлоу)
- `WorkflowEditor` редактирует единственный дефолтный воркфлоу

---

## Стадии

### Стадия 1. Обновление базовых документов

Прежде чем проектировать реализацию — привести в порядок документы, которые описывают потребности. Это нужно для архитектурного ревью на стадии 2.

#### 1.1 User stories (`docs/stories/`)

**`docs/stories/core.md` — раздел G (Воркфлоу)**

| № | Что менять | Действие |
|---|------------|----------|
| G.1 | AC «воркфлоу привязан к проекту» — не отражает мульти-воркфлоу | Добавить: «Для каждого типа задачи настраивается отдельный воркфлоу. Система предоставляет системные воркфлоу по умолчанию для каждого типа» |
| G.1 | AC «статус имеет категорию `open/in_progress/done`» | Сверить с реализацией (в коде: `initial/intermediate/final`) — расхождение |
| Новая | Менеджер хочет настроить, какой воркфлоу используется для каждого типа задачи в проекте | Добавить историю с AC |
| Новая | Системные воркфлоу используются по умолчанию, если проектный override не задан | Добавить историю |

**`docs/stories/planning.md` — раздел K (Boards)**

| № | Что менять | Действие |
|---|------------|----------|
| K.1 | AC «Колонки Kanban соответствуют статусам воркфлоу проекта» | Переписать: «Колонки Kanban настраиваются независимо от воркфлоу. Менеджер задаёт фиксированный набор колонок (напр. 5) и сопоставляет каждой статусы из всех воркфлоу проекта» |
| Новая | Менеджер хочет настроить маппинг статусов на колонки борды, чтобы задачи разных типов отображались в нужных колонках | Добавить историю с AC |

#### 1.2 Приоритизация (`docs/09-mvp.md`)

| Раздел | Что менять |
|--------|------------|
| G (Воркфлоу) | Добавить 🟢/🟡 для: «Воркфлоу по типу задачи», «Настройка маппинга статусов на колонки борды», «Системные воркфлоу по умолчанию» |
| K (Доски) | Обновить описание: «Kanban-доска с настраиваемыми колонками (не по воркфлоу, а по board_column)» |

#### 1.3 Модель данных (`docs/12-data-model.md`)

| Таблица | Изменение |
|---------|-----------|
| `Workflow` | `project_id` — nullable (NULL = системный воркфлоу) |
| `TaskType` | Добавить поле `default_workflow_id FK → workflows.id` (nullable — для кастомных типов может не быть дефолта) |
| Новая `ProjectTaskTypeConfig` | `(project_id, task_type_id, workflow_id)` — проектный override воркфлоу по типу |
| Новая `BoardColumn` | `(id, project_id, name, position)` — колонки борды проекта |
| Новая `BoardColumnStatus` | `(board_column_id, status_id)` — маппинг статусов на колонки |
| `Task.workflow_id` | Остаётся (присваивается при создании согласно логике выбора воркфлоу) |
| ERD Mermaid | Обновить диаграмму, добавить новые таблицы и связи |

Логика выбора воркфлоу при создании задачи (документировать в `12-data-model.md`):
```
task_type → ProjectTaskTypeConfig(project) → TaskType.default_workflow_id → ошибка создания
```

#### 1.4 API (`docs/15-api.md`)

Новые эндпоинты для документирования:

| Эндпоинт | Метод | Описание |
|----------|-------|----------|
| `/projects/{id}/board-columns` | GET | Список колонок борды |
| `/projects/{id}/board-columns` | POST | Создать колонку |
| `/board-columns/{id}` | PATCH | Переименовать / перепозиционировать колонку |
| `/board-columns/{id}` | DELETE | Удалить колонку (нельзя, если есть задачи в статусах этой колонки?) |
| `/board-columns/{id}/statuses` | POST | Добавить статус в колонку |
| `/board-columns/{id}/statuses/{status_id}` | DELETE | Убрать статус из колонки |
| `/projects/{id}/task-type-configs` | GET | Конфигурация воркфлоу по типам для проекта |
| `/projects/{id}/task-type-configs/{task_type_id}` | PUT | Задать/сменить воркфлоу для типа |
| `/projects/{id}/task-type-configs/{task_type_id}` | DELETE | Сбросить к системному дефолту |
| `/task-types` (или `/projects/{id}/task-types`) | GET | Список типов задач (системных + проектных) |

---

### Стадия 2. Архитектурное ревью

Предыдущее ревью (`docs/16-arch-review.md`) проводилось 2026-04-26 для модели с `Assignment`/`global_status`. С тех пор модель существенно изменилась (рефакторинг этапа 8: убран Assignment, добавлен TaskType/Comment). Нужно новое ревью.

**Цель ревью:** Зафиксировать текущее реальное состояние кода, выявить расхождения между документами и реализацией, оценить корректность дизайна FR-001.

**Что проверить:**

#### 2.1 Delta между старой документацией и текущим кодом

| Тема | Документы говорят | Код на самом деле | Действие |
|------|-------------------|-------------------|----------|
| Назначение исполнителей | `Assignment` (один на пользователя), multi-assignee, global_status | `Task.assignee_id` — единственный исполнитель, нет Assignment-таблицы | Решить: документацию привести к коду или наоборот |
| `global_status` | Поле в `Task`, обновляется при изменении Assignment'ов | Нет в текущем коде (удалено вместе с Assignment) | Убрать из docs или восстановить |
| Decision Process | Solution/TaskDecision/декрипт process в backend | По коду реализован? (проверить models/decision.py) | Синхронизировать |
| Категории статусов | `open/in_progress/done` (в docs) | `initial/intermediate/final` (в коде) | Обновить документацию |
| `workflow_id` у Assignment | Assignment хранит workflow_id | Assignment удалён, workflow_id теперь на Task | Обновить `12-data-model.md` |

#### 2.2 Корректность дизайна FR-001

| Вопрос | Анализ |
|--------|--------|
| Нужна ли система BoardColumn для MVP фичи? | BoardColumn решает отображение задач разных типов на одной борде. Без неё борда либо показывает только один воркфлоу, либо слипает статусы. Нужна. |
| Как обрабатывать задачи без маппинга в BoardColumn? | Если статус задачи не сопоставлен ни с одной колонкой — задача не отображается на борде. Решение: при создании воркфлоу/BoardColumn автоматически создавать маппинг. |
| Что происходит с бордой при удалении статуса из воркфлоу? | Маппинг `BoardColumnStatus` на удалённый статус должен автоматически удаляться (ON DELETE CASCADE). |
| Нужен ли `Task.workflow_id` после FR-001? | Да — воркфлоу фиксируется на задаче при создании и не меняется при изменении настроек проекта. |
| Как рендерить BoardColumn на фронте? | GET `/projects/{id}/board-columns` возвращает колонки с вложенными `status_ids`. Задача помещается в колонку по `task.current_status_id`. |
| Может ли один статус быть в нескольких колонках? | Не должен — иначе задача отобразится дважды. Нужна валидация на уровне API. |

#### 2.3 Риски реализации

| Риск | Уровень | Митигация |
|------|---------|-----------|
| Нет данных BoardColumn для существующего проекта при первом деплое | 🔴 | Seed при `reset_db.py` создаёт дефолтные BoardColumn для дефолтного воркфлоу |
| Статус задачи не попал ни в одну колонку | 🟡 | Специальная «Без колонки» на борде или предупреждение в настройках |
| Сложность WorkflowEditor при N воркфлоу | 🟡 | Редактор показывает таб-вкладки по воркфлоу (один воркфлоу — нет вкладок) |
| Миграция существующих задач при смене воркфлоу для типа | 🟡 | `current_status_id` сохраняется; если статус не в новом воркфлоу — задача помечается как «Требует внимания» |

**Ожидаемый выход стадии 2:** Документ `docs/17-arch-review-2.md` с перечнем найденных расхождений, закрытыми вопросами по дизайну, открытыми вопросами (если остались). Все критические расхождения между docs и кодом — исправлены до перехода к стадии 3.

---

### Стадия 3. План реализации

#### 3.1 Backend

**Шаг B1. Миграция модели данных**

- [ ] `Workflow.project_id` → nullable (`Optional[uuid.UUID]`)
- [ ] `TaskType` — добавить `default_workflow_id: Optional[uuid.UUID]` FK → `workflows.id`
- [ ] Новая модель `ProjectTaskTypeConfig (id, project_id, task_type_id, workflow_id)`, уникальный индекс `(project_id, task_type_id)`
- [ ] Новая модель `BoardColumn (id, project_id, name, position)`, индекс `(project_id, position)`
- [ ] Новая модель `BoardColumnStatus (board_column_id, status_id)`, уникальный индекс `(status_id)` (статус в одной колонке)
- [ ] `reset_db.py` — seed системных воркфлоу (task/bug/story/epic/decision) + дефолтные BoardColumn для demo-проекта

**Шаг B2. Сервисный слой**

- [ ] `workflow_service.py` — новые функции:
  - `get_workflow_for_task_type(project_id, task_type_id)` — логика выбора: ProjectTaskTypeConfig → TaskType.default_workflow_id → error
  - `get_board_columns(project_id)` — колонки с вложенными статусами
  - `create_board_column / update_board_column / delete_board_column`
  - `add_status_to_column / remove_status_from_column`
  - `get_project_task_type_configs(project_id)` — список конфигураций по типам
  - `set_task_type_workflow(project_id, task_type_id, workflow_id)` — create/update ProjectTaskTypeConfig
- [ ] `task_service.create_task` — использовать `get_workflow_for_task_type` вместо `is_default` lookup

**Шаг B3. API эндпоинты**

- [ ] `GET /projects/{id}/task-types` — список типов задач, доступных в проекте (системных + кастомных)
- [ ] `GET /projects/{id}/task-type-configs` — конфигурация воркфлоу по типам
- [ ] `PUT /projects/{id}/task-type-configs/{task_type_id}` — задать/сменить воркфлоу
- [ ] `DELETE /projects/{id}/task-type-configs/{task_type_id}` — сбросить к системному
- [ ] `GET /projects/{id}/board-columns` — список колонок с status_ids
- [ ] `POST /projects/{id}/board-columns` — создать колонку
- [ ] `PATCH /board-columns/{id}` — переименовать / изменить позицию
- [ ] `DELETE /board-columns/{id}` — удалить колонку
- [ ] `POST /board-columns/{id}/statuses` — добавить статус в колонку
- [ ] `DELETE /board-columns/{id}/statuses/{status_id}` — убрать статус из колонки

**Шаг B4. Тесты**

- [ ] `test_task_type_workflow_selection.py` — логика выбора воркфлоу при создании задачи:
  - Нет ProjectTaskTypeConfig → берётся TaskType.default_workflow_id
  - Есть ProjectTaskTypeConfig → берётся workflow из него
  - Нет ни того ни другого → 400 BAD_REQUEST
- [ ] `test_board_columns.py` — CRUD колонок, валидация уникальности статуса в колонке
- [ ] `test_board_columns.py` — при удалении статуса из воркфлоу → его BoardColumnStatus удаляется каскадно

---

#### 3.2 Frontend

**Шаг F1. Новые API-хуки**

В `frontend/src/features/projects/workflowApi.ts`:
- [ ] `useBoardColumns(projectId)` — GET `/projects/{id}/board-columns`
- [ ] `useCreateBoardColumn / useUpdateBoardColumn / useDeleteBoardColumn`
- [ ] `useAddStatusToColumn / useRemoveStatusFromColumn`
- [ ] `useTaskTypeConfigs(projectId)` — GET `/projects/{id}/task-type-configs`
- [ ] `useSetTaskTypeWorkflow / useResetTaskTypeWorkflow`
- [ ] `useProjectTaskTypes(projectId)` — GET `/projects/{id}/task-types`

**Шаг F2. WorkflowEditor — поддержка нескольких воркфлоу**

Текущий `WorkflowEditor` редактирует только `is_default` воркфлоу. Нужно:
- [ ] Получать список всех воркфлоу проекта
- [ ] Вкладки по воркфлоу (при одном воркфлоу — без вкладок, как сейчас)
- [ ] Кнопка «Создать воркфлоу» → диалог с именем
- [ ] Кнопка удаления воркфлоу (с подтверждением; нельзя удалить, если есть задачи)

**Шаг F3. Новый компонент `BoardColumnEditor`**

В `frontend/src/features/projects/BoardColumnEditor.tsx`:
- [ ] Список BoardColumn с позицией (DnD-переупорядочивание, как в StatusesEditor)
- [ ] Каждая колонка — название + набор статусов (мультиселект из всех статусов всех воркфлоу проекта)
- [ ] Добавить/удалить статус из колонки drag-and-drop или чекбокс
- [ ] Добавить/удалить колонку
- [ ] Предупреждение если есть статусы, не сопоставленные ни с одной колонкой

**Шаг F4. Обновление `ProjectSettings`**

- [ ] Добавить секцию «Task type workflows» — маппинг типов на воркфлоу (таблица: тип | воркфлоу | select для смены)
- [ ] Добавить секцию «Board columns» — `<BoardColumnEditor />`

**Шаг F5. Обновление `TaskBoard`**

- [ ] Получать `useBoardColumns(projectId)` вместо `useProjectWorkflows`
- [ ] Рендерить колонки по `board_column.name` + `board_column.position`
- [ ] Задача помещается в колонку по `task.current_status_id ∈ board_column.status_ids`
- [ ] При drag → вызывать `useTransitionStatus` с первым разрешённым статусом из целевой колонки (или диалог выбора, если несколько)
- [ ] UX-долг item 5 (подсветка всех колонок при drag) — решается здесь: разрешённые колонки = те, где есть допустимый переход из текущего статуса

**Шаг F6. Обновление `CreateTaskModal`**

- [ ] При смене `task_type` показывать статусы из воркфлоу этого типа (через `useProjectTaskTypes` + config lookup)
- [ ] Или скрыть поле начального статуса (задача создаётся в дефолтном начальном статусе своего воркфлоу)

---

### Стадия 4. ADR и обновление навигации

- [ ] ADR-009: «Воркфлоу по типу задачи и BoardColumn» — зафиксировать решение о BoardColumn vs прямом рендере по воркфлоу
- [ ] Обновить `docs/README.md` — добавить `phase-9-fr001-multi-workflow.md` в таблицу документов
- [ ] Обновить `CLAUDE.md` — этап 9 в таблице реализации
- [ ] Закрыть UX-долг item 5 в `docs/ux-debt.md` (drag подсветка)

---

## Общий чеклист прогресса

### Стадия 1 — Документы

- [x] `stories/core.md` G — исправлены категории статусов, добавлены 2 новые истории FR-001
- [x] `stories/core.md` F — мульти-исполнители → 🟡, AC одиночного assignee обновлены
- [x] `stories/planning.md` K — обновлён AC Kanban, добавлена история board_column
- [x] `09-mvp.md` — приоритизация обновлена (F мульти → 🟡, T всё → 🟡, G/K FR-001 → 🟢)
- [x] `12-data-model.md` — полный переписать ERD под текущий код; v2-таблицы вынесены
- [ ] `15-api.md` — задокументировать новые эндпоинты FR-001 (board-columns, task-type-configs)

### Стадия 2 — Архитектурное ревью

- [x] Создать `docs/17-arch-review-2.md` — 20 delta, 2 критических блокера
- [x] Устранить расхождения docs/код (12-data-model, stories, 07-decision-process, tech-debt)
- [x] Закрыть открытые вопросы дизайна FR-001 (см. раздел 3 ревью)

### Стадия 3 — Реализация

#### Backend
- [ ] B1. Миграция модели данных
- [ ] B2. Сервисный слой (workflow selection, board columns CRUD)
- [ ] B3. API эндпоинты
- [ ] B4. Тесты

#### Frontend
- [ ] F1. Новые API-хуки (workflowApi.ts)
- [ ] F2. WorkflowEditor — мульти-воркфлоу
- [ ] F3. BoardColumnEditor — новый компонент
- [ ] F4. ProjectSettings — секции task type configs + board columns
- [ ] F5. TaskBoard — рендер по board_column
- [ ] F6. CreateTaskModal — учёт воркфлоу по типу

### Стадия 4 — ADR и навигация

- [ ] ADR-009
- [ ] docs/README.md, CLAUDE.md
- [ ] Закрыть UX-долг item 5

---

## Открытые вопросы (до стадии 2)

1. **Что делать с задачами без BoardColumn-маппинга?** Предложение: показывать в специальной колонке «Без колонки» (только для менеджера) или не отображать + badge-предупреждение в настройках.

2. **Смена воркфлоу для типа при наличии открытых задач?** Задачи сохраняют `workflow_id` — их `current_status_id` может оказаться в чужом воркфлоу. Нужна ли миграционная процедура (аналог `migrate_status`)?

3. **Системные воркфлоу редактируемы на уровне проекта?** Логично: проект копирует системный воркфлоу при первой кастомизации. Тогда `ProjectTaskTypeConfig.workflow_id` ссылается на копию, а не на системный оригинал.

4. **Нужен ли `task_type` в `BoardColumn` (фильтрация задач типа на конкретной колонке)?** Простой вариант: колонка не знает о типе — задача попадает в колонку только по статусу. Сложный вариант: колонка может фильтровать по типу. Для MVP — простой.
