# Список покупок

Android-приложение и сервер синхронизации для общего списка покупок на своем TrueNAS или любом Docker-сервере.

Проект рассчитан на домашнее использование: сервер хранит списки, пользователей и настройки, а Android-приложение синхронизируется с ним при запуске и после изменений. Сервер можно развернуть напрямую из GitHub, через готовый Docker-образ или через YAML в TrueNAS 25.04 Custom App.

## Основные возможности

- регистрация и вход пользователей;
- обязательное создание администратора при первом запуске сервера;
- несколько списков покупок у одного пользователя;
- общий доступ к спискам между зарегистрированными пользователями;
- просмотр участников конкретного списка;
- приглашение в список по одноразовой ссылке;
- переименование, копирование, очистка и удаление списков;
- удаление списка у не-владельца отключает только его доступ;
- добавление, отметка и удаление товаров;
- справочник товаров с автопоиском при добавлении позиции;
- синхронизация при запуске приложения и после действий пользователя;
- веб-мастер настройки сервера по адресу `/setup`;
- публичная конфигурация сервера по адресу `/server-config`;
- готовые Docker Compose-файлы для разных сценариев запуска.

## Как это устроено

- `backend` - серверная часть на FastAPI и PostgreSQL.
- `android` - Android-приложение на Kotlin и Jetpack Compose Material 3.
- `docker-compose.yml` - локальный запуск сервера со сборкой из текущих файлов.
- `docker-compose.github-build.yml` - запуск со сборкой backend напрямую из GitHub.
- `docker-compose.truenas-custom.yml` - YAML для TrueNAS 25.04 Custom App без отдельного `.env`.
- `docker-compose.ghcr.yml` - запуск готового образа из GitHub Container Registry.
- `docs` - подробные инструкции по TrueNAS, GitHub-развертыванию и API.

## Быстрый запуск на TrueNAS 25.04

Самый простой вариант для TrueNAS 25.04.2.6:

1. Откройте в TrueNAS раздел приложений.
2. Выберите Custom App или Install via YAML.
3. Вставьте содержимое файла `docker-compose.truenas-custom.yml`.
4. Запустите приложение.
5. Откройте мастер настройки:

```text
http://truenas-ip:8000/setup
```

6. Создайте администратора и укажите внешний HTTPS-адрес сервера.

Подробная инструкция: [docs/truenas-custom-app.md](docs/truenas-custom-app.md).

## Запуск через готовый Docker-образ

Если нужен запуск без сборки backend на сервере, используйте `docker-compose.ghcr.yml`.

Создайте `.env` рядом с compose-файлом:

```env
POSTGRES_PASSWORD=long-random-postgres-password
JWT_SECRET=long-random-jwt-secret
API_PORT=8000
APP_VERSION=latest
```

Запустите:

```bash
docker compose -f docker-compose.ghcr.yml up -d
```

Образ сервера публикуется в GitHub Container Registry:

```text
ghcr.io/shurshick/shopping-list-truenas-api
```

## Запуск со сборкой напрямую из GitHub

Этот вариант удобен, если на сервере можно собирать Docker-образ:

```bash
mkdir -p shopping-list
cd shopping-list
curl -L \
  -o docker-compose.yml \
  https://raw.githubusercontent.com/shurshick/shopping-list-truenas/main/docker-compose.github-build.yml
```

Создайте `.env`:

```env
POSTGRES_PASSWORD=long-random-postgres-password
JWT_SECRET=long-random-jwt-secret
API_PORT=8000
```

Запустите:

```bash
docker compose up -d --build
```

Подробности: [docs/github-deploy.md](docs/github-deploy.md).

## Первичная настройка сервера

После запуска откройте:

```text
http://truenas-ip:8000/setup
```

При первом запуске сервер обязательно попросит создать администратора. Нужно указать email и пароль администратора, название приложения, внешний HTTPS-адрес и режим регистрации новых пользователей.

Позже настройки можно менять на той же странице `/setup`, введя email и пароль администратора.

## Android-приложение

APK публикуется в разделе [Releases](https://github.com/shurshick/shopping-list-truenas/releases).

При первом запуске приложения укажите адрес сервера, например:

```text
https://shopping.example.com
```

После входа приложение покажет выбранный список покупок. Кнопка `+` в верхней панели создает новый список, шестеренка открывает меню текущего списка, а основное меню содержит выбор списка и справочник товаров.

## Доступ из интернета

Для доступа извне рекомендуется использовать домен и HTTPS через reverse proxy на TrueNAS или другом сервере: Nginx Proxy Manager, Caddy, Traefik или аналогичный инструмент.

Не публикуйте API в интернет без HTTPS: приложение передает email, пароль и токены авторизации.

## Обновление

Если сервер запущен через готовый образ:

```bash
docker compose -f docker-compose.ghcr.yml pull
docker compose -f docker-compose.ghcr.yml up -d
```

Если сервер собирается из GitHub:

```bash
docker compose build --pull
docker compose up -d
```

Для TrueNAS Custom App обновите YAML при необходимости и перезапустите приложение.

## Полезные ссылки

- [Развертывание через TrueNAS Custom App](docs/truenas-custom-app.md)
- [Развертывание серверной части с GitHub](docs/github-deploy.md)
- [Описание API](docs/api.md)
- [Релизы Android APK и серверных архивов](https://github.com/shurshick/shopping-list-truenas/releases)
