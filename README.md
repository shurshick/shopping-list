# Список покупок

Android-приложение и сервер синхронизации для совместных списков покупок. Сервер можно запустить на обычном Docker-сервере, VPS, домашнем Linux-сервере, NAS с Docker или через TrueNAS Custom App.

Проект рассчитан на самостоятельное размещение: ваши списки, пользователи и настройки хранятся на вашем сервере, а Android-приложение синхронизируется с ним при запуске и после изменений.

## Основные возможности

- регистрация и вход пользователей;
- обязательное создание администратора при первом запуске сервера;
- несколько списков покупок у одного пользователя;
- общий доступ к спискам между зарегистрированными пользователями;
- просмотр участников конкретного списка;
- приглашение в список по одноразовой ссылке;
- срок действия ссылки-приглашения, по умолчанию 7 дней;
- переименование, копирование, очистка и удаление списков;
- удаление списка у не-владельца отключает только его доступ;
- добавление, редактирование, отметка и удаление товаров;
- офлайн-очередь изменений для действий со списком и товарами;
- отмена удаления товара;
- разделение товаров на блоки "Купить" и "Куплено";
- очистка, возврат купленных товаров или полная очистка списка;
- справочник товаров с автопоиском при добавлении позиции;
- экран настроек Android-приложения с адресом сервера, темой оформления и выходом из аккаунта;
- светлая, тёмная и системная тема Android-приложения;
- окно "О приложении" с версией и ссылкой на проект;
- синхронизация при запуске приложения и после действий пользователя;
- веб-мастер настройки сервера по адресу `/setup`;
- автоматические миграции базы данных при запуске контейнера API;
- публичная конфигурация сервера по адресу `/server-config`;
- готовые Docker Compose-файлы для разных сценариев запуска.

## Требования

### Android

- Минимальная версия Android: **Android 8.0 Oreo**.
- Минимальный API: **26** (`minSdk = 26`).
- Целевая версия сборки: **Android 15**, API **35** (`targetSdk = 35`).
- Установка выполняется APK-файлом из раздела Releases.

### Сервер

- Docker и Docker Compose.
- Доступ к порту API, по умолчанию `8000`.
- Для доступа из интернета рекомендуется домен и HTTPS через reverse proxy.
- Для хранения данных используется PostgreSQL.

Сервер можно запустить несколькими способами:

- локальная сборка из исходников через `docker-compose.yml`;
- сборка backend напрямую из GitHub через `docker-compose.github-build.yml`;
- готовый GHCR-образ через `docker-compose.ghcr.yml`;
- TrueNAS 25.04 Custom App через `docker-compose.truenas-custom.yml` с готовым GHCR-образом.

## Состав проекта

- `backend` - серверная часть на FastAPI и PostgreSQL.
- `android` - Android-приложение на Kotlin и Jetpack Compose Material 3.
- `docker-compose.yml` - локальный запуск сервера со сборкой из текущих файлов.
- `docker-compose.github-build.yml` - запуск со сборкой backend напрямую из GitHub.
- `docker-compose.ghcr.yml` - запуск готового backend-образа из GitHub Container Registry.
- `docker-compose.truenas-custom.yml` - YAML для TrueNAS 25.04 Custom App без отдельного `.env`, использует готовый GHCR-образ API.
- `docs` - подробные инструкции по API и вариантам развертывания.

## Быстрый запуск через Docker Compose

```bash
git clone https://github.com/shurshick/shopping-list.git
cd shopping-list
cp .env.example .env
```

Заполните `.env`:

```env
POSTGRES_PASSWORD=long-random-postgres-password
JWT_SECRET=long-random-jwt-secret
API_PORT=8000
INVITE_TOKEN_HOURS=168
```

Запустите:

```bash
docker compose up -d --build
```

Откройте мастер настройки:

```text
http://server-ip:8000/setup
```

## Запуск через готовый Docker-образ

Если нужен запуск без сборки backend на сервере, используйте `docker-compose.ghcr.yml`.

Создайте `.env` рядом с compose-файлом:

