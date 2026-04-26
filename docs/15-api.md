# 15. REST API — контракты для MVP-сценариев

Внутренний API для фронтенда. Базовый URL: `/api/v1`. Формат: JSON. Аутентификация: HTTP-only cookie (session). Пагинация: offset-based, параметры `?limit=50&offset=0`.

Документ покрывает все эндпоинты, необходимые для прохождения MVP-сценариев из `09-mvp.md`.

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
- `404 Not Found` — проект не найден, soft-deleted, или `restricted`/`private` без доступа (возвращается `404`, а не `403`, чтобы не раскрывать факт существования проекта)

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

Если пользователь уже добавлен напрямую — обновляется его индивидуальная роль, возвращается `200 OK` (не `409`). Если пользователь был добавлен только через группу — создаётся отдельная индивидуальная запись с указанной ролью, которая перекрывает групповую роль. Групповая запись остаётся без изменений.

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

#### GET /projects/{project_id}/workflows/{workflow_id}
Детали воркфлоу: полный список статусов и переходов.

**Ответ 200:**
```json
{
  "id": "uuid",
  "name": "Default",
  "is_default": true,
  "statuses": [
    {
      "id": "uuid",
      "name": "To Do",
      "category": "open",
      "color": "#CCCCCC",
      "position": 1,
      "is_initial": true,
      "is_final": false
    },
    {
      "id": "uuid",
      "name": "In Progress",
      "category": "in_progress",
      "color": "#0099FF",
      "position": 2,
      "is_initial": false,
      "is_final": false
    },
    {
      "id": "uuid",
      "name": "Done",
      "category": "done",
      "color": "#00CC66",
      "position": 3,
      "is_initial": false,
      "is_final": true
    }
  ],
  "transitions": [
    { "id": "uuid", "from_status_id": "uuid1", "to_status_id": "uuid2", "allowed_roles": [] },
    { "id": "uuid", "from_status_id": "uuid2", "to_status_id": "uuid3", "allowed_roles": [] }
  ]
}
```

**Ошибки:**
- `404 Not Found` — воркфлоу не найден

---

#### PATCH /projects/{project_id}/workflows/{workflow_id}
Переименовать воркфлоу или сменить дефолтный.

**Тело запроса:**
```json
{
  "name": "Новое название",
  "is_default": true
}
```

**Ответ 200:** (обновлённый объект воркфлоу)

**Ошибки:**
- `403 Forbidden` — нет прав (нужен Manager или Admin)

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

**Ошибки:**
- `404 Not Found` — задача не найдена, soft-deleted, или принадлежит проекту `restricted`/`private`, к которому у пользователя нет доступа (в обоих случаях возвращается `404`, а не `403` или `410` — чтобы не раскрывать факт существования ресурса)

---

#### PATCH /tasks/{task_id}
Обновить задачу (частичное обновление). Поле `version` обязательно для оптимистичной блокировки.

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
- `400 Bad Request` — поле `version` отсутствует в теле запроса (код `VERSION_REQUIRED`)
- `403 Forbidden` — нет прав на редактирование
- `409 Conflict` — `version` в запросе устарел; тело ответа содержит `current_version`:
```json
{
  "error": {
    "code": "VERSION_CONFLICT",
    "message": "Задача была изменена другим пользователем",
    "details": {
      "current_version": 5
    }
  }
}
```

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
- `400 Bad Request` — смена роли заблокирована (Solution уже подан); код `ROLE_CHANGE_NOT_ALLOWED`
- `403 Forbidden` — нет прав (только менеджер или Admin)

---

#### DELETE /assignments/{assignment_id}
Удалить исполнителя из задачи.

**Ответ 204:** (нет тела)

**Ошибки:**
- `403 Forbidden` — нет прав (нужен Manager)
- `400 Bad Request` — нельзя удалить исполнителя с поданным Solution (код `ASSIGNMENT_HAS_SUBMITTED_SOLUTION`). Solution исполнителя остаётся в истории задачи. Для удаления необходимо сначала отозвать Solution (если это разрешено).

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
- `413 Payload Too Large` — файл больше 20 МБ (код `FILE_TOO_LARGE`)
- `400 Bad Request` — превышен лимит хранилища проекта 500 МБ (код `PROJECT_STORAGE_EXCEEDED`)

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

