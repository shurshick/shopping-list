# Запуск через TrueNAS 25.04 Custom App

Эта инструкция рассчитана на TrueNAS 25.04.2.6 и запуск через пользовательское приложение.

## Самый простой вариант

1. Откройте в TrueNAS раздел приложений.
2. Выберите Custom App или Install via YAML.
3. В поле YAML вставьте содержимое файла `docker-compose.truenas-custom.yml`.
4. Запустите приложение.
5. После запуска откройте:

```text
http://truenas-ip:8000/setup
```

6. Создайте администратора и укажите внешний HTTPS-адрес сервера.

## Что уже встроено в YAML

В `docker-compose.truenas-custom.yml` уже указаны:

- контейнер PostgreSQL;
- контейнер API;
- порт `8000`;
- переменные окружения сервера;
- срок действия ссылок-приглашений `INVITE_TOKEN_HOURS: 168`;
- volume для базы данных;
- готовый образ API `ghcr.io/shurshick/shopping-list-api:latest` из GitHub Container Registry.

Отдельный `.env` для этого варианта не нужен.

## Что желательно заменить перед постоянным использованием

Для быстрого запуска YAML можно использовать как есть. Перед постоянной эксплуатацией замените внутри YAML:

```yaml
POSTGRES_PASSWORD: shopping-list-postgres-password-change-me
JWT_SECRET: shopping-list-jwt-secret-change-me-before-real-use
```

Пароль PostgreSQL встречается в двух местах:

```yaml
POSTGRES_PASSWORD: ...
DATABASE_URL: postgresql+psycopg://shopping:...@postgres:5432/shopping
```

Значение должно совпадать в обоих местах.

Миграции базы данных применяются автоматически при запуске контейнера API.

## Обновление уже установленного приложения

Для обычного домашнего использования в YAML указан тег `latest`:

```yaml
image: ghcr.io/shurshick/shopping-list-api:latest
```

Так не нужно менять YAML при каждом новом релизе. Для обновления остановите и снова запустите приложение. Если TrueNAS предлагает обновить или заново скачать образ, выберите обновление образа.

Если нужно жёстко закрепиться на конкретной версии, замените `latest` на номер релиза:

```yaml
image: ghcr.io/shurshick/shopping-list-api:latest
```

Если версия в `/docs` не изменилась, удалите старый контейнер приложения в TrueNAS и создайте его заново с тем же volume PostgreSQL. Данные списков находятся в volume `postgres_data`, поэтому сам контейнер API можно пересоздавать.

## Если порт 8000 занят

В секции `ports` замените левую часть:

```yaml
ports:
  - "18000:8000"
```

После этого мастер будет доступен по адресу:

```text
http://truenas-ip:18000/setup
```
