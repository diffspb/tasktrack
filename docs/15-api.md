# 15. REST API — контракты для MVP-сценариев

Внутренний API для фронтенда. Базовый URL: `/api/v1`. Формат: JSON. Аутентификация: HTTP-only cookie (session). Пагинация: offset-based, параметры `?limit=50&offset=0`.

Документ покрывает все эндпоинты, необходимые для прохождения 5 MVP-сценариев из `09-mvp.md`.

---

## S1. Классический флоу (один исполнитель)

### Аутентификация

#### POST /auth/register
Регистрация по email + пароль.

**Тело запроса:**
```json
{
  "email": "user@example.com",
  "password": "min8chars",
  "display_name": "Иван Иванов"
}
```

**Ответ 201:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "display_name": "Иван Иванов"
}
```

**Ошибки:**
- `400 Bad Request` — невалидный email, короткий пароль
- `409 Conflict` — email уже зарегистрирован

---

#### POST /auth/login
Вход по email + пароль. Устанавливает session cookie.

**Тело запроса:**
```json
{
  "email": "user@example.com",
  "password": "mypassword"
}
```

**Ответ 200:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "display_name": "Иван Иванов"
}
```

**Ошибки:**
- `401 Unauthorized` — неверный email или пароль

---

#### POST /auth/logout
Завершить сессию.

**Ответ 204:** (нет тела)

---

#### POST /auth/password-reset/request
Запросить ссылку для сброса пароля.

**Тело запроса:**
```json
{
  "email": "user@example.com"
}
```

**Ответ 200:** (всегда, даже если email не найден — защита от энумерации)
```json
{
  "message": "Если email зарегистрирован, письмо отправлено"
}
```

---

#### POST /auth/password-reset/confirm
Установить новый пароль по токену из письма.

**Тело запроса:**
```json
{
  "token": "reset_token_from_email",
  "new_password": "newpassword123"
}
```

**Ответ 200:**
```json
{
  "message": "Пароль успешно изменён"
}
```

**Ошибки:**
- `400 Bad Request` — невалидный или просроченный токен

---

#### GET /auth/me
Получить текущего пользователя.

**Ответ 200:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "display_name": "Иван Иванов",
  "avatar_url": "https://...",
  "timezone": "Europe/Moscow"
}
```

**Ошибки:**
- `401 Unauthorized` — не авторизован

---

### Проекты

#### POST /projects
Создать проект.

**Тело запроса:**
```json
{
  "name": "Backend",
  "key": "BACK",
  "description": "Бэкенд-сервисы",
  "owner_id": "uuid",
  "visibility": "restricted"
}
```

**Ответ 201:**
```json
{
  "id": "uuid",
  "name": "Backend",
  "key": "BACK",
  "description": "Бэкенд-сервисы",
  "visibility": "restricted",
  "owner_id": "uuid",
  "is_archived": false,
  "created_at": "2026-04-26T10:00:00Z"
}
```

**Ошибки:**
- `400 Bad Request` — невалидный ключ (не уникален, неверный формат)
- `403 Forbidden` — нет прав (не Admin)

---

#### GET /projects
Список доступных проектов.

**Query-параметры:** `?limit=50&offset=0&archived=false&search=text`

**Ответ 200:**
```json
{
  "total": 5,
  "items": [
    {
      "id": "uuid",
      "name": "Backend",
      "key": "BACK",
      "visibility": "restricted",
      "is_archived": false,
      "updated_at": "2026-04-25T15:00:00Z"
    }
  ]
}
```

---

#### GET /projects/{project_id}
Детали проекта.

**Ответ 200:**
```json
{
  "id": "uuid",
  "name": "Backend",
  "key": "BACK",
  "description": "...",
  "visibility": "restricted",
  "owner_id": "uuid",
  "is_archived": false,
  "workflows": [{ "id": "uuid", "name": "Default", "is_default": true }],
  "created_at": "2026-04-26T10:00:00Z"
}
```

**Ошибки:**
- `403 Forbidden` — нет доступа к проекту
- `404 Not Found` — проект не найден

---

#### PATCH /projects/{project_id}
Обновить настройки проекта (частичное обновление).

**Тело запроса:**
```json
{
  "name": "Backend v2",
  "description": "Новое описание",
  "visibility": "public"
}
```

**Ответ 200:** (обновлённый объект проекта)

**Ошибки:**
- `403 Forbidden` — нет прав (нужен Manager или Admin)

---

#### POST /projects/{project_id}/archive
Архивировать проект.

**Ответ 200:**
```json
{
  "id": "uuid",
  "is_archived": true,
  "archived_at": "2026-04-26T12:00:00Z"
}
```

---

#### POST /projects/{project_id}/members
Добавить участника или группу в проект.

**Тело запроса:**
```json
{
  "user_id": "uuid",
  "role": "member"
}
```
или
```json
{
  "group_id": "uuid",
  "role": "viewer"
}
```

**Ответ 201:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "group_id": null,
  "role": "member",
  "created_at": "2026-04-26T10:00:00Z"
}
```

