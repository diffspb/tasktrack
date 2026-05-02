# 17. Архитектурное ревью № 2

**Дата:** 2026-05-02  
**Объём ревью:** весь бэкенд (models/, services/, api/v1/), ключевые файлы фронтенда, сравнение с docs/12-data-model.md, docs/07-decision-process.md, docs/15-api.md  
**Контекст:** ревью перед стартом FR-001 (multi-workflow). Первое ревью (2026-04-26) проводилось до реализации и описывало планируемую архитектуру. С тех пор выполнен значительный рефакторинг (этапы 3–8): удалён `Assignment`, добавлен `TaskType` как таблица, упрощён Decision Process. Документация за кодом не успела.

---

## Статус

🔴 **Критические расхождения требуют решения до старта FR-001.**

---

## 1. Сводная таблица расхождений (код vs docs)

| # | Что расходится | Серьёзность | Действие |
|---|---------------|-------------|----------|
| D-01 | `Assignment` полностью удалена из кода | **Критично** | Решить: зафиксировать MVP-упрощение в docs или восстановить |
| D-02 | `Task.global_status` нет в коде | **Критично** | То же |
| D-03 | `Solution` заменена суррогатом: `Comment + labels=["solution"]` | **Критично** | Задокументировать как tech-debt или убрать из scope MVP |
| D-04 | `TaskDecision` отсутствует в коде | **Критично** | То же |
| D-05 | Decision Process API полностью отсутствует | **Критично** | Зафиксировать статус в docs |
| D-06 | `GET /projects/{id}/task-types` — нет в бэкенде, вызывается фронтом | **Критично** | Реализовать эндпоинт (см. раздел 2) |
| D-07 | `StatusCategory`: docs говорят `open/in_progress/done`, код — `initial/intermediate/final` | Средне | Обновить docs |
| D-08 | `Transition.required_role` (scalar) vs docs `allowed_roles[]` (array) | Средне | Обновить docs; решить: нужен ли массив ролей |
| D-09 | `TaskType` — таблица в коде, enum-поле в docs ERD | Средне | Обновить ERD |
| D-10 | `Task.parent_task_id` — в коде, нет в docs ERD | Средне | Добавить в ERD |
| D-11 | `Comment.is_deleted` → `deleted_at`; добавлен `labels[]`; нет `search_vector` | Средне | Обновить docs |
| D-12 | `Notification` нет поля `channel`, другая схема | Средне | Обновить docs |
| D-13 | `Status.is_initial/is_final` → `is_default + category` enum | Средне | Обновить docs |
| D-14 | `ProjectMember.role`: фронт имеет `viewer`, бэкенд — нет | Средне | Синхронизировать |
| D-15 | `Task.workflow_id` нет в docs ERD (есть в коде) | Низко | Добавить в ERD |
| D-16 | `User`: docs `password_hash/oauth_*`, код `keycloak_id` | Низко | Обновить ERD |
| D-17 | `Project.archived_at` в docs, в коде только `is_archived: bool` | Низко | Обновить ERD |
| D-18 | `Resolution.is_active` в docs, в коде нет | Низко | Обновить ERD |
| D-19 | В ERD описаны 11 таблиц, отсутствующих в коде: Group, GroupMember, ProjectLink, Label, TaskLabel, Attachment, Watcher, TaskHistory, AuditLog, DecisionCriteria | Низко (v2) | Явно пометить в docs как v2 |
| D-20 | `_count_active_assignments()` считает Tasks, а не Assignment'ов (устаревшее имя) | Низко | Переименовать |

---

## 2. Детали по критическим расхождениям

### D-01 / D-02: Удалён Assignment, нет global_status

**Что произошло:** В коммите `40caac4` («упростить модель задачи — убрать Assignment, добавить TaskType/Comment») был сделан архитектурный сдвиг. Вместо «несколько исполнителей с независимыми воркфлоу» — «один исполнитель (`Task.assignee_id`)». Задача движется по одному воркфлоу через `Task.current_status_id`. Поле `global_status` (open/in_progress/awaiting_decision/…) убрано вместе с Assignment, поскольку оно было производным от состояния Assignment'ов.

