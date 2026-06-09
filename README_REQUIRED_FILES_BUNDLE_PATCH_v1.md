# Required Files Bundle Patch v1

Цель: убрать проблему, когда `getSessionTurnContract` возвращает большой `required_files`, но GPT реально читает только 1–3 `main.yaml` и начинает сцену без `character.yaml`, `past.yaml`, locks и state.

Это не заплатка под Кира и не дублирование канона персонажей.

## Что добавлено

### 1. Backend endpoint

`GET /api/v1/sessions/{session_id}/required-files-bundle`

Возвращает:

- `session_id`
- `required_files`
- `loaded_files`: список `{path, content}`
- `missing_files`
- `loaded_count`
- `missing_count`

Логика:

- `state/*` читается из session directory, с fallback на seed/global state.
- `characters/*`, `canon/*`, `gpt/*`, `templates/*` читаются из общего project data.
- Список файлов берётся из того же `recommended_files_for_context`, что и `getSessionTurnContract`.

### 2. Prompt preview rule

`prompt_preview` теперь требует после `getSessionTurnContract` вызвать `getRequiredFilesBundle` перед сценой.

### 3. Gameplay gate rule

Добавлено общее правило: нельзя начинать сцену, если прочитаны только `main.yaml`, а required_files содержит `character.yaml`, `past.yaml`, locks/canon/state.

### 4. Actions schema

Добавлен файл:

`gpt/actions_schema_minimal_with_bundle_openapi_3_1.json`

Его можно вставить в Custom GPT Actions вместо текущей ручной схемы, чтобы появился action `getRequiredFilesBundle`.

## Файлы в патче

- `app/compact_context_patch.py`
- `app/prompt_builder.py`
- `gpt/locks/gameplay_response_gate.md`
- `gpt/actions_schema_minimal_with_bundle_openapi_3_1.json`

## Что НЕ трогается

- Railway config
- `app/server.py`
- character cards
- state files
- relationships/knowledge/story_lines
- Kir-specific canon

## Тестовое сообщение для GPT

```text
Технический режим. Не считать игровым ходом. Создай новую тестовую сессию. Вызови getSessionContext. Вызови getSessionTurnContract. Затем обязательно вызови getRequiredFilesBundle. Покажи только: session_id, loaded_count, missing_files и первые 20 loaded_files.path. Сцену не начинай. Ничего не сохраняй.
```

Ожидаемо: `loaded_count` должен быть примерно равен количеству `required_files`, а среди loaded paths должны быть не только `main.yaml`, но и `character.yaml`, `past.yaml`, locks и state файлы.