**Ошибки:**
- `403 Forbidden` — при cross-project связи: у текущего пользователя нет read-доступа к проекту целевой задачи (код `PROJECT_ACCESS_DENIED`)

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
Подать Solution (draft → submitted). Также допускается повторная подача после отзыва (`withdraw`): Solution возвращается в `submitted`.

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

Если задача уже перешла в `awaiting_decision` (другой lead успел подать раньше) — Solution помечается как `submitted`, переход задачи не происходит повторно, ответ содержит `task_transitioned_to: null` и код `400` с описанием:

```json
{
  "error": {
    "code": "TASK_ALREADY_AWAITING_DECISION",
    "message": "Задача уже ожидает решения. Solution принят как submitted."
  }
}
```

**Ошибки:**
- `400 Bad Request` — Solution не в статусе `draft` (код `SOLUTION_ALREADY_SUBMITTED`)
- `400 Bad Request` — задача уже в статусе `awaiting_decision` (код `TASK_ALREADY_AWAITING_DECISION`); Solution принимается, но без повторного перехода задачи
- `403 Forbidden` — нет прав (только lead-исполнитель)

---

#### POST /solutions/{solution_id}/withdraw
Отозвать поданный Solution (submitted → draft). После отзыва Solution можно доработать и подать повторно.

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
- `400 Bad Request` — Solution не в статусе `submitted`; decision-maker уже начал рассмотрение
- `400 Bad Request` — Solution находится в статусе `revision_requested` (код `SOLUTION_IN_REVISION`); нельзя отозвать — нужно доработать и подать повторно
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

#### GET /users/me/tasks
Задачи текущего пользователя, где он является исполнителем, автором (reporter) или watcher'ом.

**Query-параметры:** `?role=assignee|reporter|watcher&status=open|in_progress|awaiting_decision|in_revision|decided|closed&project_id=uuid&page=1&page_size=50`

- `role` — фильтр по роли пользователя относительно задачи. По умолчанию — все роли.
- `status` — фильтр по `global_status` задачи.
- `project_id` — ограничить конкретным проектом.
- `page` / `page_size` — пагинация; по умолчанию page=1, page_size=50.

**Ответ 200:**
```json
{
  "total": 15,
  "page": 1,
  "page_size": 50,
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

`personal_status` возвращается только если пользователь является исполнителем задачи (`my_role = "lead"`, `"reviewer"` или `"consultant"`); для reporter и watcher поле равно `null`.

**Ошибки:**
- `400 Bad Request` — невалидное значение `role` или `status`

---

#### GET /users/me/dashboard
Агрегированный дашборд текущего пользователя: задачи где он исполнитель, автор или watcher.

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
Обновить профиль текущего пользователя (name, timezone). Аватар обновляется отдельным эндпоинтом.

**Тело запроса:**
```json
{
  "display_name": "Иван Иванов",
  "timezone": "Europe/Moscow"
}
```

**Ответ 200:** (обновлённый профиль пользователя)

**Ошибки:**
- `400 Bad Request` — невалидный timezone

---

#### POST /users/me/avatar
Загрузить или заменить аватар текущего пользователя.

**Content-Type:** `multipart/form-data`

**Поля формы:**
- `file` — изображение (до 2 МБ); допустимые форматы: JPEG, PNG, WEBP.

**Ответ 200:**
```json
{
  "avatar_url": "https://storage.example.com/avatars/uuid.jpg"
}
```

**Ошибки:**
- `400 Bad Request` — неподдерживаемый формат файла
- `413 Payload Too Large` — файл превышает 2 МБ (код `FILE_TOO_LARGE`)

---

#### DELETE /users/me/avatar
Удалить аватар текущего пользователя. После удаления поле `avatar_url` возвращает `null`.

**Ответ 204:** (нет тела)

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
  "description": "Не удалось воспроизвести проблему",
  "is_default": false,
  "position": 5
}
```