**Это MVP-упрощение или откат ключевой фичи?**

Это MVP-упрощение. Цель первого запуска — прогнать реальные проекты и собрать обратную связь по базовому флоу. Мульти-исполнители и полноценный Decision Process — следующий этап (см. tech-debt.md).

**Что нужно сделать:**

1. Обновить `docs/12-data-model.md` — убрать `Assignment` из ERD, добавить `Task.assignee_id`, `Task.workflow_id`, `Task.task_type_id`, `Task.parent_task_id`, удалить `global_status`.
2. Обновить `docs/07-decision-process.md` — добавить раздел «MVP-упрощение: Decision Process без Assignment», описать суррогат через Comment.
3. Добавить в `docs/tech-debt.md` — «Восстановить Assignment + global_status для полноценного мульти-исполнительского воркфлоу (основная фича продукта)».
4. `docs/stories/core.md` раздел F («Назначение и исполнение») — истории F2 (назначить нескольких исполнителей) переместить в 🟡 v2, F1 (один исполнитель) оставить 🟢.

---

### D-03 / D-04 / D-05: Decision Process через суррогат

**Что в коде:** `Comment` с `labels=["solution"]` используется как замена `Solution`. В `meta` задачи хранится `solution_comment_id`. `TaskDecision` не существует. API `submit_solution`, `make_decision`, `request_revision` не реализованы. В `task_service.transition_status` есть функция `_check_decision_task_unblocked()` — проверяет наличие `solution_comment_id` в метаданных подзадач.

**Что нужно сделать:**

1. Обновить `docs/07-decision-process.md` — добавить раздел «MVP-реализация» с описанием суррогатной механики (комментарии с labels).
2. Зафиксировать в `docs/tech-debt.md` — «Полноценная реализация Decision Process: таблицы Solution, TaskDecision, API submit/make-decision/request-revision».
3. `docs/stories/decision-process.md` — истории T (Decision Process) с AC — переместить полные AC в 🟡 v2, для 🟢 MVP описать упрощённый флоу через комментарии.

---

### D-06: Сломанный эндпоинт GET /projects/{id}/task-types

**Что происходит:** Фронтенд (функция `useProjectTaskTypes` в `api.ts`) вызывает `GET /api/v1/projects/{projectId}/task-types`. Этого эндпоинта не существует ни в одном роутере бэкенда. Каждый вызов возвращает 404.

**Немедленное действие (до FR-001):** Добавить эндпоинт в бэкенд.

```python
# backend/app/api/v1/projects.py
@router.get("/{project_id}/task-types")
async def get_project_task_types(project_id: UUID, session=Depends(get_session)):
    # Системные типы (is_system=True, project_id=NULL) + кастомные типы проекта
    task_types = await session.scalars(
        select(TaskType).where(
            or_(TaskType.is_system == True, TaskType.project_id == project_id)
        ).order_by(TaskType.is_system.desc(), TaskType.name)
    )
    return {"items": [TaskTypeResponse.model_validate(t) for t in task_types]}
```

**Тест:** `test_projects.py` — добавить `test_get_project_task_types`.

---

### D-07: StatusCategory именование

**Документы говорят:** `open / in_progress / done`  
**Код:** `initial / intermediate / final`

Значения `initial/intermediate/final` точнее отражают семантику (это позиция в воркфлоу, а не семантическое значение задачи). Решение: обновить документацию под код.

---

### D-08: Transition.allowed_roles vs required_role

**Документы:** `allowed_roles: string[]` (массив, пустой = доступно всем)  
**Код:** `required_role: String(50) nullable` (одна роль или NULL = доступно всем)

Потеря: нельзя задать несколько ролей одновременно. Для MVP — приемлемо (обычно один required_role). Документировать как ограничение и добавить в tech-debt.

---

### D-14: ProjectMember viewer role

