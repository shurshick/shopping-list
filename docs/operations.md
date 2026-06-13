# Эксплуатация сервера

Документ актуален для `v1.4.0`.

## Проверка состояния

После запуска или обновления проверьте:

```text
http://server-ip:8000/health/live
http://server-ip:8000/health/ready
```

`/health/live` отвечает, если процесс API запущен.  
`/health/ready` дополнительно проверяет БД и состояние миграций.

Административная диагностика доступна после входа администратором:

```text
http://server-ip:8000/admin
http://server-ip:8000/admin/system
```

## Обновление Docker image

Если используется готовый GHCR-образ:

```bash
docker compose -f docker-compose.ghcr.yml pull
docker compose -f docker-compose.ghcr.yml up -d
```

Если используется сборка из GitHub:

```bash
docker compose build --pull
docker compose up -d
```

Для TrueNAS Custom App обновите YAML, если в нем менялись параметры, и перезапустите приложение. Если image tag указан как `latest`, TrueNAS должен скачать свежий образ при обновлении/пересоздании контейнера.

## Backup перед обновлением

Рекомендуемый порядок:

1. Сделать снимок/backup PostgreSQL средствами сервера или NAS.
2. Дополнительно выполнить CLI backup приложения:

```bash
python -m app.cli backup --output backup.json
```

3. Обновить image.
4. Проверить `/health/ready`.
5. Проверить `/admin/system`.

## Миграции БД

Контейнер API в проекте запускает Alembic migration перед стартом приложения. Текущий статус можно проверить:

```bash
python -m app.cli db-status
```

В `/admin/system` отображаются:

- текущая revision БД;
- последняя известная head revision;
- статус `up-to-date` или `pending`;
- время запуска приложения.

Если миграция завершилась ошибкой:

1. Не удаляйте volume PostgreSQL.
2. Сделайте копию текущих данных.
3. Проверьте логи контейнера API.
4. Проверьте `python -m app.cli db-status`.
5. Обновляйте схему только после backup.

## Admin UI

Доступные разделы:

- `/admin/users` - пользователи, блокировка, разблокировка, смена пароля.
- `/admin/lists` - все списки, archive/restore.
- `/admin/invites` - invite-ссылки и отзыв активных приглашений.
- `/admin/system` - версия, БД, миграции, uptime, режим регистрации.
- `/admin/logs` - последние события приложения.
- `/admin/diagnostics` - сводка для диагностики.

Admin endpoints требуют Bearer token администратора. Веб-страница `/admin` позволяет войти и получить базовый статус.

## Metrics

`GET /metrics` возвращает безопасный JSON:

- количество пользователей;
- количество списков;
- количество товаров;
- активные приглашения;
- количество известных client operations;
- uptime;
- статус БД;
- версию backend.

Email, пароли, токены и секреты не возвращаются.

## Nginx Proxy Manager

Рекомендуемая схема:

- Forward Hostname/IP: IP сервера или имя контейнера API.
- Forward Port: `8000`.
- Websockets Support: не требуется.
- SSL Certificate: выпущенный Let's Encrypt или свой сертификат.
- Force SSL: включить.

При внешнем доступе используйте только HTTPS. Через обычный HTTP передаются email, пароль и Bearer token.

## Переменные окружения

Основные:

- `DATABASE_URL` - строка подключения backend к PostgreSQL.
- `POSTGRES_PASSWORD` - пароль PostgreSQL в compose-файлах.
- `JWT_SECRET` - секрет подписи токенов.
- `API_PORT` - внешний порт API, обычно `8000`.
- `INVITE_TOKEN_HOURS` - срок действия invite-ссылок.
- `APP_VERSION` - tag Docker image, например `latest` или `v1.4.0`.

Секретные переменные:

- `JWT_SECRET`
- `POSTGRES_PASSWORD`
- `DATABASE_URL`, если содержит пароль

Не публикуйте `.env`, пароли, токены и ключи подписи.