**Ошибки:**
- `400 Bad Request` — указаны и user_id, и group_id одновременно
- `403 Forbidden` — нет прав (нужен Manager или Admin)
- `409 Conflict` — участник уже добавлен

---

#### GET /projects/{project_id}/members
Список участников проекта.

**Ответ 200:**
```json
{
  "total": 10,
  "items": [
    {
      "id": "uuid",
      "type": "user",
      "user": { "id": "uuid", "display_name": "Иван Иванов", "email": "..." },
      "group": null,
      "role": "member"
    }
  ]
}
```

---

#### PATCH /projects/{project_id}/members/{member_id}
Изменить роль участника.

**Тело запроса:**
```json
{
  "role": "manager"
}
```

**Ответ 200:** (обновлённая запись участника)

---

#### DELETE /projects/{project_id}/members/{member_id}
Удалить участника из проекта.

**Ответ 204:** (нет тела)

---

### Воркфлоу

#### GET /projects/{project_id}/workflows
Список воркфлоу проекта.

**Ответ 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Default",
      "is_default": true,
      "statuses": [
        { "id": "uuid", "name": "To Do", "category": "open", "is_initial": true, "is_final": false, "position": 1 },
        { "id": "uuid", "name": "In Progress", "category": "in_progress", "is_initial": false, "is_final": false, "position": 2 },
        { "id": "uuid", "name": "Done", "category": "done", "is_initial": false, "is_final": true, "position": 3 }
      ],
      "transitions": [
        { "id": "uuid", "from_status_id": "uuid1", "to_status_id": "uuid2", "allowed_roles": [] },
        { "id": "uuid", "from_status_id": "uuid2", "to_status_id": "uuid3", "allowed_roles": [] }
      ]
    }
  ]
}
```

---

#### POST /projects/{project_id}/workflows
Создать воркфлоу.

**Тело запроса:**
```json
{
  "name": "Bug tracking",
  "is_default": false
}
```

**Ответ 201:** (созданный объект воркфлоу)

---

#### POST /projects/{project_id}/workflows/{workflow_id}/statuses
Добавить статус в воркфлоу.

**Тело запроса:**
```json
{
  "name": "In Review",
  "category": "in_progress",
  "color": "#FFA500",
  "position": 3,
  "is_initial": false,
  "is_final": false
}
```

**Ответ 201:** (созданный статус)

---

#### POST /projects/{project_id}/workflows/{workflow_id}/transitions
Добавить переход между статусами.

**Тело запроса:**
```json
{
  "from_status_id": "uuid",
  "to_status_id": "uuid",
  "allowed_roles": ["member", "manager"]
}
```

**Ответ 201:** (созданный переход)

---

### Задачи

#### POST /projects/{project_id}/tasks
Создать задачу.

**Тело запроса:**
```json
{
  "title": "Реализовать авторизацию",
  "description": "Описание задачи в rich-text/markdown",
  "task_type": "feature",
  "priority": "high",
  "due_date": "2026-05-15",
  "estimated_hours": 8,
  "workflow_id": "uuid",
  "decision_maker_id": "uuid",
  "allow_multi_accept": false,
  "label_ids": ["uuid1", "uuid2"]
}
```

**Ответ 201:**
```json
{
  "id": "uuid",
  "key": "BACK-42",
  "title": "Реализовать авторизацию",
  "task_type": "feature",
  "priority": "high",
  "status": {
    "id": "uuid",
    "name": "To Do",
    "category": "open"
  },
  "global_status": "open",
  "reporter": { "id": "uuid", "display_name": "Иван" },
  "decision_maker": { "id": "uuid", "display_name": "Пётр" },
  "allow_multi_accept": false,
  "due_date": "2026-05-15",
  "created_at": "2026-04-26T10:00:00Z",
  "version": 1
}
```

**Ошибки:**
- `400 Bad Request` — невалидные поля
- `403 Forbidden` — нет прав (нужен Member или выше)

---

#### GET /projects/{project_id}/tasks
Список задач проекта с фильтрами.

**Query-параметры:** `?limit=50&offset=0&status_id=uuid&assignee_id=uuid&label_id=uuid&priority=high&search=text&global_status=in_progress`

**Ответ 200:**
```json
{
  "total": 42,
  "items": [
    {
      "id": "uuid",
      "key": "BACK-42",
      "title": "Реализовать авторизацию",
      "priority": "high",
      "global_status": "in_progress",
      "due_date": "2026-05-15",
      "assignees": [
        { "id": "uuid", "display_name": "Анна", "role": "lead", "personal_status": "In Progress" }
      ],
      "labels": [{ "id": "uuid", "name": "auth", "color": "#333" }]
    }
  ]
}
```

---

#### GET /tasks/{task_id}
Детали задачи.

**Ответ 200:**
```json
{
  "id": "uuid",
  "key": "BACK-42",
  "title": "Реализовать авторизацию",
  "description": "...",
  "task_type": "feature",
  "priority": "high",
  "global_status": "in_progress",
  "current_status": { "id": "uuid", "name": "To Do" },
  "reporter": { "id": "uuid", "display_name": "Иван" },
  "decision_maker": { "id": "uuid", "display_name": "Пётр" },
  "allow_multi_accept": false,
  "due_date": "2026-05-15",
  "estimated_hours": 8,
  "assignments": [
    {
      "id": "uuid",
      "user": { "id": "uuid", "display_name": "Анна" },
      "assignee_role": "lead",
      "personal_status": { "id": "uuid", "name": "In Progress", "category": "in_progress" },
      "resolution": null,
      "started_at": "2026-04-26T09:00:00Z"
    }
  ],
  "labels": [],
  "decision_criteria": [],
  "links": [],
  "version": 3,
  "created_at": "2026-04-26T10:00:00Z",
  "updated_at": "2026-04-26T11:00:00Z"
}
```

---

#### PATCH /tasks/{task_id}
Обновить задачу (частичное обновление). Поддерживает `version` для оптимистичной блокировки.

**Тело запроса:**
```json
{
  "title": "Новый заголовок",
  "priority": "critical",
  "due_date": "2026-05-20",
  "version": 3
}
```

**Ответ 200:** (обновлённый объект задачи с новым `version`)

**Ошибки:**
- `409 Conflict` — конфликт версий (version в запросе не совпадает с version в БД)
- `403 Forbidden` — нет прав на редактирование

---

#### DELETE /tasks/{task_id}
Soft-delete задачи.

**Ответ 204:** (нет тела)

**Ошибки:**
- `403 Forbidden` — нет прав

---

### Назначение исполнителей

#### POST /tasks/{task_id}/assignments
Назначить исполнителя.

**Тело запроса:**
```json
{
  "user_id": "uuid",
  "assignee_role": "lead"
}
```

**Ответ 201:**
```json
{
  "id": "uuid",
  "task_id": "uuid",
  "user": { "id": "uuid", "display_name": "Анна" },
  "assignee_role": "lead",
  "personal_status": { "id": "uuid", "name": "To Do" },
  "created_at": "2026-04-26T10:00:00Z"
}
```

**Ошибки:**
- `403 Forbidden` — нет прав (нужен Manager)
- `404 Not Found` — пользователь не найден или не состоит в проекте

---

#### PATCH /assignments/{assignment_id}/status
Перевести Assignment в новый статус воркфлоу.

**Тело запроса:**
```json
{
  "status_id": "uuid",
  "resolution_id": "uuid"
}
```

`resolution_id` обязателен при переходе в финальный статус воркфлоу (`is_final = true`).

**Ответ 200:** (обновлённый Assignment)

**Ошибки:**
- `400 Bad Request` — переход статуса недопустим воркфлоу; отсутствует `resolution_id` при финальном статусе
- `403 Forbidden` — нет прав (смена статуса — исполнитель своего Assignment или менеджер)

---

#### PATCH /assignments/{assignment_id}/role
Изменить роль исполнителя в задаче.

**Тело запроса:**
```json
{
  "role": "reviewer"
}
```

Смена роли доступна только до момента подачи исполнителем Solution (пока Solution не переведён в `submitted`).

**Ответ 200:** (обновлённый Assignment)

**Ошибки:**
- `400 Bad Request` — смена роли заблокирована (Solution уже подан)
- `403 Forbidden` — нет прав (только менеджер или Admin)

---

#### DELETE /assignments/{assignment_id}
Удалить исполнителя из задачи.

**Ответ 204:** (нет тела)

**Ошибки:**
- `403 Forbidden` — нет прав (нужен Manager)
- `400 Bad Request` — нельзя удалить исполнителя с принятым Solution

---

### Статусы, история, комментарии

#### GET /tasks/{task_id}/history
История изменений задачи.

**Query-параметры:** `?limit=50&offset=0`

**Ответ 200:**
```json
{
  "total": 15,
  "items": [
    {
      "id": "uuid",
      "user": { "id": "uuid", "display_name": "Анна" },
      "action": "status_changed",
      "field_name": "personal_status",
      "old_value": "To Do",
      "new_value": "In Progress",
      "created_at": "2026-04-26T09:30:00Z"
    }
  ]
}
```

---

#### POST /tasks/{task_id}/comments
Добавить комментарий.

**Тело запроса:**
```json
{
  "content": "Комментарий с **форматированием** и @uuid-пользователя",
  "parent_comment_id": null
}
```

**Ответ 201:**
```json
{
  "id": "uuid",
  "author": { "id": "uuid", "display_name": "Анна" },
  "content": "...",
  "parent_comment_id": null,
  "is_deleted": false,
  "created_at": "2026-04-26T10:15:00Z"
}
```

---

#### GET /tasks/{task_id}/comments
Список комментариев задачи (хронологический, с ответами).

**Ответ 200:**
```json
{
  "total": 5,
  "items": [
    {
      "id": "uuid",
      "author": { "id": "uuid", "display_name": "Анна" },
      "content": "...",
      "is_deleted": false,
      "edited_at": null,
      "replies": [],
      "created_at": "..."
    }
  ]
}
```

---

#### PATCH /comments/{comment_id}
Редактировать комментарий.

**Тело запроса:**
```json
{
  "content": "Исправленный текст"
}
```

**Ответ 200:** (обновлённый комментарий с `edited_at`)

**Ошибки:**
- `403 Forbidden` — не автор комментария

---

#### DELETE /comments/{comment_id}
Удалить комментарий (мягкое: `is_deleted = true`).

**Ответ 200:**
```json
{
  "id": "uuid",
  "is_deleted": true
}
```

---

#### POST /tasks/{task_id}/attachments
Загрузить вложение.

**Content-Type:** `multipart/form-data`

**Поля формы:**
- `file` — файл (до 20 МБ)

**Ответ 201:**
```json
{
  "id": "uuid",
  "filename": "screenshot.png",
  "file_size": 102400,
  "mime_type": "image/png",
  "created_at": "2026-04-26T10:00:00Z"
}
```

**Ошибки:**
- `413 Payload Too Large` — файл больше 20 МБ
- `400 Bad Request` — превышен лимит проекта (500 МБ)

---

#### POST /tasks/{task_id}/links
Добавить связь между задачами.

**Тело запроса:**
```json
{
  "target_task_id": "uuid",
  "link_type": "blocks"
}
```

**Доступные типы:** `blocks`, `is_blocked_by`, `duplicates`, `related`

**Ответ 201:**
```json
{
  "id": "uuid",
  "source_task_id": "uuid",
  "target_task_id": "uuid",
  "link_type": "blocks"
}
```

---

#### POST /tasks/{task_id}/watchers
Подписаться на задачу (стать Watcher'ом).

**Ответ 201:** `{ "task_id": "uuid", "user_id": "uuid" }`

---

#### DELETE /tasks/{task_id}/watchers/me
Отписаться от задачи.

**Ответ 204:** (нет тела)

---

#### POST /tasks/{task_id}/close
Принудительное закрытие задачи менеджером.

**Тело запроса:**
```json
{
  "resolution_id": "uuid",
  "reason": "Причина принудительного закрытия"
}
```

**Ответ 200:** (обновлённая задача со `global_status: "closed"`)

**Ошибки:**
- `403 Forbidden` — нет прав (нужен Manager или Admin)

---

#### POST /tasks/{task_id}/reopen
Переоткрыть задачу.

**Тело запроса:**
```json
{
  "assignment_ids": ["uuid1", "uuid2"],
  "reason": "Резолюция оказалась неверной"
}
```

Если `assignment_ids` не указан — переоткрываются все Assignment'ы.

**Ответ 200:** (обновлённая задача)

**Ошибки:**
- `403 Forbidden` — нет прав (нужен Manager, Admin или автор задачи; автор может переоткрыть только свою задачу)

---

## S2 + S3. Мульти-исполнители и Decision Process

### DecisionCriteria

#### POST /tasks/{task_id}/decision-criteria
Задать критерии принятия решения.

**Тело запроса:**
```json
{
  "items": [
    { "description": "Минимальное время выполнения", "position": 1 },
    { "description": "Покрытие тестами ≥ 80%", "position": 2 }
  ]
}
```

**Ответ 201:**
```json
{
  "items": [
    { "id": "uuid", "description": "Минимальное время выполнения", "position": 1, "is_locked": false }
  ]
}
```

**Ошибки:**
- `400 Bad Request` — критерии заблокированы (кто-то уже подал Solution)
- `403 Forbidden` — нет прав

---

#### GET /tasks/{task_id}/decision-criteria
Получить критерии задачи.

**Ответ 200:**
```json
{
  "items": [
    { "id": "uuid", "description": "Минимальное время выполнения", "position": 1, "is_locked": true }
  ]
}
```

---

#### PUT /tasks/{task_id}/decision-criteria
Перезаписать весь список критериев (полная замена).

**Тело запроса:** (аналогично POST)

**Ошибки:**
- `400 Bad Request` — критерии заблокированы

---

### Solution

#### POST /assignments/{assignment_id}/solution
Создать Solution (в статусе draft).

**Тело запроса:**
```json
{
  "content": "Мой подход: использовать OAuth2 с JWT. Преимущества: ..."
}
```

**Ответ 201:**
```json
{
  "id": "uuid",
  "assignment_id": "uuid",
  "content": "...",
  "status": "draft",
  "submitted_at": null,
  "created_at": "2026-04-26T11:00:00Z"
}
```

**Ошибки:**
- `400 Bad Request` — у Assignment уже есть Solution; пользователь не lead
- `403 Forbidden` — нет прав

---

#### GET /assignments/{assignment_id}/solution
Получить Solution для Assignment.

**Ответ 200:**
```json
{
  "id": "uuid",
  "assignment_id": "uuid",
  "content": "...",
  "status": "draft",
  "submitted_at": null,
  "revision_comment": null,
  "attachments": [],
  "created_at": "...",
  "updated_at": "..."
}
```

**Ошибки:**
- `404 Not Found` — Solution ещё не создан
- `403 Forbidden` — нет прав на просмотр (consultant до Decision)

---

#### PATCH /solutions/{solution_id}
Обновить содержимое Solution (доступно в статусе draft или после revision).

**Тело запроса:**
```json
{
  "content": "Обновлённый текст Solution"
}
```

**Ответ 200:** (обновлённый Solution)

**Ошибки:**
- `400 Bad Request` — Solution заблокирован (submitted + decision-maker начал рассмотрение)
- `403 Forbidden` — нет прав

---

#### POST /solutions/{solution_id}/attachments
Добавить вложение к Solution.

**Content-Type:** `multipart/form-data`

**Поля:** `file` (до 20 МБ) или тело `{ "url": "https://..." }` для URL-ссылки.

**Ответ 201:** (объект вложения)

---

#### POST /solutions/{solution_id}/submit
Подать Solution (draft → submitted).

**Тело запроса:** (пустое, `{}`)

**Ответ 200:**
```json
{
  "id": "uuid",
  "status": "submitted",
  "submitted_at": "2026-04-26T14:00:00Z",
  "task_transitioned_to": "awaiting_decision"
}
```

`task_transitioned_to` = `"awaiting_decision"` если это был последний lead-Solution; `null` иначе.

**Ошибки:**
- `400 Bad Request` — Solution не в статусе draft
- `403 Forbidden` — нет прав (только lead-исполнитель)

---

#### POST /solutions/{solution_id}/withdraw
Отозвать поданный Solution (submitted → draft).

**Тело запроса:** (пустое, `{}`)

**Ответ 200:**
```json
{
  "id": "uuid",
  "status": "draft",
  "task_transitioned_to": "in_progress"
}
```

**Ошибки:**
- `400 Bad Request` — Solution не в статусе submitted; decision-maker уже начал рассмотрение
- `403 Forbidden` — нет прав (только автор Solution)

---

#### GET /tasks/{task_id}/solutions
Получить все Solution по задаче (для decision-maker и участников с правами).

**Ответ 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "assignment": {
        "id": "uuid",
        "user": { "id": "uuid", "display_name": "Анна" },
        "assignee_role": "lead"
      },
      "content": "Мой подход: ...",
      "status": "submitted",
      "submitted_at": "2026-04-26T14:00:00Z",
      "revision_comment": null,
      "attachments": []
    }
  ]
}
```

