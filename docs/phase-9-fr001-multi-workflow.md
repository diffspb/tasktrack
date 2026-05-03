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

> Детальный план с точными файлами, сигнатурами и зависимостями.  
> Порядок шагов — жёсткий: каждый шаг зависит от предыдущего.

---

#### Шаг 0. Устранение блокеров (до основных работ)

**0-A. Добавить `GET /projects/{project_id}/task-types`**

- [ ] Файл: `backend/app/api/v1/projects.py`
- [ ] Добавить эндпоинт после `GET /projects/{project_id}/members`:
  ```python
  @router.get("/{project_id}/task-types")
  async def get_project_task_types(
      project_id: UUID,
      session: AsyncSession = Depends(get_session),
      current_user: User = Depends(get_current_user),
  ):
      await require_project_access(session, project_id, current_user)
      task_types = await session.scalars(
          select(TaskType)
          .where(or_(TaskType.is_system.is_(True), TaskType.project_id == project_id))
          .order_by(TaskType.is_system.desc(), TaskType.name)
      )
      return {"items": [TaskTypeResponse.model_validate(t) for t in task_types]}
  ```
- [ ] Тест: `tests/test_projects.py` → `test_get_project_task_types` — возвращает 5 системных типов

**0-B. Добавить `viewer` в `ProjectMemberRole`**

- [ ] Файл: `backend/app/models/project.py`
- [ ] Добавить `viewer = "viewer"` в enum `ProjectMemberRole`
- [ ] Файл: `docs/13-permissions.md` — описать права viewer (read-only: видит задачи и комментарии, но не может изменять)
- [ ] Тест: `tests/test_projects.py` → добавить viewer в `test_add_project_member`

---

#### Шаг 1. Модели данных (backend)

Все изменения — в `backend/app/models/`.

**1-A. `workflow.py` — Workflow.project_id nullable**

- [ ] Изменить:
  ```python
  # было:
  project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
  # стало:
  project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
  ```
- [ ] Существующие записи не затрагиваются — они имеют project_id, просто поле теперь nullable

**1-B. `task_type.py` — добавить `default_workflow_id`**

- [ ] Добавить поле:
  ```python
  default_workflow_id: Mapped[uuid.UUID | None] = mapped_column(
      ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True
  )
  ```
- [ ] Добавить relationship:
  ```python
  default_workflow: Mapped["Workflow | None"] = relationship("Workflow", foreign_keys=[default_workflow_id])
  ```

**1-C. Новые модели в `workflow.py`**

- [ ] Добавить класс `ProjectTaskTypeConfig`:
  ```python
  class ProjectTaskTypeConfig(Base, UUIDMixin, TimestampMixin):
      __tablename__ = "project_task_type_configs"
      
      project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
      task_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("task_types.id", ondelete="CASCADE"), nullable=False)
      workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
      
      __table_args__ = (UniqueConstraint("project_id", "task_type_id"),)
  ```

- [ ] Добавить класс `BoardColumn`:
  ```python
  class BoardColumn(Base, UUIDMixin, TimestampMixin):
      __tablename__ = "board_columns"
      
      project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
      name: Mapped[str] = mapped_column(String(100), nullable=False)
      position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
      
      statuses: Mapped[list["BoardColumnStatus"]] = relationship(
          "BoardColumnStatus", back_populates="column", cascade="all, delete-orphan"
      )
      
      __table_args__ = (Index("ix_board_columns_project_position", "project_id", "position"),)
  ```

- [ ] Добавить класс `BoardColumnStatus`:
  ```python
  class BoardColumnStatus(Base):
      __tablename__ = "board_column_statuses"
      
      board_column_id: Mapped[uuid.UUID] = mapped_column(
          ForeignKey("board_columns.id", ondelete="CASCADE"), primary_key=True
      )
      status_id: Mapped[uuid.UUID] = mapped_column(
          ForeignKey("statuses.id", ondelete="CASCADE"), primary_key=True,
          unique=True  # один статус — одна колонка
      )
      
      column: Mapped["BoardColumn"] = relationship("BoardColumn", back_populates="statuses")
  ```