`is_default` — если `true`, данная резолюция будет выбрана по умолчанию при переходе в финальный статус. Только одна резолюция может быть `is_default = true` для проекта.

**Ответ 201:** (созданная резолюция)

**Ошибки:**
- `403 Forbidden` — нет прав (нужен Manager или Admin)

---

#### PATCH /resolutions/{resolution_id}
Обновить резолюцию (переименовать, изменить описание, позицию, деактивировать или задать дефолтную).

**Тело запроса:**
```json
{
  "name": "Не воспроизводится",
  "description": "Не удалось воспроизвести проблему",
  "is_default": true,
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
- `409 Conflict` — резолюция используется в существующих Assignment'ах (код `RESOLUTION_IN_USE`); следует деактивировать (`is_active = false`)

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
Обновить статус воркфлоу: переименовать, изменить цвет, позицию, тип (initial/intermediate/final) или сделать дефолтным.

**Тело запроса:**
```json
{
  "name": "В рассмотрении",
  "color": "#FFA500",
  "category": "in_progress",
  "is_initial": false,
  "is_final": false,
  "is_default": false
}
```

`is_default` — отметить статус как дефолтный (начальный для новых Assignment'ов). Смена дефолтного статуса допускается только если нет активных Assignment'ов в текущем дефолтном статусе.

**Ответ 200:** (обновлённый статус)

**Ошибки:**
- `403 Forbidden` — нет прав (нужен Manager или Admin)
- `409 Conflict` — смена дефолтного статуса заблокирована: есть активные Assignment'ы в текущем дефолтном статусе

---

#### DELETE /projects/{project_id}/workflows/{workflow_id}/statuses/{status_id}
Удалить статус из воркфлоу.

Если в этом статусе есть активные Assignment'ы — возвращает `409 Conflict` с информацией о затронутых Assignment'ах. Перед удалением нужно выполнить миграцию через `POST .../statuses/{status_id}/migrate`.

**Ответ 204:** (нет тела)

**Ошибки:**
- `403 Forbidden` — нет прав (удаление статуса — только Admin)
- `409 Conflict` — в статусе есть активные Assignment'ы (код `STATUS_IN_USE`):
```json
{
  "error": {
    "code": "STATUS_IN_USE",
    "message": "Статус используется активными Assignment'ами",
    "details": {
      "affected_assignments_count": 5,
      "default_status_id": "uuid"
    }
  }
}
```
Клиент должен явно вызвать миграцию (см. следующий эндпоинт), после чего повторить удаление.

---

#### POST /projects/{project_id}/workflows/{workflow_id}/statuses/{status_id}/migrate
Принудительная миграция Assignment'ов из удаляемого статуса в целевой. Вызывается перед удалением статуса при наличии активных Assignment'ов. После успешной миграции статус можно удалить без конфликта.

**Тело запроса:**
```json
{
  "target_status_id": "uuid"
}
```

**Ответ 200:**
```json
{
  "migrated_assignments_count": 5,
  "target_status_id": "uuid"
}
```

После миграции затронутые пользователи получают in-app уведомление; событие логируется в `AuditLog`.

**Ошибки:**
- `400 Bad Request` — `target_status_id` не принадлежит тому же воркфлоу
- `403 Forbidden` — нет прав (нужен Admin)
- `404 Not Found` — исходный или целевой статус не найден

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

**Query-параметры:** `?q=авторизация&project_id=uuid&limit=50&offset=0&include_deleted=false`

- Soft-deleted задачи не включаются в результаты по умолчанию.
- Параметр `?include_deleted=true` доступен только пользователям с ProjectRole = Admin. Для остальных параметр игнорируется.

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

- Пользователь с AssigneeRole = `consultant` не видит Solution'ы других исполнителей до вынесения Decision. Проверка выполняется на уровне приложения: `GET /assignments/{id}/solution` и `GET /tasks/{id}/solutions` возвращают `403 Forbidden` для consultant'а, если `TaskDecision` ещё не создан. Прямое обращение `GET /solutions/{id}` выполняет ту же проверку и не обходится через `assignment_id`.

### GET /tasks/{id}/decisions

Доступен всем участникам задачи и всем участникам проекта с ProjectRole ≥ Viewer. Decision публичен после вынесения — возвращает `404 Not Found` если Decision ещё не вынесен.

---

## Edge cases

### GET /tasks/{id} для soft-deleted задачи

Возвращает `404 Not Found` (не `410 Gone`). Soft-deleted задачи не отличаются от несуществующих с точки зрения API. Admin может получить soft-deleted задачу через `?include_deleted=true`.

### GET /tasks/{id} для задачи из restricted/private проекта без доступа

Возвращает `404 Not Found` (не `403 Forbidden`). Это предотвращает раскрытие факта существования ресурса через статус-код.

### PATCH /tasks/{id} без поля version

Если тело запроса не содержит поля `version` — возвращается `400 Bad Request` с кодом `VERSION_REQUIRED` и сообщением «version required for optimistic locking».

### PATCH /tasks/{id} с устаревшим version

Если `version` в запросе не совпадает с текущим значением в БД — `409 Conflict` с кодом `VERSION_CONFLICT`. Тело ответа содержит `current_version` для того, чтобы клиент мог получить свежую версию задачи и повторить редактирование.

### POST /solutions/{id}/submit при конкурентной подаче

Если два lead-исполнителя подают Solution почти одновременно, оба запроса обрабатываются транзакционно с `SELECT FOR UPDATE` на строке задачи. Второй запрос ожидает завершения первого. Гонки данных нет при правильной реализации — оба получают корректный ответ последовательно.

### POST /solutions/{id}/submit когда задача уже в awaiting_decision

Если задача уже перешла в `awaiting_decision` (другой lead успел подать Solution раньше) — возвращается `400 Bad Request` с кодом `TASK_ALREADY_AWAITING_DECISION`. При этом данный Solution всё равно помечается как `submitted` и участвует в Decision Process. Повторный переход задачи не происходит.

### POST /solutions/{id}/submit после отзыва (withdraw)

Допускается. После отзыва Solution возвращается в `draft`. Исполнитель может доработать его и подать повторно — Solution переходит в `submitted`.

### POST /solutions/{id}/withdraw для Solution в статусе revision_requested

Возвращает `400 Bad Request` с кодом `SOLUTION_IN_REVISION`. Нельзя отозвать Solution, отправленный на доработку: исполнитель должен внести правки и подать его повторно.

### DELETE /assignments/{id} для lead с submitted Solution

Возвращает `400 Bad Request` с кодом `ASSIGNMENT_HAS_SUBMITTED_SOLUTION`. Solution исполнителя остаётся в истории задачи. Для удаления исполнителя с поданным Solution необходимо сначала отозвать Solution (если это разрешено).

### POST /projects/{id}/members для пользователя, уже добавленного через группу

Если пользователь уже состоит в проекте только через членство в группе — создаётся индивидуальная запись `ProjectMember` с указанной ролью, которая перекрывает групповую. Возвращается `200 OK` (не `409 Conflict`). Если пользователь уже добавлен напрямую — обновляется его существующая запись (`200 OK`). Групповая роль остаётся без изменений.

### GET /search — soft-deleted задачи

Soft-deleted задачи не включаются в результаты поиска. Параметр `?include_deleted=true` доступен только пользователям с ProjectRole = Admin. Для остальных параметр игнорируется.

### POST /tasks/{task_id}/links (cross-project)

При создании связи между задачами из разных проектов проверяется read-доступ текущего пользователя к проекту целевой задачи. Если доступа нет — `403 Forbidden` с кодом `PROJECT_ACCESS_DENIED` (не `404`, чтобы явно указать на проблему с правами, а не на отсутствие ресурса).

---

## Приложение: справочник error codes

Все ошибки возвращаются в формате `{ "error": { "code": "...", "message": "...", "details": {} } }`.

### Not Found (404)

| Код | Описание |
|-----|---------|
| `TASK_NOT_FOUND` | Задача не найдена, soft-deleted или недоступна (restricted/private проект) |
| `PROJECT_NOT_FOUND` | Проект не найден, недоступен или soft-deleted |
| `ASSIGNMENT_NOT_FOUND` | Assignment не найден |
| `SOLUTION_NOT_FOUND` | Solution не найден или ещё не создан |
| `DECISION_NOT_FOUND` | Decision по задаче ещё не вынесен |
| `WORKFLOW_NOT_FOUND` | Воркфлоу не найден |
| `STATUS_NOT_FOUND` | Статус воркфлоу не найден |
| `RESOLUTION_NOT_FOUND` | Резолюция не найдена |
| `USER_NOT_FOUND` | Пользователь не найден или деактивирован |

### Оптимистичные блокировки (400/409)

| Код | HTTP | Описание |
|-----|------|---------|
| `VERSION_REQUIRED` | 400 | Поле `version` обязательно для этого запроса |
| `VERSION_CONFLICT` | 409 | Конфликт версий при оптимистичной блокировке; `details.current_version` содержит актуальное значение |

### Воркфлоу и статусы (400/409)

| Код | HTTP | Описание |
|-----|------|---------|
| `INVALID_STATUS_TRANSITION` | 400 | Переход между статусами недопустим воркфлоу |
| `RESOLUTION_REQUIRED` | 400 | Резолюция обязательна при переходе в финальный статус |
| `WORKFLOW_TRANSITION_NOT_ALLOWED` | 403 | Нет права на данный переход (роль не включена в `allowed_roles`) |

### Solution и Decision Process (400/409)

| Код | HTTP | Описание |
|-----|------|---------|
| `SOLUTION_ALREADY_SUBMITTED` | 400 | Solution уже подан; действие недоступно |
| `SOLUTION_IN_REVISION` | 400 | Попытка отозвать Solution в статусе `revision_requested` — нужно доработать и подать повторно |
| `TASK_ALREADY_AWAITING_DECISION` | 400 | Задача уже в статусе `awaiting_decision`; Solution принят, но переход задачи не повторяется |
| `CANNOT_MODIFY_DECIDED_TASK` | 400 | Изменение задачи после вынесения Decision недоступно |

### Assignment (400)

| Код | HTTP | Описание |
|-----|------|---------|
| `ASSIGNMENT_HAS_SUBMITTED_SOLUTION` | 400 | Попытка удалить Assignment с поданным Solution; Solution остаётся в истории |
| `ROLE_CHANGE_NOT_ALLOWED` | 400 | Смена роли исполнителя заблокирована (Solution уже подан) |

### Ресурсы в использовании (409)

| Код | HTTP | Описание |
|-----|------|---------|
| `WORKFLOW_IN_USE` | 409 | Попытка удалить воркфлоу с активными задачами |
| `STATUS_IN_USE` | 409 | Попытка удалить статус с активными Assignment'ами; `details.affected_assignments_count` и `details.default_status_id` |
| `RESOLUTION_IN_USE` | 409 | Попытка удалить резолюцию, уже использованную в Assignment'ах; следует деактивировать |

### Доступ (403)

| Код | HTTP | Описание |
|-----|------|---------|
| `ACCESS_DENIED` | 403 | Общий отказ в доступе; может содержать `details.action_required` |
| `PROJECT_ACCESS_DENIED` | 403 | Нет доступа к проекту при cross-project операциях |

### Файлы (400/413)

| Код | HTTP | Описание |
|-----|------|---------|
| `FILE_TOO_LARGE` | 413 | Превышен лимит размера файла: 20 МБ для вложений задачи, 2 МБ для аватара |
| `PROJECT_STORAGE_EXCEEDED` | 400 | Превышен лимит хранилища проекта (500 МБ) |

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