```env
POSTGRES_PASSWORD=long-random-postgres-password
JWT_SECRET=long-random-jwt-secret
API_PORT=8000
APP_VERSION=latest
INVITE_TOKEN_HOURS=168
```

Запустите:

```bash
docker compose -f docker-compose.ghcr.yml up -d
```

Образ сервера публикуется в GitHub Container Registry:

```text
ghcr.io/shurshick/shopping-list-api
```

## Запуск со сборкой напрямую из GitHub

Этот вариант удобен, если на сервере можно собирать Docker-образ:

```bash
mkdir -p shopping-list
cd shopping-list
curl -L \
  -o docker-compose.yml \
  https://raw.githubusercontent.com/shurshick/shopping-list/main/docker-compose.github-build.yml
```

Создайте `.env`:

```env
POSTGRES_PASSWORD=long-random-postgres-password
JWT_SECRET=long-random-jwt-secret
API_PORT=8000
INVITE_TOKEN_HOURS=168
```

Запустите:

```bash
docker compose up -d --build
```

Подробности: [docs/github-deploy.md](docs/github-deploy.md).

## Запуск на TrueNAS

Для TrueNAS 25.04.2.6 можно использовать Custom App или Install via YAML:

1. Откройте в TrueNAS раздел приложений.
2. Выберите Custom App или Install via YAML.
3. Вставьте содержимое файла `docker-compose.truenas-custom.yml`.
4. Запустите приложение.
5. Откройте мастер настройки:

```text
http://truenas-ip:8000/setup
```

Подробная инструкция: [docs/truenas-custom-app.md](docs/truenas-custom-app.md).

## Первичная настройка сервера

После запуска откройте:

```text
http://server-ip:8000/setup
```

При первом запуске сервер обязательно попросит создать администратора. Нужно указать email и пароль администратора, название приложения, внешний HTTPS-адрес и режим регистрации новых пользователей.

Позже настройки можно менять на той же странице `/setup`, введя email и пароль администратора.

## Android-приложение

APK публикуется в разделе [Releases](https://github.com/shurshick/shopping-list/releases).

При первом запуске приложения укажите адрес сервера, например:

```text
https://shopping.example.com
```

После входа приложение покажет выбранный список покупок. Кнопка `+` в верхней панели создает новый список, шестеренка открывает меню текущего списка, а основное меню содержит выбор списка, справочник товаров, настройки и сведения о приложении.

В меню списка доступны участники, переименование, копирование, очистка купленных товаров, возврат купленных товаров, полная очистка, удаление, доступ по email и одноразовая ссылка-приглашение. Нажатие на название товара открывает редактирование названия и количества.

Если сервер временно недоступен, приложение сохраняет изменения в локальную очередь и отправляет их при следующей синхронизации. Внизу списка отображается количество действий, ожидающих отправки на сервер.

APK из публичных релизов подписывается постоянным ключом проекта. Если на телефоне установлена ранняя сборка и Android сообщает о конфликте пакетов, удалите старую сборку один раз и установите свежий APK. Последующие публичные версии должны устанавливаться поверх.

## Проверка Android-сборки

Android-сборка проверяется в GitHub Actions workflow `Android CI`. Workflow сам устанавливает JDK 17, использует Gradle cache, делает Gradle wrapper исполняемым и запускает:

```bash
./gradlew assembleDebug --stacktrace
```

Отсутствие Java/JDK в локальном окружении разработчика не считается ошибкой исходного кода. Если нужно собрать приложение локально, установите JDK 17 и запустите команду из папки `android`.

## Доступ из интернета

Для доступа извне рекомендуется использовать домен и HTTPS через reverse proxy: Nginx Proxy Manager, Caddy, Traefik или аналогичный инструмент.

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

Контейнер API применяет миграции базы данных автоматически перед запуском сервера.

## Полезные ссылки

- [Развертывание серверной части с GitHub](docs/github-deploy.md)
- [Развертывание через TrueNAS Custom App](docs/truenas-custom-app.md)
- [Описание API](docs/api.md)
- [Релизы Android APK и серверных архивов](https://github.com/shurshick/shopping-list/releases)
