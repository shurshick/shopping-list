# Список покупок v1.4.0

Публичный релиз Android-приложения и серверной части для самостоятельного размещения.

## Изменения именно в v1.4.0

- Добавлены административные разделы backend для эксплуатации сервера: пользователи, списки, приглашения, система, логи и диагностика.
- Администратор может отключать и включать пользователей, а также задавать новый пароль пользователю.
- Нельзя отключить последнего активного администратора.
- Отключенный пользователь больше не может войти и использовать уже выданный токен.
- Добавлено архивирование и восстановление списков через admin API.
- Архивные списки не показываются обычному клиенту в `/sync`.
- Добавлен просмотр и отзыв invite-ссылок через admin API.
- Отозванное приглашение больше нельзя принять.
- Добавлены безопасные health endpoints: `/health/live`, `/health/ready`, `/health/db`.
- Добавлен безопасный `/metrics` в JSON-формате без email, паролей и секретов.
- Добавлены CLI-команды `backup`, `restore` и `db-status`.
- Backup по умолчанию не содержит `password_hash`, JWT-секреты и пароли БД.
- Добавлена видимость Alembic-миграций в CLI и `/admin/system`.
- Добавлена in-memory диагностика последних событий сервера.
- Добавлена миграция БД `20260613_0004_ops_admin_fields`.
- Backend tests расширены до 45 тестов.
- Android версия обновлена до `1.4.0`, `versionCode = 23`.

## Полный состав

- Android-приложение для совместных списков покупок.
- Сервер синхронизации на FastAPI и PostgreSQL.
- Docker/GHCR-образы для самостоятельного размещения.
- Первый запуск через `/setup` с обязательным созданием администратора.
- Админские разделы `/admin`, `/admin/status`, `/admin/users`, `/admin/lists`, `/admin/invites`, `/admin/system`, `/admin/logs`, `/admin/diagnostics`.
- Offline queue Android с идемпотентными операциями через `client_operation_id`.
- Health и metrics endpoints для проверки состояния сервера.
- CLI-команды обслуживания: backup, restore, db-status.

## Совместимость

- Старый `/health` сохранен.
- Старые Android-клиенты без `client_operation_id` продолжают работать.
- Offline queue не менялась в этом релизе.
- Роли участников списков `owner/editor/viewer` в этом релизе не добавлялись.
- WebSocket, push-уведомления и Redis не добавлялись.

## Android

- Минимальная версия Android: Android 8.0 Oreo.
- Минимальный API: 26.
- Целевая версия сборки: Android 15, API 35.

## Docker images

```text
ghcr.io/shurshick/shopping-list-api:latest
ghcr.io/shurshick/shopping-list-api:v1.4.0
```

## Проверки

```bash
python -m pytest backend/tests -q
cd android
./gradlew assembleDebug --stacktrace
./gradlew assembleRelease --stacktrace
git diff --check
```

## Файлы релиза

- `shopping-list-android-v1.4.0.apk` - Android-приложение для установки на телефон.
- `shopping-list-server-v1.4.0.zip` - серверная часть, Docker Compose-файлы и инструкции.
- `shopping-list-source-v1.4.0.zip` - полный архив исходного кода.

## Перед обновлением сервера

1. Сделайте backup БД или выполните `python -m app.cli backup --output backup.json` внутри окружения backend.
2. Обновите Docker image до `latest` или `v1.4.0`.
3. Перезапустите контейнер API.
4. Проверьте `/health/ready` и `/admin/system`.

Подробности: `docs/operations.md` и `docs/backup_restore.md`.
