# Таск-трекер с поддержкой мульти-исполнителей — документация

## О продукте

Внутренний таск-трекер с уникальной механикой: **одна задача может выполняться несколькими исполнителями параллельно**, каждый ведёт задачу через **свой персональный воркфлоу** независимо от других. При завершении всех частей вместо автоматического закрытия запускается **Decision Process**: каждый исполнитель подаёт свой Solution, decision-maker выносит Decision — выбирает один или несколько Solution как итог.

**Контекст:** single-tenant, внутренний инструмент без биллинга. Много проектов в одном инстансе, видимость настраивается по группам. Цель первого запуска — исследовательская: прогнать 2–3 реальных проекта и собрать обратную связь.

---

## Статус

🟢 **В разработке. Реализация MVP.**

| Этап | Тег | Статус |
|------|-----|--------|
| 0. Фундамент (health, scaffold, тесты) | `impl-phase-0` | ✅ |
| 1. Пользователи и проекты | `impl-phase-1` | ✅ |
| 2. Воркфлоу и резолюции | `impl-phase-2` | 🔲 в работе |
| 3. Задачи и назначения (S1 через API) | `impl-phase-3` | 🔲 |
| 4. Frontend scaffold + Projects UI | `impl-phase-4` | 🔲 |
| 5. Tasks UI + Kanban | `s1-complete` | 🔲 |
| 6. Decision Process backend | `impl-phase-6` | 🔲 |
| 7. Decision Process UI | `s23-complete` | 🔲 |
| 8. Доводка + Alembic | `mvp-research-launch` | 🔲 |

Инфра и окружение: без Docker (тесты на SQLite in-memory, dev — локальный PostgreSQL).  
Актуальное состояние и архитектурные решения → **[16-arch-review.md](./16-arch-review.md)**.

---

## Структура документации

### Для разработчика / аналитика

| Файл | Что внутри |
|------|------------|
| [00-context.md](./00-context.md) | Контекст, целевая аудитория, границы и out of scope |
| [glossary.md](./glossary.md) | Единый словарь терминов — источник правды |
| [16-arch-review.md](./16-arch-review.md) | **Актуальное состояние:** противоречия, риски, валидация API, стек, открытые вопросы |
| [17-architecture.md](./17-architecture.md) | Архитектура реализации: структура репозитория, бэкенд, фронтенд, интеграция с инфрой |
| [18-implementation-plan.md](./18-implementation-plan.md) | **План реализации MVP:** 8 этапов с целями, составом работ и тегами |
| [09-mvp.md](./09-mvp.md) | 5 MVP-сценариев + приоритизация всех историй (🟢/🟡/🔴) |
| [02-roles.md](./02-roles.md) | Роли пользователей |
| [03-user-stories.md](./03-user-stories.md) | Индекс user stories → `stories/` |
| [stories/core.md](./stories/core.md) | Auth, Projects, Tasks, Assignment, Workflow, Resolutions |
| [stories/collaboration.md](./stories/collaboration.md) | Comments, Notifications, History, Time tracking |
| [stories/planning.md](./stories/planning.md) | Epics, Labels, Search, Boards, Analytics, Integrations |
| [stories/access.md](./stories/access.md) | Permissions, Groups & Visibility, Project Links |
| [stories/decision-process.md](./stories/decision-process.md) | Decision Process + мульти-исполнители (с AC для 🟢) |
| [07-decision-process.md](./07-decision-process.md) | Decision Process: механика, состояния, Solution, revision |
| [04-multi-assignee.md](./04-multi-assignee.md) | Мульти-исполнители: механика, роли lead/reviewer/consultant |
| [12-data-model.md](./12-data-model.md) | ERD (Mermaid), схема воркфлоу, нетривиальные решения |
| [13-permissions.md](./13-permissions.md) | Матрица прав: ProjectRole × действие, AssigneeRole × действие |
| [14-diagrams.md](./14-diagrams.md) | State-диаграммы задачи и Solution, sequence S2, уведомления |
| [15-api.md](./15-api.md) | REST API контракты для MVP-сценариев |
| [10-nfr.md](./10-nfr.md) | NFR: масштаб, стек, инфра, Keycloak, деплой |
| [05-often-missed.md](./05-often-missed.md) | Решения по часто упускаемым техническим деталям |

### Лог решений

| Файл | Что внутри |
|------|------------|
| [decisions/](./decisions/) | ADR-каталог: все ключевые архитектурные и продуктовые решения |
| [decisions/ADR-001](./decisions/ADR-001-decision-process.md) | Decision Process как механизм закрытия |
| [decisions/ADR-002](./decisions/ADR-002-tech-stack.md) | Технологический стек и инфраструктура |
| [decisions/ADR-003](./decisions/ADR-003-notifications.md) | Уведомления: отказ от email |
| [decisions/ADR-004](./decisions/ADR-004-data-model.md) | Ключевые решения по модели данных |
| [decisions/ADR-005](./decisions/ADR-005-product.md) | Сборник продуктовых решений |

### Исторические файлы (не актуальны как планы)

| Файл | Что внутри |
|------|------------|
| [08-pre-design-tasks.md](./08-pre-design-tasks.md) | Чек-лист подготовки к проектированию — все блоки закрыты |
| [11-analyst-tasks.md](./11-analyst-tasks.md) | Задачи аналитика — все выполнены |
| [01-needs.md](./01-needs.md) | Исходные потребности («зачем») |
| [06-next-steps.md](./06-next-steps.md) | Устаревший roadmap → редирект |

---

## Рекомендуемый порядок чтения

1. **[00-context.md](./00-context.md)** — что строим, для кого, что точно не делаем.
2. **[glossary.md](./glossary.md)** — прочитать один раз, держать открытым.
3. **[16-arch-review.md](./16-arch-review.md)** — текущее состояние пакета, риски, открытые вопросы.
4. **[09-mvp.md](./09-mvp.md)** — scope и приоритизация до погружения в детали.
5. **[07-decision-process.md](./07-decision-process.md)** — ключевой механизм продукта.
6. **[03-user-stories.md](./03-user-stories.md)** → **[stories/decision-process.md](./stories/decision-process.md)** — истории с AC.
7. **[12-data-model.md](./12-data-model.md)** — ERD и схема воркфлоу.
8. **[13-permissions.md](./13-permissions.md)** — матрица прав.
9. **[15-api.md](./15-api.md)** — API контракты.
10. **[10-nfr.md](./10-nfr.md)** — инфраструктура и ограничения.