**1-D. Экспорт новых моделей**

- [ ] Файл: `backend/app/models/__init__.py` — добавить `BoardColumn, BoardColumnStatus, ProjectTaskTypeConfig` в импорты

---

#### Шаг 2. Seed (`backend/scripts/reset_db.py`)

Порядок seed-данных важен из-за FK-зависимостей.

**2-A. Системные воркфлоу (project_id=NULL)**

- [ ] Создать 4 системных воркфлоу перед созданием TaskType:
  ```python
  # Воркфлоу "Базовый задача/история" (для task, story)
  wf_task = Workflow(name="Task/Story", is_default=False)       # project_id=None
  
  # Воркфлоу "Баг-трекинг" (для bug)
  wf_bug = Workflow(name="Bug", is_default=False)
  
  # Воркфлоу "Эпик" (для epic)
  wf_epic = Workflow(name="Epic", is_default=False)
  
  # Воркфлоу "Decision Process" (для decision)
  wf_decision = Workflow(name="Decision Process", is_default=False)
  
  session.add_all([wf_task, wf_bug, wf_epic, wf_decision])
  await session.flush()
  ```

- [ ] Создать статусы для системных воркфлоу:
  ```python
  # wf_task: To Do → In Progress → Review → Done
  st_task_todo   = Status(workflow_id=wf_task.id, name="To Do",       category=initial, is_default=True,  position=0)
  st_task_inprog = Status(workflow_id=wf_task.id, name="In Progress", category=intermediate, position=1)
  st_task_review = Status(workflow_id=wf_task.id, name="Review",      category=intermediate, position=2)
  st_task_done   = Status(workflow_id=wf_task.id, name="Done",        category=final, position=3)
  
  # wf_bug: Open → In Progress → Review → Verified → Closed
  st_bug_open     = Status(workflow_id=wf_bug.id, name="Open",     category=initial, is_default=True, position=0)
  st_bug_inprog   = Status(workflow_id=wf_bug.id, name="In Progress", category=intermediate, position=1)
  st_bug_review   = Status(workflow_id=wf_bug.id, name="Review",   category=intermediate, position=2)
  st_bug_verified = Status(workflow_id=wf_bug.id, name="Verified", category=intermediate, position=3)
  st_bug_closed   = Status(workflow_id=wf_bug.id, name="Closed",   category=final, position=4)
  
  # wf_epic: Planning → Active → Done
  st_epic_plan   = Status(workflow_id=wf_epic.id, name="Planning", category=initial, is_default=True, position=0)
  st_epic_active = Status(workflow_id=wf_epic.id, name="Active",   category=intermediate, position=1)
  st_epic_done   = Status(workflow_id=wf_epic.id, name="Done",     category=final, position=2)
  
  # wf_decision: Open → Collecting → Awaiting Decision → Decided
  st_dec_open     = Status(workflow_id=wf_decision.id, name="Open",              category=initial, is_default=True, position=0)
  st_dec_collect  = Status(workflow_id=wf_decision.id, name="Collecting",        category=intermediate, position=1)
  st_dec_awaiting = Status(workflow_id=wf_decision.id, name="Awaiting Decision", category=intermediate, position=2)
  st_dec_decided  = Status(workflow_id=wf_decision.id, name="Decided",           category=final, position=3)
  ```

- [ ] Создать переходы для каждого системного воркфлоу (линейные + возврат)

**2-B. Привязать `default_workflow_id` к системным типам задач**

- [ ] После `await session.flush()` для статусов:
  ```python
  tt_task.default_workflow_id     = wf_task.id
  tt_bug.default_workflow_id      = wf_bug.id
  tt_story.default_workflow_id    = wf_task.id   # story → тот же воркфлоу что task
  tt_epic.default_workflow_id     = wf_epic.id
  tt_decision.default_workflow_id = wf_decision.id
  ```

**2-C. BoardColumn для demo-проекта**