**Ошибки:**
- `403 Forbidden` — нет прав (consultant до Decision)

---

### Decision

#### POST /tasks/{task_id}/decisions
Вынести Decision (принять один или несколько Solution'ов).

**Тело запроса:**
```json
{
  "accepted_solution_ids": ["uuid-solution1"],
  "note": "Выбран подход 1 как более масштабируемый"
}
```

**Ответ 201:**
```json
{
  "id": "uuid",
  "task_id": "uuid",
  "decision_maker": { "id": "uuid", "display_name": "Пётр" },
  "accepted_solution_ids": ["uuid-solution1"],
  "note": "Выбран подход 1 как более масштабируемый",
  "decided_at": "2026-04-26T16:00:00Z"
}
```

После создания Decision:
- Принятые Solution'ы → статус `accepted`
- Остальные `submitted` Solution'ы → статус неизменён (остаются как `submitted`)
- Задача → `decided` → `closed`
- Уведомления: email + in-app всем lead-исполнителям

**Ошибки:**
- `400 Bad Request` — задача не в статусе `awaiting_decision`; `accepted_solution_ids` пуст; несколько Solution при `allow_multi_accept: false`
- `403 Forbidden` — не decision-maker
- `409 Conflict` — Decision уже вынесен

---

#### GET /tasks/{task_id}/decisions
Получить Decision по задаче.

**Ответ 200:**
```json
{
  "id": "uuid",
  "decision_maker": { "id": "uuid", "display_name": "Пётр" },
  "accepted_solution_ids": ["uuid"],
  "accepted_solutions": [
    {
      "id": "uuid",
      "assignment": { "user": { "display_name": "Анна" } },
      "content": "...",
      "submitted_at": "..."
    }
  ],
  "note": "...",
  "decided_at": "2026-04-26T16:00:00Z"
}
```

**Ошибки:**
- `404 Not Found` — Decision ещё не вынесен

---

#### POST /solutions/{solution_id}/request-revision
Отправить Solution на доработку (revision).

**Тело запроса:**
```json
{
  "feedback": "Необходимо добавить обработку edge-case'ов при истечении токена"
}
```

**Ответ 200:**
```json
{
  "solution_id": "uuid",
  "status": "revision_requested",
  "revision_comment": "Необходимо добавить обработку...",
  "task_transitioned_to": "in_revision"
}
```

`task_transitioned_to` = `"in_revision"` если это первый revision в текущем цикле.

**Ошибки:**
- `400 Bad Request` — Solution не в статусе `submitted`; `feedback` пуст; задача не в `awaiting_decision`
- `403 Forbidden` — не decision-maker

---

## S4. Видимость проекта

### Группы

#### POST /groups
Создать группу пользователей.

**Тело запроса:**
```json
{
  "name": "Frontend Team",
  "description": "Команда фронтенда"
}
```

**Ответ 201:**
```json
{
  "id": "uuid",
  "name": "Frontend Team",
  "description": "...",
  "created_at": "..."
}
```

**Ошибки:**
- `403 Forbidden` — не Admin

---

#### GET /groups
Список всех групп.

**Ответ 200:**
```json
{
  "total": 3,
  "items": [
    { "id": "uuid", "name": "Frontend Team", "member_count": 5 }
  ]
}
```

---

#### POST /groups/{group_id}/members
Добавить пользователя в группу.

**Тело запроса:**
```json
{
  "user_id": "uuid"
}
```

**Ответ 201:** `{ "group_id": "uuid", "user_id": "uuid", "added_at": "..." }`

---

#### DELETE /groups/{group_id}/members/{user_id}
Удалить пользователя из группы.

**Ответ 204:** (нет тела)

---

### Управление видимостью

Видимость проекта изменяется через `PATCH /projects/{project_id}` с полем `visibility` (см. выше).

---

## S5. Связи между проектами

#### POST /projects/{project_id}/links
Установить связь `related` с другим проектом.

**Тело запроса:**
```json
{
  "target_project_id": "uuid",
  "link_type": "related"
}
```

**Ответ 201:**
```json
{
  "id": "uuid",
  "project_a_id": "uuid",
  "project_b_id": "uuid",
  "link_type": "related",
  "created_by": { "id": "uuid", "display_name": "Иван" },
  "created_at": "..."
}
```

**Ошибки:**
- `400 Bad Request` — связь уже существует; нет доступа к target_project
- `403 Forbidden` — нет прав (нужен Manager)

---

#### GET /projects/{project_id}/links
Список связей проекта.

**Ответ 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "link_type": "related",
      "linked_project": {
        "id": "uuid",
        "name": "Frontend",
        "key": "FRONT"
      }
    }
  ]
}
```

---

#### DELETE /projects/{project_id}/links/{link_id}
Удалить связь между проектами.

**Ответ 204:** (нет тела)

---

## Вспомогательные эндпоинты

### Профиль пользователя и дашборд

#### GET /users/me/dashboard
Задачи текущего пользователя: где он исполнитель, автор или watcher.

**Query-параметры:** `?status_id=uuid&global_status=in_progress&project_id=uuid&limit=50&offset=0`

**Ответ 200:**
```json
{
  "total": 15,
  "items": [
    {
      "id": "uuid",
      "key": "BACK-42",
      "title": "Реализовать авторизацию",
      "global_status": "in_progress",
      "project": { "id": "uuid", "key": "BACK", "name": "Backend" },
      "personal_status": { "id": "uuid", "name": "In Progress" },
      "my_role": "lead",
      "due_date": "2026-05-15"
    }
  ]
}
```

---

#### PATCH /users/me
Обновить профиль текущего пользователя.

**Тело запроса:**
```json
{
  "display_name": "Иван Иванов",
  "avatar_url": "https://...",
  "timezone": "Europe/Moscow"
}
```

**Ответ 200:** (обновлённый профиль пользователя)

**Ошибки:**
- `400 Bad Request` — невалидный timezone; avatar_url недоступен

---

### OAuth

#### GET /auth/oauth/google
Инициация Google OAuth. Перенаправляет пользователя на страницу авторизации Google.

**Ответ 302:** redirect на `accounts.google.com/o/oauth2/auth?...`

---

#### GET /auth/oauth/google/callback
Callback после авторизации через Google. Обрабатывает код от Google, создаёт или обновляет пользователя, устанавливает сессию.

**Query-параметры:** `?code=...&state=...`

**Ответ 302:** redirect на дашборд приложения.

**Ошибки:**
- `400 Bad Request` — невалидный code или state
- `401 Unauthorized` — Google отказал в доступе

---

### Резолюции

#### GET /projects/{project_id}/resolutions
Список резолюций проекта.

**Ответ 200:**
```json
{
  "items": [
    { "id": "uuid", "name": "Done", "is_active": true, "position": 1 },
    { "id": "uuid", "name": "Won't Fix", "is_active": true, "position": 2 }
  ]
}
```

---

#### POST /projects/{project_id}/resolutions
Создать резолюцию.

**Тело запроса:**
```json
{
  "name": "Cannot Reproduce",
  "position": 5
}
```

**Ответ 201:** (созданная резолюция)

**Ошибки:**
- `403 Forbidden` — нет прав (нужен Manager или Admin)

---

#### PATCH /resolutions/{resolution_id}
Обновить резолюцию (переименовать, изменить позицию, деактивировать).

**Тело запроса:**
```json
{
  "name": "Не воспроизводится",
  "is_active": false
}
```

**Ответ 200:** (обновлённая резолюция)

**Ошибки:**
- `403 Forbidden` — нет прав (нужен Manager или Admin)

---

#### DELETE /resolutions/{resolution_id}
Удалить резолюцию (только если не используется ни в одном Assignment).

**Ответ 204:** (нет тела)

**Ошибки:**
- `403 Forbidden` — нет прав
- `409 Conflict` — резолюция используется в существующих Assignment'ах; следует деактивировать (`is_active = false`)

---

### Связи задач

#### GET /tasks/{task_id}/links
Список связей задачи.

**Ответ 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "link_type": "blocks",
      "target_task": { "id": "uuid", "key": "BACK-43", "title": "...", "project": { "key": "BACK" } }
    }
  ]
}
```

