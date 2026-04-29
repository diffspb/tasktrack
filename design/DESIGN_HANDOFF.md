# TaskTrack — Design Handoff

**Дата:** 29 апреля 2026  
**Стек прототипа:** React 18 + Babel (inline JSX, без сборки)  
**Целевой стек:** React 19 + Vite + shadcn/ui + TanStack Query  
**Дизайн-принцип:** UI должен быть знаком пользователям Jira — без кривой обучения.

---

## Файлы прототипа

```
design/prototype/
  TaskTrack.html       — точка входа (открыть в браузере)
  tt-data.jsx          — mock-данные: задачи, проекты, пользователи
  tt-ui.jsx            — атомарные компоненты (Badge, Avatar, Button…)
  tt-kanban.jsx        — Kanban-доска
  tt-backlog.jsx       — Backlog (таблица + фильтры)
  tt-dashboard.jsx     — My Dashboard
  tt-detail.jsx        — Детальная страница задачи + Decision Process
  tt-create.jsx        — Форма создания задачи
  tt-projects.jsx      — Список проектов
  tt-settings.jsx      — Настройки проекта
  tt-app.jsx           — App shell: sidebar, header, routing
```

> Прототип работает без сборки — просто откройте `TaskTrack.html` в браузере.  
> Tweaks-панель (кнопка ✦ внизу справа) позволяет переключать POV между пользователями.

---

## Что спроектировано

### ✅ App Shell
- **Sidebar** — переключение между проектами, навигация (Dashboard / Board / Backlog / Members / Settings), профиль пользователя
- **Header** — breadcrumb, поиск (⌘K), переключатель светлой/тёмной темы, notification badge с выпадающей панелью
- **Светлая и тёмная тема** — реализованы через CSS-переменные (`var(--bg)`, `var(--fg)`, `var(--primary)` и др.), переключение через `data-theme` на `<html>`

**Цветовая система:**
```css
/* Tokens — все в oklch для перцептивной равномерности */
--bg, --bg-card, --bg-muted, --bg-hover
--fg, --fg-muted, --fg-subtle
--border, --border-subtle, --border-focus
--primary, --primary-fg
--sidebar-bg, --sidebar-fg, --sidebar-active, --sidebar-border
--shadow-sm, --shadow, --shadow-lg
```

---

### ✅ My Dashboard

**Файл:** `tt-dashboard.jsx`

Персонализированный вид для текущего пользователя:
- **Stat cards** — мои открытые задачи, ожидают Decision, нужна доработка (revision), закрыто за неделю
- **Alert-баннеры** — красный (есть `revision_requested` на моих решениях), жёлтый (я decision-maker и задачи ждут Decision)
- **4 секции задач:** In Progress, To Do, Awaiting My Decision, Needs Revision

**UX-решения:**
- Баннеры видны только когда требуется действие от текущего пользователя
- Секция «Awaiting My Decision» показывает глобальный статус, а не личный — потому что пользователь тут decision-maker, а не исполнитель
- Переключение POV (Tweaks) меняет весь контент дашборда

---

### ✅ Kanban-доска

**Файл:** `tt-kanban.jsx`

**Ключевое:** это не стандартный канбан — каждый пользователь видит задачи в колонках **своего личного воркфлоу** (`Assignment.personal_status`), независимо от глобального статуса задачи.

- **Колонки:** To Do / In Progress / In Review / Done (настраиваемые через Project Settings → Workflow)
- **Task card:** цветная полоска приоритета слева, ключ задачи (TT-1), тип, глобальный статус, название, метки, прогресс-бар для мульти-исполнителей, стек аватаров, дедлайн, счётчик комментариев
- **Drag-and-drop:** HTML5 DnD API, подсветка целевой колонки, placeholder «Drop here», оптимистичное обновление статуса

**Важно для разработки:**  
Запрос для загрузки Kanban должен фильтровать задачи по `user_id` исполнителя и возвращать `personal_status` из таблицы `task_assignees`, а не глобальный `tasks.global_status`.

---

### ✅ Backlog

**Файл:** `tt-backlog.jsx`