- [ ] После создания проектного воркфлоу `wf` и его статусов:
  ```python
  # Дефолтные колонки борды для проекта DEMO
  bc1 = BoardColumn(project_id=demo.id, name="To Do",       position=0)
  bc2 = BoardColumn(project_id=demo.id, name="In Progress", position=1)
  bc3 = BoardColumn(project_id=demo.id, name="Review",      position=2)
  bc4 = BoardColumn(project_id=demo.id, name="Done",        position=3)
  session.add_all([bc1, bc2, bc3, bc4])
  await session.flush()
  
  session.add_all([
      BoardColumnStatus(board_column_id=bc1.id, status_id=todo.id),
      BoardColumnStatus(board_column_id=bc2.id, status_id=inprog.id),
      BoardColumnStatus(board_column_id=bc3.id, status_id=review.id),
      BoardColumnStatus(board_column_id=bc4.id, status_id=done.id),
  ])
  ```

---

#### Шаг 3. Сервисный слой (backend)

Все изменения — в `backend/app/services/workflow_service.py`.

**3-A. Новая функция `get_workflow_for_task_type`**

- [ ] Добавить после `list_workflows`:
  ```python
  async def get_workflow_for_task_type(
      session: AsyncSession, project_id: uuid.UUID, task_type_id: uuid.UUID
  ) -> Workflow:
      """Выбор воркфлоу: ProjectTaskTypeConfig → TaskType.default_workflow_id → project default."""
      # 1. Проектный override
      config = await session.scalar(
          select(ProjectTaskTypeConfig)
          .where(
              ProjectTaskTypeConfig.project_id == project_id,
              ProjectTaskTypeConfig.task_type_id == task_type_id,
          )
      )
      if config:
          return await _get_workflow_or_404(session, config.workflow_id)
  
      # 2. Системный дефолт по типу
      task_type = await session.get(TaskType, task_type_id)
      if task_type and task_type.default_workflow_id:
          return await _get_workflow_or_404(session, task_type.default_workflow_id)
  
      # 3. Дефолтный воркфлоу проекта (backward compat)
      wf = await session.scalar(
          select(Workflow).where(
              Workflow.project_id == project_id, Workflow.is_default.is_(True)
          )
      )
      if wf:
          return wf
  
      raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": "NO_DEFAULT_WORKFLOW"})
  ```

**3-B. Board columns: CRUD**

- [ ] Добавить функции:
  ```python
  async def get_board_columns(session, project_id) -> list[BoardColumn]:
      """Колонки с вложенными status_ids, отсортированные по position."""
      ...selectinload(BoardColumn.statuses)...
  
  async def create_board_column(session, project_id, name, position) -> BoardColumn: ...
  
  async def update_board_column(session, column_id, name=None, position=None) -> BoardColumn: ...
  
  async def delete_board_column(session, column_id) -> None: ...
  
  async def add_status_to_column(session, column_id, status_id) -> BoardColumnStatus:
      """Проверить: статус не в другой колонке, статус принадлежит воркфлоу проекта."""
      # Проверка STATUS_ALREADY_MAPPED
      existing = await session.scalar(select(BoardColumnStatus).where(BoardColumnStatus.status_id == status_id))
      if existing:
          raise HTTPException(409, {"code": "STATUS_ALREADY_MAPPED"})
      ...
  
  async def remove_status_from_column(session, column_id, status_id) -> None: ...
  ```

**3-C. Task type configs: CRUD**

- [ ] Добавить функции:
  ```python
  async def get_task_type_configs(session, project_id) -> list[dict]:
      """Все типы задач (системные + проектные) с текущим воркфлоу.
      Для типов без ProjectTaskTypeConfig — показывает TaskType.default_workflow_id."""
      ...
  
  async def set_task_type_workflow(session, project_id, task_type_id, workflow_id) -> ProjectTaskTypeConfig:
      """Upsert: создаёт или обновляет ProjectTaskTypeConfig."""
      # Проверить: workflow принадлежит проекту или is system (project_id=NULL)
      wf = await session.get(Workflow, workflow_id)
      if not wf or (wf.project_id is not None and wf.project_id != project_id):
          raise HTTPException(400, {"code": "WORKFLOW_NOT_ACCESSIBLE"})
      ...
  
  async def reset_task_type_workflow(session, project_id, task_type_id) -> None:
      """Удалить ProjectTaskTypeConfig → тип вернётся к системному дефолту."""
      ...
  ```

