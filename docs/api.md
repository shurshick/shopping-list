# API сервера

Актуально для версии `v1.4.0`.

Базовый адрес: `https://your-domain.example`

## Авторизация

- `POST /auth/register` - зарегистрировать пользователя.
- `POST /auth/login` - войти в аккаунт.

Обычная регистрация доступна только после завершения мастера `/setup` и только если администратор разрешил регистрацию.

Отключенный администратором пользователь не может войти и не может использовать ранее выданный token.

Тело запроса:

```json
{
  "email": "user@example.com",
  "password": "secret123"
}
```

Ответ:

```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

## Синхронизация

- `GET /sync` - получить списки пользователя и товары.

Заголовок:

```text
Authorization: Bearer <token>
```

Архивные списки в `/sync` не возвращаются.

## Идемпотентность offline-операций

Новые Android-клиенты отправляют UUID `client_operation_id` для операций offline queue. Его можно передать в теле `POST /lists` и `POST /lists/{list_id}/items`, а также в заголовке:

```text
X-Client-Operation-Id: <uuid>
```

Если сервер уже применил операцию с таким `client_operation_id` для текущего пользователя, повторный запрос возвращает сохраненный результат и не выполняет действие второй раз.

Старые клиенты без `client_operation_id` работают как раньше.

## Списки

- `POST /lists` - создать список.
- `PATCH /lists/{list_id}` - переименовать список, доступно владельцу.
- `DELETE /lists/{list_id}` - удалить список; для участника без владения удаляет только его доступ.
- `POST /lists/{list_id}/copy` - создать копию списка.
- `GET /lists/{list_id}/members` - посмотреть участников списка.
- `POST /lists/{list_id}/share` - открыть доступ пользователю по email.
- `POST /lists/{list_id}/invite` - создать одноразовую invite-ссылку.
- `POST /invites/{token}/accept` - принять invite-ссылку.
- `GET /join/{token}` - HTML-страница invite-ссылки для открытия Android-приложения.

Срок действия приглашений задается переменной `INVITE_TOKEN_HOURS`, по умолчанию 168 часов.

## Товары

- `POST /lists/{list_id}/items` - добавить товар.
- `PATCH /items/{item_id}` - изменить название, количество или отметку покупки.
- `DELETE /items/{item_id}` - удалить товар.
- `DELETE /lists/{list_id}/items` - очистить список.
- `DELETE /lists/{list_id}/items/checked` - удалить купленные товары.
- `PATCH /lists/{list_id}/items/checked` - вернуть купленные товары в блок "Купить".

## История

- `GET /lists/{list_id}/activity` - последние события списка.
- `DELETE /lists/{list_id}/activity` - очистить историю выбранного списка.
- `DELETE /admin/activity` - очистить всю историю действий, только admin.

## Публичная конфигурация

- `GET /server-config`

Ответ не содержит секретов, паролей, JWT-ключей и строки подключения к БД.

```json
{
  "app_name": "Список покупок",
  "external_url": "https://shopping.example.com",
  "allow_registration": true,
  "setup_completed": true
}
```

## Health endpoints

- `GET /health` - старый endpoint для обратной совместимости.
- `GET /health/live` - процесс API жив; глубокую проверку БД не делает.
- `GET /health/ready` - API готов обслуживать запросы; проверяет БД и состояние миграций.
- `GET /health/db` - безопасная проверка БД без раскрытия строки подключения.

Пример:

```json
{
  "status": "ok",
  "version": "1.4.0",
  "timestamp": "2026-06-13T12:00:00"
}
```

## Metrics

- `GET /metrics`

JSON endpoint с безопасными счетчиками:

- `users_total`
- `lists_total`
- `items_total`
- `invites_active`
- `client_operations_total`
- `app_uptime_seconds`
- `db_status`
- `version`

Endpoint не возвращает email пользователей, пароли, токены и секреты.

## Admin endpoints

Все admin endpoints требуют Bearer token администратора.

### Состояние

- `GET /admin`
- `GET /admin/status`
- `GET /admin/system`
- `GET /admin/logs`
- `GET /admin/diagnostics`

`/admin/system` показывает версию backend, статус БД, текущую и ожидаемую Alembic revision, uptime, режим регистрации, время запуска и время сервера. Секреты не выводятся.

### Пользователи

- `GET /admin/users`
- `POST /admin/users/{user_id}/disable`
- `POST /admin/users/{user_id}/enable`
- `POST /admin/users/{user_id}/set-password`

Нельзя отключить последнего активного администратора. `password_hash` не показывается.

Тело `set-password`:

```json
{
  "password": "new-secret-password"
}
```

### Списки

- `GET /admin/lists`
- `GET /admin/lists/{list_id}`
- `POST /admin/lists/{list_id}/archive`
- `POST /admin/lists/{list_id}/restore`

Hard delete через admin API в этом релизе не добавлен. Безопасный вариант для эксплуатации - archive/restore.

### Приглашения

- `GET /admin/invites`
- `POST /admin/invites/{invite_id}/revoke`

Raw token полностью не показывается. Отозванное приглашение нельзя принять.

## Защита веб-форм

HTML-форма `/setup` использует CSRF token и проверку `Origin`/`Referer`. Мобильный API с Bearer token CSRF token не требует.

Rate limit хранится в памяти процесса и сбрасывается при перезапуске контейнера.

## Android-клиент

- Минимальная версия Android: Android 8.0 Oreo.
- Минимальный API: 26.
- Целевая версия сборки: Android 15, API 35.