Компактный табличный вид всех задач проекта:
- **Однострочные строки** — тип + название (обрезается с ellipsis) + метки в одну линию
- **Фильтры:** поиск по тексту, status, priority, type, assignee (фильтр «Assigned to me» через `personal_status`)
- **Сортировка** по клику на заголовки (key, title, status, due date)
- **Колонка «My Status»** — личный статус текущего пользователя, если он назначен на задачу

---

### ✅ Task Detail Panel

**Файл:** `tt-detail.jsx`

Открывается слайдом справа (как в Jira/Linear). 4 вкладки:

#### Overview
- Глобальный статус + прогресс-бар решений (`submitted / total leads`)
- Кнопки перехода по воркфлоу для текущего пользователя
- **Decision Criteria** — пронумерованный список
- **Assignees table** — имя, роль (lead/reviewer/consultant), personal status, solution status. Строка текущего пользователя выделена.
- Метаданные: дедлайн, репортер, дата создания, метки

#### Solutions
- Список всех поданных Solution'ов с именем исполнителя, датой, текстом, вложениями
- **Баннер revision** — жёлтый блок с комментарием decision-maker'а
- **Для decision-maker'а:** кнопки Accept / Request Revision (с модалкой для feedback)
- **Для исполнителя с `revision_requested`:** кнопка «Resubmit Solution»
- Если текущий пользователь lead и ещё не подал — CTA «Submit Solution»

#### Comments
- Хронологический список с аватарами
- Поле ввода с @-упоминаниями (placeholder)

#### History
- Аудит-лог событий в обратном хронологическом порядке (статус, назначение, solution, decision)

**Состояния Decision Process и их визуализация:**

| `global_status` | Как показывается |
|---|---|
| `open` | Серый badge |
| `in_progress` | Синий badge |
| `awaiting_decision` | Жёлтый badge + прогресс-бар полный |
| `in_revision` | Оранжевый badge + баннер с feedback |
| `decided` | Зелёный badge + accepted solution подсвечен |
| `closed` | Серый badge |

---

### ✅ Create Task

**Файл:** `tt-create.jsx`

Единая прокручиваемая форма (без шагов), как в Jira:

1. **Project** — переключатель проекта (влияет на префикс ключа)
2. **Issue type** — Task / Feature / Bug
3. **Title** — обязательное
4. **Priority** — Low / Medium / High / Critical
5. **Description**
6. **Due date + Labels**
7. **Assignees** — несколько строк user + role(lead/reviewer/consultant), кнопка «Add assignee»
8. **Decision maker** — по умолчанию текущий пользователь
9. **Multi-accept toggle** — появляется только если назначено 2+ lead'а
10. **Decision Criteria** — сворачиваемая секция (авторасширяется при multi-lead)

---

### ✅ All Projects

**Файл:** `tt-projects.jsx`

- **Карточки проектов:** цветная полоска, ключ, название, описание, статистика (active / total / members), стек аватаров, badge видимости, роль текущего пользователя
- **Create Project** — модалка: выбор цвета, автогенерация ключа, описание, 3 режима видимости (Public / Restricted / Private) с визуальным выбором

---

### ✅ Project Settings

**Файл:** `tt-settings.jsx`

Левая навигация + 4 вкладки:

| Вкладка | Содержимое |
|---|---|
| **General** | Название, ключ с preview (`TT-42`), описание, радио-карточки видимости, кнопка «Archive» |
| **Members** | Таблица участников: аватар, имя, роль-дропдаун, дата вступления, Remove; модалка Invite |
| **Workflow** | Список статусов с inline-редактированием имён, цветовые свотчи, drag-handle, удаление |
| **Labels** | Теги с добавлением (Enter) и удалением по крестику |

---

## Что НЕ спроектировано

Список экранов и функций, которые остались за рамками прототипа:

### Высокий приоритет
- **Submit Solution flow** — форма подачи решения исполнителем (поле форматированного текста + вложения + кнопка «Submit»), переход задачи в `awaiting_decision`
- **Notifications page** — полная лента уведомлений с группировкой по дате, mark as read / mark all, переход к задаче по клику

### Средний приоритет
- **User Profile** — имя, аватар, часовой пояс, настройки уведомлений
- **Workflow transitions modal** — диалог смены статуса с обязательными полями (если workflow это требует)
- **Task creation from Backlog** — быстрое создание задачи inline в строке таблицы
- **Cross-project task links** — UI для создания связей `blocks / duplicate / related` между задачами разных проектов
- **Search results page** — выпадающее окно ⌘K с результатами поиска по задачам, проектам, пользователям