---

#### DELETE /tasks/{task_id}/links/{link_id}
Удалить связь между задачами.

**Ответ 204:** (нет тела)

**Ошибки:**
- `403 Forbidden` — нет прав (нужен Member или выше)
- `404 Not Found` — связь не найдена

---

### Метки задачи

#### POST /tasks/{task_id}/labels/{label_id}
Добавить метку к задаче.

**Ответ 201:** `{ "task_id": "uuid", "label_id": "uuid" }`

**Ошибки:**
- `403 Forbidden` — нет прав (нужен Member или выше)
- `404 Not Found` — метка не принадлежит проекту задачи
- `409 Conflict` — метка уже добавлена

---

#### DELETE /tasks/{task_id}/labels/{label_id}
Снять метку с задачи.

**Ответ 204:** (нет тела)

**Ошибки:**
- `403 Forbidden` — нет прав

---

### Поиск участников проекта

#### GET /projects/{project_id}/members/search
Поиск участников проекта для назначения исполнителем.

**Query-параметры:** `?q=иван&limit=20`

**Ответ 200:**
```json
{
  "items": [
    { "id": "uuid", "display_name": "Иван Иванов", "role": "member" }
  ]
}
```

---

### Управление воркфлоу

#### PATCH /projects/{project_id}/workflows/{workflow_id}/statuses/{status_id}
Переименовать статус в воркфлоу (или изменить цвет, позицию).

