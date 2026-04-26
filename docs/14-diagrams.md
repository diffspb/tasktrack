# 14. Диаграммы и схемы

---

## 3.1. State-диаграммы

### Глобальные состояния задачи

Эта диаграмма показывает все состояния задачи с учётом мульти-исполнителей, включая граничные случаи.

```mermaid
stateDiagram-v2
    [*] --> open : Задача создана

    open --> in_progress : Хотя бы один lead\nначал работу\n(Assignment в не-начальном статусе)

    in_progress --> awaiting_decision : Все lead-Assignment\nв финальном статусе\n(все Solution submitted)

    awaiting_decision --> in_revision : Decision-maker\nотправил ≥1 Solution\nна доработку

    in_revision --> awaiting_decision : Все Solution из\nrevision_requested\nснова submitted

    awaiting_decision --> decided : Decision-maker\nвынес Decision

    decided --> closed : Явное действие:\ndecision-maker или менеджер\nзакрывают задачу

    %% Принудительное закрытие менеджером
    in_progress --> closed : Принудительное закрытие\nменеджером (с резолюцией)
    awaiting_decision --> closed : Принудительное закрытие\nменеджером
    in_revision --> closed : Принудительное закрытие\nменеджером

    %% Переоткрытие
    closed --> open : Переоткрытие менеджером\nили автором задачи\n(выбирается, чья часть переоткрывается)
    decided --> in_progress : Переоткрытие менеджером\nили автором задачи

    %% Граничный случай: один исполнитель
    note right of awaiting_decision
        При одном исполнителе:\nopen → in_progress → closed\n(Decision Process не запускается)
    end note

    %% Граничный случай: добавление исполнителя
    note right of in_progress
        Добавление нового исполнителя:\nновый Assignment начинает с\nначального статуса воркфлоу
    end note

    note right of awaiting_decision
        Добавление исполнителя:\nменеджер явно подтверждает\nвозврат в in_progress
    end note
```

### Состояния Solution

```mermaid
stateDiagram-v2
    [*] --> draft : Исполнитель (lead)\nначал работу над Solution

    draft --> submitted : Исполнитель нажал\n«Подать Solution»

    submitted --> draft : Исполнитель отозвал\n(пока decision-maker\nне начал рассмотрение)

    submitted --> accepted : Decision-maker\nпринял Solution\n→ TaskDecision создан

    submitted --> revision_requested : Decision-maker\nотправил на доработку\n(с комментарием)

    revision_requested --> draft : Исполнитель открыл\nSolution для правок

    draft --> submitted : Исполнитель повторно\nподал Solution

    accepted --> [*]

    note right of submitted
        При подаче последнего lead-Solution:\nзадача переходит в awaiting_decision.\nDecision-maker получает уведомление.
    end note

    note right of revision_requested
        Задача переходит в in_revision.\nИсполнитель получает email + in-app\nс текстом обратной связи.
    end note
```

### Граничные случаи (описание)

| Сценарий | Поведение |
|----------|-----------|
| Добавление исполнителя в задачу со статусом `open` | Новый Assignment создаётся с начальным статусом воркфлоу. Задача остаётся в `open`. |
| Добавление исполнителя в задачу со статусом `in_progress` | Новый Assignment создаётся с начальным статусом. Задача остаётся в `in_progress`. |
| Добавление исполнителя в задачу со статусом `awaiting_decision` | Менеджер подтверждает возврат задачи в `in_progress`. Новый Assignment стартует с начального статуса. |
| Добавление исполнителя в `decided` / `closed` | Недоступно без явного переоткрытия задачи. |
| Отзыв последнего поданного Solution | Задача возвращается из `awaiting_decision` в `in_progress`. |
| Принудительное закрытие менеджером | Все незавершённые Assignment получают статус «Закрыто менеджером». Задача → `closed`. |
| Удаление lead-исполнителя с `submitted` Solution | Solution становится недействительным. Если оставшиеся lead'ы уже подали — задача остаётся/возвращается в `awaiting_decision`. Иначе — в `in_progress`. |
| Один исполнитель | `open → in_progress → closed`. Decision Process не запускается. |

---

## 3.2. Sequence-диаграмма: Сценарий S2 — Decision Process

Акторы: Manager (менеджер), Assignee1 (lead-исполнитель 1), Assignee2 (lead-исполнитель 2), DecisionMaker (decision-maker), System (бэкенд + уведомления).

