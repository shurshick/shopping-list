# Архитектура проекта

Документ актуален для `v1.4.0`.

## Общая схема

Проект состоит из Android-приложения и backend API на FastAPI. Данные хранятся в PostgreSQL, миграции выполняются Alembic при запуске контейнера. Публикация серверного образа выполняется в GHCR, релизы собираются через GitHub Actions.

## Backend Layers

- `backend/app/main.py` собирает FastAPI-приложение и подключает router-слои.
- `backend/app/routers` содержит HTTP endpoints. Публичные URL сохранены без изменений.
- `backend/app/services` содержит бизнес-логику, которую нужно держать отдельно от HTTP-слоя. В `idempotency_service.py` находится replay `client_operation_id`.
- `backend/app/repositories` содержит доступ к данным, который не должен жить внутри router-функций. В `operations_repo.py` находится работа с таблицей `client_operations`.
- `backend/app/models.py` описывает SQLAlchemy-модели.
- `backend/app/schemas.py` описывает Pydantic request/response-контракты.
- `backend/app/setup.py`, `csrf.py`, `rate_limit.py`, `security.py`, `database.py`, `config.py` сохранены совместимыми с текущим Docker-развертыванием.

## Android Layers

- `MainActivity.kt` отвечает за Compose UI и навигацию между экранами.
- `ShoppingViewModel.kt` хранит состояние экрана и вызывает API/storage-слои.
- `data/ApiClient.kt`, `data/ShoppingApi.kt`, `data/ApiModels.kt` отвечают за HTTP API.
- `data/local/TokenStorage.kt` хранит токен в `EncryptedSharedPreferences`, переносит старый токен из обычных preferences и очищает токен при выходе.
- `data/local/AppPreferences.kt` хранит адрес сервера, тему, выбранный список, кеш списков и временные ID.
- `data/local/OfflineQueueStorage.kt` хранит JSON offline-очереди.
- `data/local/ProductCatalogStorage.kt` хранит справочник товаров.

## Offline Queue

Если сервер недоступен, Android сохраняет операцию в локальную очередь. При следующей синхронизации операции отправляются на сервер в исходном порядке, затем приложение получает свежий `/sync`.

Каждая новая операция получает UUID `client_operation_id` до первой сетевой попытки. Если сервер применил операцию, но телефон не получил ответ, повторная отправка использует тот же UUID.

## Client Operation Flow

1. Android создает UUID `client_operation_id`.
2. Клиент отправляет UUID в `X-Client-Operation-Id` или в теле create-запроса.
3. Backend проверяет таблицу `client_operations`.
4. Если операция уже есть, backend возвращает сохраненный response.
5. Если операции нет, backend выполняет действие, сохраняет response и только после этого завершает транзакцию.

Так replay не создает дубликаты списков, товаров или событий истории.

## Temp ID Mapping

Для `create_list` и `create_item` Android передает `temp_id`. Backend сохраняет `temp_id` и созданный `server_id` в `client_operations`. Это помогает сопоставлять локальные временные объекты с серверными объектами после replay.

## Security Model

- Авторизация мобильного API выполняется через Bearer JWT.
- Android хранит токен в `EncryptedSharedPreferences`.
- Release APK не подключает сетевой logging interceptor.
- `/auth/login`, `/auth/register` и `/setup` защищены базовым in-memory rate limit.
- `/setup` защищен CSRF-токеном и проверкой `Origin`/`Referer`.
- `/server-config` возвращает только публичные параметры и не раскрывает секреты.

## Setup/Admin Protection

Первый запуск требует создания администратора через `/setup`. После создания администратора повторный setup требует корректный email и пароль администратора. `/admin/status` и очистка общей истории доступны только пользователю с правами администратора.

## Docker Deployment

Поддерживаются прежние сценарии:

- локальная сборка через `docker-compose.yml`;
- сборка backend напрямую из GitHub;
- готовый GHCR-образ `ghcr.io/shurshick/shopping-list-api`;
- TrueNAS Custom App YAML.

В `v1.4.0` добавлены ops/admin endpoints, CLI-команды обслуживания и миграция `20260613_0004_ops_admin_fields`.
