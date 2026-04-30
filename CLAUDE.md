# CLAUDE.md — инструкции для работы с проектом

## Что это за проект

Внутренний таск-трекер с ключевой фичей — несколько исполнителей на одну задачу, каждый с независимым воркфлоу. При завершении всех частей запускается **Decision Process**: каждый исполнитель подаёт Solution, decision-maker выносит Decision.

Стек: Python / FastAPI / PostgreSQL / Keycloak / Traefik / Docker Compose + React 19 / Vite / shadcn/ui.  
Текущий этап: **реализация MVP, Этап 6 (Decision Process backend)**.

Актуальное состояние → `docs/README.md`. Архитектура → `docs/17-architecture.md`. План реализации → `docs/18-implementation-plan.md`.

---

## Структура документации

```
docs/
  README.md                  — навигатор, статус, порядок чтения
  glossary.md                — единый словарь (источник правды по терминам)
  decisions/                 — ADR-каталог ключевых решений
    README.md                — индекс ADR
    ADR-XXX-название.md
  stories/                   — user stories, разбитые по доменам
    core.md / collaboration.md / planning.md / access.md / decision-process.md
  00-context.md              — контекст и out of scope
  07-decision-process.md     — ключевой механизм продукта
  12-data-model.md           — ERD (Mermaid)
  13-permissions.md          — матрица прав
  15-api.md                  — REST API контракты
  16-arch-review.md          — архитектурное ревью
  tech-debt.md               — открытый бэкенд-долг
  ux-debt.md                 — открытый UX-долг фронтенда
  ... (остальные файлы — см. docs/README.md)
```

---

## Правила ведения документации

### Терминология

