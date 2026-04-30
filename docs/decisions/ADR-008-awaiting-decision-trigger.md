# ADR-008: Триггер перехода в `awaiting_decision` — Solution.submit, не финальный статус Assignment

**Статус:** Принято
**Дата:** 2026-04-30

## Контекст

В `07-decision-process.md` и `15-api.md` описаны два места, где задаётся момент перехода задачи в `awaiting_decision`:

1. **07-decision-process.md:** «Задача переходит в `awaiting_decision` автоматически, когда все **lead**-исполнители перевели свои Solution в `submitted`».
2. **API-контракт `POST /solutions/{id}/submit`:** ответ `task_transitioned_to: "awaiting_decision"`.

При этом реализация Этапов 3–5 (`task_service._recalculate_global_status`) переводила задачу в `awaiting_decision`, как только все lead'ы достигли финального статуса воркфлоу — независимо от Solution. Это противоречит спецификации.

В рамках Этапа 6 (Decision Process backend) разногласие нужно было устранить.

## Решение

`awaiting_decision`, `in_revision`, `decided` — Solution-driven переходы. Финальный статус Assignment в воркфлоу сам по себе их не вызывает.

**Новая семантика `_recalculate_global_status`:**

- **Single lead:**
  - финальный personal_status → `closed` (Decision Process не запускается, как в `07-decision-process.md`)
  - иначе → `in_progress` (если есть lead) / `open` (если нет)

- **Multi lead** (≥ 2 lead-исполнителей):
  - всех Solution'ов нет или какие-то ещё не submitted → `in_progress`
  - все Solution'ы в `submitted` → `awaiting_decision`
  - хотя бы один Solution в `revision_requested` → `in_revision`
  - финальный personal_status сам по себе **не** влияет на global_status

- **Decided/closed** — устанавливаются явно: `make_decision` → `decided`, `close_task` → `closed`. Если `TaskDecision` уже создан и задача в `decided`/`closed`, пересчёт не сбрасывает её обратно.

**Параллельный submit двух lead'ов** обрабатывается через `SELECT FOR UPDATE` на строке `Task` в `decision_service.submit_solution`. Два запроса сериализуются на уровне БД, ровно один из них приводит к переходу в `awaiting_decision`.

## Последствия

- Изменена реализация `task_service._recalculate_global_status`. Старый тест `test_multi_lead_sets_awaiting_decision` переписан в `test_multi_lead_final_status_does_not_trigger_awaiting_decision`.
- Multi-lead задача без Solution-инфраструктуры (т.е. до Этапа 6) теперь не закрывается автоматически — но это уже невозможный сценарий после Этапа 6: создавать multi-lead задачу = пользоваться Decision Process.
- `await session.commit()` в `submit_solution` — единая точка, где блокировка задачи на `Task` снимается. Все остальные мутации Solution идут вне блокировки задачи.
- Документ `07-decision-process.md` остаётся источником правды; этот ADR фиксирует, что реализация теперь ему соответствует.
