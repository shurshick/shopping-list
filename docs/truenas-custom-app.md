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
- volume для базы данных;
- сборка backend напрямую из публичного GitHub-репозитория.

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