**Тело запроса:**
```json
{
  "name": "В рассмотрении",
  "color": "#FFA500"
}
```

**Ответ 200:** (обновлённый статус)

**Ошибки:**
- `403 Forbidden` — нет прав (нужен Manager или Admin)

---

#### DELETE /projects/{project_id}/workflows/{workflow_id}/statuses/{status_id}
Удалить статус из воркфлоу.

Если в этом статусе есть активные Assignment'ы — возвращает `409 Conflict` с описанием последствий. Если подтверждение получено (через параметр `?force=true`) — статус удаляется, все Assignment'ы в нём откатываются к дефолтному статусу воркфлоу, участники получают уведомление.

**Query-параметры:** `?force=true` — подтвердить удаление при наличии активных Assignment'ов.

**Ответ 204:** (нет тела)

**Ошибки:**
- `403 Forbidden` — нет прав (нужен Manager или Admin)
- `409 Conflict` — в статусе есть активные Assignment'ы; тело ответа содержит количество затронутых задач и описание что произойдёт при `force=true`

---

#### DELETE /projects/{project_id}/workflows/{workflow_id}/transitions/{transition_id}
Удалить переход между статусами.

**Ответ 204:** (нет тела)

**Ошибки:**
- `403 Forbidden` — нет прав (нужен Manager или Admin)
- `404 Not Found` — переход не найден

