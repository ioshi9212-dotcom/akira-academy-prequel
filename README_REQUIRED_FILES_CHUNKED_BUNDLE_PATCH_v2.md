# Required Files Chunked Bundle Patch v2

Purpose: fix ResponseTooLargeError from `/required-files-bundle` without adding character-specific canon duplicates.

## What changed

Updated `app/compact_context_patch.py`:

- keeps `/api/v1/sessions/{session_id}/required-files-bundle`;
- changes it to return a size-limited chunk instead of all required files at once;
- adds `/api/v1/sessions/{session_id}/required-files-manifest`;
- adds `/api/v1/sessions/{session_id}/required-files-chunk`;
- splits large files into parts using `part_index` / `parts_total`;
- returns `has_more` and `next_chunk_index` for sequential loading.

Updated `app/prompt_builder.py` and `gpt/locks/gameplay_response_gate.md` so the GPT knows the required flow:

1. `getSessionContext`
2. `getSessionTurnContract`
3. `getRequiredFilesManifest`
4. `getRequiredFilesChunk(chunk_index=0)`
5. repeat chunks until `has_more=false`
6. only then render the scene

## Why this is not a temporary character patch

No Kir/Akira/Livia facts are duplicated. The fix is generic: every required file is loaded through chunked bundle, so any character/canon/state file can be read without hitting Actions response-size limits.

## After deploy

In Custom GPT Actions, reload the live schema from Railway:

```txt
https://akira-academy-prequel-production.up.railway.app/openapi.json
```

## Test prompt

```txt
Технический режим. Не считать игровым ходом. Сцену не продолжать. Ничего не сохранять.

Создай новую тестовую сессию.
Вызови:
1. getSessionContext
2. getSessionTurnContract
3. getRequiredFilesManifest
4. getRequiredFilesChunk с chunk_index=0
5. если has_more=true, продолжай вызывать getRequiredFilesChunk с next_chunk_index, пока has_more=false.

Покажи только:
- session_id
- manifest.loaded_count
- manifest.missing_count
- manifest.chunks_total
- сколько chunk-вызовов сделано
- первые 25 уникальных loaded_files.path из загруженных chunks.
```
