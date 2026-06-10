# API сервера

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
- `POST /lists/{list_id}/share` - открыть доступ другому зарегистрированному пользователю.

## Товары

- `POST /lists/{list_id}/items` - добавить покупку.
- `PATCH /items/{item_id}` - изменить покупку или отметку.
- `DELETE /items/{item_id}` - удалить покупку.