---

### Метки

#### GET /projects/{project_id}/labels
Список меток проекта.

**Ответ 200:** `{ "items": [{ "id": "uuid", "name": "auth", "color": "#333", "is_active": true }] }`

---

#### POST /projects/{project_id}/labels
Создать метку.

**Тело запроса:** `{ "name": "auth", "color": "#333333" }`

**Ответ 201:** (созданная метка)

---

#### PATCH /labels/{label_id}
Обновить метку.

**Тело запроса:** `{ "name": "backend-auth", "is_active": false }`

**Ответ 200:** (обновлённая метка)

---

### Уведомления

#### GET /notifications
Список уведомлений текущего пользователя.

**Query-параметры:** `?limit=50&offset=0&is_read=false`

**Ответ 200:**
```json
{
  "total": 12,
  "unread_count": 3,
  "items": [
    {
      "id": "uuid",
      "event_type": "assigned",
      "entity_type": "task",
      "entity_id": "uuid",
      "message": "Вас назначили на задачу BACK-42",
      "is_read": false,
      "created_at": "2026-04-26T10:00:00Z"
    }
  ]
}
```

---

#### POST /notifications/read-all
Пометить все уведомления как прочитанные.

**Ответ 204:** (нет тела)

---

#### PATCH /notifications/{notification_id}
Пометить конкретное уведомление как прочитанное.

