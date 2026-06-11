# Развертывание серверной части с GitHub и Docker

Серверную часть можно поднять напрямую из публичного GitHub-репозитория без GitHub token.

## Вариант 1: без клонирования, сборка напрямую из GitHub

Этот вариант удобен для обычного Docker-сервера, VPS, домашнего Linux-сервера или NAS: скачивается только compose-файл, а backend Docker сам соберет приложение из публичного GitHub-репозитория.

```bash
mkdir -p shopping-list
cd shopping-list
curl -L \
  -o docker-compose.yml \
  https://raw.githubusercontent.com/shurshick/shopping-list/main/docker-compose.github-build.yml
```

Создайте `.env` рядом с `docker-compose.yml`:

```env
POSTGRES_PASSWORD=long-random-password
JWT_SECRET=another-long-random-secret
API_PORT=8000
```

Запустите:

```bash
docker compose up -d --build
```

Откройте мастер настройки:

```text
http://server-ip:8000/setup
```

## Вариант 2: клонирование публичного репозитория

```bash
git clone https://github.com/shurshick/shopping-list.git
cd shopping-list
cp .env.example .env
```

Заполните `.env`, затем запустите:

```bash
docker compose up -d --build
```

## Вариант 3: готовый образ GHCR

Файл `docker-compose.ghcr.yml` запускает готовый образ:

```text
ghcr.io/shurshick/shopping-list-api:latest
```

Если `docker compose pull` получает `403`, проверьте видимость пакета в GitHub Packages или используйте вариант 1 или 2.

## Обновление

Для варианта без клонирования:

```bash
docker compose build --pull
docker compose up -d
```

Для клонированного репозитория:

```bash
git pull
docker compose up -d --build
```
