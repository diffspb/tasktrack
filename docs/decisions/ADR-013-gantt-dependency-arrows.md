# ADR-013: Стрелки зависимостей на диаграмме Ганта

**Статус:** Принято  
**Дата:** 2026-05-09  
**Дополняет:** [ADR-012](./ADR-012-gantt-charts.md) (Гант был реализован без стрелок; теперь добавлены)

## Контекст

ADR-012 отложил отрисовку стрелок на v2. Связи между задачами (`TaskLink` + `LinkType`) уже хранились в БД, но на Ганте не отображались. Пользователю нужно видеть стрелки финиш-старт: «A blocks B» → стрелка от правого края A до левого края B.

`gantt-task-react` поддерживает зависимости из коробки: поле `dependencies: string[]` на каждом `GanttTask` → библиотека рисует SVG-стрелки самостоятельно.

## Решение

### Какие связи дают стрелки

Стрелки рисуются только для **направленных** (`is_directed: true`) связей с **ненулевым** `constraint`:

| LinkType | constraint | Стрелка |
|---|---|---|
| `blocks` | `{"type":"blocking"}` | ✅ |
| `depends_on` | `{"type":"sequential","mode":"finish_to_start"}` | ✅ |
| `relates_to` | `null` | ❌ информационная |
| `duplicates` | `null` | ❌ |
| `clones` | `null` | ❌ |

### Направление стрелки

`dependencies: ['X']` на задаче Y означает «Y зависит от X» → стрелка от конца X до начала Y.

- **`blocks`** (source blocks target): `ganttTask[target].dependencies.push(source.id)`
- **`depends_on`** (source depends on target): `ganttTask[source].dependencies.push(target.id)`

### API — новый эндпоинт

```
GET /gantt/{id}/links
```

Возвращает все `TaskLink`, у которых **оба** участника (source и target) входят в полное дерево задач ганта (тот же рекурсивный CTE, что и `GET /gantt/{id}/tasks`). Это исключает «внешние» связи с задачами, не добавленными в данный гант.

`TaskLinkResponse` расширен полем `link_type: LinkTypeResponse` — фронтенд читает `constraint` и `is_directed` без дополнительных запросов.

### Фронтенд

- `useGanttLinks(ganttId)` в `ganttApi.ts`
- `GanttChart` получает проп `links?: TaskLink[]`, в `useMemo` вычисляет `depsMap` и проставляет `dependencies` каждому `GanttTask`
- Цвет стрелок: `arrowColor="var(--border)"` — нейтральный, единый для всех типов

## Последствия

- Стрелки работают только между задачами, **видимыми** на диаграмме (обе стороны в дереве ганта)
- **Единый цвет стрелок** — разграничение по типу связи отложено (см. `docs/ux-debt.md #7`)
- **Стрелки в свёрнутых узлах не отрисовываются** — ограничение библиотеки (см. `docs/ux-debt.md #7`)
- Связи типа `relates_to`, `duplicates`, `clones` видны в блоке Relations задачи, но на шкале стрелок не дают