**3-D. Обновить `task_service.create_task`**

- [ ] Файл: `backend/app/services/task_service.py`
- [ ] Заменить блок `if workflow_id is None:` на вызов `get_workflow_for_task_type`:
  ```python
  # было:
  if workflow_id is None:
      wf = await session.scalar(select(Workflow).where(...is_default...))
      if not wf: raise HTTPException(...)
      workflow_id = wf.id
  
  # стало:
  if workflow_id is None:
      wf = await get_workflow_for_task_type(session, project_id, task_type.id)
      workflow_id = wf.id
  ```
- [ ] Убрать отдельный вызов `_resolve_task_type` ПЕРЕД вызовом `get_workflow_for_task_type` (task_type нужен раньше для выбора воркфлоу):
  ```python
  task_type = await _resolve_task_type(session, data.task_type_key, project_id)
  wf = await get_workflow_for_task_type(session, project_id, task_type.id)  # вместо is_default lookup
  ```

**3-E. Переименовать `_count_active_assignments`**

- [ ] В `workflow_service.py` переименовать `_count_active_assignments` → `_count_tasks_in_status` (3 места: definition + 2 вызова)

---

#### Шаг 4. API эндпоинты (backend)

**4-A. Эндпоинты в `backend/app/api/v1/projects.py`**

- [ ] `GET /projects/{project_id}/task-type-configs` — вызывает `get_task_type_configs()`
- [ ] `PUT /projects/{project_id}/task-type-configs/{task_type_id}` — вызывает `set_task_type_workflow()`; проверить роль Manager/Admin
- [ ] `DELETE /projects/{project_id}/task-type-configs/{task_type_id}` — вызывает `reset_task_type_workflow()`

**4-B. Новый файл `backend/app/api/v1/board_columns.py`**

- [ ] Создать роутер с prefix `/board-columns`:
  ```python
  router = APIRouter(prefix="/board-columns", tags=["board-columns"])
  
  # PATCH /board-columns/{column_id}
  # DELETE /board-columns/{column_id}
  # POST /board-columns/{column_id}/statuses
  # DELETE /board-columns/{column_id}/statuses/{status_id}
  ```
- [ ] Эндпоинты создания/списка BoardColumn — в `projects.py`:
  ```python
  # GET /projects/{project_id}/board-columns
  # POST /projects/{project_id}/board-columns
  ```

**4-C. Схемы Pydantic**

- [ ] Новые схемы в `backend/app/schemas/workflow.py` (или отдельный файл `board_column.py`):
  ```python
  class BoardColumnResponse(BaseModel):
      id: UUID
      project_id: UUID
      name: str
      position: int
      status_ids: list[UUID]
  
  class BoardColumnCreate(BaseModel):
      name: str
      position: int
  
  class BoardColumnUpdate(BaseModel):
      name: str | None = None
      position: int | None = None
  
  class TaskTypeConfigResponse(BaseModel):
      task_type_id: UUID
      task_type_key: str
      task_type_name: str
      workflow_id: UUID
      workflow_name: str
      is_project_override: bool
  ```

**4-D. Регистрация роутеров**

- [ ] Файл: `backend/app/api/v1/router.py` — добавить `from .board_columns import router as board_columns_router` + `api_router.include_router(board_columns_router)`

---

#### Шаг 5. Тесты (backend)

