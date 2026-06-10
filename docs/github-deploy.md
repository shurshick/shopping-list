# Развертывание серверной части с GitHub

На время тестирования репозиторий сделан публичным, поэтому серверную часть можно поднять без GitHub token.

## Вариант 1: без клонирования, сборка напрямую из GitHub

Этот вариант удобнее всего для проверки на TrueNAS: скачивается только compose-файл, а backend Docker сам соберет из публичного GitHub-репозитория.

```bash
mkdir -p shopping-list
cd shopping-list
curl -L \
  -o docker-compose.yml \
  https://raw.githubusercontent.com/shurshick/shopping-list-truenas/main/docker-compose.github-build.yml
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
http://truenas-ip:8000/setup
```

## Вариант 2: клонирование публичного репозитория

```bash
git clone https://github.com/shurshick/shopping-list-truenas.git
cd shopping-list-truenas
cp .env.example .env
```

Заполните `.env`, затем запустите:

```bash
docker compose up -d --build
```

## Вариант 3: готовый образ GHCR

Файл `docker-compose.ghcr.yml` запускает готовый образ:

```text
ghcr.io/shurshick/shopping-list-truenas-api:latest
```

Сейчас репозиторий публичный, но видимость GHCR-пакета может требовать отдельного переключения в настройках GitHub Packages. Если `docker compose pull` получает `403`, используйте вариант 1 или 2.

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
