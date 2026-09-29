#!/usr/bin/env bash
# Проверка образа перед выкладкой (FR-003, TT-07):
#   1. старт с пустой БД — миграции до head, /health отвечает;
#   2. вход обязателен: без токена API отвечает 401;
#   3. резервная копия → потеря данных → восстановление возвращает данные;
#   4. обновление с предыдущей схемы: откат ревизии, рестарт — снова head;
#   5. ключ служебной учётной записи из CLI работает в REST, после отзыва — 401;
#   6. образ не запускается с AUTH_STUB=true (APP_ENV=production).
#
#   TASKTRACK_IMAGE=tasktrack:smoke bash deploy/smoke-test.sh
set -euo pipefail

cd "$(dirname "$0")/.."
export TASKTRACK_IMAGE="${TASKTRACK_IMAGE:-tasktrack:smoke}"
PORT="${TASKTRACK_SMOKE_PORT:-18000}"
export TASKTRACK_SMOKE_PORT="$PORT"
PROJECT="ttsmoke$$"
export TASKTRACK_COMPOSE="docker compose -p $PROJECT -f deploy/docker-compose.smoke.yml"
WORK="$(mktemp -d)"
trap '$TASKTRACK_COMPOSE logs app > "$WORK/app.log" 2>&1 || true; $TASKTRACK_COMPOSE down -v >/dev/null 2>&1; echo "логи приложения: $WORK/app.log"' EXIT

step() { echo "==> $*"; }
fail() { echo "✗ $*" >&2; exit 1; }
psql() { $TASKTRACK_COMPOSE exec -T postgres psql -U tasktrack -d tasktrack -tAq -v ON_ERROR_STOP=1 -c "$1"; }
wait_healthy() {
    for _ in $(seq 60); do
        curl -fsS "http://localhost:$PORT/api/v1/health" >/dev/null 2>&1 && return 0
        sleep 1
    done
    fail "приложение не ответило на /health за 60 с"
}
HEAD="$(docker run --rm --entrypoint alembic "$TASKTRACK_IMAGE" heads | awk '{print $1}')"
[ -n "$HEAD" ] || fail "в образе нет alembic-ревизий"

step "1. старт с пустой БД ($TASKTRACK_IMAGE, head=$HEAD)"
$TASKTRACK_COMPOSE up -d --quiet-pull >/dev/null 2>&1
wait_healthy
[ "$(psql 'SELECT version_num FROM alembic_version')" = "$HEAD" ] || fail "схема не на head"

step "2. без токена — 401"
code="$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$PORT/api/v1/users/me")"
[ "$code" = "401" ] || fail "ожидался 401, получен $code"

step "3. резервная копия и восстановление"
psql "INSERT INTO users (id, keycloak_id, email, display_name, is_active, is_superuser, timezone, created_at, updated_at)
      VALUES (gen_random_uuid(), 'smoke', 'smoke@localhost', 'Smoke', true, false, 'UTC', now(), now())"
DUMP="$(bash deploy/backup.sh "$WORK")"
psql "DELETE FROM users WHERE email = 'smoke@localhost'"
TASKTRACK_YES=1 bash deploy/restore.sh "$DUMP" >/dev/null
wait_healthy
[ "$(psql "SELECT count(*) FROM users WHERE email = 'smoke@localhost'")" = "1" ] || fail "данные не восстановлены"

step "4. обновление с предыдущей схемы"
$TASKTRACK_COMPOSE exec -T app alembic downgrade -1 >/dev/null 2>&1
[ "$(psql 'SELECT version_num FROM alembic_version')" != "$HEAD" ] || fail "откат ревизии не выполнен"
$TASKTRACK_COMPOSE restart app >/dev/null 2>&1
wait_healthy
[ "$(psql 'SELECT version_num FROM alembic_version')" = "$HEAD" ] || fail "после рестарта схема не на head"
[ "$(psql "SELECT count(*) FROM users WHERE email = 'smoke@localhost'")" = "1" ] || fail "данные потеряны при обновлении"

step "5. ключ служебной учётной записи"
sa() { $TASKTRACK_COMPOSE exec -T app python scripts/service_account.py "$@"; }
sa create --email smoke@agents --name "Smoke agent" >/dev/null
OUT="$(sa issue --email smoke@agents --key-name smoke)"
TOKEN="$(echo "$OUT" | tail -1)"
KEY_ID="$(echo "$OUT" | sed -n 's/^key id=\([^ ]*\).*/\1/p')"
code="$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $TOKEN" "http://localhost:$PORT/api/v1/users/me")"
[ "$code" = "200" ] || fail "ключ не принят: $code"
sa revoke --key-id "$KEY_ID" >/dev/null
code="$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $TOKEN" "http://localhost:$PORT/api/v1/users/me")"
[ "$code" = "401" ] || fail "отозванный ключ принят: $code"

step "6. AUTH_STUB=true запрещён в образе"
if out="$(docker run --rm -e AUTH_STUB=true -e DATABASE_URL=postgresql+asyncpg://x:y@127.0.0.1:1/x "$TASKTRACK_IMAGE" 2>&1)"; then
    fail "приложение запустилось с AUTH_STUB=true"
fi
echo "$out" | grep -q "AUTH_STUB=true is not allowed" || fail "нет понятной ошибки про AUTH_STUB"

echo "✓ smoke-тест пройден"
