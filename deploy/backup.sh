#!/usr/bin/env bash
# TaskTrack — резервная копия БД (FR-003, TT-07).
# Запуск из каталога установки (где лежат docker-compose*.yml):
#   bash backup.sh [каталог]          → <каталог>/tasktrack-YYYYmmdd-HHMMSS.dump
# Формат — pg_dump custom (-Fc): сжат, восстанавливается restore.sh.
#
# Переменные окружения:
#   TASKTRACK_COMPOSE — команда compose (по умолчанию prod-набор файлов)
set -euo pipefail

COMPOSE="${TASKTRACK_COMPOSE:-docker compose -f docker-compose.yml -f docker-compose.prod.yml}"
DEST="${1:-backups}"
mkdir -p "$DEST"
FILE="$DEST/tasktrack-$(date +%Y%m%d-%H%M%S).dump"

$COMPOSE exec -T postgres pg_dump -U tasktrack -d tasktrack -Fc > "$FILE.partial"
mv "$FILE.partial" "$FILE"
echo "$FILE"