**Фронтенд:** `ROLES = ['admin', 'manager', 'member', 'viewer']`  
**Бэкенд enum:** `ProjectMemberRole = {admin, manager, member}` (нет `viewer`)

При попытке добавить участника с ролью `viewer` бэкенд может вернуть ошибку валидации. Нужно синхронизировать: либо добавить `viewer` в бэкенд enum, либо убрать из фронтенда.

По `docs/13-permissions.md` роль `Viewer` описана. Решение: добавить `viewer` в `ProjectMemberRole`.

---

## 3. Дизайн-вопросы FR-001 (закрытые)

По итогам анализа кода следующие вопросы FR-001 можно считать закрытыми:

| Вопрос | Решение |
|--------|---------|
| `TaskType` — таблица или enum? | Таблица (уже реализована). Нужно добавить `default_workflow_id`. |
| `Workflow.project_id` — nullable? | В коде NOT NULL. Для FR-001 сделать nullable (системные воркфлоу). Миграция: `ALTER TABLE workflows ALTER COLUMN project_id DROP NOT NULL`. |
| `Task.workflow_id` — оставить? | Да, оставить. Фиксируется при создании задачи. |
| Нужна ли отдельная таблица `BoardColumn`? | Да. Без неё борда показывает только один воркфлоу. |

Открытые вопросы FR-001 — см. `docs/phase-9-fr001-multi-workflow.md` раздел «Открытые вопросы».

---

## 4. Риски текущей реализации (до FR-001)

| Риск | Уровень | Описание |
|------|---------|----------|
| `GET /projects/{id}/task-types` — 404 | 🔴 | Фронтенд не может загрузить типы задач. CreateTaskModal, TypeFilter — не работают полноценно. |
| Decision Process через комментарии | 🟡 | Нет явного состояния solution (draft/submitted/accepted). Нет API для DM. Клиент знает только через `meta.solution_comment_id`. |
| `ProjectMember viewer` на фронте | 🟡 | Если пользователь добавлен как viewer — бэкенд может не принять. |
| `_count_active_assignments()` имя | 🟢 | Косметика, работает корректно. |

---

## 5. Что сделать до старта FR-001

### Обязательно (блокеры)

- [ ] **B1.** Добавить `GET /projects/{id}/task-types` в бэкенд + тест
- [ ] **B2.** Добавить `viewer` в `ProjectMemberRole` на бэкенде (или убрать из фронтенда)

### Обновление документации

- [ ] **D1.** `docs/12-data-model.md` — переписать ERD под текущий код (убрать Assignment, Solution, TaskDecision; добавить TaskType как таблицу, Task.assignee_id, parent_task_id, workflow_id; обновить Status, Transition, Comment, Notification)
- [ ] **D2.** `docs/07-decision-process.md` — добавить раздел «MVP-упрощение» с описанием суррогатной реализации
- [ ] **D3.** `docs/tech-debt.md` — добавить 3 пункта: (а) Assignment/global_status, (б) Solution/TaskDecision, (в) Transition.required_role → allowed_roles[]
- [ ] **D4.** `docs/stories/core.md` раздел F — F2 (мульти-исполнители) → 🟡 v2
- [ ] **D5.** `docs/stories/decision-process.md` — пересмотреть 🟢/🟡 для историй T в свете MVP-упрощений

### Косметика (можно после FR-001)

- [ ] Переименовать `_count_active_assignments` → `_count_tasks_in_status` в `workflow_service.py`
- [ ] Синхронизировать docs по низко-приоритетным delta (D-13, D-16, D-17, D-18, D-19)

---

## 6. Итоговая оценка

**Вердикт:** код и документация разошлись на уровне ключевой архитектурной концепции. Это нормально для MVP-итерации, но нужно явно зафиксировать границу между «что реализовано сейчас» и «что запланировано в v2».

Критических блокеров для запуска MVP — два (D-06 broken endpoint, D-14 viewer role). Оба быстро исправляются. После исправления можно начинать FR-001.

Обновление документации (ERD, Decision Process) — обязательно до написания кода FR-001, иначе новый этап будет строиться на неверных предпосылках.
