# Backup и restore

Документ актуален для `v1.4.0`.

## Что важно знать

CLI backup приложения предназначен для удобного экспорта данных в JSON. Для серьезного обновления сервера лучше дополнительно делать backup PostgreSQL средствами Docker/NAS/хостинга.

По умолчанию JSON backup не содержит `password_hash`, JWT secret, пароль PostgreSQL и raw invite tokens.

## Создать backup без чувствительных данных

```bash
python -m app.cli backup --output backup.json
```

В backup входят:

- пользователи без `password_hash`;
- списки;
- товары;
- участники списков;
- настройки сервера без секретов;
- metadata приглашений без полного token.

## Создать backup с password hashes

```bash
python -m app.cli backup --output backup-with-auth.json --include-auth-hashes
```

Такой файл содержит чувствительные данные. Храните его как секрет: не отправляйте в чат, не коммитьте в git, не кладите в публичные папки.

## Проверить статус БД и миграций

```bash
python -m app.cli db-status
```

Пример ответа:

```json
{
  "current": "20260613_0004",
  "head": "20260613_0004",
  "status": "up-to-date"
}
```

## Restore

Базовое восстановление рассчитано на чистую БД:

```bash
python -m app.cli restore --input backup.json
```

Если БД не пустая, команда остановится. Это сделано специально, чтобы случайно не перезаписать рабочие данные.

Принудительное восстановление:

```bash
python -m app.cli restore --input backup.json --force
```

Используйте `--force` только после отдельного backup текущей БД.

## Ограничения restore

- Backup без `--include-auth-hashes` восстанавливает пользователей без рабочих паролей. После такого restore администратору нужно задать пароли заново.
- Raw invite tokens по умолчанию не сохраняются, поэтому старые invite-ссылки после restore из безопасного backup не восстанавливаются.
- `client_operations` в стандартный backup не включаются. Это не ломает данные списков, но replay старых offline-операций после restore может не знать о ранее обработанных UUID.

## Рекомендуемый сценарий перед обновлением

1. Остановите активные изменения, если это возможно.
2. Сделайте snapshot/backup PostgreSQL.
3. Выполните:

```bash
python -m app.cli backup --output backup-before-update.json --include-auth-hashes
```

4. Обновите Docker image.
5. Проверьте:

```text
/health/ready
/admin/system
```

6. Убедитесь, что Android-приложение синхронизируется.