- [ ] Файл: `backend/tests/test_task_type_workflow.py` — новый файл:
  ```
  test_create_task_uses_system_default_workflow
    Задача создаётся без workflow_id → берётся TaskType.default_workflow_id системного воркфлоу.
  
  test_create_task_uses_project_override
    Есть ProjectTaskTypeConfig для bug → задача берёт воркфлоу из конфига, а не системный.
  
  test_create_task_falls_back_to_project_default
    TaskType.default_workflow_id = NULL → берётся is_default воркфлоу проекта.
  
  test_create_task_no_workflow_anywhere
    Ни конфига, ни default_workflow_id, ни project default → 400 NO_DEFAULT_WORKFLOW.
  
  test_set_task_type_workflow_upsert
    PUT создаёт config; повторный PUT обновляет workflow_id.
  
  test_set_task_type_workflow_not_accessible
    Попытка задать воркфлоу чужого проекта → 400 WORKFLOW_NOT_ACCESSIBLE.
  
  test_reset_task_type_workflow
    DELETE удаляет config; последующее создание задачи снова использует system default.
  ```

- [ ] Файл: `backend/tests/test_board_columns.py` — новый файл:
  ```
  test_get_board_columns_empty
    Проект без BoardColumn → пустой список.
  
  test_create_board_column
    POST создаёт колонку; GET возвращает её.
  
  test_add_status_to_column
    POST /board-columns/{id}/statuses → status_ids обновляется.
  
  test_status_in_one_column_only
    Попытка добавить статус во вторую колонку → 409 STATUS_ALREADY_MAPPED.
  
  test_delete_status_from_workflow_cascades
    Удаление статуса из воркфлоу → BoardColumnStatus удаляется каскадно; GET board-columns не возвращает этот status_id.
  
  test_reorder_columns
    PATCH position=0 меняет порядок колонок.
  
  test_delete_column
    DELETE колонки → статусы освобождаются (нет в других колонках).
  
  test_board_columns_require_manager_role
    Создание/изменение/удаление колонок member'ом → 403.
  ```

- [ ] Обновить `backend/tests/test_tasks.py`:
  ```
  test_create_task_default — добавить assert task.workflow_id == wf_task.id (системный воркфлоу)
  ```

---

#### Шаг 6. Фронтенд: API-хуки

**6-A. Обновить `frontend/src/features/projects/workflowApi.ts`**

- [ ] Добавить типы:
  ```typescript
  export interface BoardColumn {
    id: string
    project_id: string
    name: string
    position: number
    status_ids: string[]
  }
  
  export interface TaskTypeConfig {
    task_type_id: string
    task_type_key: string
    task_type_name: string
    workflow_id: string
    workflow_name: string
    is_project_override: boolean
  }
  ```

- [ ] Добавить хуки:
  ```typescript
  // Board columns
  export function useBoardColumns(projectId: string | undefined)
  export function useCreateBoardColumn(projectId: string)
  export function useUpdateBoardColumn(projectId: string)
  export function useDeleteBoardColumn(projectId: string)
  export function useAddStatusToColumn(projectId: string)
  export function useRemoveStatusFromColumn(projectId: string)
  
  // Task type configs
  export function useTaskTypeConfigs(projectId: string | undefined)
  export function useSetTaskTypeWorkflow(projectId: string)
  export function useResetTaskTypeWorkflow(projectId: string)
  ```
  Invalidation key для всех: `['board-columns', projectId]` и `['task-type-configs', projectId]`.

**6-B. Обновить `frontend/src/features/tasks/api.ts`**

- [ ] Хук `useProjectTaskTypes` уже вызывает корректный URL — ничего не менять, endpoint будет работать после шага 0-A.

---

#### Шаг 7. WorkflowEditor — мульти-воркфлоу

Файл: `frontend/src/features/projects/WorkflowEditor.tsx`

**Текущее состояние:** компонент получает один `is_default` воркфлоу и рендерит его статусы + переходы.

**Изменения:**

- [ ] **Выбор воркфлоу:** добавить список всех воркфлоу проекта вверху как горизонтальные таб-кнопки. Выбранная вкладка определяет `selectedWorkflowId`. При одном воркфлоу — вкладки скрыты (без изменения UX).
  ```tsx
  // При ≥2 воркфлоу показывать:
  <div className="flex gap-2 border-b pb-2 mb-4">
    {workflows.map(wf => (
      <button key={wf.id} onClick={() => setSelected(wf.id)}
        className={cn("px-3 py-1 rounded text-sm", selected === wf.id && "bg-muted font-medium")}>
        {wf.name}
        {wf.is_default && <span className="ml-1 text-[10px] text-muted-foreground">default</span>}
      </button>
    ))}
    <button onClick={() => setCreateOpen(true)} className="ml-auto ..."><Plus /> Новый</button>
  </div>
  ```

