# Release Notes

Заметки для GitHub Releases теперь хранятся отдельно по версиям в каталоге `docs/releases/`.

Это сделано для того, чтобы описание каждого релиза содержало только изменения этого релиза и не разрасталось за счёт предыдущих версий.

## Где смотреть

- `docs/releases/v1.4.7.md`
- `docs/releases/v1.4.6.md`
- `docs/releases/v1.4.5.md`
- `docs/releases/v1.4.4.md`
- `docs/releases/v1.4.3.md`
- `docs/releases/v1.4.2.md`
- `docs/releases/v1.4.1.md`
- `docs/releases/v1.4.0.md`

## Правило для следующих релизов

Перед публикацией нового тега нужно создать отдельный файл `docs/releases/<tag>.md`.

Пример:

```text
docs/releases/v1.4.8.md
```

Workflow публикации GitHub Release берёт описание именно из этого файла.