- **Глоссарий — единственный источник правды.** Перед добавлением нового термина проверить `glossary.md`. Если термин уже есть — использовать его. Если нового нет — добавить в глоссарий первым.
- Строго разводить **Solution** (поданное решение исполнителя) и **Decision** (итоговое решение decision-maker'а). Слово «решение» без уточнения не использовать.
- Роль исполнителя в задаче: **исполнитель**, не «assignee», не «соисполнитель». Если нужен EN-термин — `Assignment` / `Assignee` (как в коде).

### Архитектурные решения (ADR)

- Любое нетривиальное решение (продуктовое, архитектурное, инфраструктурное) фиксировать в `docs/decisions/ADR-XXX-название.md`.
- Формат: контекст → решение → последствия. Шаблон в `docs/decisions/README.md`.
- После создания ADR — добавить строку в таблицу `docs/decisions/README.md`.
- **Не переписывать** существующие ADR задним числом. Если решение изменилось — создать новый ADR со ссылкой на предыдущий и статусом «Заменяет ADR-XXX».
- **Не класть в ADR техдолг и UX-долг** — это не решения, а отложенная работа. Для них есть `docs/tech-debt.md` и `docs/ux-debt.md`. Закрытые пункты долга — удалять, история есть в git.

### Приоритизация историй

- Каждая user story в `docs/stories/` должна иметь метку: 🟢 MVP / 🟡 v2 / 🔴 не делаем.
- Метки берутся из `docs/09-mvp.md` — он источник правды по приоритизации.
- AC пишутся только для 🟢-историй. Формат: маркированный чек-лист условий (не Given/When/Then).

### Модель данных

- Изменения ERD → обновить `docs/12-data-model.md`.
- Если изменение затрагивает API — синхронно обновить `docs/15-api.md`.
- Если изменение — следствие нового архитектурного решения — завести ADR.

### Статус и навигация

- `docs/README.md` — живой навигатор. Обновлять при добавлении новых файлов и при изменении статуса работ.
- Статус проекта в README должен отражать реальность: что сделано, что осталось, конкретные хвосты. Не писать «готово», пока есть открытые вопросы.
- `docs/16-arch-review.md` — актуальный документ состояния. Обновлять при закрытии открытых вопросов.

### Git

- Коммитить по смысловым блокам, не сваливать всё в один коммит.
- Сообщение коммита: тип(`scope`): описание на русском. Типы: `feat`, `fix`, `refactor`, `docs`.
- Теги ставить на смысловые вехи: `impl-phase-N`, `s1-complete`, `s23-complete`, `mvp-research-launch`.

### Чего не делать

- Не создавать новые файлы для временных заметок — использовать существующую структуру.
- Не дублировать истории между `stories/` и `04-multi-assignee.md` — `stories/` первичен.
- Не оставлять файлы с пометкой «черновик» без плана, когда они будут доработаны.
- Не писать «открытые вопросы» в файлах без явного владельца и срока — либо закрыть, либо завести ADR с меткой «На рассмотрении».

---

## Реализация

Реализация идёт поэтапно (8 этапов). Подробный план — `docs/18-implementation-plan.md`.

**Текущий этап:** 6 — Decision Process backend

| Этап | Тег | Статус |
|------|-----|--------|
| 0. Фундамент | `impl-phase-0` | ✅ |
| 1. Пользователи и проекты | `impl-phase-1` | ✅ |
| 2. Воркфлоу и резолюции | `impl-phase-2` | ✅ |
| 3. Задачи и назначения | `impl-phase-3` | ✅ |
| 4. Frontend scaffold | `impl-phase-4` | ✅ |
| 5. Tasks UI + Kanban | `s1-complete` | ✅ |
| 6. Decision Process backend | `impl-phase-6` | 🔲 |
| 7. Decision Process UI | `s23-complete` | 🔲 |
| 8. Доводка + Alembic | `mvp-research-launch` | 🔲 |

### Правила разработки

- Тест пишется **до или вместе** с кодом сервиса, никогда после
- `make test` обязателен перед каждым коммитом
- Каждый этап — один коммит + тег `impl-phase-N`
- **Миграции:** `metadata.create_all` в lifespan до Этапа 8, затем переключение на Alembic

### Тесты

- Запускаются против **PostgreSQL** через `testcontainers` — Docker обязателен, контейнер поднимается автоматически
- **Savepoint-изоляция:** каждый тест оборачивается в транзакцию с `SAVEPOINT`, данные откатываются после — схема пересоздаётся только один раз за сессию
- `SELECT FOR UPDATE` работает (нужно для Decision Process в Этапе 6)
- Если в тесте создаёте объекты напрямую через `db_session` — вызывайте `await db_session.flush()` перед добавлением зависимых записей (PostgreSQL проверяет FK немедленно)

### Быстрый старт (бэкенд)

```bash
cd backend
python3 -m virtualenv .venv    # использовать virtualenv, не python3 -m venv
source .venv/bin/activate
cp .env.dev.example .env.dev
make install                   # pip install -e ".[dev]"
make db-start                  # docker run postgres:16-alpine на :5432
make reset                     # drop_all + create_all + seed
make dev                       # uvicorn --reload на :8000
make test                      # pytest — PostgreSQL через testcontainers (Docker обязателен)
```

### Быстрый старт (фронтенд)

```bash
cd frontend
npm install
npm run dev                    # Vite на :5173 (proxy /api → :8000)
npm test                       # Vitest
```

### Фронтенд — стек и структура

- **Vite 8 + React 19 + TypeScript + Tailwind v4 + shadcn/ui**
- Цветовые токены (oklch) из прототипа → `src/index.css`
- Компоненты shadcn/ui в `src/components/ui/` — добавлять через `npx shadcn@latest add`
- Роутинг: React Router v7, `src/app/router.tsx`
- Серверный стейт: TanStack Query, хуки в `features/*/api.ts`
- HTTP-клиент: axios, `src/shared/api/client.ts`
- Тесты: Vitest + React Testing Library, файлы рядом с компонентом в `__tests__/`
- `make gen-types` — генерировать TypeScript-типы из `/openapi.json` (бэкенд должен быть запущен)

### DB параметры (dev)

Описаны в `backend/.env.dev.example`. Дефолт:
```
DATABASE_URL=postgresql+asyncpg://tasktrack:tasktrack@localhost:5432/tasktrack
AUTH_STUB=true
```

---

## Работа с агентами

Рабочий каталог репозитория: `/home/sanek/projects/claudecode/tasktrack_project/`  
Remote: `github.com:diffspb/tasktrack.git`

### Git-права агентов

Агенты **могут:**
- Создавать ветки вида `feat/phase-N-описание` или `fix/описание`
- Делать `git add`, `git commit` в фиче-ветках
- Делать `git push origin feat/...` в фиче-ветки
- Ставить теги на завершённые этапы

Агенты **не могут:**
- Пушить напрямую в `main` (`git push origin main` — запрещено)
- Делать force push (`--force`)
- Удалять ветки или теги
- Делать `git reset --hard`

### Именование веток

```
feat/phase-2-workflow     — реализация этапа
feat/phase-3-tasks
fix/health-endpoint       — исправление бага
docs/update-readme        — обновление документации
```

### Процесс

1. Агент создаёт ветку: `git checkout -b feat/phase-N-description`
2. Делает работу, коммитит
3. Пушит ветку: `git push origin feat/phase-N-description`
4. Основной процесс (человек) проверяет и мержит в `main`, ставит тег

> Исключение: мелкие правки документации (`docs/`) можно коммитить прямо в `main`.