- [ ] **Создание воркфлоу:** кнопка «Новый воркфлоу» → `Dialog` с полем названия → `useCreateWorkflow(projectId)`. После создания — переход на новую вкладку.

- [ ] **Удаление воркфлоу:** кнопка в хедере вкладки с `AlertDialog` подтверждения. Нельзя удалить если есть задачи (API вернёт `409 WORKFLOW_IN_USE`). Нельзя удалить последний воркфлоу проекта.

- [ ] Рендер `StatusesEditor` и `TransitionsEditor` — без изменений, передаётся `selectedWorkflowId`.

---

#### Шаг 8. BoardColumnEditor — новый компонент

Файл: `frontend/src/features/projects/BoardColumnEditor.tsx`

**Структура компонента:**

```tsx
export function BoardColumnEditor({ projectId }: { projectId: string }) {
  // Данные
  const { data: columnsData } = useBoardColumns(projectId)
  const { data: workflowsData } = useProjectWorkflows(projectId)
  
  // Все статусы из всех воркфлоу проекта
  const allStatuses = useMemo(() => workflowsData?.flatMap(wf => wf.statuses) ?? [], [workflowsData])
  const mappedStatusIds = useMemo(
    () => new Set(columnsData?.items.flatMap(c => c.status_ids) ?? []),
    [columnsData]
  )
  const unmappedStatuses = allStatuses.filter(s => !mappedStatusIds.has(s.id))
  
  // DnD для переупорядочивания колонок (тот же паттерн что StatusesEditor)
  ...
}
```

**Элементы UI:**

- [ ] **Список колонок** с DnD-ручкой и переупорядочиванием (onDragEnd → `useUpdateBoardColumn` с новыми position-ами)
- [ ] **Каждая колонка:**
  - Inline-редактирование названия (тот же паттерн что в `SortableStatusRow`)
  - Список сопоставленных статусов — каждый как `Badge` с цветной точкой типа воркфлоу и кнопкой ×
  - `Popover`-кнопка «Добавить статус» — список немаппированных статусов (сгруппированных по воркфлоу), чекбоксы или клик для добавления
  - Кнопка удаления колонки (с `AlertDialog`)
- [ ] **Кнопка «Добавить колонку»** внизу → `useCreateBoardColumn` → новая колонка в конце списка
- [ ] **Предупреждение** если `unmappedStatuses.length > 0`: жёлтый banner «N статусов не сопоставлены ни одной колонке — задачи с этими статусами не отобразятся на борде»

---

#### Шаг 9. ProjectSettings — новые секции

Файл: `frontend/src/features/projects/ProjectSettings.tsx`

- [ ] Добавить секцию **«Task type workflows»** перед секцией Workflow:
  ```tsx
  <section className="space-y-4">
    <div>
      <h2 className="text-base font-semibold">Workflow per task type</h2>
      <p className="text-sm text-muted-foreground">
        Choose which workflow each task type uses. Defaults to system workflow if not set.
      </p>
    </div>
    <TaskTypeWorkflowTable projectId={projectId} />
  </section>
  ```

- [ ] Новый компонент `TaskTypeWorkflowTable` (inline в ProjectSettings.tsx):
  ```tsx
  // Таблица: иконка типа | название типа | select воркфлоу (с placeholder "System default") | кнопка сброса
  // useTaskTypeConfigs(projectId) → строки
  // useSetTaskTypeWorkflow / useResetTaskTypeWorkflow → actions
  // Select из useProjectWorkflows(projectId) → опции + "System default"
  ```

