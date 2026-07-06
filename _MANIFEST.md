# Akira Academy Minimal API Skeleton

Цель: вернуть рабочий Railway/API слой без старого болота `gpt/locks`, runtime patches, digest-rules и глобальных legacy state-файлов.

## Что взято из старых ZIP

Из старой рабочей Академии сохранены идеи:
- FastAPI entrypoint через `app.server:app`.
- `createSession`.
- `context`.
- `turn-contract`.
- required-files manifest/chunks.
- prompt preview / prompt builder как внутренний brief.
- session state overlay в `/data/sessions/<session_id>/state`.
- `applyTurnResult`.

## Что НЕ перенесено

Не перенесены:
- `gpt/locks/*`
- `engine/*`
- `app/*_runtime_patch.py`
- `app/*_hotfix.py`
- `state/knowledge_state.json`
- `state/relationships.json`
- глобальная загрузка всех персонажей/отношений/локаций/лора
- старый `compact.py` как монолит

## Что требуется в чистой репе

Этот пакет предполагает, что в репе уже есть:

```text
assembly/scene_assembly_chain.yaml
rules/scene_core.md
characters/index.yaml
locations/index.yaml
state/index.yaml
state/current_state.json
state/calendar_runtime.json
calendar/calendar_index.yaml
calendar/days/<current_date>.yaml
characters/<id>/main.yaml
state/character_memory/<id>.json
state/relationship_pairs/<a>__<b>.json
```

## Файлы пакета

```text
app/
  __init__.py
  server.py
  main.py
  models.py
  loader.py
  assembler.py
  prompt_builder.py

requirements.txt
Procfile
railway.json
```

## Главный принцип

Railway/API собирает `scene_packet`. GPT только пишет сцену.

Если персонаж не попал в `full_character_ids`, GPT не должен давать ему meaningful dialogue/action.
Если файл must-load не найден, `packet_status` не `ready`; сцену писать нельзя.

## Проверка после заливки

1. `/health`
2. `POST /api/v1/sessions`
3. `GET /api/v1/sessions/{session_id}/context`
4. `POST /api/v1/sessions/{session_id}/turn-contract`
5. `POST /api/v1/sessions/{session_id}/required-files-manifest`
6. `POST /api/v1/sessions/{session_id}/required-files-chunk?chunk_index=0`
7. `POST /api/v1/sessions/{session_id}/scene-packet`

