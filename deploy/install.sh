#!/usr/bin/env bash
# TaskTrack — установка и обновление
# Использование:
#   bash <(curl -fsSL https://raw.githubusercontent.com/diffspb/tasktrack/main/deploy/install.sh)
#
# Переменные окружения:
#   TASKTRACK_DIR — каталог установки (по умолчанию ~/tasktrack)
#   GHCR_TOKEN    — GitHub-токен для загрузки образа (если репо приватное)

set -euo pipefail

IMAGE="ghcr.io/diffspb/tasktrack:latest"
RAW="https://raw.githubusercontent.com/diffspb/tasktrack/main"
DEPLOY_DIR="${TASKTRACK_DIR:-$HOME/tasktrack}"

echo "==> TaskTrack deploy → $DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"
cd "$DEPLOY_DIR"

# Скачать актуальные compose-файлы
curl -fsSL "$RAW/docker-compose.yml"      -o docker-compose.yml
curl -fsSL "$RAW/docker-compose.prod.yml" -o docker-compose.prod.yml
curl -fsSL "$RAW/deploy/backup.sh"        -o backup.sh
curl -fsSL "$RAW/deploy/restore.sh"       -o restore.sh

# Первый запуск: создать шаблон окружения и выйти
if [ ! -f .env.prod ]; then
    curl -fsSL "$RAW/.env.prod.example" -o .env.prod
    echo ""
    echo "✋  Первый запуск."
    echo "   Отредактируйте файл: $DEPLOY_DIR/.env.prod"
    echo "   Обязательно задайте POSTGRES_PASSWORD."
    echo "   Затем запустите скрипт снова."
    exit 0
fi

# Авторизация в GHCR (если образ приватный)
if [ -n "${GHCR_TOKEN:-}" ]; then
    echo "$GHCR_TOKEN" | docker login ghcr.io -u diffspb --password-stdin
fi

# Загрузить образ и запустить
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

echo ""
echo "✅  Запущено. Статус:"
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

echo ""
echo "Схема БД создаётся и обновляется автоматически при старте (Alembic)."
echo "Резервная копия:  bash backup.sh [каталог]"
echo "Восстановление:   bash restore.sh <файл.dump>"
echo "Не запускайте scripts/reset_db.py на рабочей установке — он удаляет данные и заливает демо-набор."