- [ ] Добавить секцию **«Board columns»** после секции Workflow:
  ```tsx
  <section className="space-y-4">
    <div>
      <h2 className="text-base font-semibold">Board columns</h2>
      <p className="text-sm text-muted-foreground">
        Map workflow statuses to board columns. Tasks appear in the matching column.
      </p>
    </div>
    <BoardColumnEditor projectId={projectId} />
  </section>
  ```

---

#### Шаг 10. TaskBoard — рендер по board_column

Файл: `frontend/src/features/tasks/TaskBoard.tsx`

**Текущее состояние:** берёт `defaultWorkflow.statuses`, рендерит колонку на каждый статус.

**Изменения:**

- [ ] Заменить `useProjectWorkflows` на `useBoardColumns`:
  ```tsx
  // было:
  const { data: workflows } = useProjectWorkflows(projectId ?? '')
  const defaultWorkflow = workflows?.find(w => w.is_default) ?? workflows?.[0]
  const statuses = [...(defaultWorkflow?.statuses ?? [])].sort(...)
  const transitions = defaultWorkflow?.transitions ?? []
  
  // стало:
  const { data: boardColumnsData } = useBoardColumns(projectId ?? '')
  const { data: workflows } = useProjectWorkflows(projectId ?? '')  // нужны для transitions
  const columns = [...(boardColumnsData?.items ?? [])].sort((a, b) => a.position - b.position)
  // transitions из всех воркфлоу проекта (для drag-валидации)
  const allTransitions = useMemo(() => workflows?.flatMap(wf => wf.transitions) ?? [], [workflows])
  ```

- [ ] Рендер колонок:
  ```tsx
  // было: statuses.map(status => <Column key={status.id} statusId={status.id} ... />)
  // стало:
  columns.map(column => (
    <Column
      key={column.id}
      name={column.name}
      statusIds={column.status_ids}
      tasks={activeTasks.filter(t => column.status_ids.includes(t.current_status_id))}
      isDropTarget={isColumnDropTarget(column, draggedId, allTransitions)}
      ...
    />
  ))
  ```

- [ ] **UX-долг item 5 (исправление подсветки при drag):** вычислять разрешённые целевые колонки:
  ```tsx
  function isColumnDropTarget(column: BoardColumn, draggedTaskId: string | null, transitions): boolean {
    if (!draggedTaskId) return false
    const task = taskById.get(draggedTaskId)
    if (!task) return false
    // Колонка — разрешённая цель, если хотя бы один из её статусов достижим из task.current_status_id
    return column.status_ids.some(targetStatusId =>
      transitions.some(t =>
        t.from_status_id === task.current_status_id && t.to_status_id === targetStatusId
      )
    )
  }
  ```
  Применять: разрешённые → `bg-primary/10`, запрещённые → `opacity-50` (без подсветки).

- [ ] **Drop logic:** при drop в колонку с несколькими статусами — выбирать первый разрешённый переход:
  ```tsx
  async function handleDrop(targetColumn: BoardColumn) {
    const task = taskById.get(draggedId!)
    const targetStatusId = targetColumn.status_ids.find(sid =>
      allTransitions.some(t => t.from_status_id === task.current_status_id && t.to_status_id === sid)
    )
    if (!targetStatusId) return // переход не разрешён
    await transition.mutateAsync({ taskId: task.id, status_id: targetStatusId })
  }
  ```

- [ ] Если `boardColumnsData` не загружены (пустой проект без BoardColumn) — показывать fallback-состояние: «Настройте колонки борды в настройках проекта» с кнопкой-ссылкой.

---

#### Шаг 11. CreateTaskModal — без изменений (скрыть поле начального статуса)

Файл: `frontend/src/features/tasks/CreateTaskModal.tsx`

- [ ] Поле начального статуса НЕ добавлять — задача всегда создаётся в дефолтном статусе воркфлоу.
- [ ] `useProjectTaskTypes` теперь работает (шаг 0-A) — проверить что загрузка типов в модале не падает.

---

#### Шаг 12. Smoke-тест (ручной)

