# Настройка Keycloak для TaskTrack

Keycloak уже запущен на `auth.busypage.ru`, realm `home`. Нужно добавить клиент `tasktrack`.

## 1. Создать клиент

1. Открыть [https://auth.busypage.ru/admin](https://auth.busypage.ru/admin) → realm **home**
2. Clients → **Create client**
3. Client type: `OpenID Connect`, Client ID: `tasktrack` → Next
4. **Capability config:**
   - Standard flow: ✅ ON
   - Direct access grants: ❌ OFF
   - Client authentication: ❌ OFF (public client, PKCE без секрета)
5. **Login settings:**
   - Valid redirect URIs: `https://tasktrack.busypage.ru/auth/callback`
   - Valid post logout redirect URIs: `https://tasktrack.busypage.ru`
   - Web origins: `https://tasktrack.busypage.ru`
6. Save

## 2. Назначить роли пользователям

Приложение разрешает вход любому пользователю с валидным Keycloak-токеном. Для ограничения доступа — через Keycloak client-scopes или группы:

1. Users → выбрать пользователя → **Role mapping**
2. Assign role: `user` (или `admin` для администраторов)

Пользователи без назначенной роли смогут войти в Keycloak, но в приложении будут добавлены как обычные участники.

## 3. Feature request для home-realm.json

Чтобы не настраивать вручную на каждом сервере, нужно добавить в `simple/keycloak/realms/home-realm.json`:

```json
{
  "clientId": "tasktrack",
  "enabled": true,
  "publicClient": true,
  "standardFlowEnabled": true,
  "directAccessGrantsEnabled": false,
  "redirectUris": [
    "https://tasktrack.busypage.ru/auth/callback"
  ],
  "webOrigins": [
    "https://tasktrack.busypage.ru"
  ],
  "attributes": {
    "pkce.code.challenge.method": "S256"
  }
}
```

## Деплой

```bash
# На сервере в директории проекта
cp .env.prod.example .env.prod
# Отредактировать .env.prod: POSTGRES_PASSWORD и DATABASE_URL

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# После первого старта — инициализировать БД
docker compose exec app python scripts/reset_db.py
```

## Локальная разработка

```bash
cp frontend/.env.dev.example frontend/.env.dev
# VITE_AUTH_STUB=true — Keycloak не нужен
npm run dev
```