**Тело запроса:** `{ "is_read": true }`

**Ответ 200:** (обновлённое уведомление)

---

### Поиск

#### GET /search
Полнотекстовый поиск по задачам.

**Query-параметры:** `?q=авторизация&project_id=uuid&limit=50&offset=0`

**Ответ 200:**
```json
{
  "total": 7,
  "items": [
    {
      "id": "uuid",
      "key": "BACK-42",
      "title": "Реализовать **авторизацию**",
      "highlight": "...реализовать **авторизацию** через OAuth2...",
      "project": { "id": "uuid", "key": "BACK", "name": "Backend" }
    }
  ]
}
```

---

### Экспорт

#### GET /projects/{project_id}/tasks/export
Экспортировать задачи в CSV.

**Query-параметры:** те же фильтры, что у GET /projects/{id}/tasks

**Ответ 200:**
- Content-Type: `text/csv; charset=utf-8`
- Content-Disposition: `attachment; filename="BACK-tasks-2026-04-26.csv"`

---

## Политика доступа к ресурсам

### Soft-deleted объекты

- Soft-deleted `Task` (поле `deleted_at IS NOT NULL`): возвращает `404 Not Found` для любого запроса, кроме явного admin-запроса с параметром `?include_deleted=true`.
- Soft-deleted `Project`: аналогично — `404 Not Found`.
- `GET /search` и все списки задач не включают soft-deleted задачи по умолчанию. Параметр `?include_deleted=true` доступен только пользователям с ProjectRole = Admin.