```mermaid
sequenceDiagram
    autonumber
    actor Manager
    actor Assignee1
    actor Assignee2
    actor DecisionMaker
    participant System

    %% === Создание задачи ===
    Manager->>System: POST /projects/{id}/tasks\n{title, description, decision_maker_id,\nallow_multi_accept: false}
    System-->>Manager: 201 Created {task_id, key: "PROJ-42", status: "open"}

    %% === Задание критериев ===
    Manager->>System: POST /tasks/{id}/decision-criteria\n{items: ["Минимальное время", "Покрытие тестами ≥80%"]}
    System-->>Manager: 201 Created {criteria[]}

    %% === Назначение исполнителей ===
    Manager->>System: POST /tasks/{id}/assignments\n{user_id: assignee1_id, role: "lead"}
    System-->>Manager: 201 Created {assignment_id: a1}
    System-)Assignee1: in-app: «Вас назначили на PROJ-42»

    Manager->>System: POST /tasks/{id}/assignments\n{user_id: assignee2_id, role: "lead"}
    System-->>Manager: 201 Created {assignment_id: a2}
    System-)Assignee2: in-app: «Вас назначили на PROJ-42»

    %% === Независимые воркфлоу ===
    Note over Assignee1,Assignee2: Каждый ведёт свой воркфлоу независимо

    Assignee1->>System: PATCH /assignments/{a1}/status\n{status_id: "in_progress_id"}
    System-->>Assignee1: 200 OK
    Note right of System: Task.status → in_progress\n(первый lead начал работу)

    Assignee2->>System: PATCH /assignments/{a2}/status\n{status_id: "in_progress_id"}
    System-->>Assignee2: 200 OK

    Assignee1->>System: PATCH /assignments/{a1}/status\n{status_id: "done_id"}
    System-->>Assignee1: 200 OK

    Assignee2->>System: PATCH /assignments/{a2}/status\n{status_id: "done_id"}
    System-->>Assignee2: 200 OK

    %% === Подача Solution ===
    Assignee1->>System: POST /assignments/{a1}/solution\n{content: "Мой подход: ...", attachments: [...]}
    System-->>Assignee1: 201 Created {solution_id: s1, status: "draft"}

    Assignee1->>System: POST /solutions/{s1}/submit
    System-->>Assignee1: 200 OK {status: "submitted"}
    Note right of System: Все lead'ы ещё не подали → ждём

    Assignee2->>System: POST /assignments/{a2}/solution\n{content: "Альтернативный подход: ..."}
    System-->>Assignee2: 201 Created {solution_id: s2, status: "draft"}

    Assignee2->>System: POST /solutions/{s2}/submit
    System-->>Assignee2: 200 OK {status: "submitted"}
    Note right of System: Все lead'ы подали Solution\n→ Task.status = awaiting_decision

    System-)DecisionMaker: in-app + email: «PROJ-42 ожидает вашего Decision»

    %% === Просмотр и вынесение Decision ===
    DecisionMaker->>System: GET /tasks/{id}/solutions
    System-->>DecisionMaker: 200 OK {solutions: [s1_data, s2_data], criteria: [...]}

    DecisionMaker->>System: POST /tasks/{id}/decisions\n{accepted_solution_ids: [s1], note: "Выбран подход 1 как более..."}
    System-->>DecisionMaker: 201 Created {decision_id, decided_at}
    Note right of System: Solution s1 → accepted\nSolution s2 → rejected\nTask.status → decided → closed

    System-)Assignee1: in-app + email: «По PROJ-42 принят ваш Solution»
    System-)Assignee2: in-app + email: «По PROJ-42 вынесен Decision»
    System-)Manager: in-app: «PROJ-42 закрыта»
```

---

## 3.3. Таблица уведомлений

Легенда каналов: **in-app** — уведомление в интерфейсе приложения; **email** — письмо на email.

По умолчанию все участники задачи (исполнители + автор) автоматически становятся Watcher'ами при назначении/создании. Уведомления получают Watcher'ы задачи (если не отписались) + специфичные получатели события.

| # | Событие | Получатели | Канал |
|---|---------|-----------|-------|
| 1 | Задача создана | Автор задачи (Reporter) | in-app |
| 2 | Пользователь назначен исполнителем (Assignment создан) | Новый исполнитель | in-app |
| 3 | Исполнитель удалён из задачи | Удалённый исполнитель | in-app |
| 4 | Статус задачи (глобальный) изменён | Все Watcher'ы | in-app |
| 5 | Добавлен комментарий | Все Watcher'ы | in-app |
| 6 | Пользователь упомянут через @ | Упомянутый пользователь | in-app |
| 7 | Задача переходит в `awaiting_decision` | Decision-maker | in-app + email |
| 8 | Solution отправлен на доработку (revision_requested) | Исполнитель, чей Solution отправлен | in-app + email |
| 9 | Decision вынесен | Lead-исполнители — email + in-app; прочие Watcher'ы — только in-app | in-app + email (только lead'ы); in-app (прочие Watcher'ы) |
| 10 | Задача переоткрыта | Все Watcher'ы | in-app |
| 11 | Задача принудительно закрыта менеджером | Все исполнители с незавершёнными Assignment | in-app |
| 12 | Вложение добавлено к задаче | Все Watcher'ы | in-app |
| 13 | Due date наступает завтра | Все lead-исполнители | in-app |
| 14 | Роль исполнителя в задаче изменена | Исполнитель, чья роль изменена | in-app |
| 15 | Новый исполнитель добавлен в задачу в `awaiting_decision` (задача возвращается в in_progress) | Decision-maker; все lead-исполнители | in-app |
| 16 | Статус задачи/Assignment сброшен из-за изменения воркфлоу | Все участники затронутых задач (исполнители, автор, decision-maker) | in-app |

### Правила подписки (auto-watchers)

- **Автор задачи (Reporter)** — автоматически Watcher при создании задачи.
- **Исполнитель (Assignment)** — автоматически Watcher при назначении; отписка не удаляет Assignment.
- **Decision-maker** — автоматически Watcher при создании задачи.
- **reviewer и consultant** — автоматически Watcher при назначении.
- **Любой пользователь** — может подписаться вручную через кнопку «Следить».

### Управление уведомлениями

- Каждый пользователь может отключить отдельные типы событий в настройках уведомлений.
- Отписка от задачи (Watcher) прекращает уведомления по задаче, но не снимает Assignment.
- Email для Decision Process (события 7, 8, 9) можно отключить отдельным переключателем.