1. `make reset` — проверить что seed выполняется без ошибок, создаются системные воркфлоу и BoardColumn.
2. Открыть борду проекта DEMO — задачи отображаются в колонках «To Do / In Progress / Review / Done».
3. Создать задачу типа «Баг» — убедиться что назначен воркфлоу «Bug», начальный статус «Open».
4. Открыть Settings → «Workflow per task type» — таблица типов с воркфлоу.
5. Сменить воркфлоу для bug → «Базовый» → создать новый баг → статус «To Do».
6. Открыть «Board columns» → добавить колонку, сопоставить статус → задача появляется.
7. Drag-and-drop — подсвечиваются только разрешённые колонки.

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
- [x] `15-api.md` — 10 новых эндпоинтов FR-001 (task-types, task-type-configs, board-columns); исправлены схемы статусов; добавлены error codes

### Стадия 2 — Архитектурное ревью

- [x] Создать `docs/17-arch-review-2.md` — 20 delta, 2 критических блокера
- [x] Устранить расхождения docs/код (12-data-model, stories, 07-decision-process, tech-debt)
- [x] Закрыть открытые вопросы дизайна FR-001 (см. раздел 3 ревью)

### Стадия 3 — Реализация

#### Блокеры (шаг 0)
- [x] 0-A. `GET /projects/{id}/task-types` endpoint + тест
- [x] 0-B. `viewer` роль в `ProjectMemberRole` + тест

#### Backend
- [x] 1. Модели данных (Workflow nullable, TaskType.default_workflow_id, ProjectTaskTypeConfig, BoardColumn, BoardColumnStatus)
- [x] 2. Seed (системные воркфлоу + default_workflow_id + BoardColumn для DEMO)
- [x] 3. Сервисный слой (get_workflow_for_task_type, board columns CRUD, task type configs, rename _count_active_assignments)
- [x] 4. API эндпоинты (task-type-configs в projects.py, новый board_columns.py, регистрация в router.py)
- [x] 5. Тесты (test_task_type_workflow.py: 7 тестов, test_board_columns.py: 8 тестов)

#### Frontend
- [x] 6. API-хуки (workflowApi.ts: BoardColumn/TaskTypeConfig типы + 11 новых хуков)
- [x] 7. WorkflowEditor — вкладки по воркфлоу, Dialog создания/удаления
- [x] 8. BoardColumnEditor — DnD + маппинг статусов + предупреждение о немаппированных
- [x] 9. ProjectSettings → 3 под-страницы (Team / Workflow / Board); TaskTypeWorkflowTable
- [x] 10. TaskBoard — рендер по board_column, drag подсветка только для разрешённых колонок
- [x] 11. CreateTaskModal: подключён useProjectTaskTypes (типы грузятся из API, не хардкод)
- [x] 12. Smoke-тест ручной — пройден пользователем

### Стадия 4 — ADR и навигация

- [x] ADR-009 (BoardColumn vs прямой рендер по воркфлоу)
- [x] docs/README.md, CLAUDE.md — этап 9 добавлен в таблицы
- [x] UX-долг item 5 (drag подсветка) — закрыт в шаге 10

---

## Открытые вопросы (до стадии 2)

1. **Что делать с задачами без BoardColumn-маппинга?** Предложение: показывать в специальной колонке «Без колонки» (только для менеджера) или не отображать + badge-предупреждение в настройках.

2. **Смена воркфлоу для типа при наличии открытых задач?** Задачи сохраняют `workflow_id` — их `current_status_id` может оказаться в чужом воркфлоу. Нужна ли миграционная процедура (аналог `migrate_status`)?

3. **Системные воркфлоу редактируемы на уровне проекта?** Логично: проект копирует системный воркфлоу при первой кастомизации. Тогда `ProjectTaskTypeConfig.workflow_id` ссылается на копию, а не на системный оригинал.

4. **Нужен ли `task_type` в `BoardColumn` (фильтрация задач типа на конкретной колонке)?** Простой вариант: колонка не знает о типе — задача попадает в колонку только по статусу. Сложный вариант: колонка может фильтровать по типу. Для MVP — простой.