### Restricted/Private проекты

- Запрос к `GET /projects/{project_id}` или любому ресурсу внутри проекта, к которому у пользователя нет доступа (`restricted` или `private` без членства): возвращает `404 Not Found` — не `403 Forbidden`. Это предотвращает раскрытие факта существования проекта.

### Email участников

- `GET /projects/{project_id}/members` возвращает поле `email` только пользователям с ProjectRole ≥ Member. Пользователи с Viewer-уровнем получают объект участника без поля `email`.

### Consultant и чужие Solution

- Пользователь с AssigneeRole = `consultant` не видит Solution'ы других исполнителей до вынесения Decision. Проверка выполняется на уровне приложения: `GET /assignments/{id}/solution` и `GET /tasks/{id}/solutions` возвращают `403 Forbidden` для consultant'а, если `TaskDecision` ещё не создан. Это не только правило проекта — проверяется для каждого запроса независимо.

---

## Edge cases

### PATCH /tasks/{id} без поля version

Если тело запроса не содержит поля `version` — возвращается `400 Bad Request` с кодом `VERSION_REQUIRED` и сообщением «version required for optimistic locking».

### POST /solutions/{id}/submit при конкурентной подаче

Если два lead-исполнителя подают Solution почти одновременно, оба запроса обрабатываются транзакционно с `SELECT FOR UPDATE` на строке задачи. Второй запрос ожидает завершения первого. Гонки данных нет при правильной реализации — оба получают корректный ответ последовательно.

### DELETE /assignments/{id} для lead с submitted Solution

Возвращает `400 Bad Request` с кодом `SOLUTION_ALREADY_SUBMITTED`. Solution исполнителя остаётся в истории задачи. Для удаления исполнителя с поданным Solution необходимо сначала отозвать Solution (если это разрешено).

### POST /tasks/{task_id}/links (cross-project)

При создании связи между задачами из разных проектов проверяется read-доступ текущего пользователя к проекту целевой задачи. Если доступа нет — `403 Forbidden` (не `404`, чтобы явно указать на проблему с правами, а не на отсутствие ресурса).

---

## Справочник error codes

Все ошибки возвращаются в формате `{ "error": { "code": "...", "message": "...", "details": {} } }`.

| Код | Описание |
|-----|---------|
| `TASK_NOT_FOUND` | Задача не найдена или soft-deleted |
| `PROJECT_NOT_FOUND` | Проект не найден, недоступен или soft-deleted |
| `ASSIGNMENT_NOT_FOUND` | Assignment не найден |
| `SOLUTION_NOT_FOUND` | Solution не найден или ещё не создан |
| `DECISION_NOT_FOUND` | Decision по задаче ещё не вынесен |
| `VERSION_CONFLICT` | Конфликт версий при оптимистичной блокировке (409) |
| `VERSION_REQUIRED` | Поле `version` обязательно для этого запроса (400) |
| `INVALID_STATUS_TRANSITION` | Переход между статусами недопустим воркфлоу (400) |
| `RESOLUTION_REQUIRED` | Резолюция обязательна при переходе в финальный статус (400) |
| `SOLUTION_ALREADY_SUBMITTED` | Solution уже подан; действие недоступно (400) |
| `CANNOT_MODIFY_CLOSED_TASK` | Задача закрыта; редактирование недоступно (400) |
| `WORKFLOW_IN_USE` | Воркфлоу используется активными Assignment'ами; изменение заблокировано (409) |
| `ACCESS_DENIED` | Недостаточно прав для выполнения действия (403) |
| `INVALID_ROLE_CHANGE` | Смена роли исполнителя заблокирована (Solution уже подан) (400) |

---

## Стандартные форматы ответов

### Пагинация
Все списки возвращают:
```json
{
  "total": 100,
  "items": [...]
}
```

### Ошибки
```json
{
  "error": {
    "code": "TASK_NOT_FOUND",
    "message": "Задача не найдена",
    "details": {}
  }
}
```

### Коды ошибок HTTP

| Код | Значение |
|-----|---------|
| 400 | Невалидные данные запроса |
| 401 | Не авторизован |
| 403 | Нет прав на действие |
| 404 | Ресурс не найден |
| 409 | Конфликт (версия, дублирование) |
| 413 | Слишком большой файл |
| 500 | Внутренняя ошибка сервера |