### Низкий приоритет (v2 по документации)
- Blind mode для Decision Process (Solution'ы скрыты до Decision)
- Спринты и burndown
- Аналитика Decision Process
- CSV-экспорт

---

## Как передавать в разработку

### 1. Цветовые токены → CSS-переменные / Tailwind

Все цвета в прототипе заданы через CSS-переменные в `TaskTrack.html` (`<style>` секция). При переносе на shadcn/ui — заменить на переменные из `globals.css`. Токены используют `oklch` — Tailwind v4 поддерживает это нативно.

```css
/* Прototип → shadcn/ui */
--primary: oklch(0.520 0.160 252)  →  --primary в globals.css
--bg-muted: oklch(0.960 0.004 240) →  --muted
--border: oklch(0.878 0.006 240)   →  --border
```

### 2. Компоненты → shadcn/ui mapping

| Прототип | shadcn/ui |
|---|---|
| `<Btn variant="default">` | `<Button>` |
| `<Btn variant="secondary">` | `<Button variant="outline">` |
| `<Btn variant="ghost">` | `<Button variant="ghost">` |
| `<Btn variant="danger">` | `<Button variant="destructive">` |
| Фильтр-чипы в Backlog | `<DropdownMenu>` + `<Badge>` |
| Notification panel | `<Popover>` |
| Task detail panel | `<Sheet side="right">` |
| Create task modal | `<Dialog>` |
| Project settings | роутинг `/projects/:id/settings/:tab` |
| User/Role badges | `<Badge variant="outline">` с кастомными цветами |

### 3. Данные и состояние

В прототипе данные живут в `tt-data.jsx` как константы. В реальном приложении:

```
tt-data.jsx → TanStack Query hooks
  TASKS        → useQuery(['tasks', projectId])
  PROJECTS     → useQuery(['projects'])
  NOTIFICATIONS → useQuery(['notifications', userId])
  statusMap    → optimistic update через useMutation
```

Drag-and-drop на канбане — оптимистичное обновление `Assignment.personal_status`:
```
onDrop → optimistic setStatusMap → mutation PATCH /assignments/:id → invalidate tasks
```

### 4. Роутинг

```
/                          → redirect → /dashboard
/dashboard                 → Dashboard
/projects                  → ProjectsOverview
/projects/:id/board        → KanbanBoard
/projects/:id/backlog      → BacklogView
/projects/:id/settings/*   → ProjectSettings (вложенный роутинг по табам)
/tasks/:id                 → TaskDetail (или Sheet поверх текущего роута)
```

### 5. Специфика Decision Process

Самая нетривиальная часть UI. Ключевые инварианты:

- **Kanban**: задача размещается в колонке `Assignment.personal_status`, а НЕ `Task.global_status`. Для пользователей без Assignment — по `global_status`.
- **Solutions tab**: виден только если `assignees.filter(role='lead').length > 1` или `task.solutions.length > 0`
- **Кнопки Accept/Revision** видны только `decisionMakerId === currentUserId` и `task.globalStatus === 'awaiting_decision'`
- **Кнопка Resubmit** видна только `assignment.solutionStatus === 'revision_requested'` и `assignment.userId === currentUserId`
- **Withdraw Solution** заблокирован после первого действия decision-maker'а

### 6. Доступность

В прототипе не реализованы — при разработке нужно добавить:
- `aria-label` на кнопки без текста (bell, gear, drag-handle)
- `role="dialog"` и фокус-трап на модалках
- `aria-live` на notification badge
- Keyboard navigation для Kanban (пока только mouse/touch drag)

---

## Открытые вопросы дизайна

1. **Submit Solution** — нужен ли rich-text редактор (как в Confluence) или достаточно `<textarea>` с markdown-preview?
2. **Workflow transitions** — показывать ли модалку при каждом переходе или только когда есть обязательные поля?
3. **Notification page** — группировать по дате или по задаче?
4. **Mobile** — только адаптивный web (docs/00-context.md — TBD). Если да, Kanban → list view на мобильном.
5. **Blind mode** (v2) — как показывать заглушки вместо Solution'ов до Decision? Нужен отдельный UX.
