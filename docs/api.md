# API сервера

Актуально для версии `v1.0.1`.

Базовый адрес: `https://your-domain.example`

## Авторизация

- `POST /auth/register` - зарегистрировать пользователя.
- `POST /auth/login` - войти в аккаунт.

Обычная регистрация пользователей доступна только после завершения мастера `/setup`.

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

`GET /sync`

Заголовок:

```text
Authorization: Bearer <token>
```

## Публичная конфигурация сервера

`GET /server-config`

Ответ:

```json
{
  "app_name": "Список покупок",
  "external_url": "https://shopping.example.com",
  "allow_registration": true,
  "setup_completed": true
}
```

## Списки

- `POST /lists` - создать список.
- `PATCH /lists/{list_id}` - переименовать список, доступно владельцу.
- `DELETE /lists/{list_id}` - удалить список. Для владельца удаляет список полностью, для участника убирает только его доступ.
- `POST /lists/{list_id}/copy` - создать копию списка для текущего пользователя.
- `DELETE /lists/{list_id}/items` - очистить список от всех позиций.
- `DELETE /lists/{list_id}/items/checked` - удалить только позиции, отмеченные как купленные.
- `GET /lists/{list_id}/members` - посмотреть участников списка.
- `POST /lists/{list_id}/share` - открыть доступ другому зарегистрированному пользователю.
- `POST /lists/{list_id}/invite` - создать одноразовую ссылку-приглашение.
- `POST /invites/{token}/accept` - принять одноразовое приглашение.
- `GET /join/{token}` - страница приглашения, которая открывает Android-приложение.

## Android-клиент

- Минимальная версия Android: Android 8.0 Oreo.
- Минимальный API: 26.
- Целевая версия сборки: Android 15, API 35.

## Товары

- `POST /lists/{list_id}/items` - добавить покупку.
- `PATCH /items/{item_id}` - изменить название, количество или отметку покупки.
- `DELETE /items/{item_id}` - удалить покупку.
