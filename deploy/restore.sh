#!/usr/bin/env bash
# TaskTrack — восстановление БД из резервной копии (FR-003, TT-07).
#   bash restore.sh <файл.dump>
# Останавливает приложение, заменяет схему public содержимым копии в одной
# транзакции и запускает приложение снова; при старте оно применит миграции,
# если копия старее кода.
#
# Переменные окружения:
#   TASKTRACK_PROJECT — имя compose-проекта (под PaaS-деплоером: prod-tasktrack)
#   TASKTRACK_COMPOSE — иначе команда compose (по умолчанию prod-набор файлов)
#   TASKTRACK_YES=1   — не спрашивать подтверждение
set -euo pipefail

# Под PaaS-деплоером: TASKTRACK_PROJECT=prod-tasktrack (имя compose-проекта; файлы не нужны)
if [ -n "${TASKTRACK_PROJECT:-}" ]; then
    COMPOSE="docker compose -p $TASKTRACK_PROJECT"
else
    COMPOSE="${TASKTRACK_COMPOSE:-docker compose -f docker-compose.yml -f docker-compose.prod.yml}"
fi
FILE="${1:?usage: restore.sh <file.dump>}"
[ -f "$FILE" ] || { echo "нет файла: $FILE" >&2; exit 1; }

if [ "${TASKTRACK_YES:-}" != "1" ]; then
    read -r -p "Текущие данные будут заменены содержимым $FILE. Продолжить? [y/N] " answer
    [ "$answer" = "y" ] || { echo "Отменено."; exit 1; }
fi

$COMPOSE stop app
$COMPOSE exec -T postgres psql -U tasktrack -d tasktrack -v ON_ERROR_STOP=1 -q \
    -c "SET client_min_messages TO warning" -c "DROP SCHEMA public CASCADE" -c "CREATE SCHEMA public"
$COMPOSE exec -T postgres pg_restore -U tasktrack -d tasktrack --no-owner --single-transaction --exit-on-error < "$FILE"
$COMPOSE start app
echo "✓ Восстановлено из $FILE"
